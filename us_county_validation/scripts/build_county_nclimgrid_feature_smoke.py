#!/usr/bin/env python3
"""Build a bounded county-polygon nClimGrid/NASS feature-panel smoke.

Every nonlinear temporal feature is constructed separately for each weather
cell and crop calendar before county-area weighting. The resulting exposure is
then joined to real paired-practice NASS support. This script emits no fitted
relationship, coefficient, damage, or SCC input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from validate_county_crop_weather_contract import validate_calendar, validate_outcomes  # noqa: E402


WEATHER_SOURCE_ID = "nclimgrid_daily_v1_0_0_20220829"
WEATHER_GRID_ID = "nclimgrid_daily_conus_1_24_degree"
EXPECTED_TITLE = "nClimGrid-Daily, Gridded Fields"
EXPECTED_VERSION = "v1-0-0 20220829"
EXPECTED_FIELDS = {
    "prcp": ("precipitation_amount", "millimeter"),
    "tavg": ("air_temperature", "degree_Celsius"),
    "tmin": ("air_temperature", "degree_Celsius"),
    "tmax": ("air_temperature", "degree_Celsius"),
}
WEIGHT_COLUMNS = {
    "county_geoid", "state", "weather_source_id", "weather_grid_id",
    "grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon",
    "intersection_area_m2", "county_polygon_area_m2", "spatial_weight",
    "coverage_fraction", "boundary_source_id", "boundary_vintage", "area_crs",
    "weight_role", "analysis_role", "feature_construction_eligible", "scc_authorized",
}
STAGE_FRACTIONS = (0.0, 0.3, 0.7, 1.0)


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype="string")


def _strict_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing values")
        return series.astype(bool)
    text = series.astype("string").str.strip().str.lower()
    if text.isna().any() or (~text.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return text.eq("true")


def validate_polygon_weights(weights: pd.DataFrame) -> pd.DataFrame:
    if missing := WEIGHT_COLUMNS - set(weights.columns):
        raise ValueError(f"County-polygon weights lack columns {sorted(missing)}")
    if weights.empty:
        raise ValueError("County-polygon weights are empty")
    weights = weights.copy()
    weights["county_geoid"] = weights.county_geoid.astype("string").str.strip()
    if weights.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("County-polygon weights contain malformed GEOIDs")
    if weights.county_geoid.nunique() != 1 or weights.state.nunique() != 1:
        raise ValueError("Bounded smoke accepts exactly one county/state")
    if not weights.weather_source_id.eq(WEATHER_SOURCE_ID).all():
        raise ValueError("County-polygon weights use the wrong weather source")
    if not weights.weather_grid_id.eq(WEATHER_GRID_ID).all():
        raise ValueError("County-polygon weights use the wrong weather grid")
    if not weights.weight_role.eq("county_polygon_primary_proxy").all():
        raise ValueError("Weights are not labeled as the county-polygon primary proxy")
    if not weights.analysis_role.eq("historical_county_validation_only").all():
        raise ValueError("Weights have the wrong analysis boundary")
    eligible = _strict_bool(weights.feature_construction_eligible, "feature eligibility")
    scc = _strict_bool(weights.scc_authorized, "SCC authorization")
    if not eligible.all() or scc.any():
        raise ValueError("County-polygon weights violate feature/SCC boundary flags")
    numeric = [
        "grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon",
        "intersection_area_m2", "county_polygon_area_m2", "spatial_weight",
        "coverage_fraction",
    ]
    weights[numeric] = weights[numeric].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(weights[numeric].to_numpy(dtype=float)).all():
        raise ValueError("County-polygon weights contain non-finite values")
    for column in ["grid_lat_index", "grid_lon_index"]:
        if (weights[column] % 1 != 0).any() or (weights[column] < 0).any():
            raise ValueError(f"{column} must contain nonnegative integers")
        weights[column] = weights[column].astype("int64")
    if (weights[["intersection_area_m2", "county_polygon_area_m2", "spatial_weight"]] <= 0).any().any():
        raise ValueError("County-polygon areas and weights must be positive")
    if not weights.coverage_fraction.between(0.999, 1 + 1e-8).all():
        raise ValueError("County-polygon weather coverage fails the bounded-smoke gate")
    if weights.duplicated(["county_geoid", "grid_lat_index", "grid_lon_index"]).any():
        raise ValueError("County-polygon weights contain duplicate grid cells")
    if not np.isclose(weights.spatial_weight.sum(), 1, rtol=0, atol=1e-10):
        raise ValueError("County-polygon spatial weights do not sum to one")
    expected = weights.intersection_area_m2 / weights.intersection_area_m2.sum()
    if not np.allclose(weights.spatial_weight, expected, rtol=0, atol=1e-10):
        raise ValueError("County-polygon spatial weights do not reconcile to area")
    return weights.sort_values(["grid_lat_index", "grid_lon_index"]).reset_index(drop=True)


def load_daily_cells(
    paths: list[Path], weights: pd.DataFrame
) -> tuple[pd.DatetimeIndex, dict[str, np.ndarray]]:
    if not paths:
        raise ValueError("At least one monthly nClimGrid file is required")
    date_parts: list[pd.DatetimeIndex] = []
    value_parts: dict[str, list[np.ndarray]] = {field: [] for field in EXPECTED_FIELDS}
    reference_latitude: np.ndarray | None = None
    reference_longitude: np.ndarray | None = None
    lat_index = xr.DataArray(weights.grid_lat_index.to_numpy(dtype=int), dims="cell")
    lon_index = xr.DataArray(weights.grid_lon_index.to_numpy(dtype=int), dims="cell")
    for path in paths:
        with xr.open_dataset(path, engine="h5netcdf") as dataset:
            if set(dataset.data_vars) != set(EXPECTED_FIELDS):
                raise ValueError(f"{path}: nClimGrid variables changed")
            if dataset.attrs.get("title") != EXPECTED_TITLE or dataset.attrs.get("product_version") != EXPECTED_VERSION:
                raise ValueError(f"{path}: nClimGrid title/version changed")
            latitude = dataset.lat.values.astype(float)
            longitude = dataset.lon.values.astype(float)
            if reference_latitude is None:
                reference_latitude, reference_longitude = latitude, longitude
            elif not (np.array_equal(reference_latitude, latitude) and np.array_equal(reference_longitude, longitude)):
                raise ValueError("nClimGrid coordinates changed between monthly objects")
            if weights.grid_lat_index.max() >= len(latitude) or weights.grid_lon_index.max() >= len(longitude):
                raise ValueError("County-polygon weight index lies outside the climate grid")
            if not np.allclose(latitude[weights.grid_lat_index], weights.grid_lat, rtol=0, atol=1e-6):
                raise ValueError("Weight latitude values do not match nClimGrid indices")
            if not np.allclose(longitude[weights.grid_lon_index], weights.grid_lon, rtol=0, atol=1e-6):
                raise ValueError("Weight longitude values do not match nClimGrid indices")
            dates = pd.DatetimeIndex(dataset.time.values).normalize()
            if len(dates) == 0 or dates.has_duplicates or not dates.is_monotonic_increasing:
                raise ValueError(f"{path}: invalid daily chronology")
            expected_dates = pd.date_range(dates[0], dates[-1], freq="D")
            if not dates.equals(expected_dates):
                raise ValueError(f"{path}: monthly chronology is not daily and contiguous")
            date_parts.append(dates)
            for field, (standard_name, units) in EXPECTED_FIELDS.items():
                variable = dataset[field]
                if variable.dims != ("time", "lat", "lon"):
                    raise ValueError(f"{path}: {field} dimensions changed")
                if variable.attrs.get("standard_name") != standard_name or variable.attrs.get("units") != units:
                    raise ValueError(f"{path}: {field} metadata changed")
                values = variable.isel(lat=lat_index, lon=lon_index).values.astype(float)
                if values.shape != (len(dates), len(weights)):
                    raise ValueError(f"{path}: vectorized cell extraction shape changed")
                value_parts[field].append(values)
    dates = pd.DatetimeIndex(np.concatenate([part.values for part in date_parts])).normalize()
    if dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("Combined nClimGrid files are duplicate or out of order")
    if not dates.equals(pd.date_range(dates[0], dates[-1], freq="D")):
        raise ValueError("Combined nClimGrid files have a missing daily boundary")
    values = {field: np.concatenate(parts, axis=0) for field, parts in value_parts.items()}
    if any(not np.isfinite(array).all() for array in values.values()):
        raise ValueError("Selected county weather cells contain missing/non-finite values")
    if (values["prcp"] < 0).any():
        raise ValueError("Selected county weather cells contain negative precipitation")
    return dates, values


def max_run(mask: np.ndarray) -> int:
    longest = current = 0
    for value in mask:
        current = current + 1 if bool(value) else 0
        longest = max(longest, current)
    return longest


def rolling_max(values: np.ndarray, width: int) -> float:
    if len(values) < width:
        return np.nan
    return float(np.convolve(np.asarray(values, dtype=float), np.ones(width), mode="valid").max())


def cell_window_features(
    rain: np.ndarray,
    tavg: np.ndarray,
    tmin: np.ndarray,
    tmax: np.ndarray,
    wet_day_mm: float,
) -> dict[str, float]:
    wet = rain >= wet_day_mm
    return {
        "precip_mm": float(np.sum(rain, dtype=np.float64)),
        "tmean_c": float(np.mean(tavg)),
        "tmin_mean_c": float(np.mean(tmin)),
        "tmax_mean_c": float(np.mean(tmax)),
        "wet_days_n": float(wet.sum()),
        "cdd_max_days": float(max_run(~wet)),
        "rx1day_mm": float(rain.max()),
        "rx5day_mm": rolling_max(rain, 5),
    }


def build_cell_basis(
    rain: np.ndarray,
    tavg: np.ndarray,
    tmin: np.ndarray,
    tmax: np.ndarray,
    wet_day_mm: float,
) -> dict[str, float]:
    n_days = len(rain)
    result = cell_window_features(rain, tavg, tmin, tmax, wet_day_mm)
    result["season_days"] = float(n_days)
    bounds = [int(np.floor(value * n_days)) for value in STAGE_FRACTIONS]
    stage_precipitation: list[float] = []
    for stage, (left, right) in enumerate(zip(bounds, bounds[1:]), start=1):
        if right <= left:
            raise ValueError("Calendar season is too short for declared stages")
        stage_features = cell_window_features(
            rain[left:right], tavg[left:right], tmin[left:right], tmax[left:right], wet_day_mm
        )
        result[f"stage{stage}_days"] = float(right - left)
        for name, value in stage_features.items():
            result[f"stage{stage}_{name}"] = value
        stage_precipitation.append(stage_features["precip_mm"])
    total = result["precip_mm"]
    if not np.isclose(sum(stage_precipitation), total, rtol=0, atol=1e-8):
        raise ValueError("Cell stage precipitation does not reconcile to season total")
    if total > 0:
        shares = np.asarray(stage_precipitation, dtype=float) / total
    else:
        shares = np.zeros(3, dtype=float)
    for stage, share in enumerate(shares, start=1):
        result[f"stage{stage}_precip_share"] = float(share)
    midpoints = np.asarray(
        [(left + right) / 2 for left, right in zip(STAGE_FRACTIONS, STAGE_FRACTIONS[1:])]
    )
    result["precipitation_concentration_hhi"] = float(np.square(shares).sum())
    result["precipitation_timing_centroid"] = float(shares @ midpoints)
    result["zero_precipitation_season"] = float(total == 0)
    result["wet_day_frequency"] = result["wet_days_n"] / n_days
    result["mean_wet_day_intensity_mm"] = (
        total / result["wet_days_n"] if result["wet_days_n"] > 0 else 0.0
    )
    return result


def build_panel(
    weights: pd.DataFrame,
    dates: pd.DatetimeIndex,
    climate: dict[str, np.ndarray],
    calendar_frame: pd.DataFrame,
    outcomes: pd.DataFrame,
    calendar_role: str,
    wet_day_mm: float,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if not np.isfinite(wet_day_mm) or wet_day_mm <= 0:
        raise ValueError("wet_day_mm must be finite and positive")
    weights = validate_polygon_weights(weights)
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
    county_name = str(weights.county_name.iloc[0])
    if "county_name" in selected_outcomes and not selected_outcomes.county_name.astype(
        "string"
    ).str.strip().str.casefold().eq(county_name.strip().casefold()).all():
        raise ValueError("Outcome county name does not match the spatial weights")
    calendar_selected = calendar_frame.loc[
        calendar_frame.state.eq(state) & calendar_frame.calendar_role.eq(calendar_role)
    ].copy()
    if calendar_selected.empty:
        raise ValueError("No requested calendar role matches the weighted county")
    required_calendar_keys = set(
        map(
            tuple,
            selected_outcomes[["outcome_crop", "harvest_year"]]
            .drop_duplicates()
            .itertuples(index=False, name=None),
        )
    )
    available_calendar_keys = set(
        map(
            tuple,
            calendar_selected[["calendar_crop", "harvest_year"]]
            .drop_duplicates()
            .itertuples(index=False, name=None),
        )
    )
    if required_calendar_keys != available_calendar_keys:
        raise ValueError("Outcome and selected calendar crop-year support do not match exactly")
    weight_values = weights.spatial_weight.to_numpy(dtype=float)
    rows: list[dict[str, object]] = []
    for season in calendar_selected.itertuples(index=False):
        where = (dates >= season.season_start) & (dates <= season.season_end)
        expected_days = (season.season_end - season.season_start).days + 1
        if int(where.sum()) != expected_days:
            raise ValueError(
                f"Climate files do not cover exact {season.calendar_crop}/{season.harvest_year} season"
            )
        cell_rows = []
        for cell in range(len(weights)):
            cell_rows.append(
                build_cell_basis(
                    climate["prcp"][where, cell],
                    climate["tavg"][where, cell],
                    climate["tmin"][where, cell],
                    climate["tmax"][where, cell],
                    wet_day_mm,
                )
            )
        cell_basis = pd.DataFrame(cell_rows)
        if not np.isfinite(cell_basis.to_numpy(dtype=float)).all():
            raise ValueError("Cell-level weather basis contains non-finite values")
        aggregated = {
            column: float(np.dot(cell_basis[column].to_numpy(dtype=float), weight_values))
            for column in cell_basis
        }
        for column in ["season_days", "stage1_days", "stage2_days", "stage3_days"]:
            values = cell_basis[column].unique()
            if len(values) != 1:
                raise ValueError(f"Cell basis disagrees on {column}")
            aggregated[column] = int(values[0])
        if sum(aggregated[f"stage{i}_days"] for i in range(1, 4)) != aggregated["season_days"]:
            raise ValueError("Aggregated stage days do not reconcile to season days")
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
                "outcome_crop": season.calendar_crop,
                "harvest_year": int(season.harvest_year),
                "season_start": season.season_start,
                "season_end": season.season_end,
                "calendar_source_id": season.calendar_source_id,
                "calendar_role": season.calendar_role,
                "calendar_boundary_rule": season.boundary_rule,
                "stage_definition": season.stage_definition,
                "weather_source_id": WEATHER_SOURCE_ID,
                "weather_grid_id": WEATHER_GRID_ID,
                "weight_role": "county_polygon_primary_proxy",
                "crop_pixel_exposure": False,
                "weather_day_alignment": "source_date_label_unshifted_24h_ending_early_morning",
                "wet_day_threshold_mm": wet_day_mm,
                "positive_weather_cells": int(len(weights)),
                "coverage_fraction": float(weights.coverage_fraction.min()),
                **aggregated,
            }
        )
    features = pd.DataFrame(rows)
    feature_keys = ["county_geoid", "outcome_crop", "harvest_year"]
    if features.duplicated(feature_keys).any():
        raise ValueError("Duplicate county-crop-year feature rows")
    panel = selected_outcomes.merge(features, on=feature_keys, how="left", validate="many_to_one")
    if panel.weather_source_id.isna().any():
        raise ValueError("Some outcome rows did not receive a weather feature")
    panel["weather_exposure_shared_across_practices"] = True
    panel["analysis_role"] = "historical_county_validation_smoke_only"
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
        "positive_weather_cells": int(len(weights)),
        "wet_day_threshold_mm": wet_day_mm,
        "threshold_status": "engineering_smoke_only_not_production_selected",
        "cell_first_nonlinear_basis": True,
        "county_polygon_proxy": True,
        "crop_pixel_exposure": False,
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
    weights = validate_polygon_weights(read_table(Path(args.weights)))
    dates, climate = load_daily_cells([Path(path) for path in args.climate], weights)
    panel, audit = build_panel(
        weights,
        dates,
        climate,
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
        f"wrote {len(panel)} joined NASS/weather smoke rows; "
        f"features built cell-first; no relationship estimated"
    )


if __name__ == "__main__":
    main()
