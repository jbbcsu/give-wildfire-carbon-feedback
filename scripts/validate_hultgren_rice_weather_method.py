#!/usr/bin/env python3
"""Validate source identity and arithmetic for the rice weather method."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads(args.config.read_text())
    raw = root / "data/raw/hultgren_response/3ccdffcd4e4ff6e55566ce76e2aac130ee86349a"
    checks = {
        "methods_pdf_hash": digest(root / config["source_methods_pdf"])
        == config["source_methods_pdf_sha256"],
        "crop_configuration_hash": digest(raw / "set_crop_variables.do")
        == config["set_crop_variables_sha256"],
        "climate_collapse_hash": digest(raw / "collapse_clim.do")
        == config["collapse_clim_sha256"],
        "rice_gdd_base": config["gdd_base_c"] == 14.0,
        "rice_kdd_threshold": config["kdd_threshold_c"] == 30.0,
        "rice_phase_lengths": config["precipitation_phase_month_counts"] == [2, 3, 7],
        "rice_maximum_season": config["maximum_crop_season_months"] == 12,
        "quadratic_precipitation": config["precipitation_polynomial_order"] == 2,
        "future_gate_closed": config["future_weather_ready"] is False,
        "damage_gate_closed": config["damage_ready"] is False,
        "scc_gate_closed": config["scc_ready"] is False,
    }
    subprocess.run(
        [sys.executable, str(root / "scripts/test_hultgren_rice_weather.py")],
        check=True,
        cwd=root,
        stdout=subprocess.PIPE,
        text=True,
    )
    checks["arithmetic_tests"] = True
    subprocess.run(
        [sys.executable, str(root / "scripts/test_hultgren_rice_response.py")],
        check=True,
        cwd=root,
        stdout=subprocess.PIPE,
        text=True,
    )
    checks["response_algebra_tests"] = True
    result = {
        "schema": "hultgren_rice_weather_method_validation/v1",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "passed_checks": sum(checks.values()),
        "total_checks": len(checks),
        "definitions": {
            "gdd": "Snyder single-sine degree days between 14 and 30 C",
            "kdd": "Snyder single-sine degree days above 30 C",
            "precipitation_phases": "months 1-2, 3-5, and 6 through harvest",
            "precipitation_quadratic": "sum of squared monthly totals within each phase",
            "tmin": config["tmin_definition"],
        },
        "claim_gates": {
            "primitive_weather_method": True,
            "future_rice_weather": False,
            "rice_yield_projection": False,
            "rice_damage": False,
            "rice_scc": False,
        },
        "implementation_hashes": {
            "weather_module_sha256": digest(root / "src/hultgren_rice_weather.py"),
            "response_module_sha256": digest(root / "src/hultgren_rice_response.py"),
            "test_sha256": digest(root / "scripts/test_hultgren_rice_weather.py"),
            "response_test_sha256": digest(root / "scripts/test_hultgren_rice_response.py"),
            "validator_sha256": digest(Path(__file__)),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if result["status"] != "passed":
        raise SystemExit("rice weather-method validation failed")


if __name__ == "__main__":
    main()
