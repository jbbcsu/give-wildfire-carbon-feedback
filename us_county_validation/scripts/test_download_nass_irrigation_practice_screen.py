#!/usr/bin/env python3
"""Credential-free tests for the bounded NASS irrigation screen."""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("download_nass_irrigation_practice_screen.py")
spec = importlib.util.spec_from_file_location("nass_irrigation_screen", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

corn_irrigated = module.yield_practice_parameters("corn", "IRRIGATED")
assert corn_irrigated == {
    "source_desc": "SURVEY",
    "sector_desc": "CROPS",
    "commodity_desc": "CORN",
    "class_desc": "ALL CLASSES",
    "statisticcat_desc": "YIELD",
    "agg_level_desc": "COUNTY",
    "freq_desc": "ANNUAL",
    "reference_period_desc": "YEAR",
    "domain_desc": "TOTAL",
    "prodn_practice_desc": "IRRIGATED",
    "util_practice_desc": "GRAIN",
    "unit_desc": "BU / ACRE",
    "format": "JSON",
}
assert "year" not in corn_irrigated
assert "year__GE" not in corn_irrigated

corn_irrigated_2020 = module.yield_practice_parameters("corn", "IRRIGATED", 2020)
assert corn_irrigated_2020["year"] == "2020"

soy_nonirrigated = module.yield_practice_parameters("soybeans", "NON-IRRIGATED")
assert soy_nonirrigated["commodity_desc"] == "SOYBEANS"
assert soy_nonirrigated["util_practice_desc"] == "ALL UTILIZATION PRACTICES"
assert soy_nonirrigated["prodn_practice_desc"] == "NON-IRRIGATED"

wheat_area = module.census_area_discovery_parameters("wheat", 2022)
assert wheat_area["source_desc"] == "CENSUS"
assert wheat_area["statisticcat_desc"] == "AREA HARVESTED"
assert wheat_area["unit_desc"] == "ACRES"
assert wheat_area["year"] == "2022"
assert "domain_desc" not in wheat_area
assert "prodn_practice_desc" not in wheat_area

try:
    module.yield_practice_parameters("corn", "ALL PRODUCTION PRACTICES")
except ValueError as error:
    assert "unsupported production practice" in str(error)
else:
    raise AssertionError("unapproved practice should fail")

try:
    module.census_area_discovery_parameters("corn", 1900)
except ValueError as error:
    assert "outside" in str(error)
else:
    raise AssertionError("implausible Census year should fail")

print("NASS irrigation practice screen tests passed")
