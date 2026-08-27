#!/usr/bin/env python3
"""Audit and safely build isolated 1990-2011 global crop-feature partitions.

Existing validated 1982-1989 and 2012-2016 artifacts are read-only inputs to
the readiness audit. New work is written only below the configured continuous
panel namespace. Valid outputs are skipped; an invalid, incomplete, or locked
target fails closed and is never overwritten.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tomllib
import uuid
from contextlib import ExitStack
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

from climate_inputs import daily_series_coordinates
from scpdsi_partition_provenance import sha256_file


PROJECT = Path(__file__).resolve().parents[1]
CONTRACT_ID = "global_maize_soy_continuous_panel_1982_2016_v1"
PARTITION_RECEIPT_CONTRACT_ID = "continuous_global_panel_partition_receipt_v1"
FAMILIES = [
    "direct_season",
    "direct_stage",
    "heat_season",
    "heat_stage",
    "historical_scpdsi_stage",
]
FALSE_GATES = [
    "diagnostic_fit_authorized",
    "family_stacking_authorized",
    "coefficient_export_authorized",
    "causal_interpretation_authorized",
    "production_model_selection_authorized",
    "production_fit_authorized",
    "response_draw_authorized",
    "damage_calculation_authorized",
    "future_projection_authorized",
    "scc_authorized",
    "selection_by_scc_authorized",
]
PATH_FIELDS = [
    "output_root",
    "audit_root",
    "raw_climate_root",
    "raw_climate_provenance",
    "gdhy_root",
    "gdhy_provenance",
    "gdhy_support_audit",
    "scpdsi_file",
    "scpdsi_provenance",
    "mirca_weights",
    "mirca_provenance",
    "validated_endpoint_receipt",
]


@dataclass(frozen=True)
class PartitionTask:
    family: str
    crop: str
    irrigation: str
    lat_start: int
    lat_stop: int
    year_start: int
    year_end: int
    output: str
    manifest: str | None
    receipt: str

    @property
    def task_id(self) -> str:
        return (
            f"{self.family}:{self.crop}:{self.irrigation}:"
            f"lat{self.lat_start:03d}_{self.lat_stop:03d}:"
            f"{self.year_start}_{self.year_end}"
        )


def _resolve(config_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else config_path.resolve().parents[1] / path


def load_config(config_path: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    expected = {
        "schema_version",
        "contract_id",
        "description",
        "target_year_start",
        "target_year_end",
        "validated_early_year_start",
        "validated_early_year_end",
        "construction_year_start",
        "construction_year_end",
        "validated_later_year_start",
        "validated_later_year_end",
        "crops",
        "irrigation_regimes",
        "families",
        "latitude_chunk_cells",
        "pilot_latitude_start",
        "stage_fractions",
        "expected_stages",
        "wet_day_threshold_mm",
        "heat_thresholds_c",
        "scpdsi_threshold",
        *PATH_FIELDS,
        "precipitation_files",
        "temperature_files",
        "maximum_temperature_files",
        "calendars",
        "existing_middle_crosschecks",
        *FALSE_GATES,
    }
    if set(config) != expected:
        raise ValueError(
            f"Continuous-panel config differs: missing={sorted(expected-set(config))}, "
            f"extra={sorted(set(config)-expected)}"
        )
    locked = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "target_year_start": 1982,
        "target_year_end": 2016,
        "validated_early_year_start": 1982,
        "validated_early_year_end": 1989,
        "construction_year_start": 1990,
        "construction_year_end": 2011,
        "validated_later_year_start": 2012,
        "validated_later_year_end": 2016,
        "crops": ["mai", "soy"],
        "irrigation_regimes": ["noirr", "firr"],
        "families": FAMILIES,
        "latitude_chunk_cells": 10,
        "pilot_latitude_start": 100,
        "stage_fractions": "0,0.3,0.7,1",
        "expected_stages": 3,
        "wet_day_threshold_mm": 1.0,
        "heat_thresholds_c": [29.0, 30.0],
        "scpdsi_threshold": -2.0,
        "output_root": "data/interim/continuous_global_panel_1982_2016_v1",
        "audit_root": "outputs/continuous_global_panel_1982_2016_v1",
    }
    for field, expected_value in locked.items():
        if config[field] != expected_value:
            raise ValueError(f"Continuous-panel config {field} differs from its lock")
    for gate in FALSE_GATES:
        if config[gate] is not False:
            raise ValueError(f"Continuous-panel config {gate} must be exactly false")
    for field in PATH_FIELDS:
        if not isinstance(config[field], str) or not config[field]:
            raise ValueError(f"Continuous-panel config {field} must be a nonempty path")
    for field in (
        "precipitation_files",
        "temperature_files",
        "maximum_temperature_files",
    ):
        if len(config[field]) != 4 or len(config[field]) != len(set(config[field])):
            raise ValueError(f"{field} must contain four unique chronological files")
    calendars = config["calendars"]
    expected_pairs = {(crop, irrigation) for crop in config["crops"] for irrigation in config["irrigation_regimes"]}
    observed_pairs = {(item.get("crop"), item.get("irrigation")) for item in calendars}
    if len(calendars) != 4 or observed_pairs != expected_pairs:
        raise ValueError("Exactly one calendar per crop-irrigation regime is required")
    if any(set(item) != {"crop", "irrigation", "path"} for item in calendars):
        raise ValueError("Calendar registry schema differs")
    expected_crosschecks = {
        ("mai", "noirr", 1990, 1991),
        ("mai", "noirr", 1992, 2000),
        ("soy", "noirr", 2002, 2010),
    }
    observed_crosschecks = {
        (item.get("crop"), item.get("irrigation"), item.get("year_start"), item.get("year_end"))
        for item in config["existing_middle_crosschecks"]
    }
    if observed_crosschecks != expected_crosschecks or any(
        set(item)
        != {
            "crop",
            "irrigation",
            "year_start",
            "year_end",
            "season_panel",
            "stage_panel",
        }
        for item in config["existing_middle_crosschecks"]
    ):
        raise ValueError("Existing middle-period cross-check registry differs")
    return config


def calendar_registry(config_path: Path, config: dict[str, Any]) -> dict[tuple[str, str], Path]:
    return {
        (item["crop"], item["irrigation"]): _resolve(config_path, item["path"])
        for item in config["calendars"]
    }


def generate_tasks(config_path: Path, config: dict[str, Any]) -> list[PartitionTask]:
    output_root = _resolve(config_path, config["output_root"])
    chunk = int(config["latitude_chunk_cells"])
    pilot = int(config["pilot_latitude_start"])
    starts = [pilot, *(value for value in range(0, 360, chunk) if value != pilot)]
    tasks: list[PartitionTask] = []
    for lat_start in starts:
        lat_stop = min(lat_start + chunk, 360)
        for crop in config["crops"]:
            for irrigation in config["irrigation_regimes"]:
                for family in config["families"]:
                    directory = output_root / "middle_1990_2011" / family / f"{crop}_{irrigation}"
                    stem = (
                        f"{crop}_{irrigation}_{family}_lat{lat_start:03d}_{lat_stop:03d}_"
                        f"{config['construction_year_start']}_{config['construction_year_end']}"
                    )
                    output = directory / f"{stem}.parquet"
                    manifest = (
                        Path(str(output) + ".manifest.json")
                        if family == "historical_scpdsi_stage"
                        else None
                    )
                    receipt = Path(str(output) + ".receipt.json")
                    tasks.append(
                        PartitionTask(
                            family=family,
                            crop=crop,
                            irrigation=irrigation,
                            lat_start=lat_start,
                            lat_stop=lat_stop,
                            year_start=int(config["construction_year_start"]),
                            year_end=int(config["construction_year_end"]),
                            output=str(output),
                            manifest=str(manifest) if manifest else None,
                            receipt=str(receipt),
                        )
                    )
    expected = 360 // chunk * len(config["crops"]) * len(config["irrigation_regimes"]) * len(FAMILIES)
    if len(tasks) != expected or len({task.task_id for task in tasks}) != expected:
        raise AssertionError("Continuous-panel task registry is incomplete or duplicated")
    return tasks


def _validator_command(
    task: PartitionTask,
    config_path: Path,
    config: dict[str, Any],
    *,
    output: Path | None = None,
    manifest: Path | None = None,
) -> list[str]:
    target = output or Path(task.output)
    python = str(PROJECT / ".venv/bin/python")
    scripts = PROJECT / "scripts"
    if task.family == "direct_season":
        return [python, str(scripts / "validate_feature_partition.py"), str(target)]
    if task.family == "direct_stage":
        return [
            python,
            str(scripts / "validate_stage_feature_partition.py"),
            str(target),
            "--expected-stages",
            str(config["expected_stages"]),
            "--expected-stage-fractions",
            config["stage_fractions"],
        ]
    threshold_args = [item for value in config["heat_thresholds_c"] for item in ("--threshold-c", str(value))]
    if task.family == "heat_season":
        return [python, str(scripts / "validate_heat_partition.py"), str(target), *threshold_args]
    if task.family == "heat_stage":
        return [
            python,
            str(scripts / "validate_stage_heat_partition.py"),
            str(target),
            *threshold_args,
            "--expected-stages",
            str(config["expected_stages"]),
        ]
    if task.family == "historical_scpdsi_stage":
        calendar = calendar_registry(config_path, config)[(task.crop, task.irrigation)]
        scpdsi = _resolve(config_path, config["scpdsi_file"])
        manifest_target = manifest or Path(task.manifest or "")
        return [
            python,
            str(scripts / "validate_stage_scpdsi_partition.py"),
            str(target),
            "--manifest",
            str(manifest_target),
            "--threshold",
            str(config["scpdsi_threshold"]),
            "--expected-stages",
            str(config["expected_stages"]),
            "--expected-crop",
            task.crop,
            "--expected-irrigation",
            task.irrigation,
            "--expected-year-start",
            str(task.year_start),
            "--expected-year-end",
            str(task.year_end),
            "--expected-lat-start",
            str(task.lat_start),
            "--expected-lat-stop",
            str(task.lat_stop),
            "--expected-stage-fractions",
            config["stage_fractions"],
            "--expected-scpdsi-sha256",
            _source_sha256(scpdsi),
            "--expected-calendar-sha256",
            _source_sha256(calendar),
        ]
    raise ValueError(f"Unknown task family {task.family}")


def _scope_check(
    task: PartitionTask,
    path: Path,
    config_path: Path,
    config: dict[str, Any],
) -> None:
    frame = pd.read_parquet(path)
    if frame.empty:
        return
    if set(frame["crop"].astype(str)) != {task.crop}:
        raise ValueError("Partition crop differs from task")
    if set(frame["irrigation"].astype(str)) != {task.irrigation}:
        raise ValueError("Partition irrigation differs from task")
    if set(frame["harvest_year"].astype(int)) != set(range(task.year_start, task.year_end + 1)):
        raise ValueError("Partition harvest-year scope differs from task")
    coordinate_columns = ["lat", "lon", "lon_360"]
    coordinates = frame[coordinate_columns].to_numpy(dtype=float)
    if not np.isfinite(coordinates).all():
        raise ValueError("Partition grid coordinates must be finite")
    calendar = calendar_registry(config_path, config)[(task.crop, task.irrigation)]
    with xr.open_dataset(calendar, engine="h5netcdf", decode_timedelta=False) as dataset:
        expected_latitudes = set(
            float(value)
            for value in dataset.lat.isel(lat=slice(task.lat_start, task.lat_stop)).values
        )
        longitude_values = dataset.lon.values.astype(float)
        if task.family == "historical_scpdsi_stage":
            longitude_values = np.mod(longitude_values, 360.0)
        expected_longitudes = set(float(value) for value in longitude_values)
    if not set(float(value) for value in frame["lat"].unique()).issubset(
        expected_latitudes
    ):
        raise ValueError("Partition latitude coordinates differ from the task slice")
    if not set(float(value) for value in frame["lon"].unique()).issubset(
        expected_longitudes
    ):
        raise ValueError("Partition longitude coordinates differ from the calendar grid")
    if not np.allclose(
        frame["lon_360"].to_numpy(dtype=float),
        np.mod(frame["lon"].to_numpy(dtype=float), 360.0),
        rtol=0,
        atol=1e-10,
    ):
        raise ValueError("Partition lon_360 is inconsistent with longitude")
    if task.family == "direct_season" and not np.allclose(
        frame["wet_day_threshold_mm"].to_numpy(dtype=float),
        float(config["wet_day_threshold_mm"]),
        rtol=0,
        atol=1e-12,
    ):
        raise ValueError("Partition wet-day threshold differs from the task contract")
    if task.family in {"direct_stage", "heat_stage", "historical_scpdsi_stage"}:
        if set(frame["stage_fractions"].astype(str)) != {config["stage_fractions"]}:
            raise ValueError("Partition stage fractions differ from the task contract")


def validate_task(
    task: PartitionTask,
    config_path: Path,
    config: dict[str, Any],
    *,
    output: Path | None = None,
    manifest: Path | None = None,
    receipt: Path | None = None,
    require_receipt: bool = True,
) -> tuple[bool, str]:
    target = output or Path(task.output)
    manifest_target = manifest or (Path(task.manifest) if task.manifest else None)
    receipt_target = receipt or Path(task.receipt)
    if not target.is_file():
        return False, "partition_missing"
    if task.family == "historical_scpdsi_stage" and (manifest_target is None or not manifest_target.is_file()):
        return False, "manifest_missing"
    if require_receipt and not receipt_target.is_file():
        return False, "source_receipt_missing"
    command = _validator_command(
        task, config_path, config, output=target, manifest=manifest_target
    )
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().replace("\n", " ")
        return False, f"validator_failed:{detail[:500]}"
    try:
        _scope_check(task, target, config_path, config)
        if require_receipt:
            _validate_partition_receipt(
                task, config_path, config, target, receipt_target
            )
    except (ValueError, KeyError, OSError) as error:
        return False, f"scope_failed:{error}"
    return True, "valid"


def task_status(task: PartitionTask, config_path: Path, config: dict[str, Any]) -> tuple[str, str]:
    output = Path(task.output)
    lock = Path(str(output) + ".lock")
    if lock.exists():
        return "locked", "task lock exists; manual review required"
    artifacts = [output, Path(task.receipt)]
    if task.manifest:
        artifacts.append(Path(task.manifest))
    if not any(path.exists() for path in artifacts):
        return "missing", "not built"
    valid, detail = validate_task(task, config_path, config)
    return ("valid", detail) if valid else ("invalid", detail)


def _climate_paths(config_path: Path, config: dict[str, Any], field: str) -> list[Path]:
    root = _resolve(config_path, config["raw_climate_root"])
    return [root / name for name in config[field]]


@lru_cache(maxsize=None)
def _sha256_for_unchanged_file(
    resolved_path: str, size_bytes: int, modified_ns: int
) -> str:
    """Hash a file once per process while its stat identity is unchanged."""
    del size_bytes, modified_ns
    return sha256_file(Path(resolved_path))


def _source_sha256(path: Path) -> str:
    resolved = path.resolve()
    stat = resolved.stat()
    return _sha256_for_unchanged_file(
        str(resolved), int(stat.st_size), int(stat.st_mtime_ns)
    )


def _registered_climate_sources(
    config_path: Path,
    config: dict[str, Any],
    fields: list[str],
) -> list[dict[str, object]]:
    provenance_path = _resolve(config_path, config["raw_climate_provenance"])
    provenance = tomllib.loads(provenance_path.read_text(encoding="utf-8"))
    items = provenance.get("files")
    if not isinstance(items, list):
        raise ValueError("Climate provenance file registry is missing")
    by_name: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("Climate provenance file record is malformed")
        if item["name"] in by_name:
            raise ValueError("Climate provenance contains a duplicate filename")
        by_name[item["name"]] = item
    expected_variables = {
        "precipitation_files": "pr",
        "temperature_files": "tas",
        "maximum_temperature_files": "tasmax",
    }
    records: list[dict[str, object]] = []
    for field in fields:
        for path in _climate_paths(config_path, config, field):
            if not path.is_file() or path.name not in by_name:
                raise FileNotFoundError(f"Climate source or registry record missing: {path}")
            registered = by_name[path.name]
            if registered.get("variable") != expected_variables[field]:
                raise ValueError(f"Climate provenance variable differs: {path}")
            if path.stat().st_size != int(registered.get("size_bytes", -1)):
                raise ValueError(f"Climate source size differs from provenance: {path}")
            sha512 = str(registered.get("sha512", ""))
            if len(sha512) != 128 or any(character not in "0123456789abcdef" for character in sha512):
                raise ValueError(f"Climate provenance SHA-512 is malformed: {path}")
            records.append(
                {
                    "path": str(path.resolve()),
                    "variable": expected_variables[field],
                    "years": str(registered.get("years", "")),
                    "size_bytes": int(path.stat().st_size),
                    "registered_sha512": sha512,
                }
            )
    return records


def _builder_code_identity(task: PartitionTask) -> list[dict[str, str]]:
    scripts = PROJECT / "scripts"
    builder = {
        "direct_season": "build_crop_year_features.py",
        "direct_stage": "build_crop_stage_features.py",
        "heat_season": "build_crop_heat_features.py",
        "heat_stage": "build_crop_stage_heat_features.py",
        "historical_scpdsi_stage": "build_crop_stage_scpdsi_features.py",
    }[task.family]
    dependencies = {builder}
    if task.family in {"direct_season", "direct_stage", "heat_season", "heat_stage"}:
        dependencies.add("climate_inputs.py")
    if task.family in {
        "direct_stage",
        "heat_season",
        "heat_stage",
        "historical_scpdsi_stage",
    }:
        dependencies.add("build_crop_year_features.py")
    if task.family in {"heat_stage", "historical_scpdsi_stage"}:
        dependencies.add("build_crop_heat_features.py")
        dependencies.add("build_crop_stage_heat_features.py")
    if task.family == "historical_scpdsi_stage":
        dependencies.add("scpdsi_partition_provenance.py")
    return [
        {
            "path": str((scripts / name).resolve()),
            "sha256": _source_sha256(scripts / name),
        }
        for name in sorted(dependencies)
    ]


def _partition_source_identity(
    task: PartitionTask, config_path: Path, config: dict[str, Any]
) -> dict[str, object]:
    calendar = calendar_registry(config_path, config)[(task.crop, task.irrigation)]
    identity: dict[str, object] = {
        "calendar": {
            "path": str(calendar.resolve()),
            "sha256": _source_sha256(calendar),
        },
        "builder_code": _builder_code_identity(task),
    }
    if task.family in {"direct_season", "direct_stage"}:
        fields = ["precipitation_files", "temperature_files"]
    elif task.family in {"heat_season", "heat_stage"}:
        fields = ["maximum_temperature_files"]
    else:
        fields = []
    if fields:
        provenance = _resolve(config_path, config["raw_climate_provenance"])
        identity["climate_provenance"] = {
            "path": str(provenance.resolve()),
            "sha256": _source_sha256(provenance),
        }
        identity["climate_files"] = _registered_climate_sources(
            config_path, config, fields
        )
    if task.family == "historical_scpdsi_stage":
        source = _resolve(config_path, config["scpdsi_file"])
        provenance = _resolve(config_path, config["scpdsi_provenance"])
        registered = tomllib.loads(provenance.read_text(encoding="utf-8"))
        matching = [
            item
            for item in registered.get("files", [])
            if item.get("name") == source.name
        ]
        if len(matching) != 1:
            raise ValueError("scPDSI provenance must contain exactly one source record")
        actual_sha256 = _source_sha256(source)
        if matching[0].get("sha256") != actual_sha256:
            raise ValueError("Current scPDSI source differs from registered provenance")
        if int(matching[0].get("size_bytes", -1)) != source.stat().st_size:
            raise ValueError("Current scPDSI source size differs from provenance")
        identity["scpdsi_provenance"] = {
            "path": str(provenance.resolve()),
            "sha256": _source_sha256(provenance),
        }
        identity["scpdsi_file"] = {
            "path": str(source.resolve()),
            "size_bytes": int(source.stat().st_size),
            "sha256": actual_sha256,
        }
    return identity


def _partition_contract_identity(
    task: PartitionTask, config_path: Path, config: dict[str, Any]
) -> dict[str, object]:
    parameters: dict[str, object] = {}
    if task.family in {"direct_season", "direct_stage"}:
        parameters["wet_day_threshold_mm"] = float(config["wet_day_threshold_mm"])
    if task.family in {"direct_stage", "heat_stage", "historical_scpdsi_stage"}:
        parameters["stage_fractions"] = config["stage_fractions"]
        parameters["expected_stages"] = int(config["expected_stages"])
    if task.family in {"heat_season", "heat_stage"}:
        parameters["heat_thresholds_c"] = [
            float(value) for value in config["heat_thresholds_c"]
        ]
    if task.family == "historical_scpdsi_stage":
        parameters["scpdsi_threshold"] = float(config["scpdsi_threshold"])
    return {
        "continuous_panel_contract_id": CONTRACT_ID,
        "config_file": str(config_path.resolve()),
        "config_sha256": _source_sha256(config_path),
        "task_id": task.task_id,
        "family": task.family,
        "crop": task.crop,
        "irrigation": task.irrigation,
        "year_start": task.year_start,
        "year_end": task.year_end,
        "lat_start": task.lat_start,
        "lat_stop": task.lat_stop,
        "output_file": str(Path(task.output).resolve()),
        "parameters": parameters,
        "sources": _partition_source_identity(task, config_path, config),
    }


def _write_partition_receipt(
    receipt: Path,
    task: PartitionTask,
    config_path: Path,
    config: dict[str, Any],
    output: Path,
    build_metrics: dict[str, object],
) -> None:
    frame = pd.read_parquet(output)
    payload = {
        "schema_version": 1,
        "contract_id": PARTITION_RECEIPT_CONTRACT_ID,
        "status": "validated_source_bound_partition",
        "identity": _partition_contract_identity(task, config_path, config),
        "output_sha256": sha256_file(output),
        "output_bytes": int(output.stat().st_size),
        "output_rows": int(len(frame)),
        "build_metrics": build_metrics,
        **{gate: False for gate in FALSE_GATES},
    }
    receipt.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _validate_partition_receipt(
    task: PartitionTask,
    config_path: Path,
    config: dict[str, Any],
    output: Path,
    receipt: Path,
) -> None:
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    expected_keys = {
        "schema_version", "contract_id", "status", "identity",
        "output_sha256", "output_bytes", "output_rows", "build_metrics",
        *FALSE_GATES,
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ValueError("Partition source-receipt schema differs")
    if payload.get("schema_version") != 1:
        raise ValueError("Partition source-receipt schema version differs")
    if payload.get("contract_id") != PARTITION_RECEIPT_CONTRACT_ID:
        raise ValueError("Partition source-receipt contract differs")
    if payload.get("status") != "validated_source_bound_partition":
        raise ValueError("Partition source-receipt status differs")
    if payload.get("identity") != _partition_contract_identity(
        task, config_path, config
    ):
        raise ValueError("Partition source/task identity differs from its receipt")
    if payload.get("output_sha256") != sha256_file(output):
        raise ValueError("Partition hash differs from its source receipt")
    if payload.get("output_bytes") != output.stat().st_size:
        raise ValueError("Partition byte size differs from its source receipt")
    if payload.get("output_rows") != len(pd.read_parquet(output)):
        raise ValueError("Partition row count differs from its source receipt")
    metrics = payload.get("build_metrics")
    if not isinstance(metrics, dict) or set(metrics) != {
        "schema_version", "status", "started_utc", "finished_utc",
        "wall_seconds", "peak_rss_bytes", "returncode",
    }:
        raise ValueError("Partition build-metrics schema differs")
    if (
        metrics.get("schema_version") != 1
        or metrics.get("status") != "command_completed"
        or metrics.get("returncode") != 0
    ):
        raise ValueError("Partition build did not record successful resource metrics")
    try:
        wall_seconds = float(metrics.get("wall_seconds", np.nan))
        peak_rss_bytes = int(metrics.get("peak_rss_bytes", 0))
    except (TypeError, ValueError) as error:
        raise ValueError("Partition build resource metrics are invalid") from error
    if not np.isfinite(wall_seconds) or wall_seconds < 0 or peak_rss_bytes <= 0:
        raise ValueError("Partition build resource metrics are invalid")
    for gate in FALSE_GATES:
        if payload.get(gate) is not False:
            raise ValueError(f"Partition source receipt {gate} must be false")


def _build_command(
    task: PartitionTask,
    config_path: Path,
    config: dict[str, Any],
    output: Path,
    manifest: Path | None,
) -> list[str]:
    python = str(PROJECT / ".venv/bin/python")
    scripts = PROJECT / "scripts"
    calendar = calendar_registry(config_path, config)[(task.crop, task.irrigation)]
    common = [
        "--calendar",
        str(calendar),
        "--crop",
        task.crop,
        "--irrigation",
        task.irrigation,
        "--year-start",
        str(task.year_start),
        "--year-end",
        str(task.year_end),
        "--lat-start",
        str(task.lat_start),
        "--lat-stop",
        str(task.lat_stop),
    ]
    if task.family in {"direct_season", "direct_stage"}:
        script = "build_crop_year_features.py" if task.family == "direct_season" else "build_crop_stage_features.py"
        command = [
            python,
            str(scripts / script),
            "--precip",
            *(str(path) for path in _climate_paths(config_path, config, "precipitation_files")),
            "--temperature",
            *(str(path) for path in _climate_paths(config_path, config, "temperature_files")),
            *common,
            "--wet-day-mm",
            str(config["wet_day_threshold_mm"]),
        ]
        if task.family == "direct_stage":
            command.extend(["--stage-fractions", config["stage_fractions"]])
        return [*command, "--out", str(output)]
    if task.family in {"heat_season", "heat_stage"}:
        script = "build_crop_heat_features.py" if task.family == "heat_season" else "build_crop_stage_heat_features.py"
        command = [
            python,
            str(scripts / script),
            "--tasmax",
            *(str(path) for path in _climate_paths(config_path, config, "maximum_temperature_files")),
            *common,
        ]
        for threshold in config["heat_thresholds_c"]:
            command.extend(["--threshold-c", str(threshold)])
        if task.family == "heat_stage":
            command.extend(["--stage-fractions", config["stage_fractions"]])
        return [*command, "--out", str(output)]
    if task.family == "historical_scpdsi_stage":
        if manifest is None:
            raise AssertionError("scPDSI task requires a manifest path")
        scpdsi = _resolve(config_path, config["scpdsi_file"])
        return [
            python,
            str(scripts / "build_crop_stage_scpdsi_features.py"),
            "--scpdsi",
            str(scpdsi),
            *common,
            "--threshold",
            str(config["scpdsi_threshold"]),
            "--stage-fractions",
            config["stage_fractions"],
            "--out",
            str(output),
            "--manifest-out",
            str(manifest),
            "--scpdsi-sha256",
            _source_sha256(scpdsi),
            "--calendar-sha256",
            _source_sha256(calendar),
        ]
    raise ValueError(f"Unknown task family {task.family}")


def _append_event(config_path: Path, config: dict[str, Any], event: dict[str, Any]) -> None:
    root = _resolve(config_path, config["audit_root"])
    root.mkdir(parents=True, exist_ok=True)
    path = root / "partition_build_events.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")


def build_task(task: PartitionTask, config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    status, detail = task_status(task, config_path, config)
    if status == "valid":
        return {"task_id": task.task_id, "status": "skipped_valid", "detail": detail}
    if status != "missing":
        raise RuntimeError(
            f"Refusing to overwrite {task.task_id}: status={status}; detail={detail}"
        )
    output = Path(task.output)
    manifest = Path(task.manifest) if task.manifest else None
    receipt = Path(task.receipt)
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = Path(str(output) + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RuntimeError(f"Refusing to start locked task {task.task_id}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps({"task_id": task.task_id, "pid": os.getpid()}) + "\n")

    token = uuid.uuid4().hex
    temporary_output = output.parent / f".{output.stem}.partial-{token}.parquet"
    temporary_manifest = (
        output.parent / f".{output.stem}.partial-{token}.manifest.json"
        if manifest is not None
        else None
    )
    temporary_receipt = output.parent / f".{output.stem}.partial-{token}.receipt.json"
    temporary_metrics = output.parent / f".{output.stem}.partial-{token}.metrics.json"
    _append_event(config_path, config, {"event": "started", "task_id": task.task_id})
    try:
        command = _build_command(
            task, config_path, config, temporary_output, temporary_manifest
        )
        measured_command = [
            str(PROJECT / ".venv/bin/python"),
            str(PROJECT / "scripts" / "run_command_with_resource_receipt.py"),
            "--metrics-out",
            str(temporary_metrics),
            "--",
            *command,
        ]
        subprocess.run(measured_command, check=True)
        build_metrics = json.loads(temporary_metrics.read_text(encoding="utf-8"))
        valid, validation_detail = validate_task(
            task,
            config_path,
            config,
            output=temporary_output,
            manifest=temporary_manifest,
            require_receipt=False,
        )
        if not valid:
            raise ValueError(f"New partition failed validation: {validation_detail}")
        _write_partition_receipt(
            temporary_receipt,
            task,
            config_path,
            config,
            temporary_output,
            build_metrics,
        )
        valid, validation_detail = validate_task(
            task,
            config_path,
            config,
            output=temporary_output,
            manifest=temporary_manifest,
            receipt=temporary_receipt,
        )
        if not valid:
            raise ValueError(
                f"New partition source receipt failed validation: {validation_detail}"
            )
        if (
            output.exists()
            or receipt.exists()
            or (manifest is not None and manifest.exists())
        ):
            raise RuntimeError("Final target appeared during construction; refusing overwrite")
        if temporary_manifest is not None and manifest is not None:
            payload = json.loads(temporary_manifest.read_text(encoding="utf-8"))
            payload["output_file"] = str(output.resolve())
            temporary_manifest.write_text(
                json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
                encoding="utf-8",
            )
        os.replace(temporary_output, output)
        if temporary_manifest is not None and manifest is not None:
            os.replace(temporary_manifest, manifest)
        os.replace(temporary_receipt, receipt)
        final_valid, final_detail = validate_task(task, config_path, config)
        if not final_valid:
            raise RuntimeError(f"Published partition failed validation: {final_detail}")
        record = {
            "task_id": task.task_id,
            "status": "completed_valid",
            "output": str(output),
            "output_sha256": sha256_file(output),
            "output_bytes": output.stat().st_size,
            "receipt": str(receipt),
            "receipt_sha256": sha256_file(receipt),
            "build_wall_seconds": build_metrics["wall_seconds"],
            "build_peak_rss_bytes": build_metrics["peak_rss_bytes"],
        }
        if manifest is not None:
            record["manifest"] = str(manifest)
            record["manifest_sha256"] = sha256_file(manifest)
        _append_event(config_path, config, {"event": "completed", **record})
        return record
    except Exception as error:
        _append_event(
            config_path,
            config,
            {"event": "failed", "task_id": task.task_id, "error": str(error)[:1000]},
        )
        raise
    finally:
        for temporary in (
            temporary_output,
            temporary_manifest,
            temporary_receipt,
            temporary_metrics,
        ):
            if temporary is not None and temporary.exists():
                temporary.unlink()
        if lock.exists():
            lock.unlink()


def _source_audit(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    required_paths = {
        field: _resolve(config_path, config[field])
        for field in PATH_FIELDS
        if field not in {"output_root", "audit_root"}
    }
    missing = [str(path) for path in required_paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Required continuous-panel source is missing: {missing}")
    climate_provenance = tomllib.loads(
        required_paths["raw_climate_provenance"].read_text(encoding="utf-8")
    )
    if not isinstance(climate_provenance.get("files"), list):
        raise ValueError("Climate provenance file registry is missing")
    provenance_files = {item["name"]: item for item in climate_provenance["files"]}
    if len(provenance_files) != len(climate_provenance["files"]):
        raise ValueError("Climate provenance contains duplicate filenames")
    climate_records: list[dict[str, Any]] = []
    for field in (
        "precipitation_files",
        "temperature_files",
        "maximum_temperature_files",
    ):
        for path in _climate_paths(config_path, config, field):
            if not path.is_file() or path.name not in provenance_files:
                raise FileNotFoundError(f"Climate file or provenance record missing: {path}")
            record = provenance_files[path.name]
            expected_variable = {
                "precipitation_files": "pr",
                "temperature_files": "tas",
                "maximum_temperature_files": "tasmax",
            }[field]
            if record.get("variable") != expected_variable:
                raise ValueError(f"Climate variable differs from provenance: {path}")
            if path.stat().st_size != int(record["size_bytes"]):
                raise ValueError(f"Climate file size differs from provenance: {path}")
            climate_records.append(
                {
                    "path": str(path),
                    "variable": record["variable"],
                    "years": record["years"],
                    "size_bytes": path.stat().st_size,
                    "registered_sha512": record["sha512"],
                    "size_verified": True,
                    "full_hash_recomputed_now": False,
                }
            )

    chronology: dict[str, Any] = {}
    arrays: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    with ExitStack() as stack:
        for preferred, field in (
            ("pr", "precipitation_files"),
            ("tas", "temperature_files"),
            ("tasmax", "maximum_temperature_files"),
        ):
            time, lat, lon = daily_series_coordinates(
                stack, [str(path) for path in _climate_paths(config_path, config, field)], preferred
            )
            arrays[preferred] = (time, lat, lon)
            chronology[preferred] = {
                "days": len(time),
                "first": str(time[0]),
                "last": str(time[-1]),
                "latitude_cells": len(lat),
                "longitude_cells": len(lon),
                "strict_daily_chronology_passed": True,
            }
            if (
                len(time) != 14244
                or time[0] != np.datetime64("1981-01-01T00:00:00", "ns")
                or time[-1] != np.datetime64("2019-12-31T00:00:00", "ns")
                or len(lat) != 360
                or len(lon) != 720
            ):
                raise ValueError(
                    f"{preferred} does not have the locked 1981-2019 daily global grid"
                )
        for preferred in ("tas", "tasmax"):
            if not all(
                np.array_equal(left, right)
                for left, right in zip(arrays["pr"], arrays[preferred])
            ):
                raise ValueError(f"pr and {preferred} time/grid coordinates differ")

    calendar_records = []
    for pair, path in calendar_registry(config_path, config).items():
        if not path.is_file():
            raise FileNotFoundError(path)
        with xr.open_dataset(
            path, engine="h5netcdf", decode_timedelta=False
        ) as calendar:
            if {"planting_day", "maturity_day"} - set(calendar.data_vars):
                raise ValueError(f"Crop calendar fields are incomplete: {path}")
            if (
                calendar.planting_day.dims != ("lat", "lon")
                or calendar.maturity_day.dims != ("lat", "lon")
                or not np.array_equal(calendar.lat.values, arrays["pr"][1])
                or not np.array_equal(calendar.lon.values, arrays["pr"][2])
            ):
                raise ValueError(f"Crop calendar grid differs from daily climate: {path}")
        calendar_records.append(
            {
                "crop": pair[0],
                "irrigation": pair[1],
                "path": str(path),
                "sha256": _source_sha256(path),
                "daily_climate_grid_match": True,
            }
        )
    gdhy_audit = json.loads(required_paths["gdhy_support_audit"].read_text(encoding="utf-8"))
    if gdhy_audit.get("years") != list(range(1981, 2017)):
        raise ValueError("GDHY source audit does not cover exact 1981-2016 years")
    endpoint = json.loads(required_paths["validated_endpoint_receipt"].read_text(encoding="utf-8"))
    if endpoint.get("status") != "validated_nonproduction_predictive_diagnostic":
        raise ValueError("Early/later endpoint validation receipt status differs")
    for gate in (
        "causal_interpretation_authorized",
        "production_fit_authorized",
        "damage_calculation_authorized",
        "future_projection_authorized",
        "scc_authorized",
    ):
        if endpoint.get(gate) is not False:
            raise ValueError(f"Validated endpoint receipt gate {gate} differs")
    scpdsi_provenance = tomllib.loads(
        required_paths["scpdsi_provenance"].read_text(encoding="utf-8")
    )
    scpdsi_records = [
        item
        for item in scpdsi_provenance.get("files", [])
        if item.get("name") == required_paths["scpdsi_file"].name
    ]
    if len(scpdsi_records) != 1:
        raise ValueError("scPDSI provenance must contain exactly one source record")
    scpdsi_sha256 = _source_sha256(required_paths["scpdsi_file"])
    if (
        scpdsi_records[0].get("sha256") != scpdsi_sha256
        or int(scpdsi_records[0].get("size_bytes", -1))
        != required_paths["scpdsi_file"].stat().st_size
    ):
        raise ValueError("Current scPDSI source differs from registered provenance")
    return {
        "climate_files": climate_records,
        "climate_file_count": len(climate_records),
        "climate_total_bytes": sum(record["size_bytes"] for record in climate_records),
        "chronology": chronology,
        "calendars": calendar_records,
        "gdhy_years_exact_1981_2016": True,
        "raw_climate_provenance_sha256": _source_sha256(
            required_paths["raw_climate_provenance"]
        ),
        "gdhy_support_audit_sha256": _source_sha256(required_paths["gdhy_support_audit"]),
        "scpdsi_sha256": scpdsi_sha256,
        "scpdsi_provenance_sha256": _source_sha256(
            required_paths["scpdsi_provenance"]
        ),
        "mirca_weights_sha256": _source_sha256(required_paths["mirca_weights"]),
        "validated_endpoint_receipt_sha256": sha256_file(
            required_paths["validated_endpoint_receipt"]
        ),
    }


def _crosscheck_audit(config_path: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in config["existing_middle_crosschecks"]:
        expected_years = list(range(item["year_start"], item["year_end"] + 1))
        artifacts: dict[str, Any] = {}
        for role, field in (("season", "season_panel"), ("stage", "stage_panel")):
            path = _resolve(config_path, item[field])
            if not path.is_file():
                raise FileNotFoundError(path)
            frame = pd.read_parquet(path)
            years = sorted(int(value) for value in frame["harvest_year"].unique())
            if years != expected_years:
                raise ValueError(f"Middle cross-check year coverage differs: {path}")
            artifacts[role] = {
                "path": str(path),
                "sha256": sha256_file(path),
                "rows": len(frame),
                "column_count": len(frame.columns),
                "year_coverage_verified": True,
            }
        records.append(
            {
                "crop": item["crop"],
                "irrigation": item["irrigation"],
                "year_start": item["year_start"],
                "year_end": item["year_end"],
                "artifacts": artifacts,
                "role": "crosscheck_only_not_spliced_into_isolated_construction",
            }
        )
    return records


def audit_plan(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    tasks = generate_tasks(config_path, config)
    status_records = []
    counts = {status: 0 for status in ("missing", "valid", "invalid", "locked")}
    by_family: dict[str, dict[str, int]] = {
        family: {status: 0 for status in counts} for family in FAMILIES
    }
    for task in tasks:
        status, detail = task_status(task, config_path, config)
        counts[status] += 1
        by_family[task.family][status] += 1
        if status != "missing":
            status_record: dict[str, object] = {
                "task_id": task.task_id,
                "status": status,
                "detail": detail,
            }
            if status == "valid":
                receipt_path = Path(task.receipt)
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                status_record.update(
                    {
                        "output": task.output,
                        "output_sha256": receipt["output_sha256"],
                        "output_bytes": receipt["output_bytes"],
                        "output_rows": receipt["output_rows"],
                        "receipt": task.receipt,
                        "receipt_sha256": sha256_file(receipt_path),
                        "build_metrics": receipt["build_metrics"],
                    }
                )
                if task.manifest:
                    status_record["manifest"] = task.manifest
                    status_record["manifest_sha256"] = sha256_file(
                        Path(task.manifest)
                    )
            status_records.append(status_record)
    missing_years = list(
        range(config["construction_year_start"], config["construction_year_end"] + 1)
    )
    return {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "status": "continuous_panel_readiness_audited_no_fit_or_scc_authorized",
        "config_file": str(config_path),
        "config_sha256": sha256_file(config_path),
        "target_years": list(range(config["target_year_start"], config["target_year_end"] + 1)),
        "validated_endpoint_years": [
            *range(config["validated_early_year_start"], config["validated_early_year_end"] + 1),
            *range(config["validated_later_year_start"], config["validated_later_year_end"] + 1),
        ],
        "construction_years": missing_years,
        "construction_year_count": len(missing_years),
        "partition_task_count": len(tasks),
        "task_status_counts": counts,
        "task_status_by_family": by_family,
        "nonmissing_task_records": status_records,
        "source_audit": _source_audit(config_path, config),
        "existing_middle_crosschecks": _crosscheck_audit(config_path, config),
        "new_namespace_only": True,
        "existing_validated_outputs_modified": False,
        "invalid_or_locked_outputs_overwritten": False,
        "family_separation_preserved": True,
        **{gate: False for gate in FALSE_GATES},
    }


def select_tasks(
    tasks: list[PartitionTask],
    *,
    families: list[str] | None,
    crops: list[str] | None,
    irrigations: list[str] | None,
    lat_starts: list[int] | None,
) -> list[PartitionTask]:
    return [
        task
        for task in tasks
        if (not families or task.family in families)
        and (not crops or task.crop in crops)
        and (not irrigations or task.irrigation in irrigations)
        and (not lat_starts or task.lat_start in lat_starts)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--audit-out")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-new-partitions", type=int, default=0)
    parser.add_argument("--family", action="append", choices=FAMILIES)
    parser.add_argument("--crop", action="append", choices=["mai", "soy"])
    parser.add_argument("--irrigation", action="append", choices=["noirr", "firr"])
    parser.add_argument("--lat-start", action="append", type=int)
    args = parser.parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)
    if args.execute and args.max_new_partitions <= 0:
        raise ValueError("Execution requires a strictly positive --max-new-partitions cap")
    if not args.execute and args.max_new_partitions != 0:
        raise ValueError("--max-new-partitions is only valid with --execute")
    chunk = config["latitude_chunk_cells"]
    if args.lat_start and any(value < 0 or value >= 360 or value % chunk for value in args.lat_start):
        raise ValueError("--lat-start must be an in-range configured chunk boundary")

    audit = audit_plan(config_path, config)
    if args.audit_out:
        audit_path = Path(args.audit_out)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(
            json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    if not args.execute:
        print(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False))
        return

    selected = select_tasks(
        generate_tasks(config_path, config),
        families=args.family,
        crops=args.crop,
        irrigations=args.irrigation,
        lat_starts=args.lat_start,
    )
    completed: list[dict[str, Any]] = []
    new_count = 0
    for task in selected:
        status, _ = task_status(task, config_path, config)
        if status == "valid":
            continue
        if new_count >= args.max_new_partitions:
            break
        record = build_task(task, config_path, config)
        completed.append(record)
        if record["status"] == "completed_valid":
            new_count += 1
    print(
        json.dumps(
            {
                "status": "bounded_partition_execution_completed",
                "selected_task_count": len(selected),
                "new_partition_cap": args.max_new_partitions,
                "new_valid_partitions": new_count,
                "records": completed,
                "existing_validated_outputs_modified": False,
                **{gate: False for gate in FALSE_GATES},
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
