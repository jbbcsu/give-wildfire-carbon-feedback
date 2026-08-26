#!/usr/bin/env python3
"""Invariant tests for the national all-practice PDSI public receipt."""
from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_nass_national_all_practice_pdsi_receipt import validate_public_receipt  # noqa: E402


gates = {
    "contains_raw_values": False,
    "contains_outcome_values": False,
    "contains_api_key": False,
    "contains_absolute_paths": False,
    "response_estimated": False,
    "causal_effect_estimated": False,
    "damage_calculated": False,
    "scc_calculated": False,
}
valid = {"claim_gates": gates, "files": {"joined": {"path": "data/interim/join.parquet"}}}
validate_public_receipt(valid)

absolute = {**valid, "files": {"joined": {"path": "/machine/private/join.parquet"}}}
try:
    validate_public_receipt(absolute)
except ValueError as error:
    assert "absolute path" in str(error)
else:
    raise AssertionError("public receipt accepted an absolute path")

authorized = {**valid, "claim_gates": {**gates, "response_estimated": True}}
try:
    validate_public_receipt(authorized)
except ValueError as error:
    assert "claim gate" in str(error)
else:
    raise AssertionError("public receipt accepted an authorized response claim")

outcome_value = {**valid, "summary": {"yield_bu_acre": 150.0}}
try:
    validate_public_receipt(outcome_value)
except ValueError as error:
    assert "raw outcome" in str(error)
else:
    raise AssertionError("public receipt accepted an outcome value")

print("national all-practice PDSI public-receipt tests passed")
