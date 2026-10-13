#!/usr/bin/env python3
"""Independent arithmetic, hash, and resource validation for national PDSI output."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--resource", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("fresh validation output required")
    result = json.loads(args.result.read_text())
    resource = json.loads(args.resource.read_text())
    if result["schema"] != "us_national_corn_pdsi_spatial/v1":
        raise ValueError("result schema differs")
    for record in result["sources"].values():
        path = Path(record["path"])
        if not path.is_file() or digest(path) != record["sha256"]:
            raise ValueError(f"source hash differs: {path}")
    implementation = result["implementation"]
    if digest(Path(implementation["path"])) != implementation["sha256"]:
        raise ValueError("implementation hash differs")
    contrasts = result["contrasts"]
    d1 = contrasts["pdsi_minus1_vs_0"]["estimate_log_yield"]
    d2 = contrasts["pdsi_minus2_vs_0"]["estimate_log_yield"]
    d4 = contrasts["pdsi_minus4_vs_0"]["estimate_log_yield"]
    b2 = (d2 - 2 * d1) / 2
    b1 = b2 - d1
    reconstructed = -4 * b1 + 16 * b2
    if abs(reconstructed - d4) > 1e-14:
        raise ValueError("quadratic contrasts do not reconcile")
    for item in contrasts.values():
        estimate = item["estimate_log_yield"]
        for name, se in item["standard_errors_log_yield"].items():
            expected = [100 * np.expm1(estimate - 1.96 * se), 100 * np.expm1(estimate + 1.96 * se)]
            if not np.allclose(expected, item["normal_95_intervals_percent_yield"][name], rtol=0, atol=1e-12):
                raise ValueError("reported interval does not reconcile")
    if resource["status"] != "completed" or resource["returncode"] != 0 or resource["sampled_peak_group_rss_bytes"] > 512 * 1024**2:
        raise ValueError("bounded resource gate failed")
    validation = {
        "schema": "us_national_corn_pdsi_spatial_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "result": {"path": str(args.result), "sha256": digest(args.result)},
        "resource": {"path": str(args.resource), "sha256": digest(args.resource), "sampled_peak_group_rss_bytes": resource["sampled_peak_group_rss_bytes"]},
        "checks": {"source_hashes": True, "implementation_hash": True, "quadratic_contrast_reconciliation": True, "interval_reconciliation": True, "resource_gate": True},
    }
    args.out.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
