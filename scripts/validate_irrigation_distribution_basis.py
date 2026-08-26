#!/usr/bin/env python3
"""Validate a one-outcome irrigation-weighted distribution-candidate basis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from allocate_irrigation_distribution_basis import (
    ALLOCATION_ORDER,
    CONTRACT_ID,
    basis_feature_names,
)


KEYS = ["harvest_year", "lat", "lon_360", "crop"]


def validate(
    frame: pd.DataFrame,
    audit: dict[str, Any],
    *,
    expected_crop: str,
    stages: int = 3,
    tolerance: float = 1e-8,
) -> dict[str, Any]:
    features = basis_feature_names(stages)
    required = set(
        KEYS
        + features
        + [
            "irrigation",
            "yield_observed",
            "yield_t_ha",
            "response_basis_contract_id",
            "basis_allocation_order",
            "wet_day_threshold_mm",
            "nonlinear_post_allocation_transform_authorized",
            "direct_pattern_candidate_basis_complete",
            "production_model_form_frozen",
            "fit_authorized",
        ]
    )
    if missing := required - set(frame.columns):
        raise ValueError(f"Candidate basis missing {sorted(missing)}")
    if frame.empty or frame.duplicated(KEYS).any():
        raise ValueError("Candidate basis must contain unique nonempty outcome keys")
    if set(frame["crop"].astype(str)) != {expected_crop}:
        raise ValueError("Candidate basis crop coverage differs from expectation")
    constants = {
        "irrigation": "area_weighted",
        "response_basis_contract_id": CONTRACT_ID,
        "basis_allocation_order": ALLOCATION_ORDER,
    }
    for column, expected in constants.items():
        if set(frame[column].dropna().astype(str)) != {expected}:
            raise ValueError(f"Candidate basis has invalid {column}")
    boolean_constants = {
        "nonlinear_post_allocation_transform_authorized": False,
        "direct_pattern_candidate_basis_complete": True,
        "production_model_form_frozen": False,
        "fit_authorized": False,
    }
    for column, expected in boolean_constants.items():
        if not frame[column].isin([expected]).all():
            raise ValueError(f"Candidate basis has invalid {column}")
    observed = frame["yield_observed"]
    if not observed.isin([True, False]).all():
        raise ValueError("yield_observed must be Boolean")
    yield_values = pd.to_numeric(frame["yield_t_ha"], errors="coerce")
    if not observed.eq(yield_values.notna()).all() or (yield_values.loc[observed] <= 0).any():
        raise ValueError("Yield value and observed flag are inconsistent")
    numeric = frame[features].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Candidate basis features must be finite numeric values")
    threshold = pd.to_numeric(frame["wet_day_threshold_mm"], errors="coerce")
    if not np.isfinite(threshold).all() or threshold.nunique() != 1 or threshold.iloc[0] <= 0:
        raise ValueError("Candidate basis must retain one positive wet-day threshold")

    stage_days = [f"stage{i}_stage_days" for i in range(1, stages + 1)]
    stage_precip = [f"stage{i}_precip_mm" for i in range(1, stages + 1)]
    stage_wet = [f"stage{i}_wet_days_n" for i in range(1, stages + 1)]
    stage_shares = [f"stage{i}_precip_share" for i in range(1, stages + 1)]
    reconciliations = {
        "stage_days": (numeric[stage_days].sum(axis=1) - numeric["season_days"]).abs(),
        "stage_precip_mm": (numeric[stage_precip].sum(axis=1) - numeric["precip_mm"]).abs(),
        "stage_wet_days": (numeric[stage_wet].sum(axis=1) - numeric["wet_days_n"]).abs(),
        "stage_share_plus_zero": (
            numeric[stage_shares].sum(axis=1)
            + numeric["zero_precipitation_season"]
            - 1.0
        ).abs(),
    }
    reconciliation_tolerances = {
        "stage_days": tolerance,
        "stage_precip_mm": 1e-3,
        "stage_wet_days": tolerance,
        "stage_share_plus_zero": 1e-6,
    }
    if any(
        values.max() > reconciliation_tolerances[name]
        for name, values in reconciliations.items()
    ):
        maxima = {name: float(values.max()) for name, values in reconciliations.items()}
        raise ValueError(f"Candidate basis reconciliation failed: {maxima}")

    fractions = ["wet_day_frequency", "cdd_fraction", "zero_precipitation_season"]
    fractions += [
        f"stage{i}_{name}"
        for i in range(1, stages + 1)
        for name in ("wet_day_frequency", "cdd_fraction", "precip_share")
    ]
    fraction_tolerance = 1e-6
    if (
        (numeric[fractions] < -fraction_tolerance)
        | (numeric[fractions] > 1 + fraction_tolerance)
    ).any().any():
        raise ValueError("Candidate frequency/share/fraction lies outside [0,1]")
    if (
        (numeric["precipitation_concentration_hhi"] < -fraction_tolerance)
        | (numeric["precipitation_concentration_hhi"] > 1 + fraction_tolerance)
        | (numeric["precipitation_timing_centroid"] < -fraction_tolerance)
        | (numeric["precipitation_timing_centroid"] > 1 + fraction_tolerance)
    ).any():
        raise ValueError("Candidate timing or concentration lies outside [0,1]")

    for prefix, days in [("", "season_days")] + [
        (f"stage{i}_", f"stage{i}_stage_days") for i in range(1, stages + 1)
    ]:
        if (
            (numeric[f"{prefix}wet_days_n"] > numeric[days] + tolerance)
            | (numeric[f"{prefix}cdd_max_days"] > numeric[days] + tolerance)
            | (numeric[f"{prefix}rx1day_mm"] > numeric[f"{prefix}rx5day_mm"] + tolerance)
            | (numeric[f"{prefix}rx5day_mm"] > numeric[f"{prefix}precip_mm"] + 1e-3)
        ).any():
            raise ValueError(f"Candidate {prefix or 'season_'} count/extreme bounds fail")

    if audit.get("response_basis_contract_id") != CONTRACT_ID:
        raise ValueError("Allocation audit contract ID differs from candidate basis")
    if audit.get("basis_allocation_order") != ALLOCATION_ORDER:
        raise ValueError("Allocation audit order differs from candidate basis")
    if audit.get("basis_features") != features or audit.get("basis_feature_count") != len(features):
        raise ValueError("Allocation audit feature contract differs from candidate basis")
    if audit.get("output_rows") != len(frame):
        raise ValueError("Allocation audit output row count differs from candidate basis")
    if audit.get("observed_outcomes") != int(observed.sum()):
        raise ValueError("Allocation audit observed count differs from candidate basis")
    if audit.get("fit_authorized") is not False or audit.get("scc_authorized") is not False:
        raise ValueError("Allocation audit improperly authorizes fitting or SCC use")

    return {
        "status": "validated_candidate_basis_not_fit_or_scc_authorized",
        "crop": expected_crop,
        "rows": int(len(frame)),
        "observed_outcomes": int(observed.sum()),
        "basis_feature_count": len(features),
        "response_basis_contract_id": CONTRACT_ID,
        "basis_allocation_order": ALLOCATION_ORDER,
        "wet_day_threshold_mm": float(threshold.iloc[0]),
        "maximum_reconciliation_differences": {
            name: float(values.max()) for name, values in reconciliations.items()
        },
        "reconciliation_tolerances": reconciliation_tolerances,
        "fit_authorized": False,
        "scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--allocation-audit", required=True)
    parser.add_argument("--expected-crop", required=True)
    parser.add_argument("--stages", type=int, default=3)
    parser.add_argument("--out")
    args = parser.parse_args()
    summary = validate(
        pd.read_parquet(args.panel),
        json.loads(Path(args.allocation_audit).read_text(encoding="utf-8")),
        expected_crop=args.expected_crop,
        stages=args.stages,
    )
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
