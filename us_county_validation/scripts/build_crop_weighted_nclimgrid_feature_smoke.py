#!/usr/bin/env python3
"""Build a fixed-CDL crop-pixel nClimGrid/NASS feature sensitivity smoke.

Nonlinear daily features are constructed at each weather cell before applying
the fixed crop-pixel weights. This is deliberately separate from the
county-polygon primary proxy. A 2017 mask attached to an earlier outcome year
is labeled retrospective and cannot be presented as observed historical crop
location. No response, damage, or SCC is estimated here.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from build_county_nclimgrid_feature_smoke import (  # noqa: E402
    WEATHER_GRID_ID,
    WEATHER_SOURCE_ID,
    _strict_bool,
    build_cell_basis,
    load_daily_cells,
    read_table,
)
from build_cdl_nclimgrid_crop_weights import ALLOWED_TEMPORAL_ROLES  # noqa: E402
from validate_county_crop_weather_contract import (  # noqa: E402
    validate_calendar,
    validate_outcomes,
    validate_weights,
)


REQUIRED_SPATIAL_COLUMNS = {
    "grid_lat",
    "grid_lon",
    "mask_temporal_role",
    "analysis_role",
    "response_estimation_authorized",
}


def validate_crop_weights(weights: pd.DataFrame) -> pd.DataFrame:
    if missing := REQUIRED_SPATIAL_COLUMNS - set(weights.columns):
        raise ValueError(f"CDL crop weights lack columns {sorted(missing)}")
    weights = validate_weights(weights, tolerance=1e-8)
    if not weights.weight_role.eq("fixed_crop_mask_sensitivity").all():
        raise ValueError("Feature sensitivity accepts only fixed CDL crop-mask weights")
    if not weights.analysis_role.eq("historical_county_validation_sensitivity_only").all():
        raise ValueError("CDL weights have the wrong analysis boundary")
    if _strict_bool(weights.response_estimation_authorized, "response authorization").any():
        raise ValueError("CDL weights cannot authorize response estimation")
    roles = set(weights.mask_temporal_role.astype("string"))
    if len(roles) != 1 or not roles <= ALLOWED_TEMPORAL_ROLES:
        raise ValueError("CDL weights must carry exactly one registered temporal role")
    if weights.county_geoid.nunique() != 1 or weights.state.nunique() != 1:
        raise ValueError("Bounded crop-weighted smoke accepts one county/state")
    numeric = weights[["grid_lat", "grid_lon"]].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("CDL grid coordinates contain non-finite values")
    weights[["grid_lat", "grid_lon"]] = numeric
    coordinate_keys = ["grid_lat_index", "grid_lon_index"]
    coordinates = weights[coordinate_keys + ["grid_lat", "grid_lon"]].drop_duplicates()
    if coordinates.duplicated(coordinate_keys).any():
        raise ValueError("One nClimGrid index maps to inconsistent coordinates")
    return weights


def build_panel(
    weights: pd.DataFrame,
    dates: pd.DatetimeIndex,
    climate: dict[str, np.ndarray],
    weather_cells: pd.DataFrame,
    calendar_frame: pd.DataFrame,
    outcomes: pd.DataFrame,
    calendar_role: str,
    wet_day_mm: float,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if not np.isfinite(wet_day_mm) or wet_day_mm <= 0:
        raise ValueError("wet_day_mm must be finite and positive")
    weights = validate_crop_weights(weights)
    calendar_frame = validate_calendar(calendar_frame)
    outcomes = validate_outcomes(outcomes)
    if "response_estimation_authorized" in outcomes and _strict_bool(
        outcomes.response_estimation_authorized, "outcome response authorization"
    ).any():
        raise ValueError("Outcome support cannot authorize response estimation")

    county = str(weights.county_geoid.iloc[0])
    state = str(weights.state.iloc[0])
    selected_outcomes = outcomes.loc[outcomes.county_geoid.eq(county)].copy()
    if selected_outcomes.empty or not selected_outcomes.state.eq(state).all():
        raise ValueError("Outcome support does not match the weighted county/state")
    supported = set(weights.outcome_crop)
    required = set(selected_outcomes.outcome_crop)
    if supported != required:
        raise ValueError("Outcome and CDL-weight crop support do not match exactly")
    if "wheat_all_classes" in supported:
        raise ValueError(
            "All-class wheat pooling is intentionally blocked until class-specific "
            "calendar bases and independent class shares pass the full panel gate"
        )

    weather_key = list(
        zip(weather_cells.grid_lat_index, weather_cells.grid_lon_index, strict=True)
    )
    position = {key: index for index, key in enumerate(weather_key)}
    if len(position) != len(weather_cells):
        raise ValueError("Weather-cell extraction table contains duplicate indices")

    rows: list[dict[str, object]] = []
    calendar_selected = calendar_frame.loc[
        calendar_frame.state.eq(state) & calendar_frame.calendar_role.eq(calendar_role)
    ]
    for outcome_key in (
        selected_outcomes[["outcome_crop", "harvest_year"]]
        .drop_duplicates()
        .itertuples(index=False)
    ):
        outcome_crop = str(outcome_key.outcome_crop)
        harvest_year = int(outcome_key.harvest_year)
        crop_weights = weights.loc[weights.outcome_crop.eq(outcome_crop)].copy()
        calendar_classes = crop_weights.calendar_crop.unique().tolist()
        if calendar_classes != [outcome_crop]:
            raise ValueError("Corn/soy outcome must map to its own single calendar class")
        season_rows = calendar_selected.loc[
            calendar_selected.calendar_crop.eq(outcome_crop)
            & calendar_selected.harvest_year.eq(harvest_year)
        ]
        if len(season_rows) != 1:
            raise ValueError("Expected exactly one selected calendar row per crop-year")
        season = next(season_rows.itertuples(index=False))
        where = (dates >= season.season_start) & (dates <= season.season_end)
        expected_days = (season.season_end - season.season_start).days + 1
        if int(where.sum()) != expected_days:
            raise ValueError(
                f"Climate files do not cover exact {outcome_crop}/{harvest_year} season"
            )
        class_rows = [
            build_cell_basis(
                climate["prcp"][where, cell],
                climate["tavg"][where, cell],
                climate["tmin"][where, cell],
                climate["tmax"][where, cell],
                wet_day_mm,
            )
            for cell in range(len(weather_cells))
        ]
        cell_basis = pd.DataFrame(class_rows)
        indices = np.asarray(
            [
                position[(int(row.grid_lat_index), int(row.grid_lon_index))]
                for row in crop_weights.itertuples(index=False)
            ],
            dtype=int,
        )
        spatial_weights = crop_weights.spatial_weight.to_numpy(dtype=float)
        aggregated = {
            column: float(np.dot(cell_basis[column].to_numpy(dtype=float)[indices], spatial_weights))
            for column in cell_basis
        }
        for column in ["season_days", "stage1_days", "stage2_days", "stage3_days"]:
            values = cell_basis[column].to_numpy(dtype=float)[indices]
            if not np.all(values == values[0]):
                raise ValueError(f"Cell basis disagrees on {column}")
            aggregated[column] = int(values[0])
        if not np.isclose(
            sum(aggregated[f"stage{i}_precip_mm"] for i in range(1, 4)),
            aggregated["precip_mm"],
            rtol=0,
            atol=1e-8,
        ):
            raise ValueError("Aggregated stage precipitation does not reconcile")
        rows.append(
            {
                "county_geoid": county,
                "outcome_crop": outcome_crop,
                "harvest_year": harvest_year,
                "season_start": season.season_start,
                "season_end": season.season_end,
                "calendar_source_id": season.calendar_source_id,
                "calendar_role": season.calendar_role,
                "calendar_boundary_rule": season.boundary_rule,
                "stage_definition": season.stage_definition,
                "weather_source_id": WEATHER_SOURCE_ID,
                "weather_grid_id": WEATHER_GRID_ID,
                "weight_role": "fixed_crop_mask_sensitivity",
                "mask_source_id": str(crop_weights.mask_source_id.iloc[0]),
                "mask_vintage": str(crop_weights.mask_vintage.iloc[0]),
                "mask_temporal_role": str(crop_weights.mask_temporal_role.iloc[0]),
                "crop_pixel_exposure": True,
                "weather_day_alignment": "source_date_label_unshifted_24h_ending_early_morning",
                "wet_day_threshold_mm": wet_day_mm,
                "positive_weather_cells": int(len(crop_weights)),
                "coverage_fraction": float(crop_weights.coverage_fraction.min()),
                **aggregated,
            }
        )

    features = pd.DataFrame(rows)
    feature_keys = ["county_geoid", "outcome_crop", "harvest_year"]
    if features.duplicated(feature_keys).any():
        raise ValueError("Duplicate county-crop-year feature rows")
    panel = selected_outcomes.merge(features, on=feature_keys, how="left", validate="many_to_one")
    if panel.weather_source_id.isna().any():
        raise ValueError("Some outcome rows did not receive a crop-weighted weather feature")
    panel["weather_exposure_shared_across_practices"] = True
    panel["analysis_role"] = "historical_county_validation_sensitivity_smoke_only"
    panel["response_estimation_authorized"] = False
    panel["scc_authorized"] = False
    audit = {
        "county_geoid": county,
        "state": state,
        "calendar_role": calendar_role,
        "crops": sorted(features.outcome_crop.unique().tolist()),
        "feature_rows": int(len(features)),
        "joined_panel_rows": int(len(panel)),
        "practice_values_retained": sorted(panel.irrigation_practice.unique().tolist()),
        "daily_start": dates[0].date().isoformat(),
        "daily_end": dates[-1].date().isoformat(),
        "daily_steps": int(len(dates)),
        "unique_weather_cells": int(len(weather_cells)),
        "wet_day_threshold_mm": wet_day_mm,
        "threshold_status": "engineering_smoke_only_not_production_selected",
        "cell_first_nonlinear_basis": True,
        "county_polygon_proxy": False,
        "crop_pixel_exposure": True,
        "mask_temporal_role": str(weights.mask_temporal_role.iloc[0]),
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "scc_authorized": False,
    }
    return panel.sort_values(feature_keys + ["irrigation_practice"]).reset_index(drop=True), audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--climate", required=True, nargs="+")
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--calendar-role", default="fixed_primary")
    parser.add_argument("--wet-day-mm", type=float, default=1.0)
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()

    weights = validate_crop_weights(read_table(Path(args.weights)))
    weather_cells = (
        weights[["grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon"]]
        .drop_duplicates()
        .sort_values(["grid_lat_index", "grid_lon_index"])
        .reset_index(drop=True)
    )
    dates, climate = load_daily_cells([Path(path) for path in args.climate], weather_cells)
    panel, audit = build_panel(
        weights,
        dates,
        climate,
        weather_cells,
        read_table(Path(args.calendar)),
        read_table(Path(args.outcomes)),
        args.calendar_role,
        args.wet_day_mm,
    )
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(destination, index=False)
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {len(panel)} fixed-CDL crop-weighted feature-smoke rows; "
        "no relationship estimated"
    )


if __name__ == "__main__":
    main()
