#!/usr/bin/env python3
"""Cross-software validation of the published Iroquois maize heat curve."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_maize_response import MaizeBasis, PublishedEstimate

DEFAULT_DATA = ROOT / "data/raw/hultgren_response/historical_git/dae5fe8d0d4a260328e4baa45b547368bd6790b3/corn_gmfd_v1_ready.dta"
DEFAULT_ESTIMATE = ROOT / "data/interim/hultgren_maize_response_20260923"
DEFAULT_STATA = ROOT / "data/interim/hultgren_maize_iroquois_curve_20260923/stata_curve.csv"
DEFAULT_OUTPUT = ROOT / "data/provenance/hultgren_maize_iroquois_curve_validation_20260923.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def basis(gdd: float, kdd: float, moderators: dict[str, float]) -> MaizeBasis:
    return MaizeBasis(
        gdd=gdd,
        kdd=kdd,
        prcp_poly_1_bins=(0.0, 0.0, 0.0),
        prcp_poly_2_bins=(0.0, 0.0, 0.0),
        ln_gdppc=moderators["ln_gdppc"],
        irrigated_share=moderators["irrigated_share"],
        lr_tmax_crop=moderators["lr_tmax_crop"],
        lr_prcp_crop=moderators["lr_prcp_crop"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--estimate", type=Path, default=DEFAULT_ESTIMATE)
    parser.add_argument("--stata", type=Path, default=DEFAULT_STATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    for path in (args.data, args.estimate / "coefficients.csv", args.estimate / "covariance.csv", args.stata):
        if not path.exists():
            raise FileNotFoundError(path)

    stata = pd.read_csv(args.stata).sort_values("tavg").reset_index(drop=True)
    expected_temperatures = np.arange(1.0, 41.0)
    if not np.array_equal(stata["tavg"].to_numpy(), expected_temperatures):
        raise AssertionError("Stata curve temperature support differs from 1 through 40 C")
    if not (stata["num_obs"] == 59).all():
        raise AssertionError("published Iroquois source subset no longer contains 59 observations")

    moderators = {
        "lr_tmax_crop": float(stata.loc[0, "sample_tbar"]),
        "lr_prcp_crop": float(stata.loc[0, "sample_pbar"]),
        "ln_gdppc": float(stata.loc[0, "sample_inc"]),
        "irrigated_share": float(stata.loc[0, "sample_ir"]),
    }
    for column in ("sample_tbar", "sample_pbar", "sample_inc", "sample_ir"):
        if stata[column].nunique(dropna=False) != 1:
            raise AssertionError(f"Stata moderator {column} is not constant over the curve")

    estimate = PublishedEstimate.from_exports(
        args.estimate / "coefficients.csv", args.estimate / "covariance.csv"
    )
    reference = basis(0.0, 0.0, moderators)
    python_response = []
    python_se = []
    for temperature in expected_temperatures:
        gdd = min(max(temperature - 8.0, 0.0), 23.0)
        kdd = max(temperature - 31.0, 0.0)
        result = estimate.contrast(reference, basis(gdd, kdd, moderators))
        python_response.append(result["delta_log_yield"])
        python_se.append(result["coefficient_only_standard_error"])

    response_error = np.abs(np.asarray(python_response) - stata["response"].to_numpy())
    se_error = np.abs(np.asarray(python_se) - stata["standard_error"].to_numpy())
    gates = {
        "source_subset_count_reproduced": bool((stata["num_obs"] == 59).all()),
        "temperature_basis_reproduced": bool(
            np.array_equal(
                stata["gdd_plot"].to_numpy(),
                np.minimum(np.maximum(expected_temperatures - 8.0, 0.0), 23.0),
            )
            and np.array_equal(
                stata["kdd_plot"].to_numpy(), np.maximum(expected_temperatures - 31.0, 0.0)
            )
        ),
        # The .ster path retains Stata's internal coefficient/covariance values,
        # while Python reads their decimal CSV exports.  Nanounit tolerances
        # are therefore stricter than the export precision without pretending
        # that the two serialization routes are bit-identical.
        "python_stata_response_match": bool(response_error.max() <= 2e-9),
        "python_stata_standard_error_match": bool(se_error.max() <= 3e-10),
    }
    if not all(gates.values()):
        raise AssertionError(f"Iroquois curve validation failed: {gates}")

    selected = {}
    for temperature in (8, 20, 31, 35, 40):
        index = temperature - 1
        selected[str(temperature)] = {
            "delta_log_yield_per_day": float(python_response[index]),
            "coefficient_only_standard_error": float(python_se[index]),
        }

    payload = {
        "schema": "hultgren_maize_iroquois_curve_validation/v1",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "dataset_sha256": sha256(args.data),
            "coefficient_sha256": sha256(args.estimate / "coefficients.csv"),
            "covariance_sha256": sha256(args.estimate / "covariance.csv"),
            "stata_curve_sha256": sha256(args.stata),
            "source_code": "pinned USA_CHN_mac.do at 3ccdffcd4e4ff6e55566ce76e2aac130ee86349a",
        },
        "location": {"iso": "USA", "adm2": "iroquois", "observations": 59},
        "moderators": moderators,
        "curve": {
            "temperature_c": [1, 40],
            "reference_temperature_c": 8,
            "gdd_base_c": 8,
            "kdd_threshold_c": 31,
            "response_max_absolute_error": float(response_error.max()),
            "standard_error_max_absolute_error": float(se_error.max()),
            "selected_points": selected,
        },
        "validation_gates": gates,
        "claim_gates": {
            "published_local_temperature_curve_reproduced": True,
            "future_climate_projection_validated": False,
            "precipitation_attribution_validated": False,
            "damage_estimate_validated": False,
            "scc_estimate_validated": False,
        },
        "interpretation": (
            "An independent Python evaluator reproduces Stata's published-source Iroquois maize "
            "one-day temperature response and coefficient-only uncertainty at the source local "
            "moderators. This validates a local response checkpoint, not a future yield, damage, "
            "precipitation-attribution, or SCC result."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "gates": gates, "selected_points": selected}, indent=2))


if __name__ == "__main__":
    main()
