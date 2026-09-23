#!/usr/bin/env python3
"""Algebraically validate the published-maize response evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_maize_response import MaizeBasis, PublishedEstimate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coefficients", type=Path, default=ROOT / "data/interim/hultgren_maize_response_20260923/coefficients.csv")
    parser.add_argument("--covariance", type=Path, default=ROOT / "data/interim/hultgren_maize_response_20260923/covariance.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "data/provenance/hultgren_maize_response_evaluator_validation_20260923.json")
    args = parser.parse_args()

    estimate = PublishedEstimate.from_exports(args.coefficients, args.covariance)
    baseline = MaizeBasis(
        gdd=1000.0, kdd=25.0,
        prcp_poly_1_bins=(80.0, 240.0, 480.0),
        prcp_poly_2_bins=(6400.0, 19200.0, 38400.0),
        ln_gdppc=9.0, irrigated_share=0.2, lr_tmax_crop=25.0, lr_prcp_crop=175.0,
    )
    comparison = MaizeBasis(
        gdd=1010.0, kdd=27.0,
        prcp_poly_1_bins=(82.0, 235.0, 490.0),
        prcp_poly_2_bins=(6724.0, 18408.0, 40016.0),
        ln_gdppc=9.0, irrigated_share=0.2, lr_tmax_crop=25.0, lr_prcp_crop=175.0,
    )
    zero = estimate.contrast(baseline, baseline)
    if zero != {"delta_log_yield": 0.0, "exact_percent_yield_change": 0.0, "coefficient_only_standard_error": 0.0}:
        raise ValueError(f"zero contrast differs: {zero}")
    contrast = estimate.contrast(baseline, comparison)
    if not all(math.isfinite(value) for value in contrast.values()):
        raise ValueError("synthetic algebra check is nonfinite")
    direct_difference = estimate.linear_predictor(comparison) - estimate.linear_predictor(baseline)
    parity_error = abs(direct_difference - contrast["delta_log_yield"])
    if parity_error > 1e-12:
        raise ValueError(f"linear-predictor contrast parity failed: {parity_error}")

    receipt = {
        "schema": "hultgren_maize_response_evaluator_validation_v1",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "coefficients": {"path": str(args.coefficients), "sha256": sha256(args.coefficients), "count": len(estimate.terms)},
        "covariance": {"path": str(args.covariance), "sha256": sha256(args.covariance), "shape": list(estimate.covariance.shape)},
        "zero_contrast": zero,
        "synthetic_algebra_contrast": contrast,
        "linear_predictor_contrast_parity_error": parity_error,
        "claim_boundary": "synthetic algebra and published coefficient/covariance transport only; primitive rainfall transformation, historical replication, future response, damages, and SCC are not validated",
        "historical_response_reproduced": False,
        "future_projection_validated": False,
        "damage_estimate_validated": False,
        "scc_estimate_validated": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "parity_error": parity_error, "claim_boundary": receipt["claim_boundary"]}, indent=2))


if __name__ == "__main__":
    main()
