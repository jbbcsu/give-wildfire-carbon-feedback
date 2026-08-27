#!/usr/bin/env python3
"""Synthetic adversarial tests for complete continuous-panel assembly."""
from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assemble_continuous_global_panel_partitions import (  # noqa: E402
    CONTRACT_ID,
    FALSE_GATES,
    PARTITION_CONTRACT_ID,
    PARTITION_RECEIPT_CONTRACT_ID,
    _exact_discovered_files,
    _parquet_rows,
    _require_no_absolute_strings,
    assemble_complete_panel,
    expected_columns,
    generate_tasks,
    load_calendar_coordinates,
    load_config,
    preflight_sources,
    reconcile_direct_pair,
    reconcile_heat_pair,
    reconcile_scpdsi_boundary,
    sha256_file,
    threshold_name,
    validate_partition_frame,
    validate_receipt_envelope,
    validate_registry_contract,
    validate_scpdsi_manifest,
    verify_source_records_unchanged,
)


CONFIG_PATH = PROJECT / "config" / "continuous_global_panel_1982_2016_v1.toml"
config = load_config(CONFIG_PATH)
registered = generate_tasks(CONFIG_PATH, config)
source_root = validate_registry_contract(registered, CONFIG_PATH, config)
assert source_root.name == "middle_1990_2011"
assert len(registered) == 720


def must_fail(function, text: str) -> None:
    try:
        function()
    except (ValueError, FileNotFoundError) as error:
        assert text in str(error), (text, str(error))
    else:
        raise AssertionError(f"Expected failure containing {text!r}")


coordinates = load_calendar_coordinates(CONFIG_PATH, config)


def synthetic_frame(task) -> pd.DataFrame:
    columns = expected_columns(task.family, config)
    if task.lat_start != 100:
        return pd.DataFrame(columns=columns)
    coord = coordinates[(task.crop, task.irrigation)]
    lat = float(coord.latitudes[task.lat_start])
    native_lon = float(coord.longitudes[0])
    canonical_lon = native_lon % 360.0
    rows: list[dict[str, object]] = []
    for year in range(task.year_start, task.year_end + 1):
        common = {
            "harvest_year": year,
            "plant_year": year,
            "lat": lat,
            "lon": canonical_lon if task.family == "historical_scpdsi_stage" else native_lon,
            "lon_360": canonical_lon,
            "crop": task.crop,
            "irrigation": task.irrigation,
            "cross_year": False,
        }
        if task.family == "direct_season":
            rows.append(
                {
                    **common,
                    "plant_doy": 100,
                    "maturity_doy": 108,
                    "season_days": 9,
                    "tmean_c": 20.0,
                    "precip_mm": 12.0,
                    "wet_days_n": 4,
                    "cdd_max_days": 2,
                    "rx1day_mm": 4.0,
                    "rx5day_mm": 8.0,
                    "wet_day_threshold_mm": 1.0,
                }
            )
        elif task.family == "direct_stage":
            for stage, (start, stop, tmean, rain, wet, cdd, rx1) in enumerate(
                [
                    (1, 3, 19.0, 3.0, 1, 2, 2.0),
                    (4, 6, 20.0, 4.0, 2, 1, 3.0),
                    (7, 9, 21.0, 5.0, 1, 2, 4.0),
                ],
                start=1,
            ):
                rows.append(
                    {
                        **common,
                        "stage_id": stage,
                        "stage_start_offset_day": start,
                        "stage_end_offset_day": stop,
                        "stage_days": 3,
                        "stage_fractions": "0,0.3,0.7,1",
                        "tmean_c": tmean,
                        "precip_mm": rain,
                        "wet_days_n": wet,
                        "cdd_max_days": cdd,
                        "rx1day_mm": rx1,
                        "rx5day_mm": np.nan,
                    }
                )
        elif task.family == "heat_season":
            rows.append(
                {
                    **common,
                    "plant_doy": 100,
                    "maturity_doy": 108,
                    "season_days": 9,
                    "tmax_mean_c": 30.0,
                    f"{threshold_name(29.0)}_days": 6,
                    f"{threshold_name(29.0)}_degree_days": 7.5,
                    f"{threshold_name(30.0)}_days": 3,
                    f"{threshold_name(30.0)}_degree_days": 3.0,
                }
            )
        elif task.family == "heat_stage":
            values = [
                (1, 3, 29.0, 1, 0.5, 0, 0.0),
                (4, 6, 30.0, 2, 2.0, 1, 0.5),
                (7, 9, 31.0, 3, 5.0, 2, 2.5),
            ]
            for stage, (start, stop, tmax, d29, dd29, d30, dd30) in enumerate(values, start=1):
                rows.append(
                    {
                        **common,
                        "stage_id": stage,
                        "stage_start_offset_day": start,
                        "stage_end_offset_day": stop,
                        "stage_days": 3,
                        "stage_fractions": "0,0.3,0.7,1",
                        "tmax_mean_c": tmax,
                        f"{threshold_name(29.0)}_days": d29,
                        f"{threshold_name(29.0)}_degree_days": dd29,
                        f"{threshold_name(30.0)}_days": d30,
                        f"{threshold_name(30.0)}_degree_days": dd30,
                    }
                )
        elif task.family == "historical_scpdsi_stage":
            for stage, (start, stop) in enumerate([(1, 3), (4, 6), (7, 9)], start=1):
                rows.append(
                    {
                        **common,
                        "plant_doy": 100,
                        "maturity_doy": 108,
                        "season_days": 9,
                        "stage_id": stage,
                        "stage_start_offset_day": start,
                        "stage_end_offset_day": stop,
                        "stage_days": 3,
                        "stage_fractions": "0,0.3,0.7,1",
                        "scpdsi_mean": -1.0,
                        "scpdsi_min": -1.5,
                        "scpdsi_days_at_or_below_threshold": 0,
                        "scpdsi_threshold": -2.0,
                        "monthly_index_days_covered": 3,
                        "drought_index_name": "CRU_TS_scpdsi",
                        "drought_source_role": "historical_benchmark_not_future_scc_input",
                    }
                )
        else:
            raise AssertionError(task.family)
    return pd.DataFrame(rows, columns=columns)


def write_receipt(task, calendar_hash: str, scpdsi_hash: str) -> None:
    output = Path(task.output)
    sources: dict[str, object] = {
        "calendar": {"path": "synthetic-calendar.nc", "sha256": calendar_hash}
    }
    if task.family == "historical_scpdsi_stage":
        sources["scpdsi_file"] = {
            "path": "synthetic-scpdsi.nc",
            "size_bytes": 1,
            "sha256": scpdsi_hash,
        }
    payload = {
        "schema_version": 1,
        "contract_id": PARTITION_RECEIPT_CONTRACT_ID,
        "status": "validated_source_bound_partition",
        "identity": {
            "continuous_panel_contract_id": CONTRACT_ID,
            "config_file": str(CONFIG_PATH.resolve()),
            "config_sha256": sha256_file(CONFIG_PATH),
            "task_id": task.task_id,
            "family": task.family,
            "crop": task.crop,
            "irrigation": task.irrigation,
            "year_start": task.year_start,
            "year_end": task.year_end,
            "lat_start": task.lat_start,
            "lat_stop": task.lat_stop,
            "output_file": str(output.resolve()),
            "parameters": {},
            "sources": sources,
        },
        "output_sha256": sha256_file(output),
        "output_bytes": output.stat().st_size,
        "output_rows": _parquet_rows(output),
        "build_metrics": {
            "schema_version": 1,
            "status": "command_completed",
            "started_utc": "2026-08-26T00:00:00+00:00",
            "finished_utc": "2026-08-26T00:00:01+00:00",
            "wall_seconds": 1.0,
            "peak_rss_bytes": 1,
            "returncode": 0,
        },
        **{gate: False for gate in FALSE_GATES},
    }
    Path(task.receipt).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_manifest(task, calendar_hash: str, scpdsi_hash: str) -> None:
    if not task.manifest:
        return
    output = Path(task.output)
    manifest = {
        "schema_version": 1,
        "contract_id": PARTITION_CONTRACT_ID,
        "output_file": str(output.resolve()),
        "output_sha256": sha256_file(output),
        "output_rows": _parquet_rows(output),
        "scpdsi_source_file": "synthetic-scpdsi.nc",
        "scpdsi_source_sha256": scpdsi_hash,
        "calendar_source_file": "synthetic-calendar.nc",
        "calendar_source_sha256": calendar_hash,
        "drought_variable": "scpdsi",
        "crop": task.crop,
        "irrigation": task.irrigation,
        "year_start": task.year_start,
        "year_end": task.year_end,
        "lat_start": task.lat_start,
        "lat_stop": task.lat_stop,
        "threshold": -2.0,
        "stage_fractions": "0,0.3,0.7,1",
        "expected_stages": 3,
        "calendar_fields_embedded": [
            "plant_year", "cross_year", "plant_doy", "maturity_doy", "season_days"
        ],
        "drought_source_role": "historical_benchmark_not_future_scc_input",
    }
    Path(task.manifest).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


configured_root = PROJECT / config["output_root"]
configured_root.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix=".synthetic-assembly-test-", dir=configured_root) as directory:
    root = Path(directory)
    synthetic_source = root / "source"
    synthetic_tasks = []
    calendar_hash, scpdsi_hash = "a" * 64, "b" * 64
    for task in registered:
        directory_path = synthetic_source / task.family / f"{task.crop}_{task.irrigation}"
        directory_path.mkdir(parents=True, exist_ok=True)
        output = directory_path / Path(task.output).name
        manifest = Path(str(output) + ".manifest.json") if task.manifest else None
        synthetic = replace(
            task,
            output=str(output),
            receipt=str(output) + ".receipt.json",
            manifest=str(manifest) if manifest else None,
        )
        frame = synthetic_frame(synthetic)
        frame.to_parquet(output, index=False)
        write_receipt(synthetic, calendar_hash, scpdsi_hash)
        write_manifest(synthetic, calendar_hash, scpdsi_hash)
        synthetic_tasks.append(synthetic)

    records = preflight_sources(
        synthetic_tasks,
        CONFIG_PATH,
        config,
        synthetic_source,
        strict_source_identity=False,
    )
    assert len(records) == 720

    populated = {
        task.family: task
        for task in synthetic_tasks
        if task.crop == "mai" and task.irrigation == "noirr" and task.lat_start == 100
    }
    frames = {family: pd.read_parquet(task.output) for family, task in populated.items()}
    direct = reconcile_direct_pair(frames["direct_season"], frames["direct_stage"], 1e-9)
    heat = reconcile_heat_pair(frames["heat_season"], frames["heat_stage"], [29.0, 30.0], 1e-9)
    drought = reconcile_scpdsi_boundary(
        frames["direct_stage"], frames["historical_scpdsi_stage"], 1e-9
    )
    assert direct["keys"] == 22 and heat["keys"] == 22
    assert drought["common_keys"] == 22 and drought["scpdsi_only_keys"] == 0

    subset_scpdsi = frames["historical_scpdsi_stage"].query("harvest_year != 1990")
    subset = reconcile_scpdsi_boundary(frames["direct_stage"], subset_scpdsi, 1e-9)
    assert subset["common_keys"] == 21 and subset["direct_only_keys"] == 1

    bad_direct = frames["direct_stage"].copy()
    bad_direct.loc[bad_direct.index[0], "precip_mm"] += 1.0
    must_fail(
        lambda: reconcile_direct_pair(frames["direct_season"], bad_direct, 1e-9),
        "stage-summed precipitation",
    )
    bad_heat = frames["heat_stage"].copy()
    bad_heat.loc[bad_heat.index[0], f"{threshold_name(29.0)}_degree_days"] += 1.0
    must_fail(
        lambda: reconcile_heat_pair(frames["heat_season"], bad_heat, [29.0, 30.0], 1e-9),
        "stage-summed",
    )
    extra_scpdsi = frames["historical_scpdsi_stage"].copy()
    extra_scpdsi.loc[extra_scpdsi.index[:3], "lat"] += 0.5
    extra_scpdsi.loc[extra_scpdsi.index[:3], "lon_360"] += 0.5
    must_fail(
        lambda: reconcile_scpdsi_boundary(frames["direct_stage"], extra_scpdsi, 1e-9),
        "outside direct-weather support",
    )

    scoped_task = populated["direct_season"]
    missing_year = frames["direct_season"].query("harvest_year != 1990")
    must_fail(
        lambda: validate_partition_frame(scoped_task, missing_year, config, coordinates),
        "harvest-year coverage",
    )

    receipt_path = Path(scoped_task.receipt)
    original_receipt = receipt_path.read_text(encoding="utf-8")
    tampered = json.loads(original_receipt)
    tampered["output_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(tampered), encoding="utf-8")
    must_fail(
        lambda: validate_receipt_envelope(
            scoped_task, CONFIG_PATH, config, strict_source_identity=False
        ),
        "output hash differs",
    )
    receipt_path.write_text(original_receipt, encoding="utf-8")

    output_path = Path(scoped_task.output)
    original_output = output_path.read_bytes()
    altered_output = pd.read_parquet(output_path)
    altered_output.loc[altered_output.index[0], "precip_mm"] += 0.25
    altered_output.to_parquet(output_path, index=False)
    must_fail(
        lambda: verify_source_records_unchanged(synthetic_tasks, records),
        "Partition changed after preflight",
    )
    output_path.write_bytes(original_output)
    verify_source_records_unchanged(synthetic_tasks, records)

    sc_task = populated["historical_scpdsi_stage"]
    manifest_path = Path(sc_task.manifest or "")
    original_manifest = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(original_manifest)
    manifest["output_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    sc_receipt = validate_receipt_envelope(
        sc_task, CONFIG_PATH, config, strict_source_identity=False
    )
    must_fail(
        lambda: validate_scpdsi_manifest(sc_task, sc_receipt, config),
        "output hash differs",
    )
    manifest_path.write_text(original_manifest, encoding="utf-8")

    hidden_receipt = receipt_path.with_suffix(receipt_path.suffix + ".hidden")
    receipt_path.rename(hidden_receipt)
    must_fail(
        lambda: _exact_discovered_files(synthetic_tasks, synthetic_source),
        "Exact receipt file registry differs",
    )
    hidden_receipt.rename(receipt_path)
    extra = synthetic_source / "unregistered.parquet"
    pd.DataFrame({"x": [1]}).to_parquet(extra, index=False)
    must_fail(
        lambda: _exact_discovered_files(synthetic_tasks, synthetic_source),
        "Exact partition file registry differs",
    )
    extra.unlink()

    must_fail(lambda: _require_no_absolute_strings({"path": "/tmp/forbidden"}), "absolute path")

    aggregate_root = root / "assembled"
    receipt = assemble_complete_panel(
        synthetic_tasks,
        CONFIG_PATH,
        config,
        records,
        aggregate_root,
        tolerance=1e-9,
    )
    assert receipt.is_file()
    aggregate = json.loads(receipt.read_text(encoding="utf-8"))
    assert aggregate["validated_source_tasks"] == 720
    assert len(aggregate["aggregate_tables"]) == 20
    assert len(aggregate["reconciliations"]) == 4
    assert all(item["historical_scpdsi_boundary"]["scpdsi_only_keys"] == 0 for item in aggregate["reconciliations"])
    assert aggregate["moisture_families_kept_separate"] is True
    assert aggregate["fit_performed"] is False
    _require_no_absolute_strings(aggregate)
    for table in aggregate["aggregate_tables"]:
        table_path = PROJECT / table["path"]
        assert table["sha256"] == sha256_file(table_path)
        assert table["rows"] == _parquet_rows(table_path)

print("continuous global-panel post-build assembly tests passed")
