#!/usr/bin/env python3
"""Synthetic and receipt tests for the Blue-SCC nutrition transfer audit."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/audit_blue_scc_nutrition_give_transfer.py"
SPEC = importlib.util.spec_from_file_location("audit_blue_scc_nutrition_give_transfer", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


give_rows = [
    {"country_id": "AAA", "country_name": "Alpha", "give_region_id": "R1", "mapping_version": "v1"},
    {"country_id": "BBB", "country_name": "Beta", "give_region_id": "R1", "mapping_version": "v1"},
    {"country_id": "CCC", "country_name": "Gamma", "give_region_id": "R2", "mapping_version": "v1"},
]
summary = MODULE.coverage_summary({"AAA", "BBB", "DDD"}, give_rows, {"R1", "R2"})
assert summary["overlap_countries"] == 2
assert summary["source_only_countries"] == 1
assert summary["give_only_countries"] == 1
assert summary["complete_regions"] == 1
assert summary["region_coverage"]["R1"]["complete"] is True
assert summary["region_coverage"]["R2"]["uncovered_countries"] == 1
assert MODULE.finite("1.25") is True
assert MODULE.finite("NA") is False
assert MODULE.finite("") is False


receipt = json.loads(
    (ROOT / "data/provenance/blue_scc_nutrition_give_transfer_audit_20261013.json")
    .read_text(encoding="utf-8")
)
assert receipt["status"].startswith("blocked_")
assert receipt["nutrition_input"]["all_rows_coverage"]["overlap_countries"] == 127
assert receipt["nutrition_input"]["complete_numeric_coverage"]["overlap_countries"] == 116
assert receipt["nutrition_input"]["complete_numeric_coverage"]["complete_regions"] == 4
assert receipt["nutrition_input"]["nutritional_d_na_rows"] == 11
assert receipt["nutrition_input"]["missing_values_are_zero_filled_by_published_input_builder"] is True
assert receipt["published_2020_country_scc"]["coverage"]["overlap_countries"] == 154
assert receipt["published_2020_country_scc"]["coverage"]["complete_regions"] == 6
assert receipt["interpretation"]["country_scc_sum_reconciles_to_figure4"] is False
assert receipt["annual_path"]["baseline_and_pulse_result_gdx_released"] is False
assert receipt["annual_path"]["rice50x_model_present_in_repository"] is False
assert all(value is False for value in receipt["claim_gates"].values())
assert receipt["published_2020_country_scc"]["country_values_or_membership_embedded"] is False
assert receipt["interpretation"]["external_source_files_copied"] is False

print("Blue-SCC nutrition/GIVE transfer audit tests passed")
