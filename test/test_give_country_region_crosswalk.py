#!/usr/bin/env python3
"""Synthetic failures and real receipt for the GIVE fisheries crosswalk."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/validate_give_country_region_crosswalk.py"
SPEC = importlib.util.spec_from_file_location("validate_give_country_region_crosswalk", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


config = {
    "schema": MODULE.CONFIG_SCHEMA,
    "role": MODULE.CONFIG_ROLE,
    "mapping_version": "v1",
    "expected_country_rows": 3,
    "expected_regions": ["R1", "R2"],
    "expected_region_counts": {"R1": 2, "R2": 1},
}
rows = [
    {"country_id": "AAA", "country_name": "Alpha", "give_region_id": "R1", "mapping_version": "v1"},
    {"country_id": "BBB", "country_name": "Beta", "give_region_id": "R1", "mapping_version": "v1"},
    {"country_id": "CCC", "country_name": "Gamma", "give_region_id": "R2", "mapping_version": "v1"},
]
assert MODULE.validate_rows(MODULE.FIELDNAMES, rows, config)["region_count"] == 2


def reject(changed_rows: list[dict[str, str]], message: str) -> None:
    try:
        MODULE.validate_rows(MODULE.FIELDNAMES, changed_rows, config)
    except ValueError:
        return
    raise AssertionError(message)


bad = copy.deepcopy(rows)
bad[1]["country_id"] = "AAA"
reject(bad, "duplicate country passed")
bad = copy.deepcopy(rows)
bad[1]["give_region_id"] = "R9"
reject(bad, "unknown region passed")
bad = copy.deepcopy(rows)
bad[1]["mapping_version"] = "v2"
reject(bad, "mixed mapping version passed")
bad = copy.deepcopy(rows)
bad[1]["country_name"] = ""
reject(bad, "blank country name passed")

real = MODULE.audit(ROOT / "config/give_country_fund_region_crosswalk_v1.toml")
assert real["country_rows"] == 184
assert real["region_count"] == 16
assert real["aggregator_schema_compatible"] is True
assert real["welfare_estimated"] is False

print("GIVE fisheries country-region crosswalk tests passed")
