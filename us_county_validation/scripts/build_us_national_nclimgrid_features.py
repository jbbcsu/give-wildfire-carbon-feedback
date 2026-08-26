#!/usr/bin/env python3
"""Build one resumable harvest-year partition of national U.S. weather features.

All nonlinear precipitation and temperature summaries are constructed at the
nClimGrid cell/calendar level and only then county-area weighted.  One weather
row is duplicated exactly across the paired irrigated/non-irrigated outcomes.
This script emits no coefficient, prediction, causal estimate, damage, or SCC.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import xarray as xr

from build_county_nclimgrid_feature_smoke import (
    EXPECTED_FIELDS,
    EXPECTED_TITLE,
    EXPECTED_VERSION,
    STAGE_FRACTIONS,
    WEATHER_GRID_ID,
    WEATHER_SOURCE_ID,
    build_cell_basis,
    validate_polygon_weights,
)
from build_us_national_county_nclimgrid_weights import (
    DEFAULT_CALENDAR,
    DEFAULT_COUNTIES,
    DEFAULT_GEOGRAPHY,
    DEFAULT_PANEL,
    DEFAULT_REFERENCE,
    SCHEMA as WEIGHT_SCHEMA,
    _partition_paths as weight_partition_paths,
    _tiger_hashes,
)
from us_national_nclimgrid_common import (
    DEFAULT_CONTRACT,
    DEFAULT_BOUND_CALENDAR_RECEIPT,
    DEFAULT_COMPETING_PROTOCOL,
    DEFAULT_HTTP_INVENTORY,
    DEFAULT_RAW_WEATHER_DIR,
    DEFAULT_REVIEWED_PRODUCT,
    OUTCOME_KEYS,
    PAIR_KEYS,
    PROJECT_ROOT,
    atomic_write_json,
    atomic_write_parquet,
    canonical_sha256,
    load_contract,
    prepare_support,
    read_table,
    sha256_file,
    sha256_records,
    strict_bool,
    validate_acquired_months,
    validate_bound_calendar_receipt,
)


SCHEMA = "us_national_nclimgrid_feature_year_partition_v1"
DEFAULT_WEIGHT_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_polygon_weights_national_v1"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_features_national_v1"
DAY_ALIGNMENT = "source_date_label_unshifted_24h_ending_early_morning"
DAY_COLUMNS = ["season_days", "stage1_days", "stage2_days", "stage3_days"]
SHARED_FEATURE_METADATA = [
    "state", "season_start", "season_end", "calendar_source_id", "calendar_vintage",
    "calendar_role", "calendar_boundary_rule", "stage_definition", "weather_source_id",
    "weather_grid_id", "weight_role", "crop_pixel_exposure", "weather_day_alignment",
    "wet_day_threshold_mm", "positive_weather_cells", "coverage_fraction",
    "weather_valid_coverage_fraction", "weather_valid_area_relative_to_declared_land",
]


def required_month_keys(seasons: pd.DataFrame) -> list[tuple[int, int]]:
    if seasons.empty:
        raise ValueError("cannot derive weather months from empty seasons")
    starts = pd.to_datetime(seasons.season_start, errors="raise").dt.normalize()
    ends = pd.to_datetime(seasons.season_end, errors="raise").dt.normalize()
    if (ends < starts).any():
        raise ValueError("crop calendars contain reversed seasons")
    first = starts.min().to_period("M").to_timestamp()
    last = ends.max().to_period("M").to_timestamp()
    months = pd.date_range(first, last, freq="MS")
    return [(int(value.year), int(value.month)) for value in months]


def load_daily_unique_cells(
    paths: list[Path], cells: pd.DataFrame
) -> tuple[pd.DatetimeIndex, dict[str, np.ndarray]]:
    required = {"grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon"}
    if missing := required - set(cells.columns):
        raise ValueError(f"weather-cell table lacks {sorted(missing)}")
    cells = cells.copy()
    for column in ["grid_lat_index", "grid_lon_index"]:
        cells[column] = pd.to_numeric(cells[column], errors="raise").astype("int64")
    for column in ["grid_lat", "grid_lon"]:
        cells[column] = pd.to_numeric(cells[column], errors="raise")
    if cells.empty or cells.duplicated(["grid_lat_index", "grid_lon_index"]).any():
        raise ValueError("weather-cell table is empty or duplicates grid indices")
    if not np.isfinite(cells[["grid_lat", "grid_lon"]].to_numpy(dtype=float)).all():
        raise ValueError("weather-cell coordinates are nonfinite")
    if not paths:
        raise ValueError("at least one monthly weather object is required")

    lat_index = xr.DataArray(cells.grid_lat_index.to_numpy(dtype=int), dims="cell")
    lon_index = xr.DataArray(cells.grid_lon_index.to_numpy(dtype=int), dims="cell")
    dates_parts: list[pd.DatetimeIndex] = []
    values_parts: dict[str, list[np.ndarray]] = {field: [] for field in EXPECTED_FIELDS}
    reference_lat: np.ndarray | None = None
    reference_lon: np.ndarray | None = None
    for path in paths:
        with xr.open_dataset(path, engine="h5netcdf") as dataset:
            if set(dataset.data_vars) != set(EXPECTED_FIELDS):
                raise ValueError(f"{path}: nClimGrid variables differ from the contract")
            if dataset.attrs.get("title") != EXPECTED_TITLE or dataset.attrs.get("product_version") != EXPECTED_VERSION:
                raise ValueError(f"{path}: nClimGrid title/version differs from the contract")
            latitude = dataset.lat.values.astype(float)
            longitude = dataset.lon.values.astype(float)
            if reference_lat is None:
                reference_lat, reference_lon = latitude, longitude
            elif not (np.array_equal(reference_lat, latitude) and np.array_equal(reference_lon, longitude)):
                raise ValueError("nClimGrid coordinates change between required months")
            if cells.grid_lat_index.max() >= len(latitude) or cells.grid_lon_index.max() >= len(longitude):
                raise ValueError("a county weight index lies outside the nClimGrid grid")
            if not np.allclose(latitude[cells.grid_lat_index], cells.grid_lat, rtol=0, atol=1e-6):
                raise ValueError("county weight latitude does not match the nClimGrid index")
            if not np.allclose(longitude[cells.grid_lon_index], cells.grid_lon, rtol=0, atol=1e-6):
                raise ValueError("county weight longitude does not match the nClimGrid index")
            dates = pd.DatetimeIndex(dataset.time.values).normalize()
            if dates.empty or dates.has_duplicates or not dates.is_monotonic_increasing:
                raise ValueError(f"{path}: invalid daily chronology")
            if not dates.equals(pd.date_range(dates[0], dates[-1], freq="D")):
                raise ValueError(f"{path}: daily chronology is not contiguous")
            dates_parts.append(dates)
            for field, (standard_name, units) in EXPECTED_FIELDS.items():
                variable = dataset[field]
                if variable.dims != ("time", "lat", "lon"):
                    raise ValueError(f"{path}: {field} dimensions changed")
                if variable.attrs.get("standard_name") != standard_name or variable.attrs.get("units") != units:
                    raise ValueError(f"{path}: {field} metadata changed")
                values = variable.isel(lat=lat_index, lon=lon_index).values.astype(float)
                if values.shape != (len(dates), len(cells)):
                    raise ValueError(f"{path}: selected-cell extraction shape changed")
                values_parts[field].append(values)
    dates = pd.DatetimeIndex(np.concatenate([part.values for part in dates_parts])).normalize()
    if dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("combined nClimGrid chronology is duplicate/out of order")
    if not dates.equals(pd.date_range(dates[0], dates[-1], freq="D")):
        raise ValueError("combined nClimGrid chronology has a missing daily boundary")
    values = {field: np.concatenate(parts, axis=0) for field, parts in values_parts.items()}
    if any(not np.isfinite(value).all() for value in values.values()):
        raise ValueError("selected nClimGrid cells contain missing/nonfinite weather")
    if (values["prcp"] < 0).any():
        raise ValueError("selected nClimGrid cells contain negative precipitation")
    return dates, values


def _maximum_run_by_cell(mask: np.ndarray) -> np.ndarray:
    if mask.ndim != 2:
        raise ValueError("dry-day mask must be day by cell")
    current = np.zeros(mask.shape[1], dtype=np.int64)
    maximum = np.zeros(mask.shape[1], dtype=np.int64)
    for row in mask:
        current = np.where(row, current + 1, 0)
        maximum = np.maximum(maximum, current)
    return maximum.astype(float)


def _rolling_max_by_cell(values: np.ndarray, width: int) -> np.ndarray:
    if width < 1 or values.ndim != 2:
        raise ValueError("rolling window requires a positive width and day-by-cell input")
    if len(values) < width:
        return np.full(values.shape[1], np.nan)
    cumulative = np.vstack([np.zeros((1, values.shape[1])), np.cumsum(values, axis=0, dtype=float)])
    return (cumulative[width:] - cumulative[:-width]).max(axis=0)


def _window_matrix(
    rain: np.ndarray,
    tavg: np.ndarray,
    tmin: np.ndarray,
    tmax: np.ndarray,
    wet_day_mm: float,
) -> dict[str, np.ndarray]:
    if not (rain.shape == tavg.shape == tmin.shape == tmax.shape) or rain.ndim != 2:
        raise ValueError("weather arrays must share a day-by-cell shape")
    if len(rain) == 0:
        raise ValueError("weather window is empty")
    wet = rain >= wet_day_mm
    return {
        "precip_mm": rain.sum(axis=0, dtype=np.float64),
        "tmean_c": tavg.mean(axis=0),
        "tmin_mean_c": tmin.mean(axis=0),
        "tmax_mean_c": tmax.mean(axis=0),
        "wet_days_n": wet.sum(axis=0).astype(float),
        "cdd_max_days": _maximum_run_by_cell(~wet),
        "rx1day_mm": rain.max(axis=0),
        "rx5day_mm": _rolling_max_by_cell(rain, 5),
    }


def build_cell_basis_matrix(
    rain: np.ndarray,
    tavg: np.ndarray,
    tmin: np.ndarray,
    tmax: np.ndarray,
    wet_day_mm: float,
) -> pd.DataFrame:
    if not np.isfinite(wet_day_mm) or wet_day_mm <= 0:
        raise ValueError("wet-day threshold must be finite and positive")
    if any(not np.isfinite(value).all() for value in [rain, tavg, tmin, tmax]):
        raise ValueError("cell-basis weather contains missing/nonfinite values")
    if (rain < 0).any():
        raise ValueError("cell-basis precipitation is negative")
    n_days, n_cells = rain.shape
    result = _window_matrix(rain, tavg, tmin, tmax, wet_day_mm)
    result["season_days"] = np.full(n_cells, float(n_days))
    bounds = [int(np.floor(value * n_days)) for value in STAGE_FRACTIONS]
    stage_precipitation: list[np.ndarray] = []
    for stage, (left, right) in enumerate(zip(bounds, bounds[1:]), start=1):
        if right <= left:
            raise ValueError("calendar season is too short for registered stages")
        stage_basis = _window_matrix(
            rain[left:right], tavg[left:right], tmin[left:right], tmax[left:right], wet_day_mm
        )
        result[f"stage{stage}_days"] = np.full(n_cells, float(right - left))
        for name, values in stage_basis.items():
            result[f"stage{stage}_{name}"] = values
        stage_precipitation.append(stage_basis["precip_mm"])
    stage_matrix = np.vstack(stage_precipitation)
    total = result["precip_mm"]
    if not np.allclose(stage_matrix.sum(axis=0), total, rtol=0, atol=1e-8):
        raise ValueError("cell stage precipitation does not reconcile to the season")
    shares = np.divide(
        stage_matrix, total[None, :], out=np.zeros_like(stage_matrix), where=total[None, :] > 0
    )
    for stage in range(1, 4):
        result[f"stage{stage}_precip_share"] = shares[stage - 1]
    midpoints = np.asarray(
        [(left + right) / 2 for left, right in zip(STAGE_FRACTIONS, STAGE_FRACTIONS[1:])]
    )
    result["precipitation_concentration_hhi"] = np.square(shares).sum(axis=0)
    # An explicit elementwise reduction avoids platform BLAS warnings observed
    # for this tiny 3-by-N product while remaining algebraically identical.
    result["precipitation_timing_centroid"] = np.sum(
        midpoints[:, None] * shares, axis=0, dtype=np.float64
    )
    result["zero_precipitation_season"] = (total == 0).astype(float)
    result["wet_day_frequency"] = result["wet_days_n"] / n_days
    result["mean_wet_day_intensity_mm"] = np.divide(
        total, result["wet_days_n"], out=np.zeros_like(total), where=result["wet_days_n"] > 0
    )
    frame = pd.DataFrame(result)
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("constructed cell basis contains missing/nonfinite values")
    return frame


def validate_weight_partitions(
    weight_dir: Path,
    support: pd.DataFrame,
    *,
    contract_path: Path,
    panel_path: Path,
    geography_path: Path,
    calendar_path: Path,
    calendar_validation_path: Path,
    calendar_protocol_path: Path,
    counties_path: Path,
    reference_identity: Mapping[str, Any],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    contract = load_contract(contract_path)
    weather_contract = contract["weather"]
    expected_common = {
        "contract_sha256": sha256_file(contract_path),
        "panel_sha256": sha256_file(panel_path),
        "geography_sha256": sha256_file(geography_path),
        "calendar_sha256": sha256_file(calendar_path),
        "calendar_validation_sha256": sha256_file(calendar_validation_path),
        "calendar_protocol_sha256": sha256_file(calendar_protocol_path),
        "calendar_receipt_status": validate_bound_calendar_receipt(
            calendar_path, calendar_validation_path, calendar_protocol_path
        )["status"],
        "tiger_component_sha256": _tiger_hashes(counties_path),
        "reference_weather_identity": dict(reference_identity),
        "builder_sha256": sha256_file(Path(__file__).with_name(
            "build_us_national_county_nclimgrid_weights.py"
        )),
        "min_coverage": float(weather_contract["minimum_geometric_grid_coverage"]),
        "declared_area_relative_tolerance": float(
            weather_contract["maximum_declared_area_relative_error"]
        ),
        "reference_validity_mask_rule": "all_four_fields_finite_on_every_day_of_1981_01",
        "reference_valid_grid_cells": int(weather_contract["reference_valid_grid_cells"]),
        "minimum_weather_valid_area_relative_to_declared_land": float(
            weather_contract["minimum_weather_valid_area_relative_to_declared_land"]
        ),
    }
    frames: list[pd.DataFrame] = []
    receipts: list[dict[str, Any]] = []
    for geoid in sorted(support.county_geoid.unique().tolist()):
        output, receipt_path = weight_partition_paths(weight_dir, geoid)
        if not output.is_file() or not receipt_path.is_file():
            raise ValueError(f"county {geoid} lacks a completed weight partition")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"county {geoid} weight receipt is unreadable") from error
        if receipt.get("schema") != WEIGHT_SCHEMA or receipt.get("county_geoid") != geoid:
            raise ValueError(f"county {geoid} weight receipt identity changed")
        identity = receipt.get("input_identity")
        if not isinstance(identity, dict):
            raise ValueError(f"county {geoid} weight receipt lacks input identity")
        for key, expected in expected_common.items():
            if identity.get(key) != expected:
                raise ValueError(f"county {geoid} weight receipt differs on {key}")
        county_support = support.loc[support.county_geoid.eq(geoid)]
        expected_county_hash = sha256_records(county_support, [*county_support.columns])
        if identity.get("county_geoid") != geoid or identity.get("county_outcome_key_sha256") != expected_county_hash:
            raise ValueError(f"county {geoid} weight receipt support lineage changed")
        if canonical_sha256(identity) != receipt.get("input_fingerprint_sha256"):
            raise ValueError(f"county {geoid} weight receipt fingerprint does not reconcile")
        if sha256_file(output) != receipt.get("output_sha256"):
            raise ValueError(f"county {geoid} weight output hash changed")
        weights = validate_polygon_weights(pd.read_parquet(output))
        if set(weights.county_geoid.astype(str)) != {geoid} or len(weights) != int(receipt["weight_rows"]):
            raise ValueError(f"county {geoid} weight output does not reconcile to its receipt")
        for column in [
            "weather_valid_coverage_fraction",
            "weather_valid_area_relative_to_declared_land",
            "weather_masked_intersection_area_m2",
        ]:
            if column not in weights or column not in receipt:
                raise ValueError(f"county {geoid} weight output/receipt lacks {column}")
            if not np.isclose(
                float(weights[column].iloc[0]), float(receipt[column]), rtol=0, atol=1e-12
            ):
                raise ValueError(f"county {geoid} weight output differs on {column}")
        minimum_valid_land = float(
            weather_contract["minimum_weather_valid_area_relative_to_declared_land"]
        )
        if float(weights.weather_valid_area_relative_to_declared_land.min()) < minimum_valid_land:
            raise ValueError(f"county {geoid} fails the registered valid-land coverage gate")
        if not weights.weather_valid_coverage_fraction.between(0, 1 + 1e-8).all():
            raise ValueError(f"county {geoid} has invalid weather-supported polygon coverage")
        if (
            "weather_masked_intersection_area_m2" not in weights
            or (weights.weather_masked_intersection_area_m2 < 0).any()
        ):
            raise ValueError(f"county {geoid} has invalid masked-area accounting")
        frames.append(weights)
        receipts.append(
            {
                "county_geoid": geoid,
                "output_sha256": str(receipt["output_sha256"]),
                "input_fingerprint_sha256": str(receipt["input_fingerprint_sha256"]),
                "weight_rows": int(receipt["weight_rows"]),
            }
        )
    weights = pd.concat(frames, ignore_index=True)
    if weights.duplicated(["county_geoid", "grid_lat_index", "grid_lon_index"]).any():
        raise ValueError("combined county weight partitions duplicate county/grid keys")
    return weights, receipts


def build_year_panel(
    support: pd.DataFrame,
    seasons: pd.DataFrame,
    weights: pd.DataFrame,
    cells: pd.DataFrame,
    dates: pd.DatetimeIndex,
    climate: dict[str, np.ndarray],
    contract: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if support.empty or support.harvest_year.nunique() != 1:
        raise ValueError("one feature partition requires exactly one harvest year")
    year = int(support.harvest_year.iloc[0])
    practices = set(map(str, contract["sample"]["irrigation_practices"]))
    practice_sets = support.groupby(PAIR_KEYS, observed=True).irrigation_practice.agg(set)
    if not practice_sets.map(lambda value: value == practices).all():
        raise ValueError("year support does not preserve exact practice pairs")
    if set(weights.county_geoid.astype(str)) != set(support.county_geoid.astype(str)):
        raise ValueError("year weight counties do not exactly match outcome support")
    cell_keys = list(zip(cells.grid_lat_index, cells.grid_lon_index, strict=True))
    cell_position = {key: index for index, key in enumerate(cell_keys)}
    if len(cell_position) != len(cells):
        raise ValueError("unique-cell extraction table duplicates grid indices")
    if any(value.shape != (len(dates), len(cells)) for value in climate.values()):
        raise ValueError("climate arrays do not match dates and unique weather cells")

    pair_support = support.drop_duplicates(PAIR_KEYS)
    feature_rows: list[dict[str, Any]] = []
    wet_day_mm = float(contract["weather"]["wet_day_threshold_mm"])
    grouping = ["state", "outcome_crop", "season_start", "season_end"]
    season_lookup = seasons.rename(columns={"calendar_crop": "outcome_crop"})
    routed = pair_support.merge(
        season_lookup,
        on=["state", "outcome_crop", "harvest_year"], how="left", validate="many_to_one",
        suffixes=("", "_calendar"),
    )
    if routed.season_start.isna().any():
        raise ValueError("a year outcome lacks its fixed calendar")
    for group_key, group in routed.groupby(grouping, observed=True, sort=True):
        state, crop, season_start, season_end = group_key
        season_start, season_end = pd.Timestamp(season_start), pd.Timestamp(season_end)
        where = (dates >= season_start) & (dates <= season_end)
        expected_days = (season_end - season_start).days + 1
        if int(where.sum()) != expected_days:
            raise ValueError(f"weather does not exactly cover {state}/{crop}/{year} crop season")
        county_ids = sorted(group.county_geoid.astype(str).unique().tolist())
        group_weights = weights.loc[weights.county_geoid.astype(str).isin(county_ids)].copy()
        needed_keys = list(
            zip(group_weights.grid_lat_index, group_weights.grid_lon_index, strict=True)
        )
        try:
            positions = np.asarray([cell_position[key] for key in needed_keys], dtype=int)
        except KeyError as error:
            raise ValueError("county weight cell is absent from extracted climate cells") from error
        basis = build_cell_basis_matrix(
            climate["prcp"][where][:, positions],
            climate["tavg"][where][:, positions],
            climate["tmin"][where][:, positions],
            climate["tmax"][where][:, positions],
            wet_day_mm,
        )
        group_weights = group_weights.reset_index(drop=True)
        if len(group_weights) != len(basis):
            raise AssertionError("cell basis and county weight rows lost alignment")
        calendar_row = group.iloc[0]
        for geoid, county_weight in group_weights.groupby("county_geoid", observed=True, sort=True):
            indices = county_weight.index.to_numpy(dtype=int)
            spatial = county_weight.spatial_weight.to_numpy(dtype=float)
            if not np.isclose(spatial.sum(), 1, rtol=0, atol=1e-10):
                raise ValueError(f"county {geoid} weights do not sum to one")
            aggregated = {
                column: float(np.dot(basis.loc[indices, column].to_numpy(dtype=float), spatial))
                for column in basis.columns
            }
            for column in DAY_COLUMNS:
                values = basis.loc[indices, column].to_numpy(dtype=float)
                if not np.all(values == values[0]):
                    raise ValueError(f"county cells disagree on {column}")
                aggregated[column] = int(values[0])
            if sum(aggregated[f"stage{i}_days"] for i in range(1, 4)) != aggregated["season_days"]:
                raise ValueError("aggregated stage days do not reconcile to crop-season days")
            if not np.isclose(
                sum(aggregated[f"stage{i}_precip_mm"] for i in range(1, 4)),
                aggregated["precip_mm"], rtol=0, atol=1e-8,
            ):
                raise ValueError("aggregated stage precipitation does not reconcile")
            feature_rows.append(
                {
                    "county_geoid": str(geoid),
                    "outcome_crop": str(crop),
                    "harvest_year": year,
                    "state": str(state),
                    "season_start": season_start,
                    "season_end": season_end,
                    "calendar_source_id": str(calendar_row.calendar_source_id),
                    "calendar_vintage": str(calendar_row.calendar_vintage),
                    "calendar_role": str(calendar_row.calendar_role),
                    "calendar_boundary_rule": str(calendar_row.boundary_rule),
                    "stage_definition": str(calendar_row.stage_definition),
                    "weather_source_id": WEATHER_SOURCE_ID,
                    "weather_grid_id": WEATHER_GRID_ID,
                    "weight_role": "county_polygon_primary_proxy",
                    "crop_pixel_exposure": False,
                    "weather_day_alignment": DAY_ALIGNMENT,
                    "wet_day_threshold_mm": wet_day_mm,
                    "positive_weather_cells": int(len(county_weight)),
                    "coverage_fraction": float(county_weight.coverage_fraction.iloc[0]),
                    "weather_valid_coverage_fraction": float(
                        county_weight.weather_valid_coverage_fraction.iloc[0]
                    ),
                    "weather_valid_area_relative_to_declared_land": float(
                        county_weight.weather_valid_area_relative_to_declared_land.iloc[0]
                    ),
                    **aggregated,
                }
            )
    features = pd.DataFrame(feature_rows)
    if features.empty or features.duplicated(PAIR_KEYS).any():
        raise ValueError("year weather features are empty or duplicate pair keys")
    expected_pairs = set(map(tuple, pair_support[PAIR_KEYS].itertuples(index=False, name=None)))
    actual_pairs = set(map(tuple, features[PAIR_KEYS].itertuples(index=False, name=None)))
    if actual_pairs != expected_pairs:
        raise ValueError("year weather feature keys do not exactly match outcome support")
    panel = support.merge(
        features,
        on=PAIR_KEYS + ["state"], how="left", validate="many_to_one",
        suffixes=("", "_weather"),
    )
    if panel.weather_source_id.isna().any():
        raise ValueError("some year outcomes did not receive a weather feature")
    panel["feature_construction_eligible"] = True
    panel["weather_exposure_shared_across_practices"] = True
    panel["analysis_role"] = "historical_us_county_weather_feature_support_only"
    panel["response_estimation_authorized"] = False
    panel["scc_authorized"] = False
    feature_columns = [column for column in features.columns if column not in PAIR_KEYS]
    for column in feature_columns:
        counts = panel.groupby(PAIR_KEYS, observed=True)[column].nunique(dropna=False)
        if counts.ne(1).any():
            raise ValueError(f"weather feature {column} differs across irrigation practices")
    if set(panel.weather_source_id) != {str(contract["weather"]["source_id"])}:
        raise ValueError("year output weather source differs from the national contract")
    audit = {
        "harvest_year": year,
        "counties": int(panel.county_geoid.nunique()),
        "crop_county_years": int(len(features)),
        "practice_rows": int(len(panel)),
        "corn_crop_county_years": int(features.outcome_crop.eq("corn_grain").sum()),
        "soy_crop_county_years": int(features.outcome_crop.eq("soybeans").sum()),
        "weather_cells_extracted": int(len(cells)),
        "daily_start": dates[0].date().isoformat(),
        "daily_end": dates[-1].date().isoformat(),
        "daily_steps_loaded": int(len(dates)),
        "cell_first_nonlinear_basis": True,
        "weather_exposure_shared_across_practices": True,
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "scc_authorized": False,
    }
    return panel.sort_values(OUTCOME_KEYS).reset_index(drop=True), audit


def validate_year_output(frame: pd.DataFrame, support: pd.DataFrame) -> None:
    if frame.empty or frame.duplicated(OUTCOME_KEYS).any():
        raise ValueError("year output is empty or duplicates outcome keys")
    expected = set(map(tuple, support[OUTCOME_KEYS].itertuples(index=False, name=None)))
    actual = set(map(tuple, frame[OUTCOME_KEYS].itertuples(index=False, name=None)))
    if actual != expected:
        raise ValueError("year output keys differ from selected outcome support")
    mutable_gate_columns = {
        "feature_construction_eligible", "response_estimation_authorized", "scc_authorized"
    }
    support_projection = [
        column for column in support.columns if column not in mutable_gate_columns
    ]
    if missing_support := set(support_projection) - set(frame.columns):
        raise ValueError(f"year output lacks bound outcome columns {sorted(missing_support)}")
    expected_support = support[support_projection].sort_values(OUTCOME_KEYS).reset_index(drop=True)
    observed_support = frame[support_projection].sort_values(OUTCOME_KEYS).reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(
            observed_support, expected_support, check_dtype=False, check_exact=True
        )
    except AssertionError as error:
        raise ValueError("year output outcome values/metadata differ from exact NASS support") from error
    required = {
        *SHARED_FEATURE_METADATA, "yield_bu_acre", "outcome_source_id",
        "weather_exposure_shared_across_practices", "feature_construction_eligible",
        "response_estimation_authorized", "scc_authorized", "precip_mm",
        "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c", "cdd_max_days",
        "wet_day_frequency", "mean_wet_day_intensity_mm", "rx1day_mm", "rx5day_mm",
        "precipitation_concentration_hhi", "stage1_precip_share", "stage2_precip_share",
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"year output lacks registered direct-weather fields {sorted(missing)}")
    if not strict_bool(
        frame.weather_exposure_shared_across_practices,
        "year output weather_exposure_shared_across_practices",
    ).all():
        raise ValueError("year output is not marked shared across practices")
    if not strict_bool(
        frame.feature_construction_eligible, "year output feature_construction_eligible"
    ).all():
        raise ValueError("year output contains feature-ineligible rows")
    if strict_bool(
        frame.response_estimation_authorized, "year output response_estimation_authorized"
    ).any() or strict_bool(frame.scc_authorized, "year output scc_authorized").any():
        raise ValueError("year output unexpectedly authorizes fitting or SCC")
    if strict_bool(frame.crop_pixel_exposure, "year output crop_pixel_exposure").any():
        raise ValueError("county-polygon year output claims crop-pixel exposure")
    numeric = [
        "yield_bu_acre", "positive_weather_cells", "coverage_fraction",
        "weather_valid_coverage_fraction", "weather_valid_area_relative_to_declared_land",
        "precip_mm", "tmean_c", "tmin_mean_c", "tmax_mean_c", "wet_days_n",
        "cdd_max_days", "rx1day_mm", "rx5day_mm", "precipitation_concentration_hhi",
        "precipitation_timing_centroid", "zero_precipitation_season", "wet_day_frequency",
        "mean_wet_day_intensity_mm",
        *[column for column in frame.columns if column.startswith(("stage1_", "stage2_", "stage3_"))],
    ]
    values = frame[list(dict.fromkeys(numeric))].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("year output contains missing/nonfinite numeric values")
    if (values.yield_bu_acre <= 0).any() or (values.positive_weather_cells <= 0).any():
        raise ValueError("year output contains nonpositive yield or weather-cell count")
    if not values.coverage_fraction.between(0.999, 1 + 1e-8).all():
        raise ValueError("year output geometric coverage fails the contract")
    if not values.weather_valid_coverage_fraction.between(0, 1 + 1e-8).all():
        raise ValueError("year output weather-valid polygon coverage is outside [0,1]")
    if (values.weather_valid_area_relative_to_declared_land < 0.95).any():
        raise ValueError("year output weather-valid area fails the declared-land gate")
    if set(frame.weather_source_id.astype(str)) != {WEATHER_SOURCE_ID}:
        raise ValueError("year output weather source changed")
    if set(frame.weather_grid_id.astype(str)) != {WEATHER_GRID_ID}:
        raise ValueError("year output weather grid changed")
    if set(frame.weight_role.astype(str)) != {"county_polygon_primary_proxy"}:
        raise ValueError("year output weight role changed")
    if set(frame.weather_day_alignment.astype(str)) != {DAY_ALIGNMENT}:
        raise ValueError("year output weather day alignment changed")
    if not np.allclose(
        pd.to_numeric(frame.wet_day_threshold_mm, errors="raise"), 1.0, rtol=0, atol=0
    ):
        raise ValueError("year output wet-day threshold changed")
    exact_calendar = {
        "calendar_source_id": "usda_nass_field_crops_usual_dates_2010",
        "calendar_vintage": "2010",
        "calendar_role": "fixed_primary",
        "calendar_boundary_rule": (
            "floor_midpoint_of_most_active_planting_and_harvest_intervals"
        ),
        "stage_definition": "equal_duration_0_30_70_100_engineering_proxy",
    }
    for column, expected_value in exact_calendar.items():
        if set(frame[column].astype(str)) != {expected_value}:
            raise ValueError(f"year output {column} changed")
    shared = [*SHARED_FEATURE_METADATA, *[column for column in frame.columns if column.startswith(
        ("stage1_", "stage2_", "stage3_")
    )], "precip_mm", "tmean_c", "tmin_mean_c", "tmax_mean_c", "wet_days_n",
        "cdd_max_days", "rx1day_mm", "rx5day_mm", "precipitation_concentration_hhi",
        "precipitation_timing_centroid", "zero_precipitation_season", "wet_day_frequency",
        "mean_wet_day_intensity_mm"]
    for column in dict.fromkeys(shared):
        if frame.groupby(PAIR_KEYS, observed=True)[column].nunique(dropna=False).ne(1).any():
            raise ValueError(f"year output {column} differs between practices")


def validate_output_calendar(frame: pd.DataFrame, seasons: pd.DataFrame) -> None:
    """Require exact state/crop/year dates and lineage from the bound calendar."""
    expected_columns = [
        "state", "outcome_crop", "harvest_year", "season_start", "season_end",
        "calendar_source_id", "calendar_vintage", "calendar_role",
        "calendar_boundary_rule", "stage_definition",
    ]
    expected = seasons.rename(
        columns={"calendar_crop": "outcome_crop", "boundary_rule": "calendar_boundary_rule"}
    )[expected_columns].copy()
    actual = frame[expected_columns].drop_duplicates().copy()
    for value in [expected, actual]:
        value["season_start"] = pd.to_datetime(value.season_start, errors="raise").dt.normalize()
        value["season_end"] = pd.to_datetime(value.season_end, errors="raise").dt.normalize()
        value["harvest_year"] = pd.to_numeric(value.harvest_year, errors="raise").astype("int64")
        for column in [
            "state", "outcome_crop", "calendar_source_id", "calendar_vintage",
            "calendar_role", "calendar_boundary_rule", "stage_definition",
        ]:
            value[column] = value[column].astype("string")
    expected = expected.sort_values(["state", "outcome_crop", "harvest_year"]).reset_index(drop=True)
    actual = actual.sort_values(["state", "outcome_crop", "harvest_year"]).reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(actual, expected, check_dtype=True, check_exact=True)
    except AssertionError as error:
        raise ValueError("year output dates/metadata differ from the bound calendar") from error


def validate_year_partition_checkpoint(
    output: Path,
    receipt_path: Path,
    support: pd.DataFrame,
    *,
    expected_identity: Mapping[str, Any] | None = None,
    expected_national_sample: Mapping[str, Any] | None = None,
    expected_seasons: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Validate a year partition and receipt, including self-consistent lineage."""
    if not output.is_file() or not receipt_path.is_file():
        raise ValueError("year partition output or receipt is absent")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("year partition receipt is unreadable") from error
    identity = receipt.get("input_identity")
    if receipt.get("schema") != SCHEMA or not isinstance(identity, dict):
        raise ValueError("year partition receipt schema/input identity changed")
    if canonical_sha256(identity) != receipt.get("input_fingerprint_sha256"):
        raise ValueError("year partition receipt input fingerprint does not reconcile")
    if expected_identity is not None and identity != dict(expected_identity):
        raise ValueError("year partition receipt differs from current exact input identity")
    if support.empty or support.harvest_year.nunique() != 1:
        raise ValueError("year checkpoint validation requires one nonempty support year")
    year = int(support.harvest_year.iloc[0])
    if int(receipt.get("harvest_year", -1)) != year or int(identity.get("harvest_year", -1)) != year:
        raise ValueError("year partition receipt harvest year changed")
    bounded_geoids = identity.get("bounded_smoke_geoids")
    expected_bounded = bounded_geoids is not None
    if receipt.get("bounded_smoke") is not expected_bounded:
        raise ValueError("year partition bounded-smoke flag does not reconcile")
    if receipt.get("complete_year_support") is not (not expected_bounded):
        raise ValueError("year partition complete-support flag does not reconcile")
    if receipt.get("bounded_smoke_geoids") != bounded_geoids:
        raise ValueError("year partition bounded-smoke GEOIDs do not reconcile")
    if expected_national_sample is not None and receipt.get("registered_national_sample") != dict(
        expected_national_sample
    ):
        raise ValueError("year partition registered national sample changed")
    if receipt.get("output_sha256") != sha256_file(output):
        raise ValueError("year partition output hash changed")
    frame = pd.read_parquet(output)
    validate_year_output(frame, support)
    if expected_seasons is not None:
        validate_output_calendar(frame, expected_seasons)
    if receipt.get("output_key_sha256") != sha256_records(frame, OUTCOME_KEYS):
        raise ValueError("year partition output-key hash changed")
    audit = receipt.get("build_audit")
    if not isinstance(audit, dict):
        raise ValueError("year partition lacks its build audit")
    expected_audit = {
        "harvest_year": year,
        "counties": int(frame.county_geoid.nunique()),
        "crop_county_years": int(frame.drop_duplicates(PAIR_KEYS).shape[0]),
        "practice_rows": int(len(frame)),
        "corn_crop_county_years": int(
            frame.loc[frame.outcome_crop.eq("corn_grain")].drop_duplicates(PAIR_KEYS).shape[0]
        ),
        "soy_crop_county_years": int(
            frame.loc[frame.outcome_crop.eq("soybeans")].drop_duplicates(PAIR_KEYS).shape[0]
        ),
    }
    for key, expected in expected_audit.items():
        if audit.get(key) != expected:
            raise ValueError(f"year partition build audit differs on {key}")
    for key in [
        "cell_first_nonlinear_basis", "weather_exposure_shared_across_practices"
    ]:
        if audit.get(key) is not True:
            raise ValueError(f"year partition build audit lacks true {key}")
    for key in ["relationship_estimated", "response_estimation_authorized", "scc_authorized"]:
        if audit.get(key) is not False or receipt.get(key) is not False:
            raise ValueError(f"year partition receipt unexpectedly sets {key}")
    if receipt.get("damage_estimated") is not False:
        raise ValueError("year partition receipt unexpectedly claims damage estimation")
    return frame, receipt


def _default_partition_paths(out_dir: Path, year: int, bounded_geoids: list[str] | None) -> tuple[Path, Path]:
    if bounded_geoids is None:
        directory = out_dir / f"harvest_year={year}"
        return directory / "features.parquet", directory / "receipt.json"
    tag = canonical_sha256(sorted(bounded_geoids))[:12]
    directory = out_dir / "smoke" / f"harvest_year={year}" / f"counties={tag}"
    return directory / "features.parquet", directory / "receipt.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--panel", default=str(DEFAULT_PANEL))
    parser.add_argument("--geography", default=str(DEFAULT_GEOGRAPHY))
    parser.add_argument("--calendar", default=str(DEFAULT_CALENDAR))
    parser.add_argument("--calendar-validation", default=str(DEFAULT_BOUND_CALENDAR_RECEIPT))
    parser.add_argument("--calendar-protocol", default=str(DEFAULT_COMPETING_PROTOCOL))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--counties", default=str(DEFAULT_COUNTIES))
    parser.add_argument("--reference-climate", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--weight-dir", default=str(DEFAULT_WEIGHT_DIR))
    parser.add_argument("--inventory", default=str(DEFAULT_HTTP_INVENTORY))
    parser.add_argument("--reviewed-product", default=str(DEFAULT_REVIEWED_PRODUCT))
    parser.add_argument("--raw-weather-dir", default=str(DEFAULT_RAW_WEATHER_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--county-geoid", action="append")
    parser.add_argument("--bounded-smoke", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    paths = {
        "panel": Path(args.panel), "geography": Path(args.geography),
        "calendar": Path(args.calendar), "contract": Path(args.contract),
        "counties": Path(args.counties), "reference_climate": Path(args.reference_climate),
    }
    contract = load_contract(paths["contract"])
    calendar_receipt = validate_bound_calendar_receipt(
        paths["calendar"], Path(args.calendar_validation), Path(args.calendar_protocol)
    )
    if not int(contract["sample"]["year_min"]) <= args.year <= int(contract["sample"]["year_max"]):
        raise ValueError("requested harvest year lies outside the national contract")
    support, seasons, national_audit = prepare_support(
        read_table(paths["panel"]), read_table(paths["geography"]),
        read_table(paths["calendar"]), contract,
    )
    year_support = support.loc[support.harvest_year.eq(args.year)].copy()
    year_seasons = seasons.loc[seasons.harvest_year.eq(args.year)].copy()
    bounded_geoids: list[str] | None = None
    if args.county_geoid:
        if not args.bounded_smoke:
            raise ValueError("county subsets require --bounded-smoke")
        bounded_geoids = sorted(dict.fromkeys(args.county_geoid))
        unknown = sorted(set(bounded_geoids) - set(year_support.county_geoid.astype(str)))
        if unknown:
            raise ValueError(f"bounded-smoke counties lack support in {args.year}: {unknown}")
        year_support = year_support.loc[year_support.county_geoid.isin(bounded_geoids)].copy()
        required_calendar = year_support[["state", "outcome_crop", "harvest_year"]].drop_duplicates()
        year_seasons = required_calendar.merge(
            year_seasons.rename(columns={"calendar_crop": "outcome_crop"}),
            on=["state", "outcome_crop", "harvest_year"], how="left", validate="many_to_one",
        ).rename(columns={"outcome_crop": "calendar_crop"})
    elif args.bounded_smoke:
        raise ValueError("--bounded-smoke requires at least one --county-geoid")
    if year_support.empty:
        raise ValueError("requested year/subset has no eligible outcomes")

    reference_paths, reference_records = validate_acquired_months(
        [(1981, 1)], inventory_path=Path(args.inventory),
        reviewed_product_path=Path(args.reviewed_product),
        raw_weather_dir=Path(args.raw_weather_dir),
    )
    if paths["reference_climate"].resolve() != reference_paths[0].resolve():
        raise ValueError("weight reference climate differs from the validated acquisition object")
    weight_lineage_support = support.loc[
        support.county_geoid.isin(year_support.county_geoid.unique())
    ].copy()
    weights, weight_receipts = validate_weight_partitions(
        Path(args.weight_dir), weight_lineage_support,
        contract_path=paths["contract"], panel_path=paths["panel"],
        geography_path=paths["geography"], calendar_path=paths["calendar"],
        calendar_validation_path=Path(args.calendar_validation),
        calendar_protocol_path=Path(args.calendar_protocol),
        counties_path=paths["counties"], reference_identity=reference_records[0],
    )
    months = required_month_keys(year_seasons)
    climate_paths, climate_records = validate_acquired_months(
        months, inventory_path=Path(args.inventory),
        reviewed_product_path=Path(args.reviewed_product),
        raw_weather_dir=Path(args.raw_weather_dir),
    )
    cells = (
        weights[["grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon"]]
        .drop_duplicates()
        .sort_values(["grid_lat_index", "grid_lon_index"])
        .reset_index(drop=True)
    )
    input_identity = {
        "schema": SCHEMA,
        "harvest_year": args.year,
        "bounded_smoke_geoids": bounded_geoids,
        "contract_sha256": sha256_file(paths["contract"]),
        "panel_sha256": sha256_file(paths["panel"]),
        "geography_sha256": sha256_file(paths["geography"]),
        "calendar_sha256": sha256_file(paths["calendar"]),
        "calendar_validation_sha256": sha256_file(Path(args.calendar_validation)),
        "calendar_protocol_sha256": sha256_file(Path(args.calendar_protocol)),
        "calendar_receipt_status": calendar_receipt["status"],
        "builder_sha256": sha256_file(Path(__file__)),
        "support_outcome_key_sha256": sha256_records(year_support, OUTCOME_KEYS),
        "weather_months": climate_records,
        "weight_partitions": weight_receipts,
    }
    fingerprint = canonical_sha256(input_identity)
    output, receipt_path = _default_partition_paths(Path(args.out_dir), args.year, bounded_geoids)
    if not args.force and output.is_file() and receipt_path.is_file():
        try:
            existing, _ = validate_year_partition_checkpoint(
                output, receipt_path, year_support,
                expected_identity=input_identity,
                expected_national_sample=national_audit,
                expected_seasons=year_seasons,
            )
            print(
                f"resumed validated {args.year} feature partition with {len(existing)} rows; "
                "no response estimated"
            )
            return
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            pass

    dates, climate = load_daily_unique_cells(climate_paths, cells)
    panel, build_audit = build_year_panel(
        year_support, year_seasons, weights, cells, dates, climate, contract
    )
    validate_year_output(panel, year_support)
    validate_output_calendar(panel, year_seasons)
    atomic_write_parquet(output, panel)
    receipt = {
        "schema": SCHEMA,
        "harvest_year": args.year,
        "bounded_smoke": bounded_geoids is not None,
        "bounded_smoke_geoids": bounded_geoids,
        "complete_year_support": bounded_geoids is None,
        "input_fingerprint_sha256": fingerprint,
        "input_identity": input_identity,
        "output_path": str(output),
        "output_sha256": sha256_file(output),
        "output_key_sha256": sha256_records(panel, OUTCOME_KEYS),
        "build_audit": build_audit,
        "registered_national_sample": national_audit,
        "county_proxy_interpretation": "fixed 2019 legal county polygon area average, not crop-pixel or average-farm weather",
        "stage_interpretation": "equal-duration engineering proxy, not observed phenology",
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "damage_estimated": False,
        "scc_authorized": False,
    }
    atomic_write_json(receipt_path, receipt)
    print(
        f"wrote {len(panel)} rows for harvest year {args.year}; "
        f"bounded_smoke={bounded_geoids is not None}; no response estimated"
    )


if __name__ == "__main__":
    main()
