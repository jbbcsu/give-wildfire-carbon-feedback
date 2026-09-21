#!/usr/bin/env python3
"""Complete, audit and summarize the registered five-ESM late weather matrix."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from audit_gfdl_2032_2039_maize_crossyear import require
from run_bounded_job import run
from run_gfdl_single_year_global_tile_pilot import ROOT


INTERIM = ROOT / "data/interim"
CASES = (
    ("gfdl-esm4", "ssp370"), ("gfdl-esm4", "ssp585"),
    ("mri-esm2-0", "ssp126"), ("mri-esm2-0", "ssp370"),
)
PREFIX = {"gfdl-esm4": "gfdl", "mri-esm2-0": "mri"}


def completed_or_run(label: str, command: list[str], output: Path,
                     expected_status: str) -> None:
    receipt = INTERIM / f"{label}.resource.json"
    log = INTERIM / f"{label}.log"
    if not output.exists():
        require(not receipt.exists() and not log.exists(),
                f"preserved partial attempt requires review: {label}")
        result = run(command, receipt, log, max_mib=512, min_free_gib=130,
                     max_log_mib=2, write_paths=[output], max_new_disk_mib=64)
        require(result["status"] == "completed",
                f"bounded step failed: {label} {result['status']}")
    require(receipt.is_file() and json.loads(receipt.read_text())["status"] == "completed",
            f"bounded resource receipt failed: {label}")
    require(json.loads(output.read_text())["status"] == expected_status,
            f"result status failed: {label}")
    print(f"validated {label}: sampled RSS "
          f"{json.loads(receipt.read_text())['sampled_peak_group_rss_bytes']} bytes", flush=True)


def child(command: list[str], label: str) -> None:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode:
        print(result.stdout[-8000:], flush=True)
        print(result.stderr[-8000:], file=sys.stderr, flush=True)
        raise RuntimeError(f"bounded child stopped: {label}")
    print(result.stdout[-4000:], flush=True)


def main() -> None:
    for esm, scenario in CASES:
        child([sys.executable, str(ROOT / "scripts/continue_ukesm_ssp126_2093_2099_queue.py"),
               "--esm", esm, "--scenario", scenario, "--window", "late"],
              f"{esm} {scenario} annual queue")
        label = f"{esm}_{scenario}_2092_2099_crossyear_qc_20260921"
        output = INTERIM / f"{esm}_{scenario}_2092_2099_mai_noirr_crossyear_qc_20260921.json"
        completed_or_run(
            label,
            [sys.executable, str(ROOT / "scripts/audit_ukesm_ssp126_2092_2099_crossyear.py"),
             "--esm", esm, "--scenario", scenario, "--window", "late",
             "--output", str(output)],
            output, "passed_source_only_not_gmt_response_yield_damage_or_scc",
        )
    for esm in ("gfdl-esm4", "mri-esm2-0"):
        prefix = PREFIX[esm]
        completed_or_run(
            f"{prefix}_late_window_weather_diagnostic_20260921",
            [sys.executable, str(ROOT / "scripts/diagnose_ipsl_late_weather_window.py"), "--esm", esm,
             "--output", str(INTERIM / f"{prefix}_late_window_weather_diagnostic_20260921.json")],
            INTERIM / f"{prefix}_late_window_weather_diagnostic_20260921.json",
            "descriptive_source_only_not_forced_response_yield_damage_or_scc",
        )
        completed_or_run(
            f"{prefix}_late_window_weather_arithmetic_audit_20260921",
            [sys.executable, str(ROOT / "scripts/audit_ipsl_late_weather_arithmetic.py"), "--esm", esm,
             "--source", str(INTERIM / f"{prefix}_late_window_weather_diagnostic_20260921.json"),
             "--output", str(INTERIM / f"{prefix}_late_window_weather_arithmetic_audit_20260921.json")],
            INTERIM / f"{prefix}_late_window_weather_arithmetic_audit_20260921.json",
            "passed_descriptive_weather_only_not_forced_response_yield_damage_or_scc",
        )
    result_dir = INTERIM / "five_esm_maize_area_weather_20260921"
    result = result_dir / "result.json"
    audit = result_dir / "validation.json"
    completed_or_run(
        "five_esm_maize_area_weather_20260921",
        [sys.executable, str(ROOT / "scripts/compare_five_esm_maize_area_weather.py"), "--out", str(result)],
        result, "five_esm_fixed_maize_area_weather_only_not_forced_response_or_scc",
    )
    completed_or_run(
        "five_esm_maize_area_weather_audit_20260921",
        [sys.executable, str(ROOT / "scripts/audit_five_esm_maize_area_weather.py"),
         "--result", str(result), "--out", str(audit)],
        audit, "independent_five_esm_fixed_area_weather_ledger_and_source_sample_passed",
    )
    require(json.loads(audit.read_text())["bound_annual_source_manifests"] == 120,
            "five-ESM audit did not bind all annual panels")
    print("five-ESM late weather matrix complete and independently audited", flush=True)


if __name__ == "__main__":
    main()
