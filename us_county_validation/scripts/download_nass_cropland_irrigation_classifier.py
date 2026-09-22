#!/usr/bin/env python3
"""Acquire bounded Census county records for the Kuwayama irrigation classifier.

The published classifier uses all harvested cropland, not crop-specific area.
This script deliberately downloads one Census year at a time from the official
NASS Quick Stats API and preserves the broad AG LAND discovery response before
any local series selection. The API key stays in the existing ignored secrets
file and is never printed or written to provenance.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
BASE_DOWNLOADER = HERE / "download_nass_quickstats_api.py"
DEFAULT_SECRETS = ROOT / ".secrets" / "nass.env"
DEFAULT_OUT = (
    ROOT / "data" / "raw" / "us_county" / "nass_api"
    / "kuwayama_cropland_classifier"
)


def load_base() -> ModuleType:
    specification = importlib.util.spec_from_file_location(
        "nass_quickstats_base", BASE_DOWNLOADER
    )
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {BASE_DOWNLOADER}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def discovery_parameters(year: int) -> dict[str, str]:
    if year not in {1997, 2002, 2007, 2012}:
        raise ValueError("classifier year must be 1997, 2002, 2007, or 2012")
    return {
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
        "year": str(year),
        "format": "JSON",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--secrets-file", type=Path, default=DEFAULT_SECRETS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count-only", action="store_true")
    arguments = parser.parse_args()

    base = load_base()
    key = base.read_key(arguments.secrets_file)
    parameters = discovery_parameters(arguments.year)
    count = base.count_records(parameters, key)
    print(f"census_{arguments.year}_ag_land_area_discovery: preflight count={count}")
    if arguments.count_only or count == 0:
        return
    if count > base.MAX_API_RECORDS:
        raise RuntimeError(
            f"refusing {count} records above API cap {base.MAX_API_RECORDS}; "
            "freeze a narrower official series query before acquisition"
        )
    response = base.request_json(base.DATA_ENDPOINT, parameters, key)
    raw, _ = base.write_result(
        response,
        parameters,
        count,
        arguments.out_dir,
        f"census_{arguments.year}_ag_land_area_discovery",
    )
    print(f"stored {count} records at {raw}")


if __name__ == "__main__":
    main()
