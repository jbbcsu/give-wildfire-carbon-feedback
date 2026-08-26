#!/usr/bin/env python3
"""Synthetic tests for the direct precipitation-pattern candidate basis."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from allocate_irrigation_distribution_basis import (  # noqa: E402
    ALLOCATION_ORDER,
    CONTRACT_ID,
    allocate_distribution_candidate,
    build_regime_candidate_basis,
)


def regime_row(irrigation: str, temperature: float, stage_precip: list[float], wet: list[int]) -> dict[str, object]:
    stage_days = [30, 40, 30]
    row: dict[str, object] = {
        "harvest_year": 2000,
        "lat": 10.25,
        "lon_360": 20.25,
        "crop": "mai",
        "irrigation": irrigation,
        "yield_observed": True,
        "yield_t_ha": 2.0,
        "season_days": sum(stage_days),
        "tmean_c": temperature,
        "precip_mm": sum(stage_precip),
        "wet_days_n": sum(wet),
        "cdd_max_days": 20 if irrigation == "noirr" else 10,
        "rx1day_mm": max(stage_precip) / 2,
        "rx5day_mm": max(stage_precip),
        "wet_day_threshold_mm": 1.0,
    }
    for stage, (days, precip, wet_days) in enumerate(zip(stage_days, stage_precip, wet), start=1):
        prefix = f"stage{stage}_"
        row.update(
            {
                f"{prefix}stage_days": days,
                f"{prefix}tmean_c": temperature + stage,
                f"{prefix}precip_mm": precip,
                f"{prefix}wet_days_n": wet_days,
                f"{prefix}cdd_max_days": min(days, 5 + stage),
                f"{prefix}rx1day_mm": precip / 2,
                f"{prefix}rx5day_mm": precip,
            }
        )
    return row


panel = pd.DataFrame(
    [
        regime_row("noirr", 20.0, [60.0, 30.0, 10.0], [6, 3, 1]),
        regime_row("firr", 25.0, [10.0, 30.0, 60.0], [1, 3, 6]),
    ]
)
weights = pd.DataFrame(
    {
        "lat": [10.25, 10.25],
        "lon_360": [20.25, 20.25],
        "crop": ["mai", "mai"],
        "irrigation": ["noirr", "firr"],
        "area_share": [0.75, 0.25],
        "weight_source_id": ["synthetic-independent-area-v1"] * 2,
        "weight_vintage": ["fixed_2000"] * 2,
        "source_role": ["independent_fixed_baseline_crop_area_share"] * 2,
        "production_eligible": [True, True],
        "season_specific_share": [True, True],
    }
)

regime_basis, features, threshold = build_regime_candidate_basis(panel)
assert threshold == 1.0
assert len(features) == 54
assert np.allclose(
    regime_basis[["stage1_precip_share", "stage2_precip_share", "stage3_precip_share"]].sum(axis=1),
    1.0,
)

output, audit = allocate_distribution_candidate(panel, weights, ["noirr", "firr"])
assert len(output) == 1
row = output.iloc[0]
expected_log = 0.75 * np.log1p(100.0) + 0.25 * np.log1p(100.0)
expected_stage1_share = 0.75 * 0.60 + 0.25 * 0.10
expected_hhi = 0.75 * (0.6**2 + 0.3**2 + 0.1**2) + 0.25 * (0.1**2 + 0.3**2 + 0.6**2)
assert np.isclose(row.log1p_precip_mm, expected_log)
assert np.isclose(row.stage1_precip_share, expected_stage1_share)
assert np.isclose(row.precipitation_concentration_hhi, expected_hhi)
assert not np.isclose(
    row.precipitation_concentration_hhi,
    row.stage1_precip_share**2 + row.stage2_precip_share**2 + row.stage3_precip_share**2,
)
assert np.isclose(row.mean_wet_day_intensity_mm, 10.0)
assert row.response_basis_contract_id == CONTRACT_ID
assert row.basis_allocation_order == ALLOCATION_ORDER
assert row.direct_pattern_candidate_basis_complete
assert not row.production_model_form_frozen
assert not row.fit_authorized
assert audit["basis_feature_count"] == 54
assert audit["wet_day_threshold_status"] == "candidate_definition_not_production_selection"
assert audit["scc_authorized"] is False


def expect_failure(candidate: pd.DataFrame, message: str) -> None:
    try:
        build_regime_candidate_basis(candidate)
    except ValueError as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


bad_threshold = panel.copy()
bad_threshold.loc[1, "wet_day_threshold_mm"] = 0.5
expect_failure(bad_threshold, "one common wet-day threshold")

bad_reconciliation = panel.copy()
bad_reconciliation.loc[0, "stage1_precip_mm"] += 1.0
expect_failure(bad_reconciliation, "Stage precipitation")

bad_extreme = panel.copy()
bad_extreme.loc[0, "stage1_rx5day_mm"] = 1000.0
expect_failure(bad_extreme, "ordering fails")

print("irrigation distribution-candidate basis tests passed")
