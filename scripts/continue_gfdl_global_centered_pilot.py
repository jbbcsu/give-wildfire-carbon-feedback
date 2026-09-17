#!/usr/bin/env python3
"""After the independent 28-year audit, run one bounded centered tile pilot."""
from __future__ import annotations

import json
import sys
import time

from audit_gfdl_2032_2039_maize_crossyear import require
from audit_gfdl_contiguous_28yr_global import OUTPUT as SOURCE_AUDIT
from pilot_gfdl_contiguous_global_boundary import ROOT
from run_bounded_job import run


def main() -> None:
    source_resource = SOURCE_AUDIT.with_suffix(".resource.json")
    deadline = time.monotonic() + 10800
    while not source_resource.exists():
        require(time.monotonic() < deadline, "independent source audit did not finish")
        time.sleep(10)
    require(json.loads(source_resource.read_text())["status"] == "completed",
            "independent source audit failed; centered pilot not run")
    audit = json.loads(SOURCE_AUDIT.read_text())
    require(audit["status"] == "passed_source_only_not_gmt_response_yield_damage_or_scc"
            and audit["new_years_independent_raw_daily_samples"] == 252,
            "source audit gate did not pass")
    out = ROOT / "data/interim/gfdl_ssp126_global_centered_21yr_pilot_v2_20260917/lat100_110"
    season = out / "centered_season_21yr.parquet"
    stages = out / "centered_stages_21yr.parquet"
    receipt = out / "centered_audit_21yr.json"
    resource = out / "centered.resource.json"
    log = out / "centered.log"
    require(not any(path.exists() for path in (season, stages, receipt, resource, log)),
            "existing centered pilot requires review")
    out.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(ROOT / "scripts/pilot_gfdl_global_centered_21yr_tile.py"),
               "--lat-start", "100", "--out", str(out)]
    result = run(command, resource, log, max_mib=512, min_free_gib=130,
                 max_log_mib=2, interval=0.2,
                 write_paths=[season, stages, receipt], max_new_disk_mib=64)
    require(result["status"] == "completed", f"centered pilot failed: {result['status']}")
    result_receipt = json.loads(receipt.read_text())
    require(result_receipt["status"] == "passed_centered_source_only_not_gmt_response_yield_damage_or_scc"
            and result_receipt["prior_two_latitude_parity_rows"] ==
                {"season": 5488, "stages": 16464},
            "centered tile parity gate failed")
    print("GFDL global-tile 21-year centered source-feature pilot passed; "
          "no response, yield, damage or SCC claim", flush=True)


if __name__ == "__main__":
    main()
