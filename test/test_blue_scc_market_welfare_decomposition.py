#!/usr/bin/env python3
"""Synthetic fail-closed tests for the Blue-SCC market decomposition audit."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/audit_blue_scc_market_welfare_decomposition.py"
SPEC = importlib.util.spec_from_file_location("audit_blue_scc_market_welfare_decomposition", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


projection = "\n".join([
    "summarise(profits_usd = mean(profits_usd, na.rm = TRUE))",
    "profit_diff_from_rcp_26 = profits_usd - profits_usd_baseline",
    'WDI(country = "all", indicator = "NY.GDP.MKTP.PP.KD", start = 2012, end = 2021)',
    "multiplier_value = c(1+2.59+0.62",
    "1+2.67+0.62", "1+3.12+0.76", "1+2.05+0.56", "1+3.52+1.22", "1+3.27 +0.73",
    "multiplier_value=ifelse(is.na(multiplier_value),4.55,multiplier_value)",
    "profits_usd * multiplier_value/ (1.14*GDP_ppp)",
    "profits_usd_baseline * multiplier_value / (1.14*GDP_ppp)",
    "profit_ppDiff_from_rcp_26 = profits_usd_percGDP - profits_usd_percGDP_baseline",
    'countrycode(fisheries_df_temp_gdp$country_iso3,origin="iso3c",destination="continent")',
    'countrycode(fisheries_df_temp_gdp$country_iso3,origin="iso3c",destination="region")',
])
damage = "\n".join([
    'filter(scenario == "Full Adaptation"',
    "I(profit_ppDiff_from_rcp_26/100) ~ 0 + I(tdif_from_rcp26)",
    'write.csv(fish_tcoeff,file="Data/output_modules_input_rice50x/input_rice50x/fish_tcoeff.csv")',
])
crosscutting = "\n".join([
    f'read.csv("External_Data/other/scenarios/{name}")'
    for name in (
        "SSP245_magicc_202303021423.csv", "SSP585_magicc_202303221353.csv",
        "SSP126_magicc_202308040902.csv", "SSP460_magicc_202402051249.csv",
    )
])
upstream = ["raw.rds", "panel.csv"]
locks = ["renv.lock", "DESCRIPTION", "setup.r"]
result = MODULE.inspect_design(
    projection, damage, crosscutting, "'WDI', 'countrycode'", set(), upstream, locks
)
assert result["formula_findings"]["multiplier_free_slope_equals_published_slope_divided_by_exact_country_multiplier"] is True
assert result["tracked_required_upstream_files"] == 0
assert result["tracked_dependency_locks"] == 0
assert result["reproducibility_findings"]["exact_multiplier_free_coefficients_reproducible"] is False
assert result["welfare_findings"]["indirect_and_induced_multiplier_algebraically_separable"] is True
assert result["welfare_findings"]["consumer_plus_producer_surplus_available"] is False

try:
    MODULE.inspect_design(
        projection.replace("profits_usd * multiplier_value/ (1.14*GDP_ppp)", "profits_usd"),
        damage, crosscutting, "'WDI', 'countrycode'", set(), upstream, locks,
    )
except ValueError:
    pass
else:
    raise AssertionError("changed multiplier formula passed")

receipt_path = ROOT / "data/provenance/blue_scc_market_welfare_decomposition_audit_20260928.json"
if receipt_path.exists():
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["tracked_required_upstream_files"] == 0
    assert receipt["required_upstream_files"] == 10
    assert receipt["tracked_dependency_locks"] == 0
    assert receipt["country_coverage_context"]["complete_give_regions"] == 6
    assert receipt["claim_gates"]["damage_or_scc_authorized"] is False

print("Blue-SCC market welfare decomposition audit tests passed")
