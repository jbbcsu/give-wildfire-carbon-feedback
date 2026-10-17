#!/usr/bin/env python3
"""Build exact-support climate-only county SPEI panels after all 15 extensions pass.

The production entry point is deliberately ordered so that it inspects only
small result/validation receipts until every future 11-cell case is present
and independently validated.  It never projects outcome columns and never
fits or invokes response code.
"""
from __future__ import annotations

import argparse
import calendar
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import resource
import shutil
import sys
import tomllib
from typing import Iterable, Iterator

import h5py
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from audit_us_direct_practice_spei_bridge_readiness import (  # noqa: E402
    audit_coverage,
    load_counties,
)

DEFAULT_CONFIG = ROOT / "config/us_spei_bridge_post_queue_v1.toml"
SAMPLE_COLUMNS = [
    "county_geoid", "state", "outcome_crop", "harvest_year", "irrigation_practice",
    "feature_construction_eligible", "season_start", "season_end", "calendar_source_id",
    "calendar_vintage", "calendar_boundary_rule", "stage_definition",
]
FALSE_GATES = (
    "bridge_to_nass_response", "fit_outcomes", "future_yield_projection",
    "causal_claim", "damage", "scc",
)
FORBIDDEN_OUTPUT_FRAGMENTS = ("yield", "production", "source_value_raw", "outcome_value")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return raw if sys.platform == "darwin" else raw * 1024


def resolve(path: str | Path) -> Path:
    value = Path(path)
    if not value.is_absolute():
        return ROOT / value
    if value.exists():
        return value
    # Some frozen manifests retain the absolute path of the machine that
    # produced them.  Preserve the manifest hash, but relocate its `data/...`
    # suffix to the current verified project root when the original path is
    # unavailable (for example, on the compute server).
    if "data" in value.parts:
        data_index = value.parts.index("data")
        relocated = ROOT.joinpath(*value.parts[data_index:])
        if relocated.exists():
            return relocated
    return value


def load_contract(path: Path) -> dict:
    contract = tomllib.loads(path.read_text())
    require(contract["contract_id"] in {"us_spei_bridge_post_queue_v1", "us_spei_bridge_post_queue_v2"},
            "contract identity changed")
    require(not any(contract["authorization"].values()), "every outcome/downstream authorization must remain false")
    require(contract["future"]["expected_cases"] == 15, "future case count changed")
    require(contract["future"]["models"] == [
        "gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll"
    ], "future model order changed")
    require(contract["future"]["scenarios"] == ["ssp126", "ssp370", "ssp585"], "scenario order changed")
    require(contract["index"]["scales_months"] == [1, 3, 6], "SPEI scale family changed")
    require(contract["geography"]["minimum_geometric_coverage"] == 0.999, "coverage rule changed")
    require(contract["decision"]["moisture_family_rule"] ==
            "SPEI_and_direct_rainfall_are_competing_families_and_must_not_be_stacked_or_added",
            "moisture-family nonstacking rule changed")
    return contract


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _bound_json(path: Path, expected_sha256: str, label: str) -> dict:
    require(path.is_file(), f"{label} missing: {path}")
    require(digest(path) == expected_sha256, f"{label} hash changed")
    return _read_json(path)


def _all_false(gates: dict, names: Iterable[str] = FALSE_GATES) -> bool:
    return all(gates.get(name) is False for name in names)


def collect_upstream_registry(contract: dict) -> dict:
    """Validate the all-15 receipt gate before any bulk cube or sample read."""
    future = contract["future"]
    queue_path = resolve(future["queue_manifest"])
    queue = _bound_json(queue_path, future["queue_manifest_sha256"], "future queue manifest")
    expected = [(model, scenario) for model in future["models"] for scenario in future["scenarios"]]
    queue_cases = [(item["esm"], item["scenario"]) for item in queue["cases"]]
    require(queue["case_count"] == 15 and queue_cases == expected, "future queue is not the exact ordered 15-case family")

    # Phase 1 is intentionally limited to small receipts. Missing case 4 or
    # later stops here, before any 31,208-cell cube, panel, or shapefile read.
    extension_receipts = []
    for model, scenario in expected:
        directory = resolve(future["extension_root"]) / f"{model}_{scenario}"
        result_path, validation_path = directory / "result.json", directory / "validation.json"
        require(result_path.is_file() and validation_path.is_file(),
                f"all-15 extension gate closed: missing validated case {model}_{scenario}")
        result, validation = _read_json(result_path), _read_json(validation_path)
        result_hash = digest(result_path)
        require(result["schema"] == "us_spei_bridge_future_case_result_v1", "future extension result schema changed")
        require((result["esm"], result["scenario"]) == (model, scenario), "future extension case identity changed")
        require(result["cells"] == future["extension_cells"] and result["months"] == future["months"],
                "future extension dimensions changed")
        require(result["scales"] == contract["index"]["scales_months"], "future extension scale axis changed")
        require(_all_false(result["gates"]), "future extension opened an outcome/downstream gate")
        require(validation["status"] == "passed" and validation["pair_result_sha256"] == result_hash,
                f"future extension is not independently validated: {model}_{scenario}")
        require((validation["esm"], validation["scenario"]) == (model, scenario), "future validation identity changed")
        require(_all_false(validation["gates"]), "future extension validation opened a downstream gate")
        extension_receipts.append((model, scenario, result_path, validation_path, result, validation))
    require(len(extension_receipts) == 15, "all-15 extension gate did not close exactly")

    # Phase 2 may bind data artifacts only after all 15 validations above pass.
    cases = []
    for model, scenario, ext_result_path, ext_validation_path, ext_result, ext_validation in extension_receipts:
        base_dir = resolve(future["base_root"]) / f"{model}_{scenario}"
        base_result_path, base_validation_path = base_dir / "result.json", base_dir / "validation.json"
        base_result, base_validation = _read_json(base_result_path), _read_json(base_validation_path)
        base_result_hash = digest(base_result_path)
        require(base_result["schema"] == "isimip3b_late_drought_pair_result_v1", "future base result schema changed")
        require((base_result["esm"], base_result["scenario"]) == (model, scenario), "future base identity changed")
        require(base_result["support_cells"] == future["base_cells"], "future base cell count changed")
        require(base_validation["status"] == "passed" and base_validation["pair_result_sha256"] == base_result_hash,
                "future base independent validation failed")
        base_cube = resolve(base_result["output"]["path"])
        ext_cube = resolve(ext_result["output"]["path"])
        require(digest(base_cube) == base_result["output"]["sha256"] == base_validation["output_sha256"],
                "future base cube identity changed")
        require(digest(ext_cube) == ext_result["output"]["sha256"] == ext_validation["output_sha256"],
                "future extension cube identity changed")
        cases.append({
            "model": model, "scenario": scenario,
            "base_result": base_result_path, "base_validation": base_validation_path, "base_cube": base_cube,
            "extension_result": ext_result_path, "extension_validation": ext_validation_path, "extension_cube": ext_cube,
        })

    historical = contract["historical"]
    manifest_path, manifest_validation_path = resolve(historical["base_manifest"]), resolve(historical["base_validation"])
    manifest = _bound_json(manifest_path, historical["base_manifest_sha256"], "historical base manifest")
    manifest_validation = _bound_json(
        manifest_validation_path, historical["base_validation_sha256"], "historical base validation"
    )
    require(manifest_validation["status"] == "passed" and manifest_validation["cells"] == historical["base_cells"]
            and manifest_validation["months"] == historical["months"], "historical base validation failed")
    require(len(manifest["records"]) == 61 and sum(r["cell_count"] for r in manifest["records"]) == historical["base_cells"],
            "historical base manifest scope changed")
    hist_result_path, hist_validation_path = resolve(historical["extension_result"]), resolve(historical["extension_validation"])
    hist_result = _bound_json(hist_result_path, historical["extension_result_sha256"], "historical extension result")
    hist_validation = _bound_json(
        hist_validation_path, historical["extension_validation_sha256"], "historical extension validation"
    )
    require(hist_validation["status"] == "passed" and hist_validation["result"]["sha256"] == digest(hist_result_path),
            "historical extension independent validation failed")
    require(hist_result["cells"] == historical["extension_cells"] and hist_result["months"] == historical["months"],
            "historical extension dimensions changed")
    require(_all_false(hist_result["gates"]), "historical extension opened a downstream gate")
    hist_cube = resolve(hist_result["output"]["path"])
    require(digest(hist_cube) == hist_result["output"]["sha256"], "historical extension cube identity changed")
    return {
        "queue_path": queue_path, "historical_manifest_path": manifest_path,
        "historical_manifest_validation_path": manifest_validation_path,
        "historical_manifest": manifest, "historical_extension_result_path": hist_result_path,
        "historical_extension_validation_path": hist_validation_path, "historical_extension_cube": hist_cube,
        "cases": cases,
    }


def load_sample(contract: dict) -> pd.DataFrame:
    sample = contract["sample"]
    path = resolve(sample["panel"])
    require(digest(path) == sample["panel_sha256"], "sample panel hash changed")
    require(not set(sample["outcome_columns_forbidden"]) & set(SAMPLE_COLUMNS), "outcome entered metadata projection")
    frame = pd.read_parquet(path, columns=SAMPLE_COLUMNS)
    frame = frame.loc[
        frame.outcome_crop.eq(sample["crop"])
        & frame.irrigation_practice.eq(sample["practice"])
        & frame.harvest_year.between(sample["year_min"], sample["year_max"])
    ].copy()
    frame["county_geoid"] = frame.county_geoid.astype(str).str.zfill(5)
    frame["season_start"] = pd.to_datetime(frame.season_start, errors="raise").dt.normalize()
    frame["season_end"] = pd.to_datetime(frame.season_end, errors="raise").dt.normalize()
    require(len(frame) == sample["expected_rows"] and frame.county_geoid.nunique() == sample["expected_counties"],
            "metadata-only sample support changed")
    require(frame.state.nunique() == sample["expected_states"] and frame.feature_construction_eligible.all(),
            "metadata-only sample state/eligibility changed")
    require((frame.season_start.dt.year == frame.harvest_year).all()
            and (frame.season_end.dt.year == frame.harvest_year).all()
            and (frame.season_end > frame.season_start).all(), "sample calendar boundaries changed")
    return frame.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)


def native_key_arrays(dataset) -> list[tuple[int, int]]:
    return list(zip(np.asarray(dataset["native_lat_index"], dtype=np.int64).tolist(),
                    np.asarray(dataset["native_lon_index"], dtype=np.int64).tolist()))


def _historical_chunks(registry: dict, contract: dict) -> Iterator[tuple[list[tuple[int, int]], np.ndarray, pd.DatetimeIndex]]:
    expected_months = pd.date_range("1981-01-01", "2019-12-01", freq="MS")
    for record in registry["historical_manifest"]["records"]:
        path = resolve(record["output"]["path"])
        require(digest(path) == record["output"]["sha256"], "historical base block hash changed")
        with xr.open_dataset(path, engine="h5netcdf", cache=False) as dataset:
            months = pd.DatetimeIndex(dataset.month.values)
            require(months.equals(expected_months), "historical base month axis changed")
            require(list(map(int, dataset.scale.values)) == contract["index"]["scales_months"], "historical scale axis changed")
            yield native_key_arrays(dataset), np.asarray(dataset.spei.values, dtype=np.float64), months
    path = registry["historical_extension_cube"]
    with xr.open_dataset(path, engine="h5netcdf", cache=False) as dataset:
        months = pd.DatetimeIndex(dataset.month.values)
        require(months.equals(expected_months), "historical extension month axis changed")
        require(list(map(int, dataset.scale.values)) == contract["index"]["scales_months"], "historical extension scales changed")
        yield native_key_arrays(dataset), np.asarray(dataset.spei.values, dtype=np.float64), months


def _future_chunks(case: dict, contract: dict, wanted: set[tuple[int, int]],
                   expected_support: set[tuple[int, int]]) -> Iterator[tuple[list[tuple[int, int]], np.ndarray, pd.DatetimeIndex]]:
    expected_months = pd.date_range("2091-01-01", "2100-12-01", freq="MS")
    with h5py.File(case["base_cube"], "r") as handle:
        months = pd.DatetimeIndex(handle["month"][:].astype("datetime64[ns]"))
        require(months.equals(expected_months), "future base month axis changed")
        require(list(map(int, handle["scale"][:])) == contract["index"]["scales_months"], "future base scales changed")
        all_keys = list(zip(handle["native_lat_index"][:].astype(int).tolist(),
                            handle["native_lon_index"][:].astype(int).tolist()))
        require(len(all_keys) == len(set(all_keys)) == contract["future"]["base_cells"], "future base support changed")
        positions = np.asarray([i for i, key in enumerate(all_keys) if key in wanted], dtype=np.int64)
        selected_keys = [all_keys[int(i)] for i in positions]
        values = np.asarray(handle["spei"][:, :, positions], dtype=np.float64)
        yield selected_keys, values, months
    with xr.open_dataset(case["extension_cube"], engine="h5netcdf", cache=False) as dataset:
        months = pd.DatetimeIndex(dataset.month.values)
        require(months.equals(expected_months), "future extension month axis changed")
        extension_keys = native_key_arrays(dataset)
        require(len(extension_keys) == len(set(extension_keys)) == contract["future"]["extension_cells"],
                "future extension support changed")
        require(not set(all_keys).intersection(extension_keys)
                and len(set(all_keys).union(extension_keys)) == contract["future"]["merged_cells"],
                "future base-plus-extension support is not the exact disjoint 31,219-cell merge")
        require(set(all_keys).union(extension_keys) == expected_support,
                "future merged support differs from the historical 31,219-cell support")
        positions = [i for i, key in enumerate(extension_keys) if key in wanted]
        selected_keys = [extension_keys[i] for i in positions]
        yield selected_keys, np.asarray(dataset.spei.values[:, :, positions], dtype=np.float64), months


def source_support(registry: dict, contract: dict) -> set[tuple[int, int]]:
    keys: set[tuple[int, int]] = set()
    count = 0
    for record in registry["historical_manifest"]["records"]:
        path = resolve(record["output"]["path"])
        with xr.open_dataset(path, engine="h5netcdf", cache=False) as dataset:
            block = native_key_arrays(dataset)
        require(not keys.intersection(block), "historical base support contains duplicate native cells")
        keys.update(block); count += len(block)
    require(count == contract["historical"]["base_cells"], "historical base support count changed")
    with xr.open_dataset(registry["historical_extension_cube"], engine="h5netcdf", cache=False) as dataset:
        extension = native_key_arrays(dataset)
    require(len(extension) == len(set(extension)) == contract["historical"]["extension_cells"],
            "historical extension support changed")
    require(not keys.intersection(extension), "historical extension overlaps base support")
    keys.update(extension)
    require(len(keys) == contract["historical"]["merged_cells"], "merged historical support count changed")
    return keys


def key_to_coordinate(key: tuple[int, int]) -> tuple[float, float]:
    row, column = key
    return round(89.75 - 0.5 * row, 2), round((-179.75 + 0.5 * column) % 360, 2)


def build_exact_weights(contract: dict, sample: pd.DataFrame, support: set[tuple[int, int]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    geography = contract["geography"]
    shapefile = resolve(geography["tiger_shapefile"])
    for suffix, key in ((".shp", "tiger_shp_sha256"), (".shx", "tiger_shx_sha256"),
                        (".dbf", "tiger_dbf_sha256"), (".prj", "tiger_prj_sha256")):
        require(digest(shapefile.with_suffix(suffix)) == geography[key], f"TIGER {suffix} hash changed")
    available = {key_to_coordinate(key) for key in support}
    counties = load_counties(shapefile, set(sample.county_geoid))
    coverage, weights, _missing = audit_coverage(counties, available, geography["minimum_geometric_coverage"])
    require(len(coverage) == coverage.county_geoid.nunique() == geography["expected_counties_passing"],
            "county coverage scope changed")
    require(coverage.passes_0_999_gate.all(), "exact 361-county coverage gate failed after support merge")
    require((weights.groupby("county_geoid").spatial_weight_within_available.sum() - 1.0).abs().max() < 2e-15,
            "county weights do not normalize")
    return coverage.reset_index(drop=True), weights.reset_index(drop=True)


def accumulate_county_monthly(
    chunks: Iterable[tuple[list[tuple[int, int]], np.ndarray, pd.DatetimeIndex]],
    weights: pd.DataFrame,
    expected_source_cells: int,
) -> tuple[np.ndarray, pd.DatetimeIndex, list[str]]:
    counties = sorted(weights.county_geoid.astype(str).unique())
    county_index = {value: i for i, value in enumerate(counties)}
    weight_map: dict[tuple[int, int], list[tuple[int, float]]] = {}
    for row in weights.itertuples(index=False):
        key = (int(row.native_lat_index), int(row.native_lon_index))
        weight_map.setdefault(key, []).append((county_index[str(row.county_geoid)], float(row.spatial_weight_within_available)))
    numerator = denominator = None
    months = None
    source_keys: set[tuple[int, int]] = set()
    used_keys: set[tuple[int, int]] = set()
    for keys, values, chunk_months in chunks:
        require(values.ndim == 3 and values.shape[0] == 3 and values.shape[2] == len(keys), "SPEI chunk dimensions invalid")
        require(len(keys) == len(set(keys)) and not source_keys.intersection(keys), "source cell appears more than once")
        source_keys.update(keys)
        if months is None:
            months = chunk_months
            shape = (3, len(months), len(counties))
            numerator, denominator = np.zeros(shape, dtype=np.float64), np.zeros(shape, dtype=np.float64)
        require(months.equals(chunk_months) and values.shape[1] == len(months), "source month axes differ")
        for local, key in enumerate(keys):
            targets = weight_map.get(key)
            if not targets:
                continue
            used_keys.add(key)
            vector = values[:, :, local]
            finite = np.isfinite(vector)
            for county, weight in targets:
                numerator[:, :, county] += np.where(finite, vector * weight, 0.0)
                denominator[:, :, county] += finite * weight
    require(len(source_keys) == expected_source_cells, "merged source cell count changed")
    require(used_keys == set(weight_map), "one or more weighted cells is absent from merged climate support")
    positive = denominator > 1e-14
    partial = positive & ~np.isclose(denominator, 1.0, atol=2e-12, rtol=0)
    require(not partial.any(), "county-month has partial spatial coverage; renormalization is prohibited")
    result = np.full_like(numerator, np.nan)
    result[positive] = numerator[positive] / denominator[positive]
    return result, months, counties


def month_overlaps(start: pd.Timestamp, end: pd.Timestamp) -> list[tuple[tuple[int, int], int]]:
    current = date(start.year, start.month, 1)
    result = []
    while current <= end.date():
        last = date(current.year, current.month, calendar.monthrange(current.year, current.month)[1])
        left, right = max(start.date(), current), min(end.date(), last)
        if left <= right:
            result.append(((current.year, current.month), (right - left).days + 1))
        current = date(current.year + int(current.month == 12), current.month % 12 + 1, 1)
    return result


def build_season_panel(values: np.ndarray, months: pd.DatetimeIndex, counties: list[str], calendar_rows: pd.DataFrame) -> pd.DataFrame:
    lookup = {(item.year, item.month): i for i, item in enumerate(months)}
    county_lookup = {value: i for i, value in enumerate(counties)}
    rows = []
    for source in calendar_rows.itertuples(index=False):
        geoid = str(source.county_geoid)
        require(geoid in county_lookup, f"calendar county absent from climate weights: {geoid}")
        overlaps = month_overlaps(source.season_start, source.season_end)
        positions = [lookup[key] for key, _days in overlaps if key in lookup]
        require(len(positions) == len(overlaps), "calendar month is outside climate source")
        days = np.asarray([day_count for _key, day_count in overlaps], dtype=np.float64)
        expected_days = int((source.season_end - source.season_start).days + 1)
        require(int(days.sum()) == expected_days, "calendar-day overlap accounting changed")
        item = {
            "county_geoid": geoid, "state": str(source.state), "crop": "corn_grain",
            "practice": "non_irrigated", "harvest_year": int(source.harvest_year),
            "season_start": source.season_start, "season_end": source.season_end,
            "season_days": expected_days, "calendar_source_id": str(source.calendar_source_id),
            "calendar_vintage": str(source.calendar_vintage),
            "calendar_boundary_rule": str(source.calendar_boundary_rule),
            "stage_definition": str(source.stage_definition),
        }
        for scale_index, scale in enumerate((1, 3, 6)):
            vector = values[scale_index, positions, county_lookup[geoid]]
            require(np.isfinite(vector).all(), f"nonfinite SPEI-{scale} within a frozen county season")
            item[f"spei_{scale}_day_weighted_mean"] = math.fsum((vector * days).tolist()) / expected_days
            item[f"spei_{scale}_monthly_minimum"] = float(vector.min())
            item[f"spei_{scale}_source_months"] = len(vector)
        item.update(analysis_role="climate_only_no_outcome_response", response_estimation_authorized=False,
                    projection_authorized=False, damage_authorized=False, scc_authorized=False)
        rows.append(item)
    result = pd.DataFrame(rows)
    require(not any(fragment in column.lower() for column in result.columns for fragment in FORBIDDEN_OUTPUT_FRAGMENTS),
            "outcome-like column entered climate-only season panel")
    require(not result.duplicated(["county_geoid", "harvest_year"]).any(), "season panel keys duplicated")
    return result.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)


def build_monthly_panel(values: np.ndarray, months: pd.DatetimeIndex, counties: list[str], state_by_county: dict[str, str]) -> pd.DataFrame:
    frame = pd.DataFrame({
        "county_geoid": np.repeat(counties, len(months)),
        "state": np.repeat([state_by_county[county] for county in counties], len(months)),
        "date": np.tile(months.to_numpy(), len(counties)),
        "spei_1": values[0].T.reshape(-1), "spei_3": values[1].T.reshape(-1), "spei_6": values[2].T.reshape(-1),
    })
    frame["analysis_role"] = "climate_only_no_outcome_response"
    frame["response_estimation_authorized"] = False
    frame["scc_authorized"] = False
    require(not frame.duplicated(["county_geoid", "date"]).any(), "monthly county keys duplicated")
    return frame


def future_calendar(sample: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    states = sample[["state", "calendar_source_id", "calendar_vintage", "calendar_boundary_rule", "stage_definition"]].drop_duplicates()
    require(states.groupby("state").size().eq(1).all(), "calendar metadata vary within state")
    windows = sample.assign(start_mmdd=sample.season_start.dt.strftime("%m-%d"), end_mmdd=sample.season_end.dt.strftime("%m-%d"))
    windows = windows[["state", "start_mmdd", "end_mmdd"]].drop_duplicates()
    require(windows.groupby("state").size().eq(1).all(), "frozen calendar month-days vary within state")
    counties = sample[["county_geoid", "state"]].drop_duplicates()
    require(len(counties) == sample.county_geoid.nunique(), "county-state mapping is not unique")
    base = counties.merge(windows, on="state", validate="many_to_one").merge(states, on="state", validate="many_to_one")
    rows = []
    for row in base.itertuples(index=False):
        for year in years:
            rows.append({
                "county_geoid": row.county_geoid, "state": row.state, "harvest_year": year,
                "season_start": pd.Timestamp(f"{year}-{row.start_mmdd}"),
                "season_end": pd.Timestamp(f"{year}-{row.end_mmdd}"),
                "calendar_source_id": row.calendar_source_id, "calendar_vintage": row.calendar_vintage,
                "calendar_boundary_rule": row.calendar_boundary_rule, "stage_definition": row.stage_definition,
            })
    result = pd.DataFrame(rows)
    require(not result.duplicated(["county_geoid", "harvest_year"]).any(), "future calendar keys duplicated")
    return result


def write_parquet_atomic(frame: pd.DataFrame, path: Path, compression: str) -> None:
    partial = path.with_suffix(path.suffix + ".partial")
    require(not partial.exists(), "stale partial parquet exists")
    frame.to_parquet(partial, index=False, compression=compression)
    partial.replace(path)


def write_streamed_parquet(frames: Iterable[pd.DataFrame], path: Path, compression: str) -> int:
    partial = path.with_suffix(path.suffix + ".partial")
    require(not partial.exists(), "stale partial parquet exists")
    writer = None
    rows = 0
    try:
        for frame in frames:
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(partial, table.schema, compression=compression)
            require(table.schema == writer.schema, "streamed parquet schema changed between cases")
            writer.write_table(table); rows += len(frame)
    finally:
        if writer is not None:
            writer.close()
    require(writer is not None, "no frames supplied for streamed parquet")
    partial.replace(path)
    return rows


def _artifact(path: Path, published_dir: Path) -> dict:
    return {"path": str((published_dir / path.name).relative_to(ROOT)),
            "bytes": path.stat().st_size, "sha256": digest(path)}


def _binding(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    require(not output_dir.exists() and not output_dir.with_name(output_dir.name + ".partial").exists(),
            "fresh output directory and no stale partial required")
    contract = load_contract(config_path)
    registry = collect_upstream_registry(contract)  # mandatory first access gate
    sample = load_sample(contract)
    support = source_support(registry, contract)
    coverage, weights = build_exact_weights(contract, sample, support)
    partial = output_dir.with_name(output_dir.name + ".partial")
    partial.mkdir(parents=True)
    compression = contract["outputs"]["parquet_compression"]
    try:
        coverage_path, weights_path = partial / "county_coverage.csv", partial / "county_cell_weights.parquet"
        coverage.to_csv(coverage_path, index=False)
        write_parquet_atomic(weights, weights_path, compression)
        historical, historical_months, counties = accumulate_county_monthly(
            _historical_chunks(registry, contract), weights, contract["historical"]["merged_cells"]
        )
        state_by_county = dict(sample[["county_geoid", "state"]].drop_duplicates().itertuples(index=False, name=None))
        historical_monthly = build_monthly_panel(historical, historical_months, counties, state_by_county)
        historical_season = build_season_panel(historical, historical_months, counties, sample)
        require(len(historical_monthly) == contract["outputs"]["expected_historical_monthly_rows"], "historical monthly row count changed")
        require(len(historical_season) == contract["outputs"]["expected_historical_season_rows"], "historical season row count changed")
        hist_monthly_path = partial / "historical_county_monthly_spei.parquet"
        hist_season_path = partial / "historical_county_season_spei.parquet"
        write_parquet_atomic(historical_monthly, hist_monthly_path, compression)
        write_parquet_atomic(historical_season, hist_season_path, compression)

        future_calendar_rows = future_calendar(sample, contract["future"]["harvest_years"])
        future_monthly_path = partial / "future_county_monthly_spei.parquet"
        future_season_path = partial / "future_county_season_spei.parquet"
        future_summaries = []
        weighted_keys = {(int(row.native_lat_index), int(row.native_lon_index)) for row in weights.itertuples(index=False)}

        def future_frames(kind: str):
            for case in registry["cases"]:
                values, months, case_counties = accumulate_county_monthly(
                    _future_chunks(case, contract, weighted_keys, support),
                    weights, len(weighted_keys),
                )
                require(case_counties == counties, "future county order differs from historical")
                frame = (build_monthly_panel(values, months, counties, state_by_county) if kind == "monthly"
                         else build_season_panel(values, months, counties, future_calendar_rows))
                frame.insert(0, "model", case["model"]); frame.insert(1, "scenario", case["scenario"])
                if kind == "season":
                    future_summaries.append({"model": case["model"], "scenario": case["scenario"],
                                             "rows": len(frame)})
                yield frame

        # Recompute sequentially for each output rather than retain all cases;
        # this trades bounded I/O for a hard memory ceiling.
        future_monthly_rows = write_streamed_parquet(future_frames("monthly"), future_monthly_path, compression)
        future_season_rows = write_streamed_parquet(future_frames("season"), future_season_path, compression)
        require(future_monthly_rows == contract["outputs"]["expected_future_monthly_rows"], "future monthly row count changed")
        require(future_season_rows == contract["outputs"]["expected_future_season_rows"], "future season row count changed")
        require(len(future_summaries) == 15, "future case summary count changed")
        peak = peak_rss_bytes()
        require(peak <= 512 * 1024**2, "in-process peak RSS exceeded 512 MiB")
        result = {
            "schema": "us_spei_bridge_post_queue_result_v1",
            "status": "climate_panels_completed_pending_independent_validation",
            "role": "climate_only_exact_support_county_panel_no_outcomes_no_fit",
            "contract": {"path": str(config_path.relative_to(ROOT)), "sha256": digest(config_path)},
            "all_15_extension_gate": {"passed": True, "cases": 15},
            "upstream": {
                "historical_base_manifest": _binding(registry["historical_manifest_path"]),
                "historical_base_validation": _binding(registry["historical_manifest_validation_path"]),
                "historical_extension_result": _binding(registry["historical_extension_result_path"]),
                "historical_extension_validation": _binding(registry["historical_extension_validation_path"]),
                "historical_extension_cube": _binding(registry["historical_extension_cube"]),
                "future_cases": [{
                    "model": case["model"], "scenario": case["scenario"],
                    "base_result": _binding(case["base_result"]),
                    "base_validation": _binding(case["base_validation"]),
                    "base_cube": _binding(case["base_cube"]),
                    "extension_result": _binding(case["extension_result"]),
                    "extension_validation": _binding(case["extension_validation"]),
                    "extension_cube": _binding(case["extension_cube"]),
                } for case in registry["cases"]],
            },
            "sample": {"rows": len(sample), "counties": sample.county_geoid.nunique(), "states": sample.state.nunique(),
                       "columns_read": SAMPLE_COLUMNS, "outcome_columns_read": []},
            "support": {"base_cells": contract["historical"]["base_cells"], "extension_cells": 11,
                        "merged_cells": len(support), "counties": len(coverage),
                        "counties_passing_0_999": int(coverage.passes_0_999_gate.sum()),
                        "minimum_coverage": float(coverage.coverage_fraction.min())},
            "future_cases": future_summaries,
            "outputs": {name: _artifact(path, output_dir) for name, path in {
                "county_coverage": coverage_path, "county_cell_weights": weights_path,
                "historical_monthly": hist_monthly_path, "historical_season": hist_season_path,
                "future_monthly": future_monthly_path, "future_season": future_season_path,
            }.items()},
            "resources": {"peak_rss_bytes": peak, "memory_cap_bytes": 512 * 1024**2},
            "gates": {"all_15_future_extensions_validated": True, "exact_361_county_support": True,
                      "historical_climate_panel_pending_validation": True, "future_climate_panel_pending_validation": True,
                      **{name: False for name in FALSE_GATES}},
            "moisture_family_rule": contract["decision"]["moisture_family_rule"],
            "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
        }
        (partial / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        partial.replace(output_dir)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    print(json.dumps({"status": result["status"], "support": result["support"], "resources": result["resources"]}))


if __name__ == "__main__":
    main()
