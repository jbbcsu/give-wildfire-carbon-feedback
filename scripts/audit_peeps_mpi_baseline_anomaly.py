#!/usr/bin/env python3
"""Independent scalar audit of anchored published monthly rainfall."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/interim/peeps_mpi_source_reconstruction_20260917/source_vs_published_crop_center_mm.npz"
SOURCE_SHA = "f1556e24ad9e843f064c095474b0d89954ed621d91cc51f006e63b65cb87b08d"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(saved, arrays):
    weights = arrays["hectares"]
    baseline = arrays["direct_ensemble_mean_mm_2015"]
    target = arrays["direct_ensemble_mean_mm_2100"]
    old = arrays["published_mm_2015"]
    new = arrays["published_mm_2100"]
    n = len(weights)
    if n != 30821 or any(x.shape != (12, n) for x in (baseline, target, old, new)):
        raise ValueError("source geometry changed")
    sum_weights = math.fsum(float(w) for w in weights)
    negative_count = 0
    negative_area = 0.0
    valid_area = 0.0
    minimum = math.inf
    annual_anchor_bias = []
    annual_naive_bias = []
    annual_anchor_squared = []
    annual_naive_squared = []
    monthly_anchor_squared = []
    monthly_naive_squared = []
    anchor_tv = []
    naive_tv = []
    for i in range(n):
        weight = float(weights[i])
        b = [float(baseline[m, i]) for m in range(12)]
        t = [float(target[m, i]) for m in range(12)]
        a = [b[m] + float(new[m, i]) - float(old[m, i]) for m in range(12)]
        count = sum(x < 0 for x in a)
        negative_count += count
        negative_area += weight if count else 0.0
        minimum = min(minimum, *a)
        anchor_error = [a[m] - t[m] for m in range(12)]
        naive_error = [b[m] - t[m] for m in range(12)]
        e1 = math.fsum(anchor_error)
        e0 = math.fsum(naive_error)
        annual_anchor_bias.append(weight * e1)
        annual_naive_bias.append(weight * e0)
        annual_anchor_squared.append(weight * e1**2)
        annual_naive_squared.append(weight * e0**2)
        monthly_anchor_squared.append(weight * math.fsum(x*x for x in anchor_error)/12)
        monthly_naive_squared.append(weight * math.fsum(x*x for x in naive_error)/12)
        sa, st, sb = math.fsum(a), math.fsum(t), math.fsum(b)
        if count == 0 and sa > 0 and st > 0 and sb > 0:
            valid_area += weight
            anchor_tv.append(weight * math.fsum(abs(a[m]/sa - t[m]/st) for m in range(12))/2)
            naive_tv.append(weight * math.fsum(abs(b[m]/sb - t[m]/st) for m in range(12))/2)
    expected = {
        "center_count": n, "area_ha": sum_weights,
        "negative_anchored_month_center_count": negative_count,
        "any_negative_anchored_month_area_fraction": negative_area/sum_weights,
        "minimum_anchored_monthly_mm": minimum,
        "common_valid_month_share_area_fraction": valid_area/sum_weights,
        "anchored": {
            "annual_bias_mm": math.fsum(annual_anchor_bias)/sum_weights,
            "spatial_annual_rmse_mm": math.sqrt(math.fsum(annual_anchor_squared)/sum_weights),
            "month_center_rmse_mm": math.sqrt(math.fsum(monthly_anchor_squared)/sum_weights),
            "valid_support_month_share_tv": math.fsum(anchor_tv)/valid_area if valid_area else None,
        },
        "no_change": {
            "annual_bias_mm": math.fsum(annual_naive_bias)/sum_weights,
            "spatial_annual_rmse_mm": math.sqrt(math.fsum(annual_naive_squared)/sum_weights),
            "month_center_rmse_mm": math.sqrt(math.fsum(monthly_naive_squared)/sum_weights),
            "valid_support_month_share_tv": math.fsum(naive_tv)/valid_area if valid_area else None,
        },
    }
    checks = 0
    for key in ("center_count", "area_ha", "negative_anchored_month_center_count",
                "any_negative_anchored_month_area_fraction", "minimum_anchored_monthly_mm",
                "common_valid_month_share_area_fraction"):
        if not math.isclose(saved[key], expected[key], rel_tol=2e-11, abs_tol=2e-8):
            raise AssertionError(f"{key} failed: {saved[key]} versus {expected[key]}")
        checks += 1
    for family in ("anchored", "no_change"):
        for key, value in expected[family].items():
            if (saved[family][key] is None) != (value is None) or (
                    value is not None and not math.isclose(saved[family][key], value, rel_tol=2e-11, abs_tol=2e-8)):
                raise AssertionError(f"{family}.{key} failed")
            checks += 1
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = args.result.resolve()
    out = args.out.resolve()
    if not result.is_relative_to(ROOT / "data/interim") or not out.is_relative_to(ROOT / "data/interim") or out.exists():
        parser.error("ignored source and fresh output required")
    if sha(SOURCE) != SOURCE_SHA:
        raise ValueError("source array changed")
    saved = json.loads(result.read_text())
    if saved["source_array_sha256"] != SOURCE_SHA or saved["status"] != "same_source_in_sample_anchored_monthly_physicality_not_scc":
        raise ValueError("wrong primary result")
    with np.load(SOURCE, allow_pickle=False) as archive:
        count = audit(saved, archive)
    report = {"status": "independent_scalar_anchored_arithmetic_passed",
              "checks": count, "source_array_sha256": SOURCE_SHA,
              "primary_result_sha256": sha(result)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
