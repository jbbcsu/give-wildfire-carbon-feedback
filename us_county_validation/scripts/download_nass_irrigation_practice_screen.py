#!/usr/bin/env python3
"""Acquire bounded NASS records for the county irrigation-identification screen.

Two deliberately narrow acquisitions are supported:

* ``yield-practice`` asks for all available SURVEY county yield records in the
  exact IRRIGATED and NON-IRRIGATED production-practice series.  The query has
  no year filter so the returned rows reveal the complete published time
  support, but every other series dimension is locked and each response is
  count-capped before download.
* ``census-area-discovery`` asks for one Census of Agriculture year of county
  AREA HARVESTED records, with crop, unit, and utilization fixed.  Domain and
  production-practice descriptors remain open only so their official values
  can be inspected before a numerator/denominator series is locked.

The API key is read by the existing credential-safe downloader and is never
printed or written.  Raw responses and their manifests belong under ignored
``data/raw/`` paths.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType


HERE = Path(__file__).resolve().parent
BASE_DOWNLOADER = HERE / "download_nass_quickstats_api.py"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SECRETS = ROOT / ".secrets" / "nass.env"
DEFAULT_OUT = ROOT / "data" / "raw" / "us_county" / "nass_api" / "irrigation_practice_screen"

CROP_SERIES = {
    "corn": {
        "commodity_desc": "CORN",
        "util_practice_desc": "GRAIN",
        "yield_unit_desc": "BU / ACRE",
    },
    "soybeans": {
        "commodity_desc": "SOYBEANS",
        "util_practice_desc": "ALL UTILIZATION PRACTICES",
        "yield_unit_desc": "BU / ACRE",
    },
    "wheat": {
        "commodity_desc": "WHEAT",
        "util_practice_desc": "ALL UTILIZATION PRACTICES",
        "yield_unit_desc": "BU / ACRE",
    },
}
PRACTICES = ("IRRIGATED", "NON-IRRIGATED")


def load_base() -> ModuleType:
    spec = importlib.util.spec_from_file_location("nass_quickstats_base", BASE_DOWNLOADER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {BASE_DOWNLOADER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def common_parameters(crop: str) -> dict[str, str]:
    series = CROP_SERIES[crop]
    return {
        "sector_desc": "CROPS",
        "commodity_desc": series["commodity_desc"],
        "class_desc": "ALL CLASSES",
        "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR",
        "util_practice_desc": series["util_practice_desc"],
        "format": "JSON",
    }


def yield_practice_parameters(
    crop: str, practice: str, year: int | None = None
) -> dict[str, str]:
    if practice not in PRACTICES:
        raise ValueError(f"unsupported production practice: {practice}")
    parameters = common_parameters(crop)
    parameters.update({
        "source_desc": "SURVEY",
        "statisticcat_desc": "YIELD",
        "domain_desc": "TOTAL",
        "prodn_practice_desc": practice,
        "unit_desc": CROP_SERIES[crop]["yield_unit_desc"],
    })
    if year is not None:
        if year < 1900 or year > 2100:
            raise ValueError("yield year is outside the supported screening range")
        parameters["year"] = str(year)
    return parameters


def census_area_discovery_parameters(crop: str, census_year: int) -> dict[str, str]:
    if census_year < 1997 or census_year > 2100:
        raise ValueError("Census year is outside the supported screening range")
    parameters = common_parameters(crop)
    parameters.update({
        "source_desc": "CENSUS",
        "statisticcat_desc": "AREA HARVESTED",
        "unit_desc": "ACRES",
        "year": str(census_year),
    })
    return parameters


def acquire(
    *,
    mode: str,
    crops: list[str],
    practices: list[str],
    census_year: int,
    years: list[int],
    secrets_file: Path,
    out_dir: Path,
    count_only: bool,
) -> list[tuple[str, int]]:
    base = load_base()
    key = base.read_key(secrets_file)
    results: list[tuple[str, int]] = []
    queries: list[tuple[str, dict[str, str]]] = []
    if mode == "yield-practice":
        for crop in crops:
            for practice in practices:
                requested_years: list[int | None] = years or [None]
                for year in requested_years:
                    suffix = "all_years" if year is None else str(year)
                    label = (
                        f"survey_{crop}_{practice.lower().replace('-', '_')}_yield_{suffix}"
                    )
                    queries.append((label, yield_practice_parameters(crop, practice, year)))
    elif mode == "census-area-discovery":
        for crop in crops:
            label = f"census_{census_year}_{crop}_area_harvested_discovery"
            queries.append((label, census_area_discovery_parameters(crop, census_year)))
    else:
        raise ValueError(f"unsupported mode: {mode}")

    destination = out_dir / mode.replace("-", "_")
    for label, parameters in queries:
        count = base.count_records(parameters, key)
        results.append((label, count))
        print(f"{label}: preflight count={count}")
        if count_only:
            continue
        if count > base.MAX_API_RECORDS:
            raise RuntimeError(
                f"{label}: refusing {count} records above the API cap {base.MAX_API_RECORDS}"
            )
        if count == 0:
            continue
        response = base.request_json(base.DATA_ENDPOINT, parameters, key)
        raw_path, _ = base.write_result(response, parameters, count, destination, label)
        print(f"{label}: stored {count} records at {raw_path}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", required=True,
        choices=("yield-practice", "census-area-discovery"),
    )
    parser.add_argument(
        "--crop", action="append", choices=tuple(CROP_SERIES),
        help="repeat to limit crops; default is corn, soybeans, and wheat",
    )
    parser.add_argument(
        "--practice", action="append", choices=PRACTICES,
        help="repeat to limit yield practices; default is both (ignored for Census discovery)",
    )
    parser.add_argument("--census-year", type=int, default=2022)
    parser.add_argument(
        "--year", action="append", type=int,
        help="repeat for exact-year yield-practice partitions; default requests all years",
    )
    parser.add_argument("--secrets-file", type=Path, default=DEFAULT_SECRETS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count-only", action="store_true")
    args = parser.parse_args()
    crops = list(dict.fromkeys(args.crop or list(CROP_SERIES)))
    practices = list(dict.fromkeys(args.practice or list(PRACTICES)))
    acquire(
        mode=args.mode,
        crops=crops,
        practices=practices,
        census_year=args.census_year,
        years=sorted(set(args.year or [])),
        secrets_file=args.secrets_file,
        out_dir=args.out_dir,
        count_only=args.count_only,
    )


if __name__ == "__main__":
    main()
