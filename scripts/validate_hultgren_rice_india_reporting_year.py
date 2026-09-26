#!/usr/bin/env python3
"""Validate the rice India reporting-year correction against inputs and weather."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import calendar_months_for_report_year
from src.hultgren_rice_weather import build_rice_weather_basis_from_daily

KEYS = ["harvest_year", "native_lat_index", "native_lon_index"]
WEATHER = [
    "gdd", "kdd", "tmin",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def load_weather_sources(records: list[dict[str, str]], targets: pd.DataFrame) -> tuple[pd.DatetimeIndex, dict[str, np.ndarray]]:
    paths = {name: [] for name in ("pr", "tasmin", "tasmax")}
    for record in records:
        path = Path(record["path"])
        require(digest(path) == record["sha256"], f"weather hash differs: {path}")
        paths[record["variable"]].append(path)
    rows = xr.DataArray(targets.native_lat_index.to_numpy(dtype=np.int64), dims="cell")
    cols = xr.DataArray(targets.native_lon_index.to_numpy(dtype=np.int64), dims="cell")
    dates: dict[str, list[pd.DatetimeIndex]] = {name: [] for name in paths}
    values: dict[str, list[np.ndarray]] = {name: [] for name in paths}
    for variable, variable_paths in paths.items():
        for path in variable_paths:
            with xr.open_dataset(path, engine="h5netcdf", decode_times=True, cache=False) as dataset:
                current = pd.DatetimeIndex(dataset.time.values).normalize()
                dates[variable].append(current)
                values[variable].append(
                    np.asarray(dataset[variable].isel(lat=rows, lon=cols).values, dtype=np.float64)
                )
    combined_dates = {name: parts[0].append(parts[1:]) for name, parts in dates.items()}
    require(combined_dates["pr"].equals(combined_dates["tasmin"]), "pr/tasmin dates differ")
    require(combined_dates["pr"].equals(combined_dates["tasmax"]), "pr/tasmax dates differ")
    arrays = {name: np.concatenate(parts, axis=0) for name, parts in values.items()}
    arrays["pr"] = np.maximum(arrays["pr"] * 86_400.0, 0.0)
    arrays["tasmin"] -= 273.15
    arrays["tasmax"] -= 273.15
    return combined_dates["pr"], arrays


def direct_basis(
    row: pd.Series,
    target_position: int,
    dates: pd.DatetimeIndex,
    arrays: dict[str, np.ndarray],
) -> dict[str, float]:
    lookup = {value.date(): position for position, value in enumerate(dates)}
    records = []
    for year, month in calendar_months_for_report_year(
        int(row.harvest_year), int(row.plant_month), int(row.harvest_month), "IND"
    ):
        start = pd.Timestamp(year=year, month=month, day=1)
        for stamp in pd.date_range(start, start + pd.offsets.MonthEnd(0), freq="D"):
            position = lookup[stamp.date()]
            records.append(
                (
                    date(stamp.year, stamp.month, stamp.day),
                    arrays["pr"][position, target_position],
                    arrays["tasmin"][position, target_position],
                    arrays["tasmax"][position, target_position],
                )
            )
    result = build_rice_weather_basis_from_daily(
        records,
        report_year=int(row.harvest_year),
        plant_month=int(row.plant_month),
        harvest_month=int(row.harvest_month),
        iso="IND",
    )
    return {
        "gdd": result.gdd, "kdd": result.kdd, "tmin": result.tmin,
        **{f"prcp_poly_1_bin{i}": value for i, value in enumerate(result.prcp_poly_1_bins, 1)},
        **{f"prcp_poly_2_bin{i}": value for i, value in enumerate(result.prcp_poly_2_bins, 1)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--correction-receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "fresh output required")
    correction = json.loads(args.correction_receipt.read_text(encoding="utf-8"))
    require(
        correction["status"] == "india_reporting_year_exception_applied_to_verified_cells",
        "correction build failed",
    )
    diagnostics_path = Path(correction["cell_diagnostics"]["path"])
    require(digest(diagnostics_path) == correction["cell_diagnostics"]["sha256"], "diagnostic hash differs")
    diagnostics = pd.read_parquet(diagnostics_path)
    require(len(diagnostics) == correction["counts"]["corrected_cell_years"], "diagnostic row count differs")

    original_target_rows = []
    corrected_paths: dict[str, list[Path]] = {"ri1_noirr": [], "ri1_firr": []}
    unchanged_rows = 0
    changed_rows = 0
    total_rows = 0
    max_unchanged_error = 0.0
    for record in correction["outputs"]:
        original_path = Path(record["input"]["path"])
        corrected_path = Path(record["output"]["path"])
        require(digest(original_path) == record["input"]["sha256"], "input hash differs")
        require(digest(corrected_path) == record["output"]["sha256"], "output hash differs")
        original = pd.read_parquet(original_path)
        corrected = pd.read_parquet(corrected_path)
        require(len(original) == len(corrected) and original[KEYS].equals(corrected[KEYS]), "row keys differ")
        applied = corrected.india_reporting_year_exception_applied.to_numpy(dtype=bool)
        difference = corrected[WEATHER].to_numpy(dtype=np.float64) - original[WEATHER].to_numpy(dtype=np.float64)
        if np.any(~applied):
            max_unchanged_error = max(max_unchanged_error, float(np.max(np.abs(difference[~applied]))))
        require(np.all(difference[~applied] == 0.0), "unflagged weather row changed")
        require(int(applied.sum()) == record["corrected_cell_years"], "flagged count differs")
        unchanged_rows += int((~applied).sum())
        changed_rows += int(applied.sum())
        total_rows += len(corrected)
        branch = record["calendar_branch"]
        original_target_rows.append(original.loc[applied, KEYS + WEATHER].assign(calendar_branch=branch))
        corrected_paths[branch].append(corrected_path)
        del original, corrected, difference
    require(changed_rows == len(diagnostics), "total changed rows differ")

    original_all = pd.concat(original_target_rows, ignore_index=True)
    temporal = diagnostics.merge(
        original_all,
        left_on=["calendar_branch", "native_lat_index", "native_lon_index", "harvest_year"],
        right_on=["calendar_branch", "native_lat_index", "native_lon_index", "harvest_year"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_same_year_original"),
    )
    next_year = original_all.copy()
    next_year["harvest_year"] -= 1
    temporal = temporal.merge(
        next_year,
        on=["calendar_branch", "native_lat_index", "native_lon_index", "harvest_year"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_next_generic_year"),
    )
    has_next = temporal["gdd_next_generic_year"].notna()
    max_temporal_error = 0.0
    for column in WEATHER:
        error = np.abs(
            temporal.loc[has_next, f"corrected_{column}"].to_numpy(dtype=np.float64)
            - temporal.loc[has_next, f"{column}_next_generic_year"].to_numpy(dtype=np.float64)
        )
        if len(error):
            max_temporal_error = max(max_temporal_error, float(error.max()))
    require(max_temporal_error <= 1e-10, "India correction does not equal next generic crop year")

    target_columns = ["native_lat_index", "native_lon_index", "plant_month", "harvest_month"]
    targets = diagnostics[target_columns].drop_duplicates().sort_values(target_columns[:2]).reset_index(drop=True)
    require(len(targets) == correction["country_rule_audit"]["verified_india_reporting_year_rule_sensitive_cells"], "target count differs")
    dates, arrays = load_weather_sources(correction["weather_sources"], targets)
    target_lookup = {
        (int(row.native_lat_index), int(row.native_lon_index)): position
        for position, row in targets.iterrows()
    }
    max_direct_error = 0.0
    for _, row in diagnostics.iterrows():
        cell = (int(row.native_lat_index), int(row.native_lon_index))
        direct = direct_basis(row, target_lookup[cell], dates, arrays)
        for column in WEATHER:
            max_direct_error = max(max_direct_error, abs(float(row[f"corrected_{column}"]) - direct[column]))
    require(max_direct_error <= 1e-7, "direct India daily reconstruction differs")

    require(len(corrected_paths["ri1_noirr"]) == len(corrected_paths["ri1_firr"]), "corrected branch file counts differ")
    maximum_branch_error = 0.0
    for noirr_path, firr_path in zip(corrected_paths["ri1_noirr"], corrected_paths["ri1_firr"], strict=True):
        noirr = pd.read_parquet(noirr_path, columns=KEYS + WEATHER).sort_values(KEYS).reset_index(drop=True)
        firr = pd.read_parquet(firr_path, columns=KEYS + WEATHER).sort_values(KEYS).reset_index(drop=True)
        require(noirr[KEYS].equals(firr[KEYS]), "corrected branch support differs")
        maximum_branch_error = max(
            maximum_branch_error,
            float(np.max(np.abs(noirr[WEATHER].to_numpy() - firr[WEATHER].to_numpy()))),
        )
        del noirr, firr
    require(maximum_branch_error == 0.0, "corrected branches differ")

    result = {
        "schema": "hultgren_rice_india_reporting_year_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_india_reporting_year_corrected_rice_basis",
        "correction_receipt": {"path": str(args.correction_receipt), "sha256": digest(args.correction_receipt)},
        "checks": {
            "total_rows": total_rows,
            "changed_cell_years": changed_rows,
            "unchanged_cell_years": unchanged_rows,
            "maximum_absolute_unflagged_weather_change": max_unchanged_error,
            "cell_years_with_next_generic_year_parity_check": int(has_next.sum()),
            "maximum_absolute_next_generic_year_parity_error": max_temporal_error,
            "direct_daily_reconstruction_cell_years": len(diagnostics),
            "maximum_absolute_direct_daily_reconstruction_error": max_direct_error,
            "maximum_absolute_corrected_branch_difference": maximum_branch_error,
            "ambiguous_india_reporting_year_rule_sensitive_cells": correction["country_rule_audit"]["ambiguous_india_reporting_year_rule_sensitive_cells"],
        },
        "claim_gates": {
            "india_reporting_year_exception_validated": True,
            "source_rice_application_domain_available": False,
            "published_response_evaluated": False,
            "damage_or_scc_validated": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, indent=2))


if __name__ == "__main__":
    main()
