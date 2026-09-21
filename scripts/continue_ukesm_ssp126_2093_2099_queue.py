#!/usr/bin/env python3
"""Serial, resumable registered ESM single-year mid/late weather panels."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

from audit_gfdl_2032_2039_maize_crossyear import digest, require
from continue_isimip3b_global_maize_tiles import destination
from run_bounded_job import run
from run_gfdl_single_year_global_tile_pilot import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", choices=("ukesm1-0-ll", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "gfdl-esm4"), default="ukesm1-0-ll")
    parser.add_argument("--window", choices=("mid", "late"), default="late")
    parser.add_argument("--scenario", choices=("ssp126", "ssp370", "ssp585"), default="ssp126")
    parser.add_argument("--include-anchor", action="store_true",
                        help="Include the 2042 or 2092 preexisting anchor in validation")
    parser.add_argument("--through-year", type=int)
    args = parser.parse_args()
    esm = args.esm
    require(esm == "ukesm1-0-ll" or args.window == "late" or
            (esm == "mri-esm2-0" and args.window == "mid" and args.scenario == "ssp585") or
            (esm == "gfdl-esm4" and args.window == "mid" and args.scenario == "ssp126"),
            "additional ESM/window combination is not registered")
    require(args.window == "late" or esm != "mri-esm2-0" or args.scenario == "ssp585",
            "MRI mid-century continuation registered only for SSP5-8.5")
    require(args.window == "late" or esm != "gfdl-esm4" or args.scenario == "ssp126",
            "GFDL mid-century continuation registered only for SSP1-2.6")
    first, last = (2043, 2049) if args.window == "mid" else (2093, 2099)
    if args.include_anchor:
        first -= 1
    through = args.through_year if args.through_year is not None else last
    require(first <= through <= last, "through-year outside registered series")
    scenario = args.scenario
    for year in range(first, through + 1):
        directory = destination(esm, scenario, year)
        command = [sys.executable, str(ROOT / "scripts/continue_isimip3b_global_maize_tiles.py"),
                   "--esm", esm, "--scenario", scenario, "--year", str(year)]
        controller = subprocess.run(command, capture_output=True, text=True, check=False)
        if controller.returncode:
            print(controller.stdout[-8000:], flush=True)
            print(controller.stderr[-8000:], file=sys.stderr, flush=True)
            raise RuntimeError(f"full-grid controller stopped: {esm} {scenario} {year}")
        require("global source-only tiles complete:" in controller.stdout,
                f"controller completion marker missing: {year}")
        manifest_path = directory / "global_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        require((manifest["esm"], manifest["scenario"], manifest["harvest_year"], len(manifest["tiles"]))
                == (esm, scenario, year, 36),
                f"global manifest identity failed: {year}")
        output = directory / "independent_global_validation.json"
        receipt = directory / "independent_validation.resource.json"
        log = directory / "independent_validation.log"
        if not output.exists():
            require(not receipt.exists() and not log.exists(),
                    f"partial independent validation requires review: {year}")
            result = run(
                [sys.executable, str(ROOT / "scripts/validate_isimip3b_global_maize_tiles.py"),
                 "--esm", esm, "--scenario", scenario, "--year", str(year)],
                receipt, log, max_mib=512, min_free_gib=130, max_log_mib=2,
                interval=0.2, write_paths=[output], max_new_disk_mib=64,
            )
            require(result["status"] == "completed", f"independent validator failed: {year} {result['status']}")
        require(receipt.exists() and json.loads(receipt.read_text())["status"] == "completed",
                f"independent resource receipt failed: {year}")
        payload = json.loads(output.read_text())
        expected_status = ("passed_one_year_second_esm_source_features_only_not_response_damage_or_scc"
                           if esm == "ukesm1-0-ll" else
                           "passed_one_year_source_features_only_not_response_damage_or_scc")
        require(payload["status"] == expected_status
                and (payload["esm"], payload["scenario"], payload["harvest_year"])
                == (esm, scenario, year)
                and payload["fixed_raw_daily_sample_count"] == 21
                and payload["global_manifest_sha256"] == digest(manifest_path),
                f"independent validation incomplete: {year}")
        print(f"validated {esm} {scenario} {year}: {payload['season_rows']} cells; "
              f"peak {manifest['peak_sampled_worker_rss_bytes']} bytes", flush=True)


if __name__ == "__main__":
    main()
