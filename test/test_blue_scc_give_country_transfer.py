#!/usr/bin/env python3
"""Synthetic coverage and fail-closed tests for the country-transfer audit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/audit_blue_scc_give_country_transfer.py"
SPEC = importlib.util.spec_from_file_location("audit_blue_scc_give_country_transfer", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


source_fields = ["country_iso3", "GDP_FractionChange_perC"]
source_rows = [
    {"country_iso3": "AAA", "GDP_FractionChange_perC": "-0.1"},
    {"country_iso3": "BBB", "GDP_FractionChange_perC": "0.2"},
    {"country_iso3": "DDD", "GDP_FractionChange_perC": "0"},
]
give_fields = MODULE.GIVE_FIELDS
give_rows = [
    {"country_id": "AAA", "country_name": "Alpha", "give_region_id": "R1", "mapping_version": "v1"},
    {"country_id": "BBB", "country_name": "Beta", "give_region_id": "R1", "mapping_version": "v1"},
    {"country_id": "CCC", "country_name": "Gamma", "give_region_id": "R2", "mapping_version": "v1"},
]

summary = MODULE.summarize_transfer(
    source_fields, source_rows, give_fields, give_rows, {"R1", "R2"}
)
assert summary["overlap_countries"] == 2
assert summary["source_only_countries"] == 1
assert summary["give_only_countries"] == 1
assert summary["complete_regions"] == 1
assert summary["region_coverage"]["R1"]["complete"] is True
assert summary["region_coverage"]["R2"]["uncovered_countries"] == 1


def reject(changed_source: list[dict[str, str]], message: str) -> None:
    try:
        MODULE.summarize_transfer(
            source_fields, changed_source, give_fields, give_rows, {"R1", "R2"}
        )
    except ValueError:
        return
    raise AssertionError(message)


reject(source_rows + [source_rows[0]], "duplicate source country passed")
reject(
    source_rows + [{"country_iso3": "bad", "GDP_FractionChange_perC": "0"}],
    "invalid source country passed",
)

receipt_path = ROOT / "data/provenance/blue_scc_give_country_transfer_audit_20260928.json"
if receipt_path.exists():
    import json

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "blocked_incomplete_country_coverage_and_unlicensed_source"
    assert receipt["coverage"]["overlap_countries"] == 142
    assert receipt["coverage"]["give_only_countries"] == 42
    assert receipt["coverage"]["complete_regions"] == 6
    assert receipt["claim_gates"]["country_coefficient_transfer_authorized"] is False
    assert receipt["interpretation"]["coefficient_values_or_country_membership_embedded"] is False

print("Blue-SCC/GIVE country transfer audit tests passed")
