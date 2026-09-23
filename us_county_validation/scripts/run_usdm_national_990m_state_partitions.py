#!/usr/bin/env python3
"""Build and validate national 990 m USDM exposure in state partitions."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

from build_cdl_2008_agricultural_grid import CONTIGUOUS_STATE_FIPS


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MEASURE = ROOT / "scripts/run_command_with_resource_receipt.py"
BUILD_GRID = HERE / "build_cdl_2008_agricultural_grid.py"
VALIDATE_GRID = HERE / "validate_cdl_agricultural_grid.py"
PREPARE = HERE / "prepare_usdm_agricultural_overlay_grid.py"
RUN_EXPOSURE = HERE / "run_usdm_agricultural_exposure_batches.py"
VALIDATE_EXPOSURE = HERE / "validate_usdm_agricultural_exposure.py"


def run(command: list[str], log: Path) -> None:
    completed = subprocess.run(command, text=True, capture_output=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"command failed; tail of {log}:\n{(completed.stdout + completed.stderr)[-5000:]}")


def successful_resource(path: Path, ceiling: int) -> bool:
    if not path.is_file():
        return False
    receipt = json.loads(path.read_text(encoding="utf-8"))
    return (
        receipt.get("status") == "command_completed"
        and int(receipt.get("returncode", 1)) == 0
        and int(receipt.get("peak_rss_bytes", ceiling + 1)) <= ceiling
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-config", type=Path, required=True)
    parser.add_argument("--shape-config", type=Path, required=True)
    parser.add_argument("--cdl-archive", type=Path, required=True)
    parser.add_argument("--counties", type=Path, required=True)
    parser.add_argument("--county-inventory", type=Path, required=True)
    parser.add_argument("--shape-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--state-fips", action="append")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--memory-cap-bytes", type=int, default=640 * 1024 * 1024)
    parser.add_argument("--free-disk-floor-bytes", type=int, default=100 * 1024**3)
    arguments = parser.parse_args()
    with arguments.county_inventory.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        eligible_states = {
            str(row["county_geoid"]).zfill(5)[:2]
            for row in reader
            if str(row.get("classifier_eligible", "")).strip().lower() in {"true", "1", "yes"}
            and str(row["county_geoid"]).zfill(5)[:2] in CONTIGUOUS_STATE_FIPS
        }
    states = sorted(set(arguments.state_fips or eligible_states))
    if not set(states) <= CONTIGUOUS_STATE_FIPS:
        raise ValueError("requested state lies outside the continental contract")
    if not set(states) <= eligible_states:
        raise ValueError("requested state has no eligible continental classifier counties")
    arguments.out_dir.mkdir(parents=True, exist_ok=True)
    completed_states = []
    for number, state in enumerate(states, 1):
        free = shutil.disk_usage(arguments.out_dir).free
        if free < arguments.free_disk_floor_bytes:
            raise OSError(f"free disk {free} is below frozen floor {arguments.free_disk_floor_bytes}")
        state_dir = arguments.out_dir / f"state_{state}"
        state_dir.mkdir(parents=True, exist_ok=True)
        print(f"state {state} ({number}/{len(states)}) start free={free}", flush=True)
        grid = state_dir / "grid_990m.parquet"
        grid_audit = state_dir / "grid_990m.audit.json"
        grid_resource = state_dir / "grid_990m.resource.json"
        grid_validation = state_dir / "grid_990m.validation.json"
        if not (grid.is_file() and grid_audit.is_file() and successful_resource(grid_resource, arguments.memory_cap_bytes)):
            run([
                sys.executable, str(MEASURE), "--metrics-out", str(grid_resource), "--",
                sys.executable, "-B", str(BUILD_GRID),
                "--config", str(arguments.grid_config), "--cdl-archive", str(arguments.cdl_archive),
                "--counties", str(arguments.counties), "--county-inventory", str(arguments.county_inventory),
                "--state-fips", state, "--out", str(grid), "--audit-out", str(grid_audit),
            ], state_dir / "grid_990m.log")
        run([
            sys.executable, "-B", str(VALIDATE_GRID), "--grid", str(grid),
            "--audit", str(grid_audit), "--config", str(arguments.grid_config),
            "--resource", str(grid_resource), "--memory-cap-bytes", str(arguments.memory_cap_bytes),
            "--out", str(grid_validation),
        ], state_dir / "grid_990m.validation.log")

        prepared = state_dir / "overlay_990m.npz"
        prepared_audit = state_dir / "overlay_990m.audit.json"
        prepared_resource = state_dir / "overlay_990m.resource.json"
        if not (prepared.is_file() and prepared_audit.is_file() and successful_resource(prepared_resource, arguments.memory_cap_bytes)):
            run([
                sys.executable, str(MEASURE), "--metrics-out", str(prepared_resource), "--",
                sys.executable, "-B", str(PREPARE), "--grid", str(grid),
                "--out", str(prepared), "--audit-out", str(prepared_audit),
            ], state_dir / "overlay_990m.log")

        exposure = state_dir / "exposure_990m.parquet"
        exposure_audit = state_dir / "exposure_990m.audit.json"
        exposure_resource = state_dir / "exposure_990m.resource.json"
        exposure_validation = state_dir / "exposure_990m.validation.json"
        if not (exposure.is_file() and exposure_audit.is_file() and successful_resource(exposure_resource, arguments.memory_cap_bytes)):
            run([
                sys.executable, "-B", str(RUN_EXPOSURE),
                "--config", str(arguments.shape_config), "--prepared-grid", str(prepared),
                "--prepared-grid-audit", str(prepared_audit), "--shape-dir", str(arguments.shape_dir),
                "--batch-dir", str(state_dir / "map_batches"), "--batch-size", str(arguments.batch_size),
                "--memory-cap-bytes", str(arguments.memory_cap_bytes), "--out", str(exposure),
                "--audit-out", str(exposure_audit), "--resource-out", str(exposure_resource),
            ], state_dir / "exposure_990m.log")
        run([
            sys.executable, "-B", str(VALIDATE_EXPOSURE), "--exposure", str(exposure),
            "--audit", str(exposure_audit), "--resource", str(exposure_resource),
            "--memory-cap-bytes", str(arguments.memory_cap_bytes), "--out", str(exposure_validation),
        ], state_dir / "exposure_990m.validation.log")
        grid_check = json.loads(grid_validation.read_text(encoding="utf-8"))
        exposure_check = json.loads(exposure_validation.read_text(encoding="utf-8"))
        if not grid_check.get("passed") or not exposure_check.get("passed"):
            raise ValueError(f"state {state} independent validation failed")
        completed_states.append({
            "state_fips": state, "counties": int(grid_check["counties"]),
            "grid_rows": int(grid_check["rows"]), "exposure_rows": int(exposure_check["rows"]),
            "grid_peak_rss_bytes": int(grid_check["resource"]["peak_rss_bytes"]),
            "exposure_peak_rss_bytes": int(exposure_check["resource"]["peak_rss_bytes"]),
        })
        print(f"state {state} complete counties={grid_check['counties']} grid_rows={grid_check['rows']}", flush=True)
    summary = {
        "schema": "usdm_national_990m_state_partition_run_v1",
        "states": completed_states,
        "state_count": len(completed_states),
        "counties": sum(row["counties"] for row in completed_states),
        "grid_rows": sum(row["grid_rows"] for row in completed_states),
        "exposure_rows": sum(row["exposure_rows"] for row in completed_states),
        "maximum_grid_peak_rss_bytes": max(row["grid_peak_rss_bytes"] for row in completed_states),
        "maximum_exposure_peak_rss_bytes": max(row["exposure_peak_rss_bytes"] for row in completed_states),
        "claim_boundary": "national 990 m historical exposure reconstruction only; not causal, future, damage, global-transfer, or SCC evidence",
    }
    (arguments.out_dir / "STATE_PARTITION_RUN.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
