#!/usr/bin/env python3
"""Synthetic support and contract failures for the GFDL midcentury audit."""

from __future__ import annotations

import copy
import tomllib
from pathlib import Path

import pandas as pd

from evaluate_isimip3b_gfdl_three_scenario_midcentury_holdout import (
    EXPECTED_SCENARIOS,
    evaluate_support,
    validate_config,
)
from evaluate_isimip3b_five_esm_holdout_smoke import FEATURES


ROOT = Path(__file__).resolve().parents[1]
config = tomllib.loads((ROOT / "config/isimip3b_gfdl_three_scenario_midcentury_holdout_v1.toml").read_text(encoding="utf-8"))
validate_config(config)
endcentury_config = tomllib.loads(
    (ROOT / "config/isimip3b_gfdl_three_scenario_endcentury_holdout_v1.toml").read_text(encoding="utf-8")
)
assert validate_config(endcentury_config)["period"] == "endcentury"
ipsl_config = tomllib.loads(
    (ROOT / "config/isimip3b_ipsl_three_scenario_midcentury_holdout_v1.toml").read_text(encoding="utf-8")
)
assert validate_config(ipsl_config)["period"] == "midcentury"
assert ipsl_config["selection"]["esm_id"] == "IPSL-CM6A-LR"
ipsl_endcentury_config = tomllib.loads(
    (ROOT / "config/isimip3b_ipsl_three_scenario_endcentury_holdout_v1.toml").read_text(encoding="utf-8")
)
assert validate_config(ipsl_endcentury_config)["period"] == "endcentury"
assert ipsl_endcentury_config["selection"]["esm_id"] == "IPSL-CM6A-LR"
mri_config = tomllib.loads(
    (ROOT / "config/isimip3b_mri_three_scenario_midcentury_holdout_v1.toml").read_text(encoding="utf-8")
)
assert validate_config(mri_config)["period"] == "midcentury"
assert mri_config["selection"]["esm_id"] == "MRI-ESM2-0"
mri_endcentury_config = tomllib.loads(
    (ROOT / "config/isimip3b_mri_three_scenario_endcentury_holdout_v1.toml").read_text(encoding="utf-8")
)
assert validate_config(mri_endcentury_config)["period"] == "endcentury"
assert mri_endcentury_config["selection"]["esm_id"] == "MRI-ESM2-0"
bad = copy.deepcopy(config)
bad["limitations"]["damage_or_scc_authorized"] = True
try:
    validate_config(bad)
except ValueError:
    pass
else:
    raise AssertionError("opened SCC gate passed")

rows = []
scenario_values = {"ssp126": 1.0, "ssp370": 2.0, "ssp585": 4.0}
for scenario in sorted(EXPECTED_SCENARIOS):
    for family_index, family in enumerate(FEATURES):
        for year in (2042, 2043):
            rows.append({
                "scenario": scenario,
                "feature_family": family,
                "feature_value": scenario_values[scenario] + family_index + (year - 2042) * 0.1,
                "harvest_year": year,
                "lat": 1.0,
                "lon_360": 2.0,
                "crop": "mai",
                "irrigation": "noirr",
            })
support = evaluate_support(pd.DataFrame(rows))
assert len(support) == 3 * len(FEATURES)
assert support.loc[support.holdout_id.eq("ssp585"), "above_support"].sum() == 2 * len(FEATURES)
assert support.loc[support.holdout_id.eq("ssp370"), "within_support"].sum() == 2 * len(FEATURES)

bad_rows = pd.DataFrame(rows).loc[lambda frame: ~(
    frame.scenario.eq("ssp126") & frame.feature_family.eq(FEATURES[0])
)].copy()
try:
    evaluate_support(bad_rows)
except ValueError:
    pass
else:
    raise AssertionError("incomplete scenario/feature product passed")

print("GFDL three-scenario midcentury audit tests passed")
