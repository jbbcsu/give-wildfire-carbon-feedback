#!/usr/bin/env python3
"""Synthetic tests for the paired crop-response bundle gate."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from validate_scc_response_bundle import (  # noqa: E402
    COEFFICIENT_FIELDS,
    FEATURE_FIELDS,
    validate_bundle,
)


CROPS = ["maize", "wheat"]
REGIONS = ["USA", "CAN"]
rows: list[dict[str, object]] = []
for scenario in ("baseline", "pulse"):
    for year in (2020, 2021):
        for region in REGIONS:
            for crop, share in zip(CROPS, (0.4, 0.6)):
                row: dict[str, object] = {
                    "scenario": scenario, "draw_id": "draw-1", "year": year,
                    "fund_region": region, "crop": crop, "fair_draw_id": "fair-1",
                    "climate_member_id": "gcm-member-1", "socioeconomic_id": "ssp2",
                    "calendar_id": "calendar-1", "response_draw_id": "response-1",
                    "adaptation_scenario": "fixed", "weight_draw_id": "weights-1",
                    "welfare_draw_id": "welfare-1",
                    "crop_value_share": share, "adaptation_loss_multiplier": 1.0,
                    "adaptation_cost_share": 0.0, "observed_support": True,
                }
                row.update({field: 0.1 for field in COEFFICIENT_FIELDS})
                row.update({field: 0.0 for field in FEATURE_FIELDS})
                if scenario == "pulse" and year == 2021:
                    row["seasonal_precip_anomaly"] = 0.01
                rows.append(row)

valid = pd.DataFrame(rows)
audit = validate_bundle(valid, CROPS, REGIONS, "direct", 2021)
assert audit["n_rows"] == 16 and audit["n_crops"] == 2 and audit["n_regions"] == 2

split_identity = valid.copy()
split_identity.loc[split_identity.crop.eq("wheat"), "climate_member_id"] = "gcm-member-2"
try:
    validate_bundle(split_identity, CROPS, REGIONS, "direct", 2021)
    raise AssertionError("split draw identity should fail")
except ValueError as error:
    assert "frozen" in str(error)

moving_weight = valid.copy()
mask = (
    moving_weight.scenario.eq("pulse") & moving_weight.year.eq(2021)
    & moving_weight.fund_region.eq("USA")
)
moving_weight.loc[mask & moving_weight.crop.eq("maize"), "crop_value_share"] = 0.5
moving_weight.loc[mask & moving_weight.crop.eq("wheat"), "crop_value_share"] = 0.5
try:
    validate_bundle(moving_weight, CROPS, REGIONS, "direct", 2021)
    raise AssertionError("moving weights should fail")
except ValueError as error:
    assert "fixed" in str(error) or "matched" in str(error)

pre_pulse_change = valid.copy()
pre_pulse_change.loc[
    pre_pulse_change.scenario.eq("pulse") & pre_pulse_change.year.eq(2020),
    "heat_extreme_anomaly",
] = 0.01
try:
    validate_bundle(pre_pulse_change, CROPS, REGIONS, "direct", 2021)
    raise AssertionError("pre-divergence feature change should fail")
except ValueError as error:
    assert "before" in str(error)

missing_cell = valid.drop(valid.index[0])
try:
    validate_bundle(missing_cell, CROPS, REGIONS, "direct", 2021)
    raise AssertionError("missing region-crop cell should fail")
except ValueError as error:
    assert "full" in str(error) or "matched" in str(error)

print("SCC response-bundle synthetic tests passed")
