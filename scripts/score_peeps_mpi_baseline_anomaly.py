#!/usr/bin/env python3
"""Test physicality of direct-2015 baseline plus published PEEPS anomaly."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/interim/peeps_mpi_source_reconstruction_20260917/source_vs_published_crop_center_mm.npz"
SOURCE_SHA = "f1556e24ad9e843f064c095474b0d89954ed621d91cc51f006e63b65cb87b08d"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def metrics(baseline, target, published_old, published_new, weights):
    if (weights.ndim != 1 or len(weights) == 0
            or any(a.shape != (12, len(weights)) for a in (baseline, target, published_old, published_new))
            or not all(np.isfinite(a).all() for a in (baseline, target, published_old, published_new, weights))
            or not np.all(weights > 0) or not np.all(baseline >= 0) or not np.all(target >= 0)):
        raise ValueError("invalid input shape, weight, or direct-rainfall physicality")
    anchored = baseline + (published_new - published_old)
    negative = anchored < 0
    total_weight = np.sum(weights)
    valid = np.all(~negative, axis=0) & (anchored.sum(axis=0) > 0) & (target.sum(axis=0) > 0) & (baseline.sum(axis=0) > 0)

    def weighted(values, support=None):
        if support is None:
            support = np.ones(len(weights), dtype=bool)
        return float(np.sum(values[support] * weights[support]) / np.sum(weights[support]))

    def error_summary(predicted):
        error = predicted - target
        annual = error.sum(axis=0)
        return {"annual_bias_mm": weighted(annual),
                "spatial_annual_rmse_mm": weighted(annual**2)**0.5,
                "month_center_rmse_mm": weighted(np.mean(error**2, axis=0))**0.5}

    def share_tv(predicted):
        if not np.any(valid):
            return None
        a = predicted[:, valid] / predicted[:, valid].sum(axis=0)
        b = target[:, valid] / target[:, valid].sum(axis=0)
        distance = np.sum(np.abs(a - b), axis=0) / 2
        return float(np.sum(distance * weights[valid]) / np.sum(weights[valid]))

    return {
        "center_count": len(weights), "area_ha": float(total_weight),
        "negative_anchored_month_center_count": int(negative.sum()),
        "any_negative_anchored_month_area_fraction": weighted(np.any(negative, axis=0)),
        "minimum_anchored_monthly_mm": float(np.min(anchored)),
        "common_valid_month_share_area_fraction": weighted(valid),
        "anchored": {**error_summary(anchored), "valid_support_month_share_tv": share_tv(anchored)},
        "no_change": {**error_summary(baseline), "valid_support_month_share_tv": share_tv(baseline)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if (not out.is_relative_to(ROOT / "data/interim") or out.exists()
            or shutil.disk_usage(ROOT).free < 130 * 2**30):
        parser.error("fresh ignored output and disk reserve required")
    if sha(SOURCE) != SOURCE_SHA:
        raise ValueError("frozen source array changed")
    with np.load(SOURCE, allow_pickle=False) as archive:
        record = metrics(*(archive[name] for name in (
            "direct_ensemble_mean_mm_2015", "direct_ensemble_mean_mm_2100",
            "published_mm_2015", "published_mm_2100", "hectares")))
    if record["center_count"] != 30821:
        raise ValueError("crop-center support changed")
    result = {"status": "same_source_in_sample_anchored_monthly_physicality_not_scc",
              "protocol": "PEEPS_MPI_BASELINE_ANOMALY_PROTOCOL_20260918.md",
              "source_array_sha256": SOURCE_SHA,
              "forcing_approved": False, "yield_damage_scc_estimated": False, **record}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
