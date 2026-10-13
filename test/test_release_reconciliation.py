#!/usr/bin/env python3
"""Focused tests for the EPA globalAQ release reconciliation audit."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/audit_release_reconciliation.py"
SPEC = importlib.util.spec_from_file_location("audit_release_reconciliation", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


synthetic = [
    {"discount.rate": "x", "Pollutant": "Ozone", "Model": "CESM2", "mean_npd": "3"},
    {"discount.rate": "x", "Pollutant": "Ozone", "Model": "GISS", "mean_npd": "1"},
    {"discount.rate": "x", "Pollutant": "PM", "Model": "CESM2", "mean_npd": "-4"},
    {"discount.rate": "x", "Pollutant": "PM", "Model": "GISS", "mean_npd": "-2"},
]
means, models = MODULE.mean_components(synthetic, "x")
assert means == {"Ozone": 2.0, "PM": -3.0}
assert models["Ozone"] == {"CESM2": 3.0, "GISS": 1.0}


receipt = json.loads(
    (ROOT / "data/provenance/epa_globalaq_release_reconciliation_20261013.json")
    .read_text(encoding="utf-8")
)
assert receipt["status"].startswith("blocked_")
assert receipt["source"]["commit"] == "1139e7aff1ca7806b6b542268e829f9759dd8808"
assert receipt["source"]["tree_entry_count"] == 33
assert receipt["official_api_observation"]["release_count"] == 0
assert receipt["official_api_observation"]["tag_count"] == 0
checked = receipt["checked_in_2pct_ramsey"]
assert checked["rff_component_means_usd_per_tco2"] == {
    "Ozone": 16.671648911048777,
    "PM": -24.529048760713994,
}
assert checked["mean_path_component_means_usd_per_tco2"] == {
    "Ozone": 20.658544995202234,
    "PM": -21.90869516466148,
}
assert checked["rff_net_mean_usd_per_tco2"] == -34.66761788076073
comparison = receipt["article_comparison"]
assert comparison["rff_components_reproduce_article"] is False
assert comparison["mean_path_components_reproduce_article"] is False
assert comparison["checked_in_net_equals_checked_in_component_sum"] is False
assert comparison["article_net_equals_article_component_sum"] is True
assert receipt["artifact_inventory"]["checked_in_parquet_paths"] == []
assert receipt["artifact_inventory"]["dependency_manifest_paths"] == []
assert receipt["interpretation"]["wildfire_files_or_estimates_used"] is False
assert receipt["interpretation"]["new_estimate_or_imputation_performed"] is False
assert receipt["interpretation"]["currency_price_year_conflict_requires_author_clarification"] is True
assert all(value is False for value in receipt["claim_gates"].values())

print("EPA globalAQ release reconciliation tests passed")
