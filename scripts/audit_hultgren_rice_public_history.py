#!/usr/bin/env python3
"""Audit a local clone of the public Hultgren Git history for rice domain data."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PINNED_COMMIT = "3ccdffcd4e4ff6e55566ce76e2aac130ee86349a"
HISTORICAL_REGRESSION_OUTPUT_COMMIT = "3f0a4e3317d32b0e4f6441076c35511460fb1030"
RICE_COVERAGE_PATH = "Fig1/Crop_Coverage/data/crops/rice_gmfd_v1.dta"
RICE_READY_PATH = "Fig1/Local_Impacts/data/crop_data/rice_gmfd_v1_ready.dta"
RICE_READY_COMMIT = "dae5fe8d0d4a260328e4baa45b547368bd6790b3"
EXPECTED_REMOTE = "https://gitlab.com/ClimateImpactLab/cil-ag-replication-package.git"
REQUIRED_RESPONSE_COLUMNS = {
    "ln_yield", "gdd", "kdd", "tmin", "ln_gdppc", "irrigated_share",
    "lr_tmax_crop", "lr_prcp_crop",
}


def run(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("fresh output required")
    remote = run(args.repo, "remote", "get-url", "origin")
    pinned_type = run(args.repo, "cat-file", "-t", PINNED_COMMIT)
    commits = run(args.repo, "rev-list", "--all").splitlines()
    commit_count = len(commits)
    objects = run(args.repo, "rev-list", "--objects", "--all", "--missing=print").splitlines()
    paths = [line.split(" ", 1)[1] for line in objects if " " in line]
    history_paths = set()
    for commit in commits:
        history_paths.update(run(args.repo, "ls-tree", "-r", "--name-only", commit).splitlines())
    candidate_paths = sorted(
        path for path in set(paths) | history_paths
        if re.search(r"rice|regress|sample|support", path, re.IGNORECASE)
        and re.search(r"\.(dta|ster|csv|xls|xlsx|json|zip|parquet|rds|rdata)$", path, re.IGNORECASE)
    )
    pinned_data_paths = run(
        args.repo, "ls-tree", "-r", "--name-only", PINNED_COMMIT,
        "--", "Fig1/Crop_Coverage/data/crops", "Fig1/Local_Impacts/data/crop_estimates",
        "Outputs/Regressions", "Regressions",
    ).splitlines()
    historical_outputs = run(
        args.repo, "ls-tree", "-r", "--name-only", HISTORICAL_REGRESSION_OUTPUT_COMMIT,
        "--", "Outputs/Regressions",
    ).splitlines()

    coverage = args.repo / RICE_COVERAGE_PATH
    with pd.read_stata(coverage, iterator=True, convert_categoricals=False) as reader:
        first = reader.read(1)
        coverage_rows = int(reader._nobs)
        coverage_columns = list(first.columns)
    missing_required = sorted(REQUIRED_RESPONSE_COLUMNS - set(coverage_columns))
    ready = args.repo / RICE_READY_PATH
    with pd.read_stata(ready, iterator=True, convert_categoricals=False) as reader:
        ready_first = reader.read(1)
        ready_rows = int(reader._nobs)
        ready_columns = list(ready_first.columns)
    ready_missing = sorted(REQUIRED_RESPONSE_COLUMNS - set(ready_columns))
    estimate_or_domain_candidates = [
        path for path in candidate_paths
        if path not in (RICE_COVERAGE_PATH, RICE_READY_PATH)
        and not path.lower().endswith((".ster", ".xls", ".xlsx"))
    ]
    result = {
        "schema": "hultgren_rice_public_history_domain_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "historical_public_rice_regression_panel_recovered",
        "repository": {
            "remote": remote,
            "remote_matches_expected": remote == EXPECTED_REMOTE,
            "pinned_commit": PINNED_COMMIT,
            "pinned_object_type": pinned_type,
            "reachable_commit_count": commit_count,
            "history_object_names_enumerated": len(objects),
            "unique_history_paths_enumerated": len(history_paths),
        },
        "candidate_paths": candidate_paths,
        "pinned_regression_and_rice_data_paths": pinned_data_paths,
        "historical_regression_outputs_at_3f0a4e33": historical_outputs,
        "rice_coverage_file": {
            "path": RICE_COVERAGE_PATH,
            "git_blob_sha1": run(args.repo, "rev-parse", f"{HISTORICAL_REGRESSION_OUTPUT_COMMIT}:{RICE_COVERAGE_PATH}"),
            "bytes": coverage.stat().st_size,
            "sha256": digest(coverage),
            "rows": coverage_rows,
            "columns": coverage_columns,
            "required_response_or_domain_columns_absent": missing_required,
            "classification": "crop-coverage area panel, not the rice response estimation panel",
        },
        "rice_regression_panel": {
            "path": RICE_READY_PATH,
            "reachable_commit": RICE_READY_COMMIT,
            "git_blob_sha1": run(args.repo, "rev-parse", f"{RICE_READY_COMMIT}:{RICE_READY_PATH}"),
            "bytes": ready.stat().st_size,
            "sha256": digest(ready),
            "rows": ready_rows,
            "columns": ready_columns,
            "required_response_or_domain_columns_absent": ready_missing,
            "classification": "prepared historical rice response panel",
            "present_at_pinned_commit": RICE_READY_PATH in pinned_data_paths,
            "repository_license_located": False,
        },
        "remaining_negative_evidence": {
            "non_ster_rice_regression_or_domain_candidate_paths": estimate_or_domain_candidates,
            "precomputed_rice_source_domain_summary_found": False,
            "ster_can_recover_estimation_rows_or_quantiles": False,
            "impact_data_archive_is_future_impact_output_not_historical_regression_input": True,
        },
        "claim_gates": {
            "published_rice_coefficients_available": True,
            "published_rice_prepared_panel_available": True,
            "author_minmax_or_percentile_domain_recoverable": True,
            "response_damage_or_scc_validated": False,
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    if remote != EXPECTED_REMOTE or pinned_type != "commit" or not missing_required or ready_missing:
        raise ValueError("public-history identity or recovered-panel contract failed")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "rice_coverage_file": result["rice_coverage_file"]}, indent=2))


if __name__ == "__main__":
    main()
