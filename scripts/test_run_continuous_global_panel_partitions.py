#!/usr/bin/env python3
"""Fail-closed registry and argument tests for the continuous-panel builder."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pandas as pd
import xarray as xr


PROJECT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_continuous_global_panel_partitions import (  # noqa: E402
    FAMILIES,
    _build_command,
    _scope_check,
    _validate_partition_receipt,
    _write_partition_receipt,
    build_task,
    generate_tasks,
    load_config,
    select_tasks,
    task_status,
)


CONFIG_PATH = PROJECT / "config" / "continuous_global_panel_1982_2016_v1.toml"
config = load_config(CONFIG_PATH)
tasks = generate_tasks(CONFIG_PATH, config)

assert len(tasks) == 720
assert len({task.task_id for task in tasks}) == 720
assert [task.family for task in tasks[:5]] == FAMILIES
assert all(task.lat_start == 100 for task in tasks[:20])
assert tasks[0].task_id == "direct_season:mai:noirr:lat100_110:1990_2011"
assert tasks[-1].task_id == "historical_scpdsi_stage:soy:firr:lat350_360:1990_2011"

isolated_root = (
    PROJECT / "data" / "interim" / "continuous_global_panel_1982_2016_v1"
).resolve()
for task in tasks:
    assert Path(task.output).resolve().is_relative_to(isolated_root)
    assert "1981_1990" not in task.output
    assert "2011_2019" not in task.output

pilot = select_tasks(
    tasks,
    families=["direct_season"],
    crops=["mai"],
    irrigations=["noirr"],
    lat_starts=[100],
)
assert len(pilot) == 1
command = _build_command(
    pilot[0], CONFIG_PATH, config, Path("/tmp/not-created.parquet"), None
)
precip_index = command.index("--precip")
temperature_index = command.index("--temperature")
assert command[precip_index + 1 : temperature_index] == [
    str(
        PROJECT
        / config["raw_climate_root"]
        / filename
    )
    for filename in config["precipitation_files"]
]
assert command[temperature_index + 1 : command.index("--calendar")] == [
    str(
        PROJECT
        / config["raw_climate_root"]
        / filename
    )
    for filename in config["temperature_files"]
]

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    invalid_output = root / "invalid.parquet"
    invalid_output.write_text("not parquet", encoding="utf-8")
    invalid_task = replace(
        pilot[0],
        output=str(invalid_output),
        receipt=str(invalid_output) + ".receipt.json",
    )
    status, detail = task_status(invalid_task, CONFIG_PATH, config)
    assert status == "invalid"
    assert "source_receipt_missing" in detail
    try:
        build_task(invalid_task, CONFIG_PATH, config)
    except RuntimeError as error:
        assert "Refusing to overwrite" in str(error)
    else:
        raise AssertionError("Invalid existing targets must fail closed")
    assert invalid_output.read_text(encoding="utf-8") == "not parquet"

    # Resume identity must bind both the configured source stack and the
    # latitude-index slice, rather than accepting a schema-compatible file
    # copied from a neighboring band.
    calendar_path = next(
        PROJECT / item["path"]
        for item in config["calendars"]
        if (item["crop"], item["irrigation"]) == ("mai", "noirr")
    )
    with xr.open_dataset(
        calendar_path, engine="h5netcdf", decode_timedelta=False
    ) as calendar:
        latitude = float(calendar.lat.values[100])
        longitude = float(calendar.lon.values[0])
    scoped_output = root / "scoped.parquet"
    pd.DataFrame(
        {
            "harvest_year": list(range(1990, 2012)),
            "lat": [latitude] * 22,
            "lon": [longitude] * 22,
            "lon_360": [longitude % 360] * 22,
            "crop": ["mai"] * 22,
            "irrigation": ["noirr"] * 22,
            "wet_day_threshold_mm": [1.0] * 22,
        }
    ).to_parquet(scoped_output, index=False)
    scoped_task = replace(
        pilot[0], output=str(scoped_output), receipt=str(scoped_output) + ".receipt.json"
    )
    _scope_check(scoped_task, scoped_output, CONFIG_PATH, config)
    wrong_slice = replace(scoped_task, lat_start=110, lat_stop=120)
    try:
        _scope_check(wrong_slice, scoped_output, CONFIG_PATH, config)
    except ValueError as error:
        assert "latitude coordinates" in str(error)
    else:
        raise AssertionError("A neighboring latitude slice must fail scope validation")

    receipt_path = Path(scoped_task.receipt)
    _write_partition_receipt(
        receipt_path,
        scoped_task,
        CONFIG_PATH,
        config,
        scoped_output,
        {
            "schema_version": 1,
            "status": "command_completed",
            "started_utc": "2026-08-26T00:00:00+00:00",
            "finished_utc": "2026-08-26T00:00:01+00:00",
            "wall_seconds": 1.0,
            "peak_rss_bytes": 1,
            "returncode": 0,
        },
    )
    _validate_partition_receipt(
        scoped_task, CONFIG_PATH, config, scoped_output, receipt_path
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["identity"]["sources"]["calendar"]["sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    try:
        _validate_partition_receipt(
            scoped_task, CONFIG_PATH, config, scoped_output, receipt_path
        )
    except ValueError as error:
        assert "source/task identity" in str(error)
    else:
        raise AssertionError("A stale source identity must invalidate the receipt")

    measured = root / "measured.json"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "run_command_with_resource_receipt.py"),
            "--metrics-out",
            str(measured),
            "--",
            sys.executable,
            "-c",
            "value = bytearray(1024 * 1024); assert len(value) == 1048576",
        ],
        check=True,
    )
    metrics = json.loads(measured.read_text(encoding="utf-8"))
    assert metrics["status"] == "command_completed"
    assert metrics["wall_seconds"] >= 0
    assert metrics["peak_rss_bytes"] > 0

    missing_output = root / "missing.parquet"
    locked_task = replace(pilot[0], output=str(missing_output))
    Path(str(missing_output) + ".lock").write_text("test lock\n", encoding="utf-8")
    status, _ = task_status(locked_task, CONFIG_PATH, config)
    assert status == "locked"

    tampered = root / "tampered.toml"
    tampered.write_text(
        CONFIG_PATH.read_text(encoding="utf-8").replace(
            "scc_authorized = false", "scc_authorized = true"
        ),
        encoding="utf-8",
    )
    try:
        load_config(tampered)
    except ValueError as error:
        assert "scc_authorized" in str(error)
    else:
        raise AssertionError("SCC gate tampering must fail")

    redirected = root / "redirected.toml"
    redirected.write_text(
        CONFIG_PATH.read_text(encoding="utf-8").replace(
            'output_root = "data/interim/continuous_global_panel_1982_2016_v1"',
            'output_root = "data/raw"',
        ),
        encoding="utf-8",
    )
    try:
        load_config(redirected)
    except ValueError as error:
        assert "output_root" in str(error)
    else:
        raise AssertionError("The isolated output namespace must remain locked")

gate = subprocess.run(
    [
        str(PROJECT / ".venv/bin/python"),
        str(SCRIPTS / "run_continuous_global_panel_partitions.py"),
        "--config",
        str(CONFIG_PATH),
        "--execute",
        "--max-new-partitions",
        "0",
    ],
    text=True,
    capture_output=True,
    check=False,
)
assert gate.returncode != 0
assert "strictly positive" in gate.stderr

print("continuous global-panel orchestrator tests passed")
