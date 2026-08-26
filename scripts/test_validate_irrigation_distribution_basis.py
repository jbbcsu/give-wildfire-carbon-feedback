#!/usr/bin/env python3
"""Failure-mode tests for distribution-candidate basis validation."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from allocate_irrigation_distribution_basis import (  # noqa: E402
    allocate_distribution_candidate,
)
from test_allocate_irrigation_distribution_basis import panel, weights  # noqa: E402
from validate_irrigation_distribution_basis import validate  # noqa: E402


output, audit = allocate_distribution_candidate(panel, weights, ["noirr", "firr"])
summary = validate(output, audit, expected_crop="mai")
assert summary["rows"] == 1
assert summary["basis_feature_count"] == 54
assert summary["fit_authorized"] is False


def expect_failure(frame: pd.DataFrame, record: dict[str, object], message: str) -> None:
    try:
        validate(frame, record, expected_crop="mai")
    except ValueError as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError(f"Expected failure containing {message!r}")


bad_share = output.copy()
bad_share.loc[0, "stage1_precip_share"] += 0.1
expect_failure(bad_share, audit, "reconciliation failed")

bad_order = output.copy()
bad_order.loc[0, "basis_allocation_order"] = "weather_before_weighting"
expect_failure(bad_order, audit, "invalid basis_allocation_order")

bad_audit = copy.deepcopy(audit)
bad_audit["fit_authorized"] = True
expect_failure(output, bad_audit, "improperly authorizes")

print("irrigation distribution-candidate validator tests passed")
