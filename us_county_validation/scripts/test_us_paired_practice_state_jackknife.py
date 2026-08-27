#!/usr/bin/env python3
"""Synthetic summary gates for the paired-practice state jackknife."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_us_paired_practice_state_jackknife import summarize_jackknife  # noqa: E402


full = {"quantity_increment_at_median_log_difference": -0.08}
omissions = [
    {"omitted_state": "AA", "contrasts": {"quantity_increment_at_median_log_difference": -0.07}},
    {"omitted_state": "BB", "contrasts": {"quantity_increment_at_median_log_difference": -0.09}},
    {"omitted_state": "CC", "contrasts": {"quantity_increment_at_median_log_difference": 0.01}},
]
summary = summarize_jackknife(full, omissions, {"AA", "BB", "CC"})
metric = summary["quantity_increment_at_median_log_difference"]
assert metric["omission_count"] == 3
assert metric["same_sign_count"] == 2
assert metric["minimum_leave_one_state_out"] == -0.09
assert metric["maximum_leave_one_state_out"] == 0.01

duplicate = copy.deepcopy(omissions)
duplicate[2]["omitted_state"] = "AA"
try:
    summarize_jackknife(full, duplicate, {"AA", "BB", "CC"})
except ValueError as error:
    assert "exactly once" in str(error)
else:
    raise AssertionError("duplicate state omission was accepted")

try:
    summarize_jackknife({"quantity_increment_at_median_log_difference": 0.0}, omissions, {"AA", "BB", "CC"})
except ValueError as error:
    assert "nonzero" in str(error)
else:
    raise AssertionError("zero full-sample contrast was accepted")

print("U.S. paired-practice state-jackknife synthetic tests passed")
