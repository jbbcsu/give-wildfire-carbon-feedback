#!/usr/bin/env python3
"""Build one validated U.S. direct-practice daily-heat year checkpoint."""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

from build_county_nclimgrid_feature_smoke import (
    EXPECTED_FIELDS,
    EXPECTED_TITLE,
    EXPECTED_VERSION,
    STAGE_FRACTIONS,
    validate_polygon_weights,
)
from build_daily_heat_pilot import heat_metrics
from us_national_nclimgrid_common import (
    OUTCOME_KEYS,
    PAIR_KEYS,
    PROJECT_ROOT,
    atomic_write_json,
    atomic_write_parquet,
    canonical_sha256,
    sha256_file,
    sha256_records,
    validate_acquired_months,
)


SCHEMA = "us_daily_heat_year_partition_v1"
ASSEMBLY_SCHEMA = "us_daily_heat_assembly_v1"
SCRIPT = Path(__file__).resolve()
DEFAULT_CONTRACT = PROJECT_ROOT / "us_county_validation/us_daily_heat_expansion_v1.toml"
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_features_national_v1"
DEFAULT_SOURCE_ASSEMBLY = PROJECT_ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
DEFAULT_SOURCE_RECEIPT = PROJECT_ROOT / "outputs/us_county/national_nclimgrid_features_v1/assembly_validation.json"
DEFAULT_WEIGHT_DIR = PROJECT_ROOT / "data/interim/us_county/nclimgrid_polygon_weights_national_v1"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/interim/us_county/daily_heat_national_v1"
DEFAULT_ASSEMBLY = PROJECT_ROOT / "data/interim/us_county/nass_direct_practice_daily_heat_1981_2019.parquet"
DEFAULT_ASSEMBLY_RECEIPT = PROJECT_ROOT / "data/provenance/us_daily_heat_expansion_20260907.json"


def load_contract(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        contract = tomllib.load(handle)
    if contract.get("schema") != "us_daily_heat_expansion_contract_v1":
        raise ValueError("daily-heat contract schema changed")
    if contract.get("thresholds_c") != [29.0, 30.0]:
        raise ValueError("daily-heat thresholds changed")
    if contract.get("key_fields") != PAIR_KEYS:
        raise ValueError("daily-heat key fields changed")
    resources = contract.get("resources", {})
    decisions = contract.get("decision", {})
    for gate in ("existing_local_data_only", "download_forbidden", "raw_rehydration_forbidden", "one_bounded_county_group_per_checkpoint"):
        if resources.get(gate) is not True:
            raise ValueError(f"resource gate changed: {gate}")
    if resources.get("one_harvest_year_per_checkpoint") is not False:
        raise ValueError("resource amendment does not close full-year checkpoints")
    if int(resources.get("maximum_counties_per_checkpoint", 0)) != 64:
        raise ValueError("daily-heat county batch size changed")
    for gate in (
        "coefficients_emitted", "row_predictions_emitted", "model_promotion_authorized",
        "causal_response_authorized", "future_projection_authorized", "fair_run_authorized",
        "damage_or_welfare_authorized", "scc_authorized",
    ):
        if decisions.get(gate) is not False:
            raise ValueError(f"closed decision gate changed: {gate}")
    return contract


def year_paths(directory: Path, year: int) -> tuple[Path, Path]:
    target = directory / f"harvest_year={year}"
    return target / "features.parquet", target / "receipt.json"


def batch_paths(directory: Path, year: int, batch_index: int) -> tuple[Path, Path]:
    target = directory / f"harvest_year={year}" / f"batch={batch_index:03d}"
    return target / "features.parquet", target / "receipt.json"


def county_batches(counties: list[str], maximum: int) -> list[list[str]]:
    ordered = sorted(counties)
    if not ordered or len(ordered) != len(set(ordered)) or maximum < 1:
        raise ValueError("invalid county batch support")
    return [ordered[start:start + maximum] for start in range(0, len(ordered), maximum)]


def load_source_year(source_dir: Path, year: int) -> tuple[pd.DataFrame, dict[str, Any], Path, Path]:
    feature_path, receipt_path = year_paths(source_dir, year)
    if not feature_path.is_file() or not receipt_path.is_file():
        raise ValueError(f"source feature checkpoint is absent for {year}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "us_national_nclimgrid_feature_year_partition_v1":
        raise ValueError("source year receipt schema changed")
    if receipt.get("complete_year_support") is not True or receipt.get("bounded_smoke") is not False:
        raise ValueError("source year is not the complete support checkpoint")
    if int(receipt.get("harvest_year", -1)) != year or sha256_file(feature_path) != receipt.get("output_sha256"):
        raise ValueError("source year identity/hash changed")
    frame = pd.read_parquet(feature_path).sort_values(OUTCOME_KEYS).reset_index(drop=True)
    if frame.empty or frame.duplicated(OUTCOME_KEYS).any():
        raise ValueError("source year is empty or duplicates outcome keys")
    if set(frame.harvest_year.astype(int)) != {year}:
        raise ValueError("source year payload has the wrong year")
    practices = frame.groupby(PAIR_KEYS, observed=True).irrigation_practice.agg(set)
    if not practices.map(lambda value: value == {"irrigated", "non_irrigated"}).all():
        raise ValueError("source year does not preserve exact practice pairs")
    return frame, receipt, feature_path, receipt_path


def load_bound_weights(weight_dir: Path, source_receipt: dict[str, Any], counties: list[str]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    records = source_receipt.get("input_identity", {}).get("weight_partitions")
    if not isinstance(records, list):
        raise ValueError("source receipt lacks weight lineage")
    by_county = {str(record.get("county_geoid")): record for record in records}
    if not set(counties).issubset(by_county) or len(by_county) != len(records):
        raise ValueError("source receipt does not cover the requested county batch")
    frames: list[pd.DataFrame] = []
    identities: list[dict[str, Any]] = []
    for geoid in counties:
        path = weight_dir / f"county_geoid={geoid}" / "weights.parquet"
        receipt_path = path.with_name("receipt.json")
        record = by_county[geoid]
        if not path.is_file() or not receipt_path.is_file():
            raise ValueError(f"validated weights are absent for {geoid}")
        if sha256_file(path) != record.get("output_sha256"):
            raise ValueError(f"weight payload changed for {geoid}")
        weight_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if weight_receipt.get("input_fingerprint_sha256") != record.get("input_fingerprint_sha256"):
            raise ValueError(f"weight receipt changed for {geoid}")
        frame = validate_polygon_weights(pd.read_parquet(path))
        if set(frame.county_geoid.astype(str)) != {geoid}:
            raise ValueError(f"weight payload has wrong county for {geoid}")
        frames.append(frame)
        identities.append({
            "county_geoid": geoid,
            "output_sha256": str(record["output_sha256"]),
            "input_fingerprint_sha256": str(record["input_fingerprint_sha256"]),
        })
    return pd.concat(frames, ignore_index=True), identities


def load_daily_tmax(paths: list[Path], cells: pd.DataFrame) -> tuple[pd.DatetimeIndex, np.ndarray]:
    if cells.empty or cells.duplicated(["grid_lat_index", "grid_lon_index"]).any():
        raise ValueError("selected weather cells are empty or duplicated")
    lat_index = xr.DataArray(cells.grid_lat_index.to_numpy(dtype=int), dims="cell")
    lon_index = xr.DataArray(cells.grid_lon_index.to_numpy(dtype=int), dims="cell")
    date_parts: list[pd.DatetimeIndex] = []
    value_parts: list[np.ndarray] = []
    reference_lat: np.ndarray | None = None
    reference_lon: np.ndarray | None = None
    for path in paths:
        with xr.open_dataset(path, engine="h5netcdf") as dataset:
            if set(dataset.data_vars) != set(EXPECTED_FIELDS):
                raise ValueError(f"{path.name}: nClimGrid fields changed")
            if dataset.attrs.get("title") != EXPECTED_TITLE or dataset.attrs.get("product_version") != EXPECTED_VERSION:
                raise ValueError(f"{path.name}: nClimGrid product identity changed")
            latitude = dataset.lat.values.astype(float)
            longitude = dataset.lon.values.astype(float)
            if reference_lat is None:
                reference_lat, reference_lon = latitude, longitude
            elif not (np.array_equal(reference_lat, latitude) and np.array_equal(reference_lon, longitude)):
                raise ValueError("nClimGrid coordinates changed between months")
            if not np.allclose(latitude[cells.grid_lat_index], cells.grid_lat, rtol=0, atol=1e-6):
                raise ValueError("selected latitude identity changed")
            if not np.allclose(longitude[cells.grid_lon_index], cells.grid_lon, rtol=0, atol=1e-6):
                raise ValueError("selected longitude identity changed")
            variable = dataset["tmax"]
            standard_name, units = EXPECTED_FIELDS["tmax"]
            if variable.dims != ("time", "lat", "lon") or variable.attrs.get("standard_name") != standard_name or variable.attrs.get("units") != units:
                raise ValueError(f"{path.name}: Tmax metadata changed")
            dates = pd.DatetimeIndex(dataset.time.values).normalize()
            values = variable.isel(lat=lat_index, lon=lon_index).values.astype(float)
            if values.shape != (len(dates), len(cells)) or not np.isfinite(values).all():
                raise ValueError(f"{path.name}: selected Tmax is invalid")
            date_parts.append(dates)
            value_parts.append(values)
    dates = pd.DatetimeIndex(np.concatenate([part.values for part in date_parts])).normalize()
    if dates.has_duplicates or not dates.equals(pd.date_range(dates[0], dates[-1], freq="D")):
        raise ValueError("combined Tmax chronology is not unique and contiguous")
    return dates, np.concatenate(value_parts, axis=0)


def metric_names(threshold: int, prefix: str) -> dict[str, str]:
    tag = f"{threshold}c"
    return {
        "cell_first_tmax_exceedance_c_days": f"{prefix}_tmax_exceedance_{tag}_c_days",
        "cell_first_above_threshold_days": f"{prefix}_tmax_days_gt_{tag}",
        "county_mean_first_exceedance_c_days": f"{prefix}_county_mean_first_tmax_exceedance_{tag}_c_days",
        "spatial_aggregation_gap_c_days": f"{prefix}_spatial_aggregation_gap_{tag}_c_days",
    }


def validate_heat_partition(frame: pd.DataFrame, expected_keys: pd.DataFrame, thresholds: list[float]) -> None:
    if frame.empty or frame.duplicated(PAIR_KEYS).any():
        raise ValueError("heat checkpoint is empty or duplicates keys")
    expected = expected_keys[PAIR_KEYS].sort_values(PAIR_KEYS).reset_index(drop=True)
    actual = frame[PAIR_KEYS].sort_values(PAIR_KEYS).reset_index(drop=True)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False, check_exact=True)
    numeric = [column for column in frame if any(token in column for token in ("_tmax_", "_spatial_aggregation_gap_"))]
    if not numeric or not np.isfinite(frame[numeric].to_numpy(dtype=float)).all():
        raise ValueError("heat checkpoint has missing/nonfinite metrics")
    if (frame[[column for column in numeric if "exceedance" in column or "days_gt" in column or "gap" in column]] < -1e-9).any().any():
        raise ValueError("heat checkpoint has negative threshold metrics")
    for threshold in map(int, thresholds):
        for stem in ("tmax_exceedance", "tmax_days_gt", "county_mean_first_tmax_exceedance"):
            season = frame[f"season_{stem}_{threshold}c" + ("_c_days" if stem != "tmax_days_gt" else "")]
            stages = sum(frame[f"stage{i}_{stem}_{threshold}c" + ("_c_days" if stem != "tmax_days_gt" else "")] for i in range(1, 4))
            if not np.allclose(season, stages, rtol=0, atol=1e-8):
                raise ValueError(f"stage/season heat reconciliation failed at {threshold} C")
        if (frame[f"season_county_mean_first_tmax_exceedance_{threshold}c_c_days"] > frame[f"season_tmax_exceedance_{threshold}c_c_days"] + 1e-9).any():
            raise ValueError("county-mean-first exceedance exceeds cell-first result")
    for gate in ("coefficients_emitted", "row_predictions_emitted", "causal_response_authorized", "scc_authorized"):
        if frame[gate].astype(bool).any():
            raise ValueError(f"heat checkpoint opens closed gate {gate}")


def build_year(year: int, batch_index: int, contract_path: Path, source_dir: Path, weight_dir: Path, output_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    contract = load_contract(contract_path)
    source, source_receipt, source_path, source_receipt_path = load_source_year(source_dir, year)
    shared_columns = ["state", "season_start", "season_end", "stage1_days", "stage2_days", "stage3_days", "tmax_mean_c", "stage1_tmax_mean_c", "stage2_tmax_mean_c", "stage3_tmax_mean_c"]
    for column in shared_columns:
        if source.groupby(PAIR_KEYS, observed=True)[column].nunique(dropna=False).ne(1).any():
            raise ValueError(f"source weather field differs across practices: {column}")
    all_counties = sorted(source.county_geoid.astype(str).unique().tolist())
    batches = county_batches(all_counties, int(contract["resources"]["maximum_counties_per_checkpoint"]))
    if not 0 <= batch_index < len(batches):
        raise ValueError(f"batch index must lie in [0,{len(batches) - 1}] for {year}")
    counties = batches[batch_index]
    source_subset = source.loc[source.county_geoid.astype(str).isin(counties)].copy()
    pairs = source_subset.drop_duplicates(PAIR_KEYS).sort_values(PAIR_KEYS).reset_index(drop=True)
    weights, weight_identities = load_bound_weights(weight_dir, source_receipt, counties)
    cells = weights[["grid_lat_index", "grid_lon_index", "grid_lat", "grid_lon"]].drop_duplicates().sort_values(["grid_lat_index", "grid_lon_index"]).reset_index(drop=True)
    month_records = source_receipt.get("input_identity", {}).get("weather_months")
    if not isinstance(month_records, list):
        raise ValueError("source receipt lacks monthly weather lineage")
    month_keys = [(int(record["year"]), int(record["month"])) for record in month_records]
    climate_paths, current_records = validate_acquired_months(month_keys)
    if current_records != month_records:
        raise ValueError("current climate identities differ from source year receipt")
    dates, tmax = load_daily_tmax(climate_paths, cells)
    cell_positions = {(int(row.grid_lat_index), int(row.grid_lon_index)): index for index, row in enumerate(cells.itertuples(index=False))}
    records: list[dict[str, Any]] = []
    grouping = ["state", "outcome_crop", "season_start", "season_end"]
    for group_key, group in pairs.groupby(grouping, observed=True, sort=True):
        state, crop, start, end = group_key
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        use = (dates >= start) & (dates <= end)
        expected_days = (end - start).days + 1
        if int(use.sum()) != expected_days:
            raise ValueError(f"weather does not exactly cover {state}/{crop}/{year}")
        values = tmax[use]
        bounds = [int(np.floor(fraction * expected_days)) for fraction in STAGE_FRACTIONS]
        for row in group.itertuples(index=False):
            geoid = str(row.county_geoid)
            county_weights = weights.loc[weights.county_geoid.astype(str).eq(geoid)].copy()
            positions = np.asarray([cell_positions[(int(item.grid_lat_index), int(item.grid_lon_index))] for item in county_weights.itertuples(index=False)], dtype=int)
            spatial = county_weights.spatial_weight.to_numpy(dtype=float)
            county_values = values[:, positions]
            output: dict[str, Any] = {
                "county_geoid": geoid, "outcome_crop": str(crop), "harvest_year": year,
                "state": str(state), "season_start": start, "season_end": end,
                "weather_exposure_shared_across_practices": True,
                "coefficients_emitted": False, "row_predictions_emitted": False,
                "causal_response_authorized": False, "scc_authorized": False,
            }
            for threshold_value in contract["thresholds_c"]:
                threshold = int(threshold_value)
                season_metrics = heat_metrics(county_values, spatial, threshold_value)
                for original, renamed in metric_names(threshold, "season").items():
                    output[renamed] = season_metrics[original]
                for stage, (left, right) in enumerate(zip(bounds, bounds[1:]), start=1):
                    stage_metrics = heat_metrics(county_values[left:right], spatial, threshold_value)
                    for original, renamed in metric_names(threshold, f"stage{stage}").items():
                        output[renamed] = stage_metrics[original]
                    if right - left != int(getattr(row, f"stage{stage}_days")):
                        raise ValueError("stage-day count differs from source weather panel")
                    if not np.isclose(stage_metrics["tmax_mean_c"], float(getattr(row, f"stage{stage}_tmax_mean_c")), rtol=0, atol=1e-8):
                        raise ValueError("stage Tmax mean differs from source weather panel")
                if not np.isclose(season_metrics["tmax_mean_c"], float(row.tmax_mean_c), rtol=0, atol=1e-8):
                    raise ValueError("season Tmax mean differs from source weather panel")
            records.append(output)
    frame = pd.DataFrame(records).sort_values(PAIR_KEYS).reset_index(drop=True)
    validate_heat_partition(frame, pairs[PAIR_KEYS], contract["thresholds_c"])
    identity = {
        "schema": SCHEMA, "year": year, "batch_index": batch_index,
        "total_batches": len(batches), "county_geoids": counties,
        "contract_sha256": sha256_file(contract_path), "code_sha256": sha256_file(SCRIPT),
        "protocol_sha256": sha256_file(PROJECT_ROOT / contract["protocol_path"]),
        "source_feature_sha256": sha256_file(source_path),
        "source_receipt_sha256": sha256_file(source_receipt_path),
        "source_outcome_key_sha256": sha256_records(source, OUTCOME_KEYS),
        "source_pair_key_sha256": sha256_records(pairs, PAIR_KEYS),
        "weather_months": current_records, "weight_partitions": weight_identities,
    }
    receipt = {
        "schema": SCHEMA, "status": "validated_heat_measurement_checkpoint_not_response",
        "harvest_year": year, "batch_index": batch_index, "total_batches": len(batches),
        "county_geoids": counties, "input_identity": identity,
        "input_fingerprint_sha256": canonical_sha256(identity),
        "rows": int(len(frame)), "counties": int(frame.county_geoid.nunique()),
        "thresholds_c": contract["thresholds_c"], "cell_first_nonlinear_basis": True,
        "weather_exposure_shared_across_practices": True,
        **contract["decision"],
    }
    return frame, receipt


def assemble(contract_path: Path, source_assembly: Path, source_receipt_path: Path, output_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    contract = load_contract(contract_path)
    source_receipt = json.loads(source_receipt_path.read_text(encoding="utf-8"))
    if source_receipt.get("output", {}).get("sha256") != sha256_file(source_assembly):
        raise ValueError("source assembly differs from its receipt")
    source = pd.read_parquet(source_assembly).sort_values(OUTCOME_KEYS).reset_index(drop=True)
    pairs = source.drop_duplicates(PAIR_KEYS).sort_values(PAIR_KEYS).reset_index(drop=True)
    frames: list[pd.DataFrame] = []
    partitions: list[dict[str, Any]] = []
    for year in range(int(contract["year_min"]), int(contract["year_max"]) + 1):
        year_pairs = pairs.loc[pairs.harvest_year.eq(year)].copy()
        batches = county_batches(sorted(year_pairs.county_geoid.astype(str).unique()), int(contract["resources"]["maximum_counties_per_checkpoint"]))
        for batch_index, counties in enumerate(batches):
            path, receipt_path = batch_paths(output_dir, year, batch_index)
            if not path.is_file() or not receipt_path.is_file():
                raise ValueError(f"daily-heat checkpoint is absent for {year} batch {batch_index}")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            frame = pd.read_parquet(path)
            expected = year_pairs.loc[year_pairs.county_geoid.astype(str).isin(counties), PAIR_KEYS]
            validate_heat_partition(frame, expected, contract["thresholds_c"])
            if receipt.get("schema") != SCHEMA or receipt.get("output_sha256") != sha256_file(path):
                raise ValueError(f"daily-heat checkpoint receipt changed for {year} batch {batch_index}")
            if receipt.get("input_fingerprint_sha256") != canonical_sha256(receipt.get("input_identity")):
                raise ValueError(f"daily-heat checkpoint fingerprint changed for {year} batch {batch_index}")
            if receipt.get("county_geoids") != counties or receipt.get("batch_index") != batch_index or receipt.get("total_batches") != len(batches):
                raise ValueError(f"daily-heat batch partition changed for {year} batch {batch_index}")
            frames.append(frame)
            partitions.append({"year": year, "batch_index": batch_index, "rows": len(frame), "output_sha256": receipt["output_sha256"], "receipt_sha256": sha256_file(receipt_path)})
    combined = pd.concat(frames, ignore_index=True).sort_values(PAIR_KEYS).reset_index(drop=True)
    validate_heat_partition(combined, pairs[PAIR_KEYS], contract["thresholds_c"])
    joined = source.merge(combined, on=PAIR_KEYS, how="left", validate="many_to_one", suffixes=("", "_heat"))
    if len(joined) != len(source) or joined.filter(regex="^season_tmax_exceedance_").isna().any().any():
        raise ValueError("heat assembly does not cover exact practice-row support")
    for column in [column for column in combined if column not in PAIR_KEYS]:
        if joined.groupby(PAIR_KEYS, observed=True)[column].nunique(dropna=False).ne(1).any():
            raise ValueError(f"assembled heat field differs across practices: {column}")
    receipt = {
        "schema": ASSEMBLY_SCHEMA, "status": "complete_historical_daily_heat_input_validated_not_response",
        "contract_sha256": sha256_file(contract_path), "code_sha256": sha256_file(SCRIPT),
        "source_assembly_sha256": sha256_file(source_assembly), "source_receipt_sha256": sha256_file(source_receipt_path),
        "source_outcome_rows": int(len(source)), "heat_pair_rows": int(len(combined)),
        "counties": int(combined.county_geoid.nunique()), "years": int(combined.harvest_year.nunique()),
        "pair_key_sha256": sha256_records(combined, PAIR_KEYS), "partitions": partitions,
        **contract["decision"],
    }
    return combined, receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--source-assembly", type=Path, default=DEFAULT_SOURCE_ASSEMBLY)
    parser.add_argument("--source-receipt", type=Path, default=DEFAULT_SOURCE_RECEIPT)
    parser.add_argument("--weight-dir", type=Path, default=DEFAULT_WEIGHT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--year", type=int)
    parser.add_argument("--batch-index", type=int)
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--assembly-out", type=Path, default=DEFAULT_ASSEMBLY)
    parser.add_argument("--assembly-receipt", type=Path, default=DEFAULT_ASSEMBLY_RECEIPT)
    args = parser.parse_args()
    if (args.year is None) == (not args.assemble):
        parser.error("choose exactly one of --year or --assemble")
    if args.assemble:
        if args.assembly_out.exists() or args.assembly_receipt.exists():
            raise ValueError("assembly output already exists")
        frame, receipt = assemble(args.contract, args.source_assembly, args.source_receipt, args.output_dir)
        atomic_write_parquet(args.assembly_out, frame)
        receipt["output_path"] = str(args.assembly_out)
        receipt["output_sha256"] = sha256_file(args.assembly_out)
        atomic_write_json(args.assembly_receipt, receipt)
        print(f"assembled {len(frame)} heat rows; no response, damage, or SCC")
        return
    contract = load_contract(args.contract)
    if not int(contract["year_min"]) <= args.year <= int(contract["year_max"]):
        raise ValueError("year lies outside the frozen heat contract")
    if args.batch_index is None:
        parser.error("--year requires --batch-index after the resource-safety amendment")
    output, receipt_path = batch_paths(args.output_dir, args.year, args.batch_index)
    if output.exists() or receipt_path.exists():
        raise ValueError("year checkpoint already exists")
    frame, receipt = build_year(args.year, args.batch_index, args.contract, args.source_dir, args.weight_dir, args.output_dir)
    atomic_write_parquet(output, frame)
    receipt["output_path"] = str(output)
    receipt["output_sha256"] = sha256_file(output)
    receipt["output_key_sha256"] = sha256_records(frame, PAIR_KEYS)
    atomic_write_json(receipt_path, receipt)
    print(f"wrote {len(frame)} heat rows for {args.year} batch {args.batch_index}; no response, damage, or SCC")


if __name__ == "__main__":
    main()
