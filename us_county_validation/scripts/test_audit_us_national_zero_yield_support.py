#!/usr/bin/env python3
"""Synthetic checks for the national zero-yield support audit."""

from __future__ import annotations

import copy
import tomllib

import pandas as pd

from audit_us_national_zero_yield_support import ROOT, audit


config = tomllib.loads((ROOT / "us_county_validation/us_national_zero_yield_support_v1.toml").read_text(encoding="utf-8"))
config["inputs"]["year_start"] = 2000
config["inputs"]["year_end"] = 2003
config["inputs"]["expected_reported_zero_rows"] = 2
corn = pd.DataFrame({
    "harvest_year": [2000, 2001, 2002, 2003], "county_geoid": ["01001"] * 4,
    "state_alpha": ["AL"] * 4, "commodity": ["CORN"] * 4,
    "yield_value": [10.0, 0.0, 0.0, 12.0], "yield_reported": [True] * 4,
})
positive = pd.DataFrame({
    "outcome_crop": ["corn_grain", "corn_grain"], "county_geoid": ["01001", "01001"],
    "harvest_year": [2000, 2003], "yield_bu_acre": [10.0, 12.0],
    "irrigation_share_eligible": [True, True], "irrigation_share": [0.05, 0.05],
    "rainfed_dominant_10pct": [True, True], "rainfed_dominant_20pct": [True, True],
    "rainfed_dominant_30pct": [True, True],
})
geography = pd.DataFrame({"county_geoid": ["01001"], "feature_construction_eligible": [True]})
result = audit(corn, positive, geography, config)
assert result["reported_zero_rows"] == 2 and result["zero_spell_count"] == 1
assert result["zero_spell_max_years"] == 2 and result["rows_with_adjacent_positive_observation"] == 2
assert result["first_reported_zero_year"] == 2001 and result["last_reported_zero_year"] == 2002
assert result["declared_years_before_first_zero"] == 1 and result["declared_years_after_last_zero"] == 1
assert result["top_five_state_row_share"] == 1.0 and result["state_row_concentration_hhi"] == 1.0
assert result["geography_eligible_rows_with_adjacent_positive"] == 2
assert result["irrigation_share_eligible_rows_with_adjacent_positive"] == 2
assert result["rainfed_dominant_rows_with_adjacent_positive"] == {"10": 2, "20": 2, "30": 2}


def must_fail(corn_frame: pd.DataFrame) -> None:
    try:
        audit(corn_frame, positive, geography, config)
    except ValueError:
        return
    raise AssertionError("expected zero-yield support failure")


negative = corn.copy(); negative.loc[0, "yield_value"] = -1
must_fail(negative)
duplicate = pd.concat([corn, corn.iloc[[0]]], ignore_index=True)
must_fail(duplicate)
wrong = corn.copy(); wrong.loc[0, "commodity"] = "SOYBEANS"
must_fail(wrong)

print("National zero-yield support synthetic tests passed")
