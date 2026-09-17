#!/usr/bin/env python3
"""Wait for 36 centered tiles, then run one bounded independent audit."""
from __future__ import annotations

import json
import sys
import time

from audit_gfdl_2032_2039_maize_crossyear import require
from audit_gfdl_global_centered_21yr import OUT
from continue_gfdl_global_centered_tiles import BASE
from pilot_gfdl_contiguous_global_boundary import ROOT
from run_bounded_job import run


def main() -> None:
    manifest_path = BASE / "global_manifest.json"
    deadline = time.monotonic() + 21600
    while not manifest_path.exists():
        require(time.monotonic() < deadline, "centered tile queue did not finish")
        time.sleep(10)
    manifest = json.loads(manifest_path.read_text())
    require(manifest["status"] == "complete_engineering_pending_independent_centered_validation"
            and len(manifest["tiles"]) == 36,
            "centered global queue did not pass support gate")
    resource, log = OUT.with_suffix(".resource.json"), OUT.with_suffix(".log")
    require(not any(path.exists() for path in (OUT, resource, log)),
            "existing centered global audit requires review")
    result = run([sys.executable, str(ROOT / "scripts/audit_gfdl_global_centered_21yr.py")],
                 resource, log, max_mib=512, min_free_gib=130,
                 max_log_mib=2, interval=0.2,
                 write_paths=[OUT], max_new_disk_mib=64)
    require(result["status"] == "completed", "centered global audit failed")
    audited = json.loads(OUT.read_text())
    require(audited["status"] ==
            "passed_centered_source_only_not_gmt_response_yield_damage_or_scc"
            and audited["independent_annual_feature_reconstructions"] == 168,
            "centered global independent sample gate failed")
    print("GFDL global 21-year centered source features independently audited; "
          "no GMT response, yield, damage or SCC", flush=True)


if __name__ == "__main__":
    main()
