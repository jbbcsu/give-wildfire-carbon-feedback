#!/usr/bin/env python3
"""Validate direct-reader LOCA2 sentinel parity with the established prepared route."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_historical_climate_sentinel import FEATURES


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direct", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("fresh output required")
    direct, reference = json.loads(args.direct.read_text()), json.loads(args.reference.read_text())
    if direct["status"] != "pass" or reference["status"] != "pass" or direct["support"]["years"] != reference["support"]["years"]:
        raise ValueError("sentinel status/support differs")
    direct_frame = pd.read_parquet(direct["output"]["path"])[["harvest_year", *FEATURES]]
    reference_frame = pd.read_parquet(reference["output"]["path"])[["harvest_year", *FEATURES]]
    if direct_frame.harvest_year.tolist() != reference_frame.harvest_year.tolist():
        raise ValueError("feature years differ")
    feature_error = float(np.max(np.abs(direct_frame[FEATURES].to_numpy(float) - reference_frame[FEATURES].to_numpy(float))))
    comparison_error = 0.0
    for feature in FEATURES:
        for key in ("model_mean", "observed_mean", "climatology_bias_model_minus_observed", "model_standard_deviation", "observed_standard_deviation", "standard_deviation_ratio", "quantile_rmse"):
            comparison_error = max(comparison_error, abs(direct["comparisons"][feature][key] - reference["comparisons"][feature][key]))
        for key in ("model_quantiles", "observed_quantiles", "quantile_differences_model_minus_observed"):
            comparison_error = max(comparison_error, float(np.max(np.abs(np.asarray(direct["comparisons"][feature][key]) - np.asarray(reference["comparisons"][feature][key])))))
    if feature_error > 1e-12 or comparison_error > 1e-12:
        raise ValueError("direct-reader parity tolerance failed")
    jobs = [json.loads(path.read_text()) for path in args.jobs]
    if any(job["status"] != "completed" or job["returncode"] != 0 or job["sampled_peak_group_rss_bytes"] > 512 * 1024**2 for job in jobs):
        raise ValueError("direct-reader resource gate failed")
    result = {
        "schema": "loca2_us_direct_v2_parity_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "direct": {"path": str(args.direct), "sha256": digest(args.direct)},
        "reference": {"path": str(args.reference), "sha256": digest(args.reference)},
        "jobs": [{"path": str(path), "sha256": digest(path), "sampled_peak_group_rss_bytes": job["sampled_peak_group_rss_bytes"]} for path, job in zip(args.jobs, jobs, strict=True)],
        "maximum_absolute_common_feature_difference": feature_error,
        "maximum_absolute_comparison_difference": comparison_error,
        "tolerance": 1e-12,
        "checks": {"support_identity": True, "common_feature_parity": True, "comparison_parity": True, "resource_gate": True},
    }
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
