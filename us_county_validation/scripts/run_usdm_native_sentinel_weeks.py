#!/usr/bin/env python3
"""Run each native-resolution sentinel in an isolated bounded process."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path


HERE = Path(__file__).resolve().parent
WORKER = HERE / "compute_usdm_native_sentinel_week.py"
MEASURE = HERE.parent.parent / "scripts/run_command_with_resource_receipt.py"


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentinel-config", type=Path, required=True)
    parser.add_argument("--cdl-config", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--cdl-archive", type=Path, required=True)
    parser.add_argument("--counties", type=Path, required=True)
    parser.add_argument("--shape-dir", type=Path, required=True)
    parser.add_argument("--coarse-grid", type=Path, required=True)
    parser.add_argument("--fine-grid", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.sentinel_config.read_text(encoding="utf-8"))
    selection = json.loads(arguments.selection.read_text(encoding="utf-8"))
    ceiling = int(contract["resource_ceiling_bytes"])
    arguments.out_dir.mkdir(parents=True, exist_ok=True)
    receipts = []
    for county in selection["sentinels"]:
        geoid = str(county["county_geoid"])
        for week in county["selected_weeks"]:
            map_date = str(week["map_date"])
            stem = f"{geoid}_{map_date.replace('-', '')}"
            result_path = arguments.out_dir / f"{stem}.json"
            resource_path = arguments.out_dir / f"{stem}.resource.json"
            reusable = result_path.is_file() and resource_path.is_file()
            if not reusable:
                command = [
                    sys.executable, str(MEASURE), "--metrics-out", str(resource_path), "--",
                    sys.executable, "-B", str(WORKER),
                    "--sentinel-config", str(arguments.sentinel_config),
                    "--cdl-config", str(arguments.cdl_config),
                    "--selection", str(arguments.selection),
                    "--county-geoid", geoid, "--map-date", map_date,
                    "--cdl-archive", str(arguments.cdl_archive),
                    "--counties", str(arguments.counties),
                    "--shape-dir", str(arguments.shape_dir),
                    "--coarse-grid", str(arguments.coarse_grid),
                    "--fine-grid", str(arguments.fine_grid),
                    "--out", str(result_path),
                ]
                subprocess.run(command, check=True)
            resource = json.loads(resource_path.read_text(encoding="utf-8"))
            if resource["status"] != "command_completed" or int(resource["returncode"]) != 0:
                raise ValueError(f"sentinel worker failed for {stem}")
            if int(resource["peak_rss_bytes"]) > ceiling:
                raise MemoryError(f"sentinel worker exceeded memory ceiling for {stem}")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result["county_geoid"] != geoid or result["map_date"] != map_date:
                raise ValueError(f"sentinel result identity differs for {stem}")
            receipts.append({
                "county_geoid": geoid, "map_date": map_date,
                "result": str(result_path), "result_sha512": sha512_file(result_path),
                "resource": str(resource_path), "peak_rss_bytes": int(resource["peak_rss_bytes"]),
                "wall_seconds": float(resource["wall_seconds"]),
            })
            print(f"{'reused' if reusable else 'completed'} {stem} peak={resource['peak_rss_bytes']}", flush=True)
    audit = {
        "schema": "usdm_native_30m_sentinel_run_v1",
        "selection": {"path": str(arguments.selection), "sha512": sha512_file(arguments.selection)},
        "sentinel_weeks": len(receipts),
        "maximum_peak_rss_bytes": max(row["peak_rss_bytes"] for row in receipts),
        "resource_ceiling_bytes": ceiling,
        "runs": receipts,
        "claim_boundary": "outcome-blind spatial measurement audit only; not causal, damage, global-transfer, or SCC evidence",
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"sentinel_weeks": len(receipts), "maximum_peak_rss_bytes": audit["maximum_peak_rss_bytes"]}, indent=2))


if __name__ == "__main__":
    main()
