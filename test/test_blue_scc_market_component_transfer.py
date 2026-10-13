#!/usr/bin/env python3
"""Synthetic and receipt tests for the Blue-SCC market transfer audit."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "audit_blue_scc_market_component_transfer.py"
SPEC = importlib.util.spec_from_file_location("audit_blue_scc_market_component_transfer", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


synthetic = {
    "source_countries": 3,
    "give_countries": 3,
    "overlap_countries": 2,
    "source_only_countries": 1,
    "give_only_countries": 1,
    "give_country_count_coverage_fraction": 2 / 3,
    "complete_regions": 1,
    "incomplete_regions": 1,
    "region_coverage": {
        "R1": {"complete": True},
        "R2": {"complete": False},
    },
}
compact = MODULE.compact_coverage(synthetic)
assert compact["complete_region_ids"] == ["R1"]
assert "region_coverage" not in compact


receipt = json.loads(
    (ROOT / "data/provenance/blue_scc_market_component_transfer_audit_20261013.json")
    .read_text(encoding="utf-8")
)
assert receipt["status"].startswith("blocked_")
assert receipt["market_temperature_coefficients"]["coverage"]["overlap_countries"] == 142
assert receipt["market_temperature_coefficients"]["coverage"]["complete_regions"] == 6
assert receipt["published_2020_country_market_scc"]["coverage"]["overlap_countries"] == 154
assert receipt["published_2020_country_market_scc"]["coverage"]["complete_regions"] == 6
assert receipt["support_relationship"] == {
    "coefficient_only_countries": 23,
    "country_scc_only_countries": 35,
    "intersection_countries": 120,
}
global_component = receipt["global_figure4_market_component"]
assert global_component["usd_per_tco2"] == 0.05704041587845721
assert global_component["reproduced_directly_from_figure_source_workbook"] is True
assert global_component["reproduced_by_summing_country_file"] is False
assert abs(global_component["country_file_sum_relative_difference"] + 0.07671369470131395) < 1e-15
assert receipt["formula_findings"]["global_and_country_files_use_different_aggregation_levels"] is True
assert receipt["annual_path"]["annual_regional_market_damages_reproducible"] is False
assert all(value is False for value in receipt["claim_gates"].values())
assert receipt["market_temperature_coefficients"]["country_values_or_membership_embedded"] is False
assert receipt["published_2020_country_market_scc"]["country_values_or_membership_embedded"] is False
assert receipt["interpretation"]["external_source_files_copied"] is False

print("Blue-SCC market component transfer audit tests passed")
