#!/usr/bin/env python3
"""Run the admitted ElecTD-only deterministic FrEDI heat sentinel."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fredi_electricity_heat_common import (
    compute_sentinel,
    peak_rss_mib,
    read_json,
    sha256_file,
    write_output,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config_path = root / "config/fredi_electricity_heat_v4_1_1.json"
    config = read_json(config_path)
    manifest_path = root / config["source_manifest"]
    alignment_path = root / config["alignment_audit"]
    records, diagnostics = compute_sentinel(root, config)
    output_path = root / config["sentinel"]["output"]
    write_output(output_path, records)
    code_paths = (
        "scripts/fredi_electricity_heat_common.py",
        "scripts/run_fredi_electricity_td_heat_sentinel.py",
        "scripts/validate_fredi_electricity_td_heat_sentinel.py",
    )
    receipt = {
        "schema_version": "1.0.0",
        "run_date": date.today().isoformat(),
        "config": {"path": str(config_path.relative_to(root)), "sha256": sha256_file(config_path)},
        "source_manifest": {"path": config["source_manifest"], "sha256": sha256_file(manifest_path)},
        "alignment_audit": {"path": config["alignment_audit"], "sha256": sha256_file(alignment_path)},
        "execution_code": {path: sha256_file(root / path) for path in code_paths},
        "output": {
            "path": config["sentinel"]["output"],
            "sha256": sha256_file(output_path),
            "rows": len(records),
        },
        "diagnostics": diagnostics,
        "formula": "state ElecTD response linearly interpolated at 1.5 C, multiplied by exact 2020 state elecTD_growthFactor, then summed across 48 contiguous states plus DC; no GCM averaging",
        "units": {
            "driver": config["scope"]["driver_unit"],
            "annual_impact": config["sentinel"]["annual_impact_unit"],
        },
        "endpoint_authorization": {
            gate["endpoint"]: gate["authorized_for_output"]
            for gate in config["endpoint_gates"]
        },
        "excluded": {
            "ElecSD": "bundled generation/capacity plus excluded heating/cooling demand",
            "drivers": config["scope"]["forbidden_drivers"],
            "sectors": config["scope"]["forbidden_sectors"],
        },
        "claim_status": config["claim_status"],
        "peak_rss_mib_internal": round(peak_rss_mib(), 3),
    }
    receipt_path = root / config["sentinel"]["receipt"]
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("w", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": "PASS", **diagnostics, "peak_rss_mib": receipt["peak_rss_mib_internal"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
