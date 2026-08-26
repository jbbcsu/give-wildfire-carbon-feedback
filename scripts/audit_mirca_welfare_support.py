#!/usr/bin/env python3
"""Audit analysis support using MIRCA area and a conditional production proxy.

The audit deliberately separates three concepts:

* harvested-area coverage is measured directly from fixed-vintage MIRCA area;
* production coverage is only a conditional proxy, MIRCA area multiplied by a
  same-vintage GDHY yield where that yield is observed; and
* revenue coverage is not computed without a pinned, spatially compatible
  price/value input.

This utility does not interpret an absent MIRCA row as independent evidence of
zero production.  It estimates no response, damage, or SCC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


CELL_KEYS = ["lat", "lon_360", "crop"]
OUTCOME_KEYS = ["harvest_year", *CELL_KEYS]
PANEL_REQUIRED = set(OUTCOME_KEYS + ["yield_observed"])
WEIGHT_REQUIRED = set(
    CELL_KEYS
    + [
        "irrigation",
        "area_share",
        "share_year",
        "irrigated_area_ha",
        "rainfed_area_ha",
        "total_area_ha",
        "production_eligible",
        "season_specific_share",
        "weight_source_id",
        "source_role",
    ]
)
BASELINE_YIELD_REQUIRED = {"lat", "lon_360", "yield_t_ha"}
EXPECTED_IRRIGATION = {"firr", "noirr"}
REQUIRED_SOURCE_ROLE = "independent_fixed_baseline_crop_area_share"


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported table {path}; use CSV or Parquet")


def require(frame: pd.DataFrame, fields: set[str], label: str) -> None:
    if missing := fields - set(frame.columns):
        raise ValueError(f"{label} missing fields {sorted(missing)}")


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _constant(frame: pd.DataFrame, column: str, label: str) -> object:
    if frame[column].isna().any():
        raise ValueError(f"{label} contains missing {column}")
    values = frame[column].unique()
    if len(values) != 1:
        raise ValueError(f"{label} must contain exactly one nonmissing {column}")
    return values[0]


def validate_and_collapse_weights(weights: pd.DataFrame) -> tuple[pd.DataFrame, int, str]:
    require(weights, WEIGHT_REQUIRED, "Weights")
    if weights.empty:
        raise ValueError("Weights are empty")
    if weights.duplicated(CELL_KEYS + ["irrigation"]).any():
        raise ValueError("Weights contain duplicate crop-grid-irrigation keys")
    share_year = int(_constant(weights, "share_year", "Weights"))
    source_id = str(_constant(weights, "weight_source_id", "Weights")).strip()
    if not source_id:
        raise ValueError("weight_source_id must be nonblank")
    roles = set(weights["source_role"].dropna().astype(str).str.strip().unique())
    if roles != {REQUIRED_SOURCE_ROLE}:
        raise ValueError(f"source_role must be {REQUIRED_SOURCE_ROLE}")
    for column in ("production_eligible", "season_specific_share"):
        if not weights[column].isin([True, False]).all():
            raise ValueError(f"{column} must be Boolean")
    ineligible = sorted(
        weights.loc[
            ~weights["production_eligible"].astype(bool)
            | ~weights["season_specific_share"].astype(bool),
            "crop",
        ]
        .astype(str)
        .unique()
    )
    if ineligible:
        raise ValueError(
            "Welfare-support audit accepts only production-eligible, "
            f"season-specific crop mappings; rejected {ineligible}"
        )

    numeric_columns = [
        "lat",
        "lon_360",
        "area_share",
        "irrigated_area_ha",
        "rainfed_area_ha",
        "total_area_ha",
    ]
    numeric = weights[numeric_columns].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Weight coordinates, shares, and areas must be finite numeric values")
    weights = weights.copy()
    weights[numeric_columns] = numeric
    if ((weights["lat"] < -90) | (weights["lat"] > 90)).any():
        raise ValueError("Weight latitude is outside [-90, 90]")
    if ((weights["lon_360"] < 0) | (weights["lon_360"] >= 360)).any():
        raise ValueError("Weight lon_360 is outside [0, 360)")
    if ((weights["area_share"] < 0) | (weights["area_share"] > 1)).any():
        raise ValueError("area_share must be between zero and one")
    for column in ("irrigated_area_ha", "rainfed_area_ha", "total_area_ha"):
        if (weights[column] < 0).any():
            raise ValueError(f"{column} must be nonnegative")
    if (weights["total_area_ha"] <= 0).any():
        raise ValueError("Every exported weight row must have positive total_area_ha")
    if not np.allclose(
        weights["irrigated_area_ha"] + weights["rainfed_area_ha"],
        weights["total_area_ha"],
        rtol=0.0,
        atol=1e-7,
    ):
        raise ValueError("irrigated_area_ha plus rainfed_area_ha must equal total_area_ha")

    groups = weights.groupby(CELL_KEYS, sort=False, dropna=False)
    labels = groups["irrigation"].agg(lambda values: set(values.astype(str)))
    if not labels.map(lambda value: value == EXPECTED_IRRIGATION).all():
        raise ValueError("Every crop-grid cell must contain firr and noirr weight rows")
    for column in ("irrigated_area_ha", "rainfed_area_ha", "total_area_ha"):
        if (groups[column].nunique(dropna=False) != 1).any():
            raise ValueError(f"{column} must be identical across regime rows in each cell")
    shares = groups["area_share"].sum()
    if not np.allclose(shares.to_numpy(dtype=float), 1.0, rtol=0.0, atol=1e-10):
        raise ValueError("Area shares must sum to one in every crop-grid cell")
    expected_share = np.where(
        weights["irrigation"].eq("firr"),
        weights["irrigated_area_ha"] / weights["total_area_ha"],
        weights["rainfed_area_ha"] / weights["total_area_ha"],
    )
    if not np.allclose(
        weights["area_share"].to_numpy(dtype=float), expected_share, rtol=0.0, atol=1e-10
    ):
        raise ValueError("area_share does not equal its regime area divided by total area")

    cells = groups[
        ["irrigated_area_ha", "rainfed_area_ha", "total_area_ha"]
    ].first().reset_index()
    return cells, share_year, source_id


def validate_and_collapse_panels(panels: list[pd.DataFrame]) -> pd.DataFrame:
    if not panels:
        raise ValueError("Supply at least one outcome panel")
    frames: list[pd.DataFrame] = []
    crops_seen: set[str] = set()
    for index, panel in enumerate(panels):
        label = f"Panel {index + 1}"
        require(panel, PANEL_REQUIRED, label)
        panel = panel.copy()
        for column in ("harvest_year", "lat", "lon_360"):
            panel[column] = pd.to_numeric(panel[column], errors="coerce")
        if not np.isfinite(panel[["harvest_year", "lat", "lon_360"]].to_numpy(dtype=float)).all():
            raise ValueError(f"{label} keys must be finite numeric values")
        if not np.equal(panel["harvest_year"], np.floor(panel["harvest_year"])).all():
            raise ValueError(f"{label} harvest_year must be integer valued")
        panel["harvest_year"] = panel["harvest_year"].astype(int)
        if ((panel["lat"] < -90) | (panel["lat"] > 90)).any():
            raise ValueError(f"{label} latitude is outside [-90, 90]")
        if ((panel["lon_360"] < 0) | (panel["lon_360"] >= 360)).any():
            raise ValueError(f"{label} lon_360 is outside [0, 360)")
        if panel["crop"].isna().any() or panel["crop"].astype(str).str.strip().eq("").any():
            raise ValueError(f"{label} crop must be nonblank")
        panel["crop"] = panel["crop"].astype(str).str.strip()
        if not panel["yield_observed"].isin([True, False]).all():
            raise ValueError(f"{label} yield_observed must be Boolean")
        panel_crops = set(panel["crop"].dropna().astype(str).unique())
        if not panel_crops:
            raise ValueError(f"{label} has no crop")
        overlap = crops_seen & panel_crops
        if overlap:
            raise ValueError(f"Crops occur in more than one supplied panel: {sorted(overlap)}")
        crops_seen |= panel_crops
        statuses = panel.groupby(OUTCOME_KEYS, dropna=False)["yield_observed"].nunique(dropna=False)
        if (statuses != 1).any():
            raise ValueError(f"{label} has inconsistent outcome missingness across exposure rows")
        collapsed = (
            panel.groupby(OUTCOME_KEYS, sort=False, as_index=False, dropna=False)
            .agg(yield_observed=("yield_observed", "first"))
        )
        frames.append(collapsed)
    return pd.concat(frames, ignore_index=True)


def validate_baseline_yield(frame: pd.DataFrame, crop: str) -> pd.DataFrame:
    require(frame, BASELINE_YIELD_REQUIRED, f"Baseline yield for {crop}")
    output = frame[["lat", "lon_360", "yield_t_ha"]].copy()
    if output.duplicated(["lat", "lon_360"]).any():
        raise ValueError(f"Baseline yield for {crop} has duplicate grid cells")
    for column in ("lat", "lon_360", "yield_t_ha"):
        output[column] = pd.to_numeric(output[column], errors="coerce")
    coordinates = output[["lat", "lon_360"]]
    if not np.isfinite(coordinates.to_numpy(dtype=float)).all():
        raise ValueError(f"Baseline yield for {crop} contains invalid coordinates")
    if ((output["lat"] < -90) | (output["lat"] > 90)).any():
        raise ValueError(f"Baseline yield for {crop} has latitude outside [-90, 90]")
    if ((output["lon_360"] < 0) | (output["lon_360"] >= 360)).any():
        raise ValueError(f"Baseline yield for {crop} has lon_360 outside [0, 360)")
    finite_yield = output["yield_t_ha"].dropna()
    if not np.isfinite(finite_yield.to_numpy(dtype=float)).all():
        raise ValueError(f"Baseline yield for {crop} contains nonfinite values")
    if (finite_yield < 0).any():
        raise ValueError(f"Baseline yield for {crop} contains negative values")
    return output


def read_gdhy_yield(path: Path) -> pd.DataFrame:
    with xr.open_dataset(path, engine="h5netcdf") as dataset:
        if set(dataset.dims) != {"lat", "lon"} or len(dataset.data_vars) != 1:
            raise ValueError(f"Unexpected GDHY grid schema in {path}")
        if dataset.sizes["lat"] != 360 or dataset.sizes["lon"] != 720:
            raise ValueError(f"Unexpected GDHY 0.5-degree grid shape in {path}")
        expected_lat = -89.75 + 0.5 * np.arange(360, dtype=float)
        expected_lon = 0.25 + 0.5 * np.arange(720, dtype=float)
        if not np.allclose(dataset["lat"].values, expected_lat, rtol=0.0, atol=1e-9):
            raise ValueError(f"Unexpected GDHY latitude coordinates in {path}")
        if not np.allclose(dataset["lon"].values, expected_lon, rtol=0.0, atol=1e-9):
            raise ValueError(f"Unexpected GDHY longitude coordinates in {path}")
        variable = next(iter(dataset.data_vars))
        frame = dataset[variable].to_dataframe(name="yield_t_ha").reset_index()
    frame["lon_360"] = frame["lon"] % 360.0
    return frame[["lat", "lon_360", "yield_t_ha"]]


def audit_support(
    weights: pd.DataFrame,
    panels: list[pd.DataFrame],
    baseline_yields: dict[str, pd.DataFrame],
    baseline_year: int,
    baseline_records: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    outcomes = validate_and_collapse_panels(panels)
    panel_crops = set(outcomes["crop"].astype(str).unique())
    require(weights, {"crop"}, "Weights")
    selected_weights = weights.loc[weights["crop"].astype(str).isin(panel_crops)].copy()
    if selected_weights.empty:
        raise ValueError(f"No MIRCA weights for panel crops {sorted(panel_crops)}")
    cells, share_year, source_id = validate_and_collapse_weights(selected_weights)
    if int(baseline_year) != share_year:
        raise ValueError("baseline_year must equal the fixed MIRCA share_year")
    weight_crops = set(cells["crop"].astype(str).unique())
    if missing := panel_crops - weight_crops:
        raise ValueError(f"No eligible MIRCA weights for panel crops {sorted(missing)}")
    if set(baseline_yields) != panel_crops:
        raise ValueError(
            "Baseline-yield inputs must match panel crops exactly; "
            f"expected {sorted(panel_crops)}, received {sorted(baseline_yields)}"
        )

    summaries: list[dict[str, object]] = []
    for crop in sorted(panel_crops):
        crop_cells = cells.loc[cells["crop"].astype(str).eq(crop)].copy()
        crop_outcomes = outcomes.loc[outcomes["crop"].astype(str).eq(crop)].copy()
        observed = crop_outcomes.loc[crop_outcomes["yield_observed"]].copy()
        if observed.empty:
            raise ValueError(f"Panel contains no observed outcomes for {crop}")
        observed_cells = observed[CELL_KEYS].drop_duplicates()
        observed_years = observed[OUTCOME_KEYS].drop_duplicates()
        ordered_observed = observed_years.sort_values(CELL_KEYS + ["harvest_year"]).copy()
        ordered_observed["previous_observed_year"] = ordered_observed.groupby(
            CELL_KEYS, sort=False, dropna=False
        )["harvest_year"].shift()
        consecutive_pairs = ordered_observed.loc[
            ordered_observed["harvest_year"]
            - ordered_observed["previous_observed_year"]
            == 1
        ].copy()
        consecutive_pair_cells = consecutive_pairs[CELL_KEYS].drop_duplicates()
        supported_keys = crop_cells[CELL_KEYS]
        cell_match = observed_cells.merge(
            supported_keys.assign(mirca_supported=True),
            on=CELL_KEYS,
            how="left",
            validate="one_to_one",
        )
        year_match = observed_years.merge(
            supported_keys.assign(mirca_supported=True),
            on=CELL_KEYS,
            how="left",
            validate="many_to_one",
        )
        supported_observed_cells = cell_match.loc[cell_match["mirca_supported"].eq(True), CELL_KEYS]
        supported_pair_cells = consecutive_pair_cells.merge(
            supported_keys, on=CELL_KEYS, how="inner", validate="one_to_one"
        )

        area_support = crop_cells.merge(
            supported_observed_cells.assign(panel_observed_any_year=True),
            on=CELL_KEYS,
            how="left",
            validate="one_to_one",
        )
        area_support = area_support.merge(
            supported_pair_cells.assign(panel_consecutive_pair=True),
            on=CELL_KEYS,
            how="left",
            validate="one_to_one",
        )
        in_panel = area_support["panel_observed_any_year"].eq(True)
        in_pair = area_support["panel_consecutive_pair"].eq(True)
        total_area = float(area_support["total_area_ha"].sum())
        total_irrigated = float(area_support["irrigated_area_ha"].sum())
        total_rainfed = float(area_support["rainfed_area_ha"].sum())
        panel_area = float(area_support.loc[in_panel, "total_area_ha"].sum())
        panel_irrigated = float(area_support.loc[in_panel, "irrigated_area_ha"].sum())
        panel_rainfed = float(area_support.loc[in_panel, "rainfed_area_ha"].sum())
        pair_area = float(area_support.loc[in_pair, "total_area_ha"].sum())
        pair_irrigated = float(area_support.loc[in_pair, "irrigated_area_ha"].sum())
        pair_rainfed = float(area_support.loc[in_pair, "rainfed_area_ha"].sum())

        baseline = validate_baseline_yield(baseline_yields[crop], crop)
        production = area_support.merge(
            baseline, on=["lat", "lon_360"], how="left", validate="one_to_one"
        )
        known_yield = production["yield_t_ha"].notna()
        known_area = float(production.loc[known_yield, "total_area_ha"].sum())
        production.loc[known_yield, "production_proxy_tonnes"] = (
            production.loc[known_yield, "total_area_ha"]
            * production.loc[known_yield, "yield_t_ha"]
        )
        conditional_production = float(
            production.loc[known_yield, "production_proxy_tonnes"].sum()
        )
        production_in_panel = float(
            production.loc[
                known_yield & production["panel_observed_any_year"].eq(True),
                "production_proxy_tonnes",
            ].sum()
        )
        production_in_pair = float(
            production.loc[
                known_yield & production["panel_consecutive_pair"].eq(True),
                "production_proxy_tonnes",
            ].sum()
        )
        baseline_complete = bool(np.isclose(known_area, total_area, rtol=0.0, atol=1e-7))

        summaries.append(
            {
                "crop": crop,
                "panel_year_min": int(observed["harvest_year"].min()),
                "panel_year_max": int(observed["harvest_year"].max()),
                "observed_cells": int(len(observed_cells)),
                "matched_mirca_cells": int(cell_match["mirca_supported"].eq(True).sum()),
                "unmatched_observed_cells": int(cell_match["mirca_supported"].isna().sum()),
                "observed_cell_count_coverage_fraction": float(
                    cell_match["mirca_supported"].eq(True).mean()
                ),
                "observed_crop_grid_years": int(len(observed_years)),
                "matched_crop_grid_years": int(year_match["mirca_supported"].eq(True).sum()),
                "crop_grid_year_count_coverage_fraction": float(
                    year_match["mirca_supported"].eq(True).mean()
                ),
                "consecutive_observed_pairs": int(len(consecutive_pairs)),
                "consecutive_pairs_with_mirca_support": int(
                    consecutive_pairs.merge(
                        supported_keys, on=CELL_KEYS, how="inner", validate="many_to_one"
                    ).shape[0]
                ),
                "cells_with_consecutive_observed_pair": int(len(consecutive_pair_cells)),
                "consecutive_pair_cells_with_mirca_support": int(len(supported_pair_cells)),
                "harvested_area": {
                    "source": "MIRCA fixed-vintage positive harvested-area cells",
                    "global_mirca_area_ha": total_area,
                    "area_in_panel_observed_cells_ha": panel_area,
                    "area_outside_panel_observed_cells_ha": total_area - panel_area,
                    "coverage_fraction": panel_area / total_area,
                    "global_mirca_irrigated_area_ha": total_irrigated,
                    "irrigated_area_in_panel_observed_cells_ha": panel_irrigated,
                    "irrigated_area_coverage_fraction": (
                        panel_irrigated / total_irrigated if total_irrigated > 0 else None
                    ),
                    "global_mirca_rainfed_area_ha": total_rainfed,
                    "rainfed_area_in_panel_observed_cells_ha": panel_rainfed,
                    "rainfed_area_coverage_fraction": (
                        panel_rainfed / total_rainfed if total_rainfed > 0 else None
                    ),
                    "area_in_consecutive_pair_cells_ha": pair_area,
                    "consecutive_pair_area_coverage_fraction": pair_area / total_area,
                    "irrigated_area_in_consecutive_pair_cells_ha": pair_irrigated,
                    "consecutive_pair_irrigated_area_coverage_fraction": (
                        pair_irrigated / total_irrigated if total_irrigated > 0 else None
                    ),
                    "rainfed_area_in_consecutive_pair_cells_ha": pair_rainfed,
                    "consecutive_pair_rainfed_area_coverage_fraction": (
                        pair_rainfed / total_rainfed if total_rainfed > 0 else None
                    ),
                    "unmatched_observed_cell_interpretation": (
                        "No positive MIRCA harvested-area row exists for these GDHY-observed "
                        "cells. This is a source-support mismatch, not independent proof of "
                        "zero production or value."
                    ),
                },
                "conditional_production_proxy": {
                    "definition": (
                        "MIRCA total harvested area multiplied by same-vintage GDHY yield "
                        "where GDHY yield is observed"
                    ),
                    "is_observed_production": False,
                    "baseline_year": int(baseline_year),
                    "mirca_cells_with_baseline_yield": int(known_yield.sum()),
                    "mirca_area_with_baseline_yield_ha": known_area,
                    "mirca_area_with_baseline_yield_fraction": known_area / total_area,
                    "mirca_area_without_baseline_yield_ha": total_area - known_area,
                    "conditional_total_tonnes": conditional_production,
                    "conditional_tonnes_in_panel_observed_cells": production_in_panel,
                    "conditional_coverage_fraction": (
                        production_in_panel / conditional_production
                        if conditional_production > 0
                        else None
                    ),
                    "conditional_tonnes_in_consecutive_pair_cells": production_in_pair,
                    "conditional_consecutive_pair_coverage_fraction": (
                        production_in_pair / conditional_production
                        if conditional_production > 0
                        else None
                    ),
                    "proxy_defined_for_all_positive_mirca_area": baseline_complete,
                    "global_observed_production_coverage_identified": False,
                    "interpretation": (
                        "The production fraction is conditional on cells with a GDHY baseline "
                        "yield. It is not a global production-coverage fraction when positive "
                        "MIRCA area lacks GDHY yield."
                    ),
                    "input_record": (baseline_records or {}).get(crop),
                },
                "revenue_coverage": {
                    "status": "not_computed",
                    "identified": False,
                    "blocker": (
                        "No pinned, spatially compatible crop price or production-value input "
                        "and geographic price crosswalk were supplied. A crop-wide scalar price "
                        "would only reproduce the within-crop production-proxy fraction."
                    ),
                },
            }
        )

    return {
        "schema_version": 1,
        "role": "welfare_support_diagnostic_not_response_damage_or_scc",
        "weight_source_id": source_id,
        "share_year": share_year,
        "baseline_yield_year": int(baseline_year),
        "crop_summaries": summaries,
        "cross_crop_aggregation": "prohibited_without crop-value weights",
        "missing_weight_rule": "exclude without infill or renormalization",
        "limitations": [
            "MIRCA harvested area is the only direct welfare-scale weight in this audit.",
            "The production calculation is a constructed MIRCA-area-times-GDHY-yield proxy.",
            "Missing GDHY baseline yields prevent an unconditional global production fraction.",
            "Revenue/value coverage is unidentified without a pinned compatible value input.",
        ],
        "scc_authorized": False,
    }


def parse_crop_paths(values: list[str]) -> dict[str, Path]:
    output: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--baseline-yield must have form crop=path")
        crop, filename = value.split("=", 1)
        crop = crop.strip()
        filename = filename.strip()
        if not crop or not filename or crop in output:
            raise ValueError("--baseline-yield requires unique, nonblank crop=path entries")
        output[crop] = Path(filename)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--panel", action="append", required=True)
    parser.add_argument("--baseline-yield", action="append", required=True, help="crop=GDHY_file")
    parser.add_argument("--baseline-year", required=True, type=int)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    crop_paths = parse_crop_paths(args.baseline_yield)
    missing_paths = [str(path) for path in crop_paths.values() if not path.is_file()]
    if missing_paths:
        raise FileNotFoundError(f"Missing baseline-yield files: {missing_paths}")
    baseline_records = {
        crop: {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha512": sha512(path),
        }
        for crop, path in crop_paths.items()
    }
    audit = audit_support(
        read_table(Path(args.weights)),
        [read_table(Path(path)) for path in args.panel],
        {crop: read_gdhy_yield(path) for crop, path in crop_paths.items()},
        args.baseline_year,
        baseline_records,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
