#!/usr/bin/env python3
"""Run the pinned, aggregate-only FrEDI transport heat smoke test."""

from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from fredi_transport_heat_common import (
    compute_smoke,
    peak_rss_mib,
    read_json,
    sha256_file,
    write_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="config/fredi_transport_heat_v4_1_1.json",
        help="Path relative to project root",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = root / args.config
    config = read_json(config_path)
    rows, diagnostics = compute_smoke(root, config)
    output_path = root / config["smoke_test"]["output"]
    write_csv(output_path, rows)

    manifest_path = root / config["source_manifest"]
    manifest = read_json(manifest_path)
    alignment_path = root / config["alignment_audit"]
    alignment = read_json(alignment_path)
    if alignment.get("status") != "PASS" or Decimal(str(alignment["tolerance"])) > Decimal("1e-12"):
        raise RuntimeError("embedded-v4.1.1 source alignment audit is absent or not fail-closed")
    receipt = {
        "schema_version": "1.0.0",
        "run_date": date.today().isoformat(),
        "config": {"path": args.config, "sha256": sha256_file(config_path)},
        "source_manifest": {
            "path": config["source_manifest"],
            "sha256": sha256_file(manifest_path),
        },
        "alignment_audit": {
            "path": config["alignment_audit"],
            "sha256": sha256_file(alignment_path),
            "status": alignment["status"],
        },
        "upstream_commits": {
            name: values["commit"] for name, values in manifest["upstreams"].items()
        },
        "execution_code": {
            path: sha256_file(root / path)
            for path in (
                "scripts/fredi_transport_heat_common.py",
                "scripts/run_fredi_transport_heat_smoke.py",
                "scripts/validate_fredi_transport_heat_smoke.py",
            )
        },
        "output": {
            "path": config["smoke_test"]["output"],
            "sha256": sha256_file(output_path),
            "rows": len(rows),
        },
        "diagnostics": diagnostics,
        "formula": {
            "scaled_response": "linear interpolation between 1 C and 2 C at 1.5 C",
            "Roads": "scaled_response * 2010 road miles * 2020 variant-specific road miles-and-population adjustment",
            "Rail": "scaled_response * 2010 rail miles * 2020 national rail-growth factor",
            "national": "sum of 48 contiguous states and District of Columbia; no model averaging",
        },
        "component_gates": {
            gate["endpoint"]: gate["available_in_public_v4_1_1_runtime"]
            for gate in config["component_gates"]
        },
        "units": {
            "driver": config["scope"]["driver_unit"],
            "annual_impact": config["smoke_test"]["annual_impact_unit"],
        },
        "excluded": {
            "drivers": config["scope"]["forbidden_drivers"],
            "sectors": config["scope"]["forbidden_sectors"],
            "global_extrapolation": True,
        },
        "claim_status": config["claim_status"],
        "peak_rss_mib_internal": round(peak_rss_mib(), 3),
    }
    receipt_path = root / config["smoke_test"]["receipt"]
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": "PASS", **diagnostics, "peak_rss_mib": receipt["peak_rss_mib_internal"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
