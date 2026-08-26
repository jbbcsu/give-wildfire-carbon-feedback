#!/usr/bin/env python3
"""Synthetic regression tests for blocked crop-response evaluation."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from evaluate_crop_response_models import evaluate, load_spec  # noqa: E402


models, _, _, digest = load_spec(PROJECT / "config" / "response_evaluation_spec.toml")
rng = np.random.default_rng(20260822)
rows: list[dict[str, object]] = []
for crop_index, crop in enumerate(("mai", "soy")):
    # Twenty-four cells leave more than one observation per feature after the
    # extreme holdout purges every adjacent pair sharing a yield endpoint.
    for grid in range(24):
        level = 2.0 + crop_index * 0.1 + grid * 0.01
        for year in range(2000, 2008):
            precip = 80 + grid + 3 * (year - 2000) + rng.normal(0, 1)
            temp = 20 + crop_index + 0.2 * (year - 2000) + rng.normal(0, 0.1)
            cdd = 8 + (grid % 3) + rng.normal(0, 0.2)
            rx1 = 12 + (year % 3) + rng.normal(0, 0.2)
            stages = [0.25, 0.45, 0.30]
            log_precip = np.log1p(precip)
            level += 0.03 * (log_precip - np.log1p(80)) - 0.005 * (temp - 20) + rng.normal(0, 0.002)
            row: dict[str, object] = {
                "crop": crop, "irrigation": "noirr", "lat": -40 + grid,
                "lon_360": 20 + grid, "harvest_year": year,
                "yield_t_ha": float(np.exp(level)), "yield_observed": True,
                "spatial_fold": grid % 3, "is_temporal_holdout": year >= 2006,
                "is_climate_extreme": year in {2003, 2007},
                "tmean_c": temp, "precip_mm": precip,
                "cdd_max_days": cdd, "rx1day_mm": rx1,
            }
            for stage, fraction in enumerate(stages, start=1):
                row[f"stage{stage}_tmean_c"] = temp + stage * 0.2 + rng.normal(0, 0.02)
                row[f"stage{stage}_precip_mm"] = precip * fraction + rng.normal(0, 0.1)
                row[f"stage{stage}_cdd_max_days"] = cdd / stage + rng.normal(0, 0.02)
                row[f"stage{stage}_rx1day_mm"] = rx1 / (4 - stage) + rng.normal(0, 0.02)
            rows.append(row)

valid = pd.DataFrame(rows)
audit = evaluate(valid, models, 20, 8, digest)
assert audit["status"].endswith("not_causal_or_scc_authorized")
assert audit["n_consecutive_pairs"] == 336
assert len(audit["results"]) == 2 * 3 * 3
assert {entry["holdout"] for entry in audit["results"]} == {
    "spatial_block", "temporal", "climate_extreme",
}
assert all("coefficients" not in entry for entry in audit["results"])
assert all(entry["test_rows"] > 0 for entry in audit["results"])
assert audit["nonspatial_split_contract"] == "yield_endpoint_disjoint_purged_training_pairs"
for entry in audit["results"]:
    if entry["holdout"] in {"temporal", "climate_extreme"}:
        assert entry["endpoint_overlap_count"] == 0
        assert entry["purged_train_rows"] > 0
        assert entry["purge_rule"].startswith("drop_training_pairs_sharing_either_yield_endpoint")

# Contract-marked prebuilt bases are consumed verbatim only in the explicit
# mode; primitive precipitation is absent, so an accidental rebuild cannot
# succeed silently.
prebuilt = valid.copy()
for prefix in ("", "stage1_", "stage2_", "stage3_"):
    prebuilt[f"{prefix}log1p_precip_mm"] = np.log1p(prebuilt[f"{prefix}precip_mm"])
    prebuilt[f"{prefix}tmean_x_log1p_precip"] = (
        prebuilt[f"{prefix}tmean_c"] * prebuilt[f"{prefix}log1p_precip_mm"]
    )
prebuilt = prebuilt.drop(
    columns=["precip_mm", "stage1_precip_mm", "stage2_precip_mm", "stage3_precip_mm"]
)
prebuilt["irrigation"] = "area_weighted"
prebuilt["response_basis_contract_id"] = "gdhy_aggregate_irrigation_basis_v1"
prebuilt["basis_allocation_order"] = "regime_basis_before_fixed_area_weighting"
prebuilt["diagnostic_fit_authorized"] = True
prebuilt["nonlinear_post_allocation_transform_authorized"] = False
prebuilt_audit = evaluate(
    prebuilt,
    models,
    20,
    8,
    digest,
    input_basis_mode="prebuilt_irrigation_weighted_basis",
)
assert prebuilt_audit["input_basis_mode"] == "prebuilt_irrigation_weighted_basis"
assert prebuilt_audit["response_basis_contract_id"] == "gdhy_aggregate_irrigation_basis_v1"

try:
    evaluate(prebuilt, models, 20, 8, digest)
    raise AssertionError("prebuilt bases should require explicit mode")
except ValueError as error:
    assert "explicit" in str(error)

invalid_area_weighted = valid.copy()
invalid_area_weighted["irrigation"] = "area_weighted"
try:
    evaluate(invalid_area_weighted, models, 20, 8, digest)
    raise AssertionError("primitive transforms after irrigation aggregation should fail")
except ValueError as error:
    assert "primitive-weather mode" in str(error)

duplicate = pd.concat([valid, valid.iloc[[0]]], ignore_index=True)
try:
    evaluate(duplicate, models, 20, 8, digest)
    raise AssertionError("duplicate keys should fail")
except ValueError as error:
    assert "duplicate" in str(error)

bad_label = valid.copy()
bad_label["is_temporal_holdout"] = bad_label.is_temporal_holdout.astype(object)
bad_label.loc[0, "is_temporal_holdout"] = "maybe"
try:
    evaluate(bad_label, models, 20, 8, digest)
    raise AssertionError("invalid Boolean labels should fail")
except ValueError as error:
    assert "Boolean" in str(error)

missing_stage = valid.drop(columns=["stage2_precip_mm"])
try:
    evaluate(missing_stage, models, 20, 8, digest)
    raise AssertionError("missing stage input should fail")
except ValueError as error:
    assert "stage2_precip_mm" in str(error)

moving_fold = valid.copy()
moving_fold.loc[moving_fold.index[1], "spatial_fold"] = 2
try:
    evaluate(moving_fold, models, 20, 8, digest)
    raise AssertionError("spatial fold that changes within a grid should fail")
except ValueError as error:
    assert "changes within" in str(error)

nonfinal_time = valid.copy()
nonfinal_time.loc[nonfinal_time.harvest_year.eq(2004), "is_temporal_holdout"] = True
try:
    evaluate(nonfinal_time, models, 20, 8, digest)
    raise AssertionError("nonfinal temporal labels should fail")
except ValueError as error:
    assert "final-year block" in str(error)

print("crop-response blocked-evaluation synthetic tests passed")
