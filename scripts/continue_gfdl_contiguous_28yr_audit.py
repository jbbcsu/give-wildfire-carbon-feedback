#!/usr/bin/env python3
"""Wait for the serial year queue, then run one bounded independent audit."""
from __future__ import annotations

import json
import sys
import time

from audit_gfdl_2032_2039_maize_crossyear import require
from audit_gfdl_contiguous_28yr_global import OUTPUT
from continue_gfdl_contiguous_global_missing_years import YEAR_SOURCES
from pilot_gfdl_contiguous_global_boundary import OUT, ROOT
from run_bounded_job import run


def main() -> None:
    deadline = time.monotonic() + 10800
    while True:
        paths = [OUT / str(year) / "global_manifest.json" for year in YEAR_SOURCES]
        if all(path.exists() for path in paths):
            break
        require(time.monotonic() < deadline, "missing-year queue did not complete before audit timeout")
        time.sleep(10)
    for year, path in zip(YEAR_SOURCES, paths):
        report = json.loads(path.read_text())
        require(report["status"] == "passed_source_feature_year_only_not_response_damage_or_scc"
                and report["harvest_year"] == year,
                f"year {year} manifest failed before audit")
    output = OUTPUT
    resource = output.with_suffix(".resource.json")
    log = output.with_suffix(".log")
    require(not output.exists() and not resource.exists() and not log.exists(),
            "existing/partial contiguous audit requires review")
    result = run([sys.executable, str(ROOT / "scripts/audit_gfdl_contiguous_28yr_global.py")],
                 resource, log, max_mib=512, min_free_gib=130,
                 max_log_mib=2, interval=0.2,
                 write_paths=[output], max_new_disk_mib=64)
    require(result["status"] == "completed", f"28-year audit failed: {result['status']}")
    audit = json.loads(output.read_text())
    require(audit["status"] == "passed_source_only_not_gmt_response_yield_damage_or_scc"
            and audit["years"] == list(range(2032, 2060))
            and audit["new_years_independent_raw_daily_samples"] == 252,
            "28-year audit did not meet prespecified gates")
    print("GFDL contiguous 28-year global source audit passed; "
          "no response, yield, damage or SCC claim", flush=True)


if __name__ == "__main__":
    main()
