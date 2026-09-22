#!/usr/bin/env python3
"""Deterministic tests for the all-cropland Census discovery contract."""
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("download_nass_cropland_irrigation_classifier.py")
SPEC = importlib.util.spec_from_file_location("cropland_classifier", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load classifier downloader")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

parameters = MODULE.discovery_parameters(1997)
assert parameters == {
    "source_desc": "CENSUS",
    "sector_desc": "ECONOMICS",
    "group_desc": "FARMS & LAND & ASSETS",
    "commodity_desc": "AG LAND",
    "class_desc": "CROPLAND, HARVESTED",
    "statisticcat_desc": "AREA",
    "domain_desc": "TOTAL",
    "agg_level_desc": "COUNTY",
    "freq_desc": "ANNUAL",
    "reference_period_desc": "YEAR",
    "year": "1997",
    "format": "JSON",
}

for invalid in (1992, 2017, 2022):
    try:
        MODULE.discovery_parameters(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(f"accepted invalid classifier year {invalid}")

print("all-cropland Census discovery contract tests passed")
