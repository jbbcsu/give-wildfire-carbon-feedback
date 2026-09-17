#!/usr/bin/env python3
"""Serial 21-year global-tile source means after parity and stress pilots.

No climate response, yield effect, damage or SCC estimate is fitted.
"""
from __future__ import annotations

import json
import sys
import time

from audit_gfdl_2032_2039_maize_crossyear import digest, require
from audit_gfdl_contiguous_28yr_global import OUTPUT as SOURCE_AUDIT
from pilot_gfdl_contiguous_global_boundary import ROOT
from run_bounded_job import run


BASE = ROOT / "data/interim/gfdl_ssp126_global_centered_21yr_pilot_v2_20260917"
STATUS = "passed_centered_source_only_not_gmt_response_yield_damage_or_scc"


def wait_for_parity_pilot() -> None:
    tile = BASE / "lat100_110"
    resource = tile / "centered.resource.json"
    deadline = time.monotonic() + 10800
    while not resource.exists():
        require(time.monotonic() < deadline, "centered parity pilot did not finish")
        time.sleep(10)
    require(json.loads(resource.read_text())["status"] == "completed",
            "centered parity pilot failed; do not expand")
    receipt = json.loads((tile / "centered_audit_21yr.json").read_text())
    require(receipt["status"] == STATUS and receipt["lat_start"] == 100
            and receipt["prior_two_latitude_parity_rows"] ==
                {"season": 5488, "stages": 16464},
            "centered parity pilot gate failed")


def validate_existing(start: int) -> dict:
    tile = BASE / f"lat{start:03d}_{start + 10:03d}"
    season, stages = tile / "centered_season_21yr.parquet", tile / "centered_stages_21yr.parquet"
    receipt = tile / "centered_audit_21yr.json"
    resource = tile / "centered.resource.json"
    require(all(path.exists() for path in (season, stages, receipt, resource)),
            f"{start}: centered tile incomplete")
    info = json.loads(receipt.read_text())
    gate = json.loads(resource.read_text())
    require(info["status"] == STATUS and info["lat_start"] == start
            and info["center_years"] == list(range(2042, 2050))
            and info["source_audit_sha256"] == digest(SOURCE_AUDIT)
            and info["season_sha256"] == digest(season)
            and info["stages_sha256"] == digest(stages)
            and gate["status"] == "completed"
            and gate["sampled_peak_group_rss_bytes"] <= 512 * 2**20
            and gate["sampled_peak_new_disk_bytes"] <= 64 * 2**20,
            f"{start}: centered tile receipt/resource mismatch")
    return info


def build_one(start: int) -> dict:
    tile = BASE / f"lat{start:03d}_{start + 10:03d}"
    tile.mkdir(parents=True, exist_ok=True)
    season, stages = tile / "centered_season_21yr.parquet", tile / "centered_stages_21yr.parquet"
    receipt, resource, log = (tile / name for name in
                              ("centered_audit_21yr.json", "centered.resource.json", "centered.log"))
    if receipt.exists() or resource.exists() or log.exists() or season.exists() or stages.exists():
        return validate_existing(start)
    command = [sys.executable, str(ROOT / "scripts/pilot_gfdl_global_centered_21yr_tile.py"),
               "--lat-start", str(start), "--out", str(tile)]
    result = run(command, resource, log, max_mib=512, min_free_gib=130,
                 max_log_mib=2, interval=0.2,
                 write_paths=[season, stages, receipt], max_new_disk_mib=64)
    require(result["status"] == "completed", f"{start}: bounded centered tile failed")
    info = validate_existing(start)
    print(f"validated centered GFDL tile {start:03d}-{start + 10:03d}: "
          f"{info['season_rows']} source-only seasons", flush=True)
    return info


def main() -> None:
    wait_for_parity_pilot()
    require(json.loads(SOURCE_AUDIT.read_text())["status"] ==
            "passed_source_only_not_gmt_response_yield_damage_or_scc",
            "global annual source gate changed")
    # The 40--50 tile has the largest crop-calendar support and is the
    # memory stress test. If it fails, no other new tile is attempted.
    stress = build_one(40)
    require(stress["season_rows"] == 8 * 5630 and
            stress["stage_rows"] == 8 * 3 * 5630,
            "largest-calendar-cell stress tile support changed")
    starts = [100, 40] + [start for start in range(0, 360, 10)
                          if start not in (40, 100)]
    receipts = {start: validate_existing(start) if start in (40, 100)
                else build_one(start) for start in starts}
    require(len(receipts) == 36
            and sum(x["season_rows"] for x in receipts.values()) == 8 * 67420
            and sum(x["stage_rows"] for x in receipts.values()) == 8 * 202260,
            "global centered tile support incomplete")
    manifest = {
        "schema": "gfdl_ssp126_global_maize_centered_21yr_source_tiles_v1",
        "status": "complete_engineering_pending_independent_centered_validation",
        "esm": "gfdl-esm4", "scenario": "ssp126", "member": "r1i1p1f1",
        "crop": "mai", "irrigation": "noirr", "window_years": 21,
        "center_years": list(range(2042, 2050)),
        "source_audit_sha256": digest(SOURCE_AUDIT),
        "season_rows": 8 * 67420, "stage_rows": 8 * 202260,
        "tiles": [receipts[start] for start in sorted(receipts)],
    }
    destination = BASE / "global_manifest.json"
    require(not destination.exists(), "existing centered global manifest needs review")
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("All 36 GFDL global centered source tiles built; independent "
          "global audit pending; no GMT response, yield, damage or SCC", flush=True)


if __name__ == "__main__":
    main()
