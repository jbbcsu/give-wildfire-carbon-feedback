#!/usr/bin/env python3
"""Fail-closed assembly of the complete 1990--2011 global feature partitions.

This stage is intentionally limited to validated feature tables.  It neither
joins candidate moisture families nor reads outcomes, estimates coefficients,
projects climate, computes damages, or computes an SCC.  The production entry
point requires the exact 720-task registry and every source-bound receipt
before it creates an atomic aggregate directory.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xarray as xr

from build_crop_heat_features import BASE_COLUMNS as HEAT_SEASON_BASE
from build_crop_heat_features import threshold_name
from build_crop_stage_features import STAGE_FEATURE_COLUMNS
from build_crop_stage_heat_features import BASE_COLUMNS as HEAT_STAGE_BASE
from build_crop_stage_scpdsi_features import COLUMNS as SCPDSI_COLUMNS
from build_crop_year_features import FEATURE_COLUMNS
from heat_threshold_validation import metric_columns
from run_continuous_global_panel_partitions import (
    CONTRACT_ID,
    FALSE_GATES,
    FAMILIES,
    PARTITION_RECEIPT_CONTRACT_ID,
    PartitionTask,
    _resolve,
    _validate_partition_receipt,
    calendar_registry,
    generate_tasks,
    load_config,
)
from scpdsi_partition_provenance import (
    PARTITION_CONTRACT_ID,
    read_manifest,
    require_sha256,
    same_path,
    sha256_file,
)
from validate_heat_partition import validate_frame as validate_heat_season
from validate_stage_feature_partition import validate_frame as validate_direct_stage
from validate_stage_heat_partition import validate_frame as validate_heat_stage
from validate_stage_scpdsi_partition import validate_frame as validate_scpdsi_stage


PROJECT = Path(__file__).resolve().parents[1]
ASSEMBLY_CONTRACT_ID = "continuous_global_panel_middle_assembly_v1"
EXPECTED_TASKS = 720
DIRECT_TMEAN_TOLERANCE_C = 2e-5
KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
STAGE_KEYS = [*KEYS, "stage_id"]


@dataclass(frozen=True)
class CalendarCoordinates:
    latitudes: np.ndarray
    longitudes: np.ndarray


def _relative(path: Path) -> str:
    """Return a normalized project-relative path, failing outside the project."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"Aggregate receipts cannot name a path outside the project: {path}") from error


def _require_no_absolute_strings(value: object) -> None:
    """Reject Unix and Windows absolute paths anywhere in a portable receipt."""
    if isinstance(value, dict):
        for item in value.values():
            _require_no_absolute_strings(item)
    elif isinstance(value, list):
        for item in value:
            _require_no_absolute_strings(item)
    elif isinstance(value, str) and (
        Path(value).is_absolute() or PureWindowsPath(value).is_absolute()
    ):
        raise ValueError(f"Aggregate receipt contains an absolute path: {value}")


def expected_columns(family: str, config: dict[str, Any]) -> list[str]:
    thresholds = [float(value) for value in config["heat_thresholds_c"]]
    heat_metrics = [
        item
        for value in thresholds
        for item in (
            f"{threshold_name(value)}_days",
            f"{threshold_name(value)}_degree_days",
        )
    ]
    columns = {
        "direct_season": FEATURE_COLUMNS,
        "direct_stage": STAGE_FEATURE_COLUMNS,
        "heat_season": [*HEAT_SEASON_BASE, *heat_metrics],
        "heat_stage": [*HEAT_STAGE_BASE, *heat_metrics],
        "historical_scpdsi_stage": SCPDSI_COLUMNS,
    }
    if family not in columns:
        raise ValueError(f"Unknown feature family: {family}")
    return list(columns[family])


def validate_registry_contract(
    tasks: list[PartitionTask], config_path: Path, config: dict[str, Any]
) -> Path:
    """Require the locked 36 x 2 x 2 x 5 production registry exactly."""
    if len(tasks) != EXPECTED_TASKS or len({task.task_id for task in tasks}) != EXPECTED_TASKS:
        raise ValueError(f"Assembly requires exactly {EXPECTED_TASKS} unique registered tasks")
    if config["families"] != FAMILIES or config["crops"] != ["mai", "soy"]:
        raise ValueError("Family or crop registry differs from the locked contract")
    if config["irrigation_regimes"] != ["noirr", "firr"]:
        raise ValueError("Irrigation registry differs from the locked contract")
    chunk = int(config["latitude_chunk_cells"])
    intervals = [(start, min(start + chunk, 360)) for start in range(0, 360, chunk)]
    expected_scope = {
        (
            family,
            crop,
            irrigation,
            start,
            stop,
            int(config["construction_year_start"]),
            int(config["construction_year_end"]),
        )
        for family in FAMILIES
        for crop in config["crops"]
        for irrigation in config["irrigation_regimes"]
        for start, stop in intervals
    }
    observed_scope = {
        (
            task.family,
            task.crop,
            task.irrigation,
            task.lat_start,
            task.lat_stop,
            task.year_start,
            task.year_end,
        )
        for task in tasks
    }
    if observed_scope != expected_scope:
        missing = sorted(expected_scope - observed_scope)[:5]
        extra = sorted(observed_scope - expected_scope)[:5]
        raise ValueError(f"Task scope is incomplete or duplicated: missing={missing}, extra={extra}")
    outputs = [Path(task.output).resolve() for task in tasks]
    receipts = [Path(task.receipt).resolve() for task in tasks]
    manifests = [Path(task.manifest).resolve() for task in tasks if task.manifest]
    if len(set(outputs)) != EXPECTED_TASKS or len(set(receipts)) != EXPECTED_TASKS:
        raise ValueError("Task output or receipt paths are not unique")
    if len(manifests) != 144 or len(set(manifests)) != 144:
        raise ValueError("Exactly 144 unique historical-scPDSI manifests are required")
    if any((task.manifest is None) != (task.family != "historical_scpdsi_stage") for task in tasks):
        raise ValueError("Manifest registry differs from the historical-scPDSI boundary")
    source_root = _resolve(config_path, config["output_root"]) / "middle_1990_2011"
    if any(not path.is_relative_to(source_root.resolve()) for path in outputs + receipts + manifests):
        raise ValueError("A registered source artifact is outside the isolated middle-period root")
    return source_root


def _parquet_rows(path: Path) -> int:
    return int(pq.ParquetFile(path).metadata.num_rows)


def validate_receipt_envelope(
    task: PartitionTask,
    config_path: Path,
    config: dict[str, Any],
    *,
    strict_source_identity: bool,
) -> dict[str, Any]:
    """Validate the portable envelope, then the full builder identity in production."""
    output = Path(task.output)
    receipt_path = Path(task.receipt)
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_keys = {
        "schema_version", "contract_id", "status", "identity",
        "output_sha256", "output_bytes", "output_rows", "build_metrics",
        *FALSE_GATES,
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ValueError(f"Partition receipt schema differs: {task.task_id}")
    if payload["schema_version"] != 1 or payload["contract_id"] != PARTITION_RECEIPT_CONTRACT_ID:
        raise ValueError(f"Partition receipt contract differs: {task.task_id}")
    if payload["status"] != "validated_source_bound_partition":
        raise ValueError(f"Partition receipt status differs: {task.task_id}")
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        raise ValueError(f"Partition receipt identity is malformed: {task.task_id}")
    expected_identity = {
        "continuous_panel_contract_id": CONTRACT_ID,
        "config_sha256": sha256_file(config_path),
        "task_id": task.task_id,
        "family": task.family,
        "crop": task.crop,
        "irrigation": task.irrigation,
        "year_start": task.year_start,
        "year_end": task.year_end,
        "lat_start": task.lat_start,
        "lat_stop": task.lat_stop,
    }
    for field, expected in expected_identity.items():
        if identity.get(field) != expected:
            raise ValueError(f"Partition receipt identity field {field} differs: {task.task_id}")
    if not same_path(identity.get("config_file"), config_path):
        raise ValueError(f"Partition receipt points to another config: {task.task_id}")
    if not same_path(identity.get("output_file"), output):
        raise ValueError(f"Partition receipt points to another output: {task.task_id}")
    if not isinstance(identity.get("parameters"), dict) or not isinstance(identity.get("sources"), dict):
        raise ValueError(f"Partition receipt parameters or sources are malformed: {task.task_id}")
    actual_hash = sha256_file(output)
    if require_sha256(payload.get("output_sha256"), "output_sha256") != actual_hash:
        raise ValueError(f"Partition output hash differs from receipt: {task.task_id}")
    if payload.get("output_bytes") != output.stat().st_size:
        raise ValueError(f"Partition byte count differs from receipt: {task.task_id}")
    if payload.get("output_rows") != _parquet_rows(output):
        raise ValueError(f"Partition row count differs from receipt: {task.task_id}")
    metrics = payload.get("build_metrics")
    if not isinstance(metrics, dict) or set(metrics) != {
        "schema_version", "status", "started_utc", "finished_utc",
        "wall_seconds", "peak_rss_bytes", "returncode",
    }:
        raise ValueError(f"Partition resource receipt differs: {task.task_id}")
    try:
        wall_seconds = float(metrics.get("wall_seconds", np.nan))
        peak_rss_bytes = int(metrics.get("peak_rss_bytes", 0))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Partition resource receipt is invalid: {task.task_id}") from error
    if (
        metrics.get("schema_version") != 1
        or metrics.get("status") != "command_completed"
        or metrics.get("returncode") != 0
        or not np.isfinite(wall_seconds)
        or wall_seconds < 0
        or peak_rss_bytes <= 0
    ):
        raise ValueError(f"Partition resource receipt is invalid: {task.task_id}")
    for gate in FALSE_GATES:
        if payload.get(gate) is not False:
            raise ValueError(f"Partition receipt gate {gate} must be false: {task.task_id}")
    if strict_source_identity:
        # This binds the receipt to current source objects, code, parameters,
        # task coordinates, and the exact current configuration.
        _validate_partition_receipt(task, config_path, config, output, receipt_path)
    return payload


def validate_scpdsi_manifest(
    task: PartitionTask,
    receipt: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    if task.family != "historical_scpdsi_stage" or not task.manifest:
        raise ValueError("scPDSI manifest validation called for a non-scPDSI task")
    output = Path(task.output)
    manifest_path = Path(task.manifest)
    manifest = read_manifest(manifest_path)
    expected_fields = {
        "schema_version", "contract_id", "output_file", "output_sha256", "output_rows",
        "scpdsi_source_file", "scpdsi_source_sha256", "calendar_source_file",
        "calendar_source_sha256", "drought_variable", "crop", "irrigation",
        "year_start", "year_end", "lat_start", "lat_stop", "threshold",
        "stage_fractions", "expected_stages", "calendar_fields_embedded",
        "drought_source_role",
    }
    if set(manifest) != expected_fields:
        raise ValueError(f"scPDSI manifest schema differs: {task.task_id}")
    if manifest.get("schema_version") != 1 or manifest.get("contract_id") != PARTITION_CONTRACT_ID:
        raise ValueError(f"scPDSI manifest contract differs: {task.task_id}")
    if not same_path(manifest.get("output_file"), output):
        raise ValueError(f"scPDSI manifest points to another output: {task.task_id}")
    if require_sha256(manifest.get("output_sha256"), "output_sha256") != sha256_file(output):
        raise ValueError(f"scPDSI output hash differs from manifest: {task.task_id}")
    if manifest.get("output_rows") != _parquet_rows(output):
        raise ValueError(f"scPDSI row count differs from manifest: {task.task_id}")
    expected = {
        "crop": task.crop,
        "irrigation": task.irrigation,
        "year_start": task.year_start,
        "year_end": task.year_end,
        "lat_start": task.lat_start,
        "lat_stop": task.lat_stop,
        "threshold": float(config["scpdsi_threshold"]),
        "stage_fractions": config["stage_fractions"],
        "expected_stages": int(config["expected_stages"]),
        "drought_variable": "scpdsi",
        "drought_source_role": "historical_benchmark_not_future_scc_input",
        "calendar_fields_embedded": [
            "plant_year", "cross_year", "plant_doy", "maturity_doy", "season_days"
        ],
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise ValueError(f"scPDSI manifest field {field} differs: {task.task_id}")
    sources = receipt["identity"]["sources"]
    try:
        receipt_scpdsi = require_sha256(sources["scpdsi_file"]["sha256"], "receipt scpdsi hash")
        receipt_calendar = require_sha256(sources["calendar"]["sha256"], "receipt calendar hash")
    except (KeyError, TypeError) as error:
        raise ValueError(f"scPDSI receipt lacks source hashes: {task.task_id}") from error
    if require_sha256(manifest.get("scpdsi_source_sha256"), "manifest scpdsi hash") != receipt_scpdsi:
        raise ValueError(f"scPDSI manifest and receipt source hashes differ: {task.task_id}")
    if require_sha256(manifest.get("calendar_source_sha256"), "manifest calendar hash") != receipt_calendar:
        raise ValueError(f"Calendar manifest and receipt source hashes differ: {task.task_id}")
    return manifest


def _exact_discovered_files(tasks: list[PartitionTask], source_root: Path) -> None:
    expected_outputs = {Path(task.output).resolve() for task in tasks}
    expected_receipts = {Path(task.receipt).resolve() for task in tasks}
    expected_manifests = {Path(task.manifest).resolve() for task in tasks if task.manifest}
    discovered_outputs = {path.resolve() for path in source_root.rglob("*.parquet")}
    discovered_receipts = {path.resolve() for path in source_root.rglob("*.receipt.json")}
    discovered_manifests = {path.resolve() for path in source_root.rglob("*.manifest.json")}
    for label, expected, observed in (
        ("partition", expected_outputs, discovered_outputs),
        ("receipt", expected_receipts, discovered_receipts),
        ("manifest", expected_manifests, discovered_manifests),
    ):
        if observed != expected:
            missing = sorted(str(path) for path in expected - observed)[:3]
            extra = sorted(str(path) for path in observed - expected)[:3]
            raise ValueError(f"Exact {label} file registry differs: missing={missing}, extra={extra}")
    locks = sorted(source_root.rglob("*.lock"))
    if locks:
        raise ValueError(f"Assembly is forbidden while task locks exist: {locks[:3]}")


def preflight_sources(
    tasks: list[PartitionTask],
    config_path: Path,
    config: dict[str, Any],
    source_root: Path,
    *,
    strict_source_identity: bool = True,
    exact_discovery: bool = True,
) -> list[dict[str, Any]]:
    """Require every task artifact and validate hashes before any assembly write."""
    if exact_discovery:
        _exact_discovered_files(tasks, source_root)
    records: list[dict[str, Any]] = []
    for task in sorted(tasks, key=lambda item: item.task_id):
        output, receipt_path = Path(task.output), Path(task.receipt)
        required = [output, receipt_path]
        if task.manifest:
            required.append(Path(task.manifest))
        if missing := [path for path in required if not path.is_file()]:
            raise ValueError(f"Registered task artifacts are missing for {task.task_id}: {missing}")
        if Path(str(output) + ".lock").exists():
            raise ValueError(f"Task remains locked: {task.task_id}")
        receipt = validate_receipt_envelope(
            task, config_path, config, strict_source_identity=strict_source_identity
        )
        manifest = validate_scpdsi_manifest(task, receipt, config) if task.manifest else None
        record: dict[str, Any] = {
            "task_id": task.task_id,
            "family": task.family,
            "crop": task.crop,
            "irrigation": task.irrigation,
            "lat_start": task.lat_start,
            "lat_stop": task.lat_stop,
            "year_start": task.year_start,
            "year_end": task.year_end,
            "output": _relative(output),
            "output_sha256": receipt["output_sha256"],
            "output_bytes": receipt["output_bytes"],
            "output_rows": receipt["output_rows"],
            "receipt": _relative(receipt_path),
            "receipt_sha256": sha256_file(receipt_path),
        }
        if manifest is not None:
            record.update(
                manifest=_relative(Path(task.manifest or "")),
                manifest_sha256=sha256_file(Path(task.manifest or "")),
            )
        records.append(record)
    return records


def load_calendar_coordinates(
    config_path: Path, config: dict[str, Any]
) -> dict[tuple[str, str], CalendarCoordinates]:
    registry: dict[tuple[str, str], CalendarCoordinates] = {}
    for pair, path in calendar_registry(config_path, config).items():
        with xr.open_dataset(path, engine="h5netcdf", decode_timedelta=False) as dataset:
            lat = dataset.lat.values.astype(float)
            lon = dataset.lon.values.astype(float)
        if len(lat) != 360 or len(lon) != 720 or len(np.unique(lat)) != len(lat) or len(np.unique(lon)) != len(lon):
            raise ValueError(f"Crop-calendar grid is not the locked unique 360 x 720 grid: {pair}")
        registry[pair] = CalendarCoordinates(latitudes=lat, longitudes=lon)
    return registry


def _validate_direct_season(frame: pd.DataFrame) -> None:
    if set(frame.columns) != set(FEATURE_COLUMNS):
        raise ValueError("Direct-season schema differs")
    if frame.empty:
        return
    if frame.duplicated(KEYS).any():
        raise ValueError("Direct-season partition contains duplicate keys")
    numeric = [
        "harvest_year", "plant_year", "lat", "lon", "lon_360", "plant_doy",
        "maturity_doy", "season_days", "tmean_c", "precip_mm", "wet_days_n",
        "cdd_max_days", "rx1day_mm", "rx5day_mm", "wet_day_threshold_mm",
    ]
    if not np.isfinite(frame[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Direct-season required metrics are nonfinite")
    integers = frame[[
        "harvest_year", "plant_year", "plant_doy", "maturity_doy", "season_days",
        "wet_days_n", "cdd_max_days",
    ]].to_numpy(dtype=float)
    if not np.equal(integers, np.floor(integers)).all():
        raise ValueError("Direct-season calendar/count fields are not integers")
    if not frame["cross_year"].isin([True, False]).all():
        raise ValueError("Direct-season cross_year must be Boolean")
    if not frame.plant_year.astype(int).equals(
        frame.harvest_year.astype(int) - frame.cross_year.astype(int)
    ):
        raise ValueError("Direct-season plant_year differs from harvest_year/cross_year")
    if ((frame.plant_doy < 1) | (frame.plant_doy > 366)).any() or (
        (frame.maturity_doy < 1) | (frame.maturity_doy > 366)
    ).any():
        raise ValueError("Direct-season day-of-year is outside [1, 366]")
    nonnegative = ["precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"]
    if (frame[nonnegative] < 0).any().any() or (frame.season_days <= 0).any():
        raise ValueError("Direct-season precipitation/count metrics are invalid")
    if (frame.wet_days_n > frame.season_days).any() or (frame.cdd_max_days > frame.season_days).any():
        raise ValueError("Direct-season day count exceeds season length")
    tolerance = 1e-6 + 1e-7 * frame.precip_mm.abs()
    if (frame.rx1day_mm > frame.precip_mm + tolerance).any() or (
        frame.rx5day_mm > frame.precip_mm + tolerance
    ).any() or (frame.rx5day_mm + tolerance < frame.rx1day_mm).any():
        raise ValueError("Direct-season precipitation maxima are inconsistent")


def validate_partition_frame(
    task: PartitionTask,
    frame: pd.DataFrame,
    config: dict[str, Any],
    coordinates: dict[tuple[str, str], CalendarCoordinates],
) -> None:
    """Apply family, task-scope, year, and calendar-grid checks to one partition."""
    columns = expected_columns(task.family, config)
    # The legacy builders permitted a zero-row, zero-column parquet.  It is a
    # valid completed empty latitude band only when its receipt is valid.
    if frame.empty and len(frame.columns) == 0:
        return
    if list(frame.columns) != columns:
        raise ValueError(f"Ordered schema differs for {task.task_id}")
    if task.family == "direct_season":
        _validate_direct_season(frame)
    elif task.family == "direct_stage":
        validate_direct_stage(frame, int(config["expected_stages"]), config["stage_fractions"])
    elif task.family == "heat_season":
        validate_heat_season(frame, [float(value) for value in config["heat_thresholds_c"]])
    elif task.family == "heat_stage":
        validate_heat_stage(
            frame,
            [float(value) for value in config["heat_thresholds_c"]],
            int(config["expected_stages"]),
        )
    elif task.family == "historical_scpdsi_stage":
        validate_scpdsi_stage(frame, float(config["scpdsi_threshold"]), int(config["expected_stages"]))
    else:
        raise ValueError(f"Unknown task family: {task.family}")
    if frame.empty:
        return
    if set(frame.crop.astype(str)) != {task.crop} or set(frame.irrigation.astype(str)) != {task.irrigation}:
        raise ValueError(f"Crop or irrigation scope differs for {task.task_id}")
    if set(frame.harvest_year.astype(int)) != set(range(task.year_start, task.year_end + 1)):
        raise ValueError(f"Exact harvest-year coverage differs for {task.task_id}")
    coords = coordinates[(task.crop, task.irrigation)]
    expected_lat = set(float(value) for value in coords.latitudes[task.lat_start:task.lat_stop])
    expected_lon_values = (
        np.mod(coords.longitudes, 360.0)
        if task.family == "historical_scpdsi_stage"
        else coords.longitudes
    )
    if not set(frame.lat.astype(float).unique()).issubset(expected_lat):
        raise ValueError(f"Latitude values lie outside the registered index band: {task.task_id}")
    if not set(frame.lon.astype(float).unique()).issubset(set(float(value) for value in expected_lon_values)):
        raise ValueError(f"Longitude values differ from the crop calendar: {task.task_id}")
    if not np.allclose(frame.lon_360, np.mod(frame.lon, 360.0), rtol=0, atol=1e-10):
        raise ValueError(f"lon_360 differs from longitude: {task.task_id}")
    if task.family == "direct_season" and not np.allclose(
        frame.wet_day_threshold_mm,
        float(config["wet_day_threshold_mm"]),
        rtol=0,
        atol=1e-12,
    ):
        raise ValueError(f"Wet-day threshold differs for {task.task_id}")
    if task.family in {"direct_stage", "heat_stage", "historical_scpdsi_stage"} and set(
        frame.stage_fractions.astype(str)
    ) != {config["stage_fractions"]}:
        raise ValueError(f"Stage fractions differ for {task.task_id}")


def assemble_family_group(
    tasks: list[PartitionTask],
    destination: Path,
    config: dict[str, Any],
    coordinates: dict[tuple[str, str], CalendarCoordinates],
) -> dict[str, Any]:
    """Validate and append one partition at a time to one deterministic table."""
    if not tasks:
        raise ValueError("Cannot assemble an empty task group")
    family, crop, irrigation = tasks[0].family, tasks[0].crop, tasks[0].irrigation
    if any((task.family, task.crop, task.irrigation) != (family, crop, irrigation) for task in tasks):
        raise ValueError("Assembly group mixes family/crop/irrigation identities")
    ordered_tasks = sorted(tasks, key=lambda task: (task.lat_start, task.lat_stop))
    if [(task.lat_start, task.lat_stop) for task in ordered_tasks] != [
        (start, start + 10) for start in range(0, 360, 10)
    ]:
        raise ValueError("Assembly group does not have exact latitude-index coverage")
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    schema: pa.Schema | None = None
    total_rows = 0
    expected_rows = sum(_parquet_rows(Path(task.output)) for task in ordered_tasks)
    columns = expected_columns(family, config)
    try:
        for task in ordered_tasks:
            frame = pd.read_parquet(task.output)
            validate_partition_frame(task, frame, config, coordinates)
            if frame.empty:
                continue
            sort_keys = STAGE_KEYS if "stage_id" in frame.columns else KEYS
            frame = frame.sort_values(sort_keys, kind="mergesort").reset_index(drop=True)
            table = pa.Table.from_pandas(frame[columns], preserve_index=False).replace_schema_metadata(None)
            if writer is None:
                schema = table.schema
                writer = pq.ParquetWriter(
                    destination,
                    schema,
                    compression="zstd",
                    use_dictionary=True,
                    write_statistics=True,
                )
            elif schema is None or not table.schema.equals(schema, check_metadata=False):
                raise ValueError(f"Arrow schema differs across partitions for {family}/{crop}/{irrigation}")
            writer.write_table(table)
            total_rows += len(frame)
            del frame, table
    finally:
        if writer is not None:
            writer.close()
    if total_rows != expected_rows:
        raise ValueError(f"Combined rows do not equal source rows for {family}/{crop}/{irrigation}")
    if total_rows <= 0 or not destination.is_file():
        raise ValueError(f"No populated rows for {family}/{crop}/{irrigation}")
    if _parquet_rows(destination) != total_rows:
        raise ValueError(f"Combined row count differs for {family}/{crop}/{irrigation}")
    return {
        "family": family,
        "crop": crop,
        "irrigation": irrigation,
        "path": _relative(destination),
        "sha256": sha256_file(destination),
        "bytes": destination.stat().st_size,
        "rows": total_rows,
        "source_rows": expected_rows,
        "columns": columns,
        "source_partitions": len(ordered_tasks),
    }


def _exact_join(left: pd.DataFrame, right: pd.DataFrame, keys: list[str], label: str) -> pd.DataFrame:
    if left.duplicated(keys).any() or right.duplicated(keys).any():
        raise ValueError(f"Duplicate keys before {label}")
    joined = left.merge(right, on=keys, how="outer", validate="one_to_one", indicator=True)
    if not joined._merge.eq("both").all():
        counts = joined._merge.value_counts().to_dict()
        raise ValueError(f"Exact keys differ for {label}: {counts}")
    return joined.drop(columns="_merge")


def _max_abs(left: pd.Series, right: pd.Series) -> float:
    if len(left) == 0:
        return 0.0
    return float(np.max(np.abs(left.to_numpy(dtype=float) - right.to_numpy(dtype=float))))


def _require_close(left: pd.Series, right: pd.Series, tolerance: float, label: str) -> float:
    difference = _max_abs(left, right)
    if difference > tolerance:
        raise ValueError(f"{label} differs by {difference}, above tolerance {tolerance}")
    return difference


def reconcile_direct_pair(
    season: pd.DataFrame, stages: pd.DataFrame, tolerance: float
) -> dict[str, Any]:
    if season.empty or stages.empty:
        if season.empty and stages.empty:
            return {"keys": 0, "maximum_absolute_differences": {}}
        raise ValueError("Direct season/stage empty-band status differs")
    # Explicit aggregation avoids relying on pandas' generated multi-index names.
    grouped = stages.groupby(KEYS, as_index=False, observed=True).agg(
        plant_year_stage=("plant_year", "first"),
        cross_year_stage=("cross_year", "first"),
        lon_stage=("lon", "first"),
        stage_days=("stage_days", "sum"),
        precip_mm_stage=("precip_mm", "sum"),
        wet_days_n_stage=("wet_days_n", "sum"),
        cdd_stage_max=("cdd_max_days", "max"),
        cdd_stage_sum=("cdd_max_days", "sum"),
        rx1day_mm_stage=("rx1day_mm", "max"),
        rx5day_mm_stage=("rx5day_mm", "max"),
    )
    weighted = (
        stages.assign(weighted_tmean=stages.tmean_c * stages.stage_days)
        .groupby(KEYS, as_index=False, observed=True)
        .agg(weighted_tmean=("weighted_tmean", "sum"))
    )
    grouped = grouped.merge(weighted, on=KEYS, validate="one_to_one")
    grouped["tmean_c_stage"] = grouped.weighted_tmean / grouped.stage_days
    season_fields = season[[
        *KEYS, "plant_year", "cross_year", "lon", "season_days", "tmean_c",
        "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm",
    ]]
    joined = _exact_join(season_fields, grouped, KEYS, "direct season/stage")
    maximum = {
        "lon": _require_close(joined.lon, joined.lon_stage, tolerance, "direct lon"),
        # The direct builders independently average float32 daily temperature
        # within the season and stages.  Their algebraically equivalent means
        # can consequently differ at about 1e-5 C (8.69e-6 C in the bounded
        # real pilot); keep that roundoff allowance explicit and narrow.
        "tmean_c": _require_close(
            joined.tmean_c,
            joined.tmean_c_stage,
            max(tolerance, DIRECT_TMEAN_TOLERANCE_C),
            "stage-weighted tmean",
        ),
        "precip_mm": _require_close(joined.precip_mm, joined.precip_mm_stage, tolerance, "stage-summed precipitation"),
        "rx1day_mm": _require_close(joined.rx1day_mm, joined.rx1day_mm_stage, tolerance, "stage-max rx1day"),
    }
    if not joined.plant_year.equals(joined.plant_year_stage) or not joined.cross_year.equals(joined.cross_year_stage):
        raise ValueError("Direct season/stage calendar identities differ")
    if not joined.season_days.equals(joined.stage_days) or not joined.wet_days_n.equals(joined.wet_days_n_stage):
        raise ValueError("Direct stage day or wet-day counts do not sum to the season")
    if (joined.cdd_max_days < joined.cdd_stage_max).any() or (
        joined.cdd_max_days > joined.cdd_stage_sum
    ).any():
        raise ValueError("Direct seasonal CDD lies outside valid stage bounds")
    finite_rx5 = joined.rx5day_mm_stage.notna()
    if (
        joined.loc[finite_rx5, "rx5day_mm_stage"]
        > joined.loc[finite_rx5, "rx5day_mm"] + tolerance
    ).any():
        raise ValueError("A within-stage rx5day exceeds the seasonal rx5day")
    return {"keys": len(joined), "maximum_absolute_differences": maximum}


def reconcile_heat_pair(
    season: pd.DataFrame,
    stages: pd.DataFrame,
    thresholds: list[float],
    tolerance: float,
) -> dict[str, Any]:
    if season.empty or stages.empty:
        if season.empty and stages.empty:
            return {"keys": 0, "maximum_absolute_differences": {}}
        raise ValueError("Heat season/stage empty-band status differs")
    metrics = sorted(metric_columns(thresholds))
    named: dict[str, tuple[str, str]] = {
        "plant_year_stage": ("plant_year", "first"),
        "cross_year_stage": ("cross_year", "first"),
        "lon_stage": ("lon", "first"),
        "stage_days": ("stage_days", "sum"),
    }
    named.update({f"{name}_stage": (name, "sum") for name in metrics})
    grouped = stages.groupby(KEYS, as_index=False, observed=True).agg(**named)
    weighted = (
        stages.assign(weighted_tmax=stages.tmax_mean_c * stages.stage_days)
        .groupby(KEYS, as_index=False, observed=True)
        .agg(weighted_tmax=("weighted_tmax", "sum"))
    )
    grouped = grouped.merge(weighted, on=KEYS, validate="one_to_one")
    grouped["tmax_mean_c_stage"] = grouped.weighted_tmax / grouped.stage_days
    joined = _exact_join(
        season[[*KEYS, "plant_year", "cross_year", "lon", "season_days", "tmax_mean_c", *metrics]],
        grouped,
        KEYS,
        "heat season/stage",
    )
    maximum = {
        "lon": _require_close(joined.lon, joined.lon_stage, tolerance, "heat lon"),
        "tmax_mean_c": _require_close(joined.tmax_mean_c, joined.tmax_mean_c_stage, tolerance, "stage-weighted tmax"),
    }
    if not joined.plant_year.equals(joined.plant_year_stage) or not joined.cross_year.equals(joined.cross_year_stage):
        raise ValueError("Heat season/stage calendar identities differ")
    if not joined.season_days.equals(joined.stage_days):
        raise ValueError("Heat stage days do not sum to season days")
    for metric in metrics:
        maximum[metric] = _require_close(
            joined[metric], joined[f"{metric}_stage"], tolerance, f"stage-summed {metric}"
        )
    return {"keys": len(joined), "maximum_absolute_differences": maximum}


def reconcile_direct_heat_keys(
    direct: pd.DataFrame, heat: pd.DataFrame, tolerance: float
) -> dict[str, Any]:
    if direct.empty or heat.empty:
        if direct.empty and heat.empty:
            return {"keys": 0, "maximum_absolute_differences": {}}
        raise ValueError("Direct/heat seasonal empty-band status differs")
    identity = ["plant_year", "cross_year", "lon", "plant_doy", "maturity_doy", "season_days"]
    joined = _exact_join(
        direct[[*KEYS, *identity]], heat[[*KEYS, *identity]], KEYS, "direct/heat seasonal"
    )
    maximum = {"lon": _require_close(joined.lon_x, joined.lon_y, tolerance, "direct/heat lon")}
    for field in ["plant_year", "cross_year", "plant_doy", "maturity_doy", "season_days"]:
        if not joined[f"{field}_x"].equals(joined[f"{field}_y"]):
            raise ValueError(f"Direct/heat calendar field {field} differs")
    return {"keys": len(joined), "maximum_absolute_differences": maximum}


def reconcile_scpdsi_boundary(
    direct_stages: pd.DataFrame, scpdsi: pd.DataFrame, tolerance: float
) -> dict[str, Any]:
    if direct_stages.empty:
        if not scpdsi.empty:
            raise ValueError("Historical scPDSI has rows in an empty direct-weather band")
        return {
            "direct_keys": 0, "scpdsi_keys": 0, "common_keys": 0,
            "direct_only_keys": 0, "scpdsi_only_keys": 0,
            "common_stage_rows": 0, "maximum_absolute_differences": {},
        }
    direct_base = direct_stages[KEYS].drop_duplicates()
    if scpdsi.empty:
        return {
            "direct_keys": len(direct_base), "scpdsi_keys": 0, "common_keys": 0,
            "direct_only_keys": len(direct_base), "scpdsi_only_keys": 0,
            "common_stage_rows": 0, "maximum_absolute_differences": {},
        }
    comparison = scpdsi.merge(
        direct_stages,
        on=STAGE_KEYS,
        how="left",
        validate="one_to_one",
        indicator=True,
        suffixes=("_scpdsi", "_direct"),
    )
    if not comparison._merge.eq("both").all():
        raise ValueError("Historical scPDSI has stage keys outside direct-weather support")
    maximum: dict[str, float] = {}
    # The scPDSI builder canonicalizes raw longitude to [0, 360), whereas the
    # direct-weather builder retains the calendar's native longitude.  Compare
    # the canonical coordinate rather than falsely requiring raw-lon identity.
    maximum["lon_360"] = _require_close(
        np.mod(comparison["lon_scpdsi"], 360.0),
        np.mod(comparison["lon_direct"], 360.0),
        tolerance,
        "scPDSI/direct canonical longitude",
    )
    for field in ["stage_start_offset_day", "stage_end_offset_day", "stage_days"]:
        maximum[field] = _require_close(
            comparison[f"{field}_scpdsi"],
            comparison[f"{field}_direct"],
            tolerance,
            f"scPDSI/direct {field}",
        )
    for field in ["plant_year", "cross_year", "stage_fractions"]:
        if not comparison[f"{field}_scpdsi"].equals(comparison[f"{field}_direct"]):
            raise ValueError(f"scPDSI/direct stage identity field {field} differs")
    sc_base = scpdsi[KEYS].drop_duplicates()
    base = direct_base.merge(sc_base, on=KEYS, how="outer", indicator=True)
    sc_only = int(base._merge.eq("right_only").sum())
    if sc_only:
        raise ValueError("Historical scPDSI base keys lie outside direct-weather support")
    common = int(base._merge.eq("both").sum())
    return {
        "direct_keys": len(direct_base),
        "scpdsi_keys": len(sc_base),
        "common_keys": common,
        "direct_only_keys": int(base._merge.eq("left_only").sum()),
        "scpdsi_only_keys": sc_only,
        "common_stage_rows": len(comparison),
        "maximum_absolute_differences": maximum,
    }


def _accumulate(total: dict[str, Any], item: dict[str, Any]) -> None:
    for key, value in item.items():
        if key == "maximum_absolute_differences":
            target = total.setdefault(key, {})
            for metric, difference in value.items():
                target[metric] = max(float(target.get(metric, 0.0)), float(difference))
        elif isinstance(value, (int, np.integer)):
            total[key] = int(total.get(key, 0)) + int(value)
        else:
            raise TypeError(f"Unsupported reconciliation accumulator field: {key}")


def reconcile_all_groups(
    tasks: list[PartitionTask], config: dict[str, Any], tolerance: float
) -> list[dict[str, Any]]:
    by_scope = {
        (task.family, task.crop, task.irrigation, task.lat_start): task for task in tasks
    }
    results: list[dict[str, Any]] = []
    thresholds = [float(value) for value in config["heat_thresholds_c"]]
    for crop in config["crops"]:
        for irrigation in config["irrigation_regimes"]:
            direct_total: dict[str, Any] = {}
            heat_total: dict[str, Any] = {}
            direct_heat_total: dict[str, Any] = {}
            scpdsi_total: dict[str, Any] = {}
            for lat_start in range(0, 360, int(config["latitude_chunk_cells"])):
                direct_season = pd.read_parquet(
                    by_scope[("direct_season", crop, irrigation, lat_start)].output
                )
                direct_stage = pd.read_parquet(
                    by_scope[("direct_stage", crop, irrigation, lat_start)].output
                )
                _accumulate(
                    direct_total,
                    reconcile_direct_pair(direct_season, direct_stage, tolerance),
                )
                heat_season = pd.read_parquet(
                    by_scope[("heat_season", crop, irrigation, lat_start)].output
                )
                _accumulate(
                    direct_heat_total,
                    reconcile_direct_heat_keys(direct_season, heat_season, tolerance),
                )
                del direct_season, direct_stage
                heat_stage = pd.read_parquet(
                    by_scope[("heat_stage", crop, irrigation, lat_start)].output
                )
                _accumulate(
                    heat_total,
                    reconcile_heat_pair(heat_season, heat_stage, thresholds, tolerance),
                )
                del heat_season, heat_stage
                direct_stage = pd.read_parquet(
                    by_scope[("direct_stage", crop, irrigation, lat_start)].output
                )
                scpdsi = pd.read_parquet(
                    by_scope[("historical_scpdsi_stage", crop, irrigation, lat_start)].output
                )
                _accumulate(
                    scpdsi_total,
                    reconcile_scpdsi_boundary(direct_stage, scpdsi, tolerance),
                )
                del direct_stage, scpdsi
            denominator = int(scpdsi_total["direct_keys"])
            scpdsi_total["common_support_fraction"] = (
                float(scpdsi_total["common_keys"] / denominator) if denominator else None
            )
            results.append(
                {
                    "crop": crop,
                    "irrigation": irrigation,
                    "direct_season_stage": {
                        **direct_total,
                        "exact_key_match": True,
                        "reconciliation_passed": True,
                    },
                    "heat_season_stage": {
                        **heat_total,
                        "exact_key_match": True,
                        "reconciliation_passed": True,
                    },
                    "direct_heat_season": {
                        **direct_heat_total,
                        "exact_key_match": True,
                        "calendar_identity_match": True,
                    },
                    "historical_scpdsi_boundary": {
                        **scpdsi_total,
                        "scpdsi_is_exact_subset_of_direct": True,
                        "join_rule": "inner_join_only_on_exact_crop_year_grid_stage_keys",
                        "missing_index_policy": "no_infill",
                        "drought_source_role": "historical_benchmark_not_future_scc_input",
                    },
                }
            )
    return results


def _group_tasks(tasks: Iterable[PartitionTask]) -> dict[tuple[str, str, str], list[PartitionTask]]:
    groups: dict[tuple[str, str, str], list[PartitionTask]] = {}
    for task in tasks:
        groups.setdefault((task.family, task.crop, task.irrigation), []).append(task)
    return groups


def verify_source_records_unchanged(
    tasks: list[PartitionTask], source_records: list[dict[str, Any]]
) -> None:
    """Bind an assembly call to the exact preflighted artifacts, without TOCTOU drift."""
    if len(tasks) != EXPECTED_TASKS or len(source_records) != EXPECTED_TASKS:
        raise ValueError("Assembly requires exactly 720 tasks and 720 preflight records")
    by_id = {str(record.get("task_id")): record for record in source_records}
    if len(by_id) != EXPECTED_TASKS or set(by_id) != {task.task_id for task in tasks}:
        raise ValueError("Preflight record task IDs differ from the assembly registry")
    for task in tasks:
        record = by_id[task.task_id]
        output, receipt = Path(task.output), Path(task.receipt)
        exact_fields = {
            "family": task.family,
            "crop": task.crop,
            "irrigation": task.irrigation,
            "lat_start": task.lat_start,
            "lat_stop": task.lat_stop,
            "year_start": task.year_start,
            "year_end": task.year_end,
            "output": _relative(output),
            "receipt": _relative(receipt),
        }
        for field, value in exact_fields.items():
            if record.get(field) != value:
                raise ValueError(f"Preflight record field {field} differs: {task.task_id}")
        if record.get("output_sha256") != sha256_file(output):
            raise ValueError(f"Partition changed after preflight: {task.task_id}")
        if record.get("output_bytes") != output.stat().st_size or record.get("output_rows") != _parquet_rows(output):
            raise ValueError(f"Partition size or rows changed after preflight: {task.task_id}")
        if record.get("receipt_sha256") != sha256_file(receipt):
            raise ValueError(f"Partition receipt changed after preflight: {task.task_id}")
        if task.manifest:
            manifest = Path(task.manifest)
            if record.get("manifest") != _relative(manifest) or record.get("manifest_sha256") != sha256_file(manifest):
                raise ValueError(f"scPDSI manifest changed after preflight: {task.task_id}")
        elif "manifest" in record or "manifest_sha256" in record:
            raise ValueError(f"Non-scPDSI preflight record contains a manifest: {task.task_id}")


def build_aggregate_receipt(
    config_path: Path,
    source_records: list[dict[str, Any]],
    table_records: list[dict[str, Any]],
    reconciliations: list[dict[str, Any]],
    tolerance: float,
) -> dict[str, Any]:
    receipt = {
        "schema_version": 1,
        "contract_id": ASSEMBLY_CONTRACT_ID,
        "status": "validated_complete_middle_period_feature_assembly",
        "continuous_panel_contract_id": CONTRACT_ID,
        "config": _relative(config_path),
        "config_sha256": sha256_file(config_path),
        "assembly_code": _relative(Path(__file__)),
        "assembly_code_sha256": sha256_file(Path(__file__)),
        "construction_year_start": 1990,
        "construction_year_end": 2011,
        "required_source_tasks": EXPECTED_TASKS,
        "validated_source_tasks": len(source_records),
        "source_receipts_validated": True,
        "source_manifests_validated": True,
        "source_artifacts_unchanged_during_assembly": True,
        "exact_family_crop_irrigation_latitude_year_registry": True,
        "streamed_partition_assembly": True,
        "maximum_partitions_loaded_simultaneously_for_reconciliation": 2,
        "aggregate_tables": sorted(
            table_records, key=lambda item: (item["family"], item["crop"], item["irrigation"])
        ),
        "source_partitions": sorted(source_records, key=lambda item: item["task_id"]),
        "reconciliations": sorted(reconciliations, key=lambda item: (item["crop"], item["irrigation"])),
        "numerical_tolerances": {
            "general_absolute": tolerance,
            "direct_stage_weighted_tmean_c": max(tolerance, DIRECT_TMEAN_TOLERANCE_C),
        },
        "moisture_families_kept_separate": True,
        "outcomes_read": False,
        "fit_performed": False,
        "coefficients_exported": False,
        "causal_claim_supported": False,
        "damage_or_scc_claim_supported": False,
        **{gate: False for gate in FALSE_GATES},
    }
    _require_no_absolute_strings(receipt)
    return receipt


def assemble_complete_panel(
    tasks: list[PartitionTask],
    config_path: Path,
    config: dict[str, Any],
    source_records: list[dict[str, Any]],
    out_root: Path,
    *,
    tolerance: float,
) -> Path:
    configured_root = _resolve(config_path, config["output_root"]).resolve()
    if not out_root.resolve().is_relative_to(configured_root):
        raise ValueError("Aggregate output must remain below the isolated continuous-panel root")
    source_root = (configured_root / "middle_1990_2011").resolve()
    if out_root.resolve().is_relative_to(source_root):
        raise ValueError("Aggregate output cannot be nested in the source-partition tree")
    if out_root.exists():
        raise FileExistsError(f"Refusing to overwrite an existing aggregate root: {out_root}")
    verify_source_records_unchanged(tasks, source_records)
    out_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".middle-assembly-", dir=out_root.parent))
    try:
        coordinates = load_calendar_coordinates(config_path, config)
        records: list[dict[str, Any]] = []
        groups = _group_tasks(tasks)
        if len(groups) != 20 or any(len(group) != 36 for group in groups.values()):
            raise ValueError("Aggregate family groups differ from 20 tables x 36 partitions")
        for (family, crop, irrigation), group in sorted(groups.items()):
            destination = staging / family / f"{crop}_{irrigation}_1990_2011.parquet"
            record = assemble_family_group(group, destination, config, coordinates)
            # Replace the temporary path with its deterministic final location.
            record["path"] = _relative(out_root / destination.relative_to(staging))
            records.append(record)
        reconciliations = reconcile_all_groups(tasks, config, tolerance)
        # Inputs are intentionally immutable over the assembly transaction.
        # Rehash after the last reconciliation read before publishing outputs.
        verify_source_records_unchanged(tasks, source_records)
        receipt = build_aggregate_receipt(
            config_path, source_records, records, reconciliations, tolerance
        )
        receipt_path = staging / "assembly_receipt.json"
        receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        # Validate every staged table hash against the just-written receipt.
        for record in records:
            staged = staging / Path(record["path"]).relative_to(out_root.relative_to(PROJECT))
            if record["sha256"] != sha256_file(staged) or record["rows"] != _parquet_rows(staged):
                raise ValueError(f"Staged aggregate differs from receipt: {record['path']}")
        os.replace(staging, out_root)
        return out_root / "assembly_receipt.json"
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=str(PROJECT / "config" / "continuous_global_panel_1982_2016_v1.toml"),
    )
    parser.add_argument("--out-root")
    parser.add_argument("--absolute-tolerance", type=float, default=1e-9)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="After the complete preflight, atomically write the 20 aggregate tables and receipt",
    )
    args = parser.parse_args()
    if not np.isfinite(args.absolute_tolerance) or args.absolute_tolerance < 0:
        raise ValueError("Absolute tolerance must be finite and nonnegative")
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    tasks = generate_tasks(config_path, config)
    source_root = validate_registry_contract(tasks, config_path, config)
    records = preflight_sources(tasks, config_path, config, source_root)
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "complete_source_preflight_only",
                    "validated_source_tasks": len(records),
                    "assembly_written": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    default_root = _resolve(config_path, config["output_root"]) / "assembled_middle_1990_2011"
    out_root = Path(args.out_root).resolve() if args.out_root else default_root
    receipt = assemble_complete_panel(
        tasks,
        config_path,
        config,
        records,
        out_root,
        tolerance=float(args.absolute_tolerance),
    )
    print(json.dumps({"status": "assembly_complete", "receipt": _relative(receipt)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
