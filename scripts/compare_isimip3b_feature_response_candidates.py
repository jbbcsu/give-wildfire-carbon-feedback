#!/usr/bin/env python3
"""Exact-key comparison of the rejected affine and physical-link candidates."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from validate_isimip3b_structural_feature_response_contract import ESMS, FEATURES


KEYS = ["holdout_type", "holdout_id", "feature_family"]
FUTURE_SCENARIOS = ["ssp126", "ssp370", "ssp585"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def compare(affine: pd.DataFrame, physical: pd.DataFrame) -> dict[str, object]:
    required = set(KEYS + ["benchmark_rmse", "rmse_ratio_to_cell_mean"])
    require(not (required - set(affine.columns)) and not (required - set(physical.columns)), "candidate schema is incomplete")
    for name, frame in (("affine", affine), ("physical", physical)):
        require(len(frame) == 88 and not frame.duplicated(KEYS).any(), f"{name} key product is invalid")
        expected = {("whole_esm", identity, feature) for identity in ESMS for feature in FEATURES}
        expected |= {("whole_scenario", identity, feature) for identity in FUTURE_SCENARIOS for feature in FEATURES}
        require(set(frame[KEYS].itertuples(index=False, name=None)) == expected, f"{name} holdout product changed")
        require(np.isfinite(frame[["benchmark_rmse", "rmse_ratio_to_cell_mean"]].to_numpy(float)).all(), f"{name} metrics are nonfinite")
    joined = affine[KEYS + ["benchmark_rmse", "rmse_ratio_to_cell_mean"]].merge(
        physical[KEYS + ["benchmark_rmse", "rmse_ratio_to_cell_mean"]], on=KEYS,
        suffixes=("_affine", "_physical"), validate="one_to_one",
    )
    require(np.allclose(joined.benchmark_rmse_affine, joined.benchmark_rmse_physical, rtol=0, atol=1e-12), "cell-mean benchmarks differ")
    joined["physical_minus_affine_rmse_ratio"] = joined.rmse_ratio_to_cell_mean_physical - joined.rmse_ratio_to_cell_mean_affine
    rows = joined.sort_values(KEYS).to_dict(orient="records")
    summaries = []
    for feature, group in joined.groupby("feature_family", sort=True):
        summaries.append({
            "feature_family": feature,
            "comparisons": len(group),
            "affine_median_rmse_ratio": float(group.rmse_ratio_to_cell_mean_affine.median()),
            "physical_median_rmse_ratio": float(group.rmse_ratio_to_cell_mean_physical.median()),
            "physical_better_than_affine": int((group.physical_minus_affine_rmse_ratio < 0).sum()),
        })
    return {
        "schema": "isimip3b_feature_response_candidate_comparison_v1",
        "status": "validated_rejected_candidate_comparison_not_model_promotion",
        "comparisons": rows,
        "feature_summaries": summaries,
        "summary": {
            "exact_key_comparisons": len(joined),
            "physical_better_than_affine": int((joined.physical_minus_affine_rmse_ratio < 0).sum()),
            "both_better_than_cell_mean": int(((joined.rmse_ratio_to_cell_mean_affine < 1) & (joined.rmse_ratio_to_cell_mean_physical < 1)).sum()),
            "physical_rescues_affine_failure": int(((joined.rmse_ratio_to_cell_mean_affine >= 1) & (joined.rmse_ratio_to_cell_mean_physical < 1)).sum()),
            "physical_loses_affine_success": int(((joined.rmse_ratio_to_cell_mean_affine < 1) & (joined.rmse_ratio_to_cell_mean_physical >= 1)).sum()),
        },
        "actual_fair_candidate_path_evaluated": False,
        "production_promoted": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "disclaimer": "This exact-key comparison diagnoses two rejected candidates; it does not select a production model or authorize FAIR pulse, response, damage, welfare, or SCC evaluation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--affine", required=True, type=Path)
    parser.add_argument("--physical", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = compare(pd.read_csv(args.affine), pd.read_csv(args.physical))
    result["sources"] = [
        {"role": "affine_candidate", "path": args.affine.as_posix(), "sha256": sha256(args.affine)},
        {"role": "physical_link_candidate", "path": args.physical.as_posix(), "sha256": sha256(args.physical)},
    ]
    result["implementation"] = {"path": Path(__file__).as_posix(), "sha256": sha256(Path(__file__))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"candidate comparison: physical better in {result['summary']['physical_better_than_affine']}/88; rescues {result['summary']['physical_rescues_affine_failure']}")


if __name__ == "__main__":
    main()
