#!/usr/bin/env python3
"""Audit MapSPAM production support against FAOSTAT national crop values.

This is a coverage gate, not a weight builder.  It matches only MapSPAM
``stat_code`` values that are exact current ISO-alpha3 codes in the official UN
M49 table.  Four-character and historical/noncurrent codes are not guessed,
renamed, spatially inferred, or renormalized away.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path


BASELINE_YEARS = {1999, 2000, 2001}
FAOSTAT_CONSTANT_USD = "gross_production_value_constant_20142016_1000_us_usd"
CROPS = {
    "maize": {"mapspam": "maize_total_mt", "faostat_item": 56},
    "soybean": {"mapspam": "soybean_total_mt", "faostat_item": 236},
}


class EnglishCountryTableParser(HTMLParser):
    """Read the first table inside the official ``ENG_COUNTRIES`` div."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.div_depth = 0
        self.in_english = False
        self.finished = False
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "div":
            if not self.in_english and attributes.get("id") == "ENG_COUNTRIES":
                self.in_english = True
                self.div_depth = 1
            elif self.in_english:
                self.div_depth += 1
        elif self.in_english and tag == "table" and not self.finished:
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.row = []
        elif self.in_row and tag in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.in_cell and tag in {"td", "th"}:
            self.row.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell = False
        elif self.in_row and tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.in_row = False
        elif self.in_table and tag == "table":
            self.in_table = False
            self.finished = True
        elif self.in_english and tag == "div":
            self.div_depth -= 1
            if self.div_depth == 0:
                self.in_english = False


def parse_unsd_m49(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    parser = EnglishCountryTableParser()
    parser.feed(path.read_text(encoding="utf-8"))
    if not parser.rows or parser.rows[0] != [
        "Country or Area",
        "M49 code",
        "ISO-alpha3 code",
    ]:
        raise ValueError("UNSD English country table header differs")
    iso_to_m49: dict[str, str] = {}
    m49_to_iso: dict[str, str] = {}
    for row_number, row in enumerate(parser.rows[1:], start=2):
        if len(row) != 3:
            raise ValueError(f"UNSD M49 row {row_number} has {len(row)} cells")
        _, m49, iso3 = row
        if len(m49) != 3 or not m49.isdigit():
            raise ValueError(f"Invalid UNSD M49 code at row {row_number}: {m49!r}")
        if len(iso3) != 3 or not iso3.isalpha() or not iso3.isupper():
            raise ValueError(f"Invalid UNSD ISO3 code at row {row_number}: {iso3!r}")
        if iso3 in iso_to_m49 or m49 in m49_to_iso:
            raise ValueError("Duplicate UNSD M49/ISO3 code")
        iso_to_m49[iso3] = m49
        m49_to_iso[m49] = iso3
    if len(iso_to_m49) < 200:
        raise ValueError(f"UNSD M49 table unexpectedly short: {len(iso_to_m49)}")
    return iso_to_m49, m49_to_iso


def read_faostat_baseline(path: Path) -> dict[tuple[int, str], dict[str, object]]:
    values: dict[tuple[int, str], list[tuple[int, float, str]]] = defaultdict(list)
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"item_code", "m49_code", "year", FAOSTAT_CONSTANT_USD, FAOSTAT_CONSTANT_USD + "_flag"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("FAOSTAT table lacks crosswalk-audit columns")
        for row_number, row in enumerate(reader, start=2):
            year = int(row["year"])
            if year not in BASELINE_YEARS or row[FAOSTAT_CONSTANT_USD] == "":
                continue
            item_code = int(row["item_code"])
            if item_code not in {definition["faostat_item"] for definition in CROPS.values()}:
                continue
            value = float(row[FAOSTAT_CONSTANT_USD])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid FAOSTAT constant-USD value at row {row_number}")
            m49 = row["m49_code"].zfill(3)
            values[(item_code, m49)].append(
                (year, value, row[FAOSTAT_CONSTANT_USD + "_flag"])
            )
    result: dict[tuple[int, str], dict[str, object]] = {}
    for key, observations in values.items():
        years = [year for year, _, _ in observations]
        if len(years) != len(set(years)):
            raise ValueError(f"Duplicate FAOSTAT baseline year for {key}")
        result[key] = {
            "mean_constant_2014_2016_thousand_usd": sum(value for _, value, _ in observations)
            / len(observations),
            "years": sorted(years),
            "flags": sorted({flag for _, _, flag in observations}),
        }
    return result


def audit(
    mapspam_path: Path,
    faostat_path: Path,
    unsd_html_path: Path,
) -> dict[str, object]:
    iso_to_m49, _ = parse_unsd_m49(unsd_html_path)
    faostat = read_faostat_baseline(faostat_path)
    production: dict[str, dict[str, float]] = {
        crop: defaultdict(float) for crop in CROPS
    }
    rows = 0
    with mapspam_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"stat_code", *(definition["mapspam"] for definition in CROPS.values())}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("MapSPAM selected table lacks crosswalk-audit columns")
        for row_number, row in enumerate(reader, start=2):
            rows += 1
            stat_code = row["stat_code"]
            for crop, definition in CROPS.items():
                value = float(row[str(definition["mapspam"])])
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"Invalid MapSPAM production at row {row_number}")
                production[crop][stat_code] += value
    if rows == 0:
        raise ValueError("MapSPAM selected table is empty")

    crop_audits: dict[str, object] = {}
    for crop, definition in CROPS.items():
        total = sum(production[crop].values())
        if total <= 0:
            raise ValueError(f"No positive MapSPAM production for {crop}")
        buckets: dict[str, dict[str, object]] = {
            "matched_faostat_value": {"production_mt": 0.0, "stat_codes": []},
            "current_iso3_without_faostat_baseline_value": {"production_mt": 0.0, "stat_codes": []},
            "not_current_iso3": {"production_mt": 0.0, "stat_codes": []},
        }
        for stat_code, value in sorted(production[crop].items()):
            if value <= 0:
                continue
            if stat_code not in iso_to_m49:
                bucket = "not_current_iso3"
            else:
                key = (int(definition["faostat_item"]), iso_to_m49[stat_code])
                bucket = (
                    "matched_faostat_value"
                    if key in faostat
                    else "current_iso3_without_faostat_baseline_value"
                )
            buckets[bucket]["production_mt"] = float(buckets[bucket]["production_mt"]) + value
            cast_codes = buckets[bucket]["stat_codes"]
            assert isinstance(cast_codes, list)
            cast_codes.append(stat_code)
        for bucket in buckets.values():
            bucket["production_share"] = float(bucket["production_mt"]) / total
            codes = bucket["stat_codes"]
            assert isinstance(codes, list)
            bucket["positive_stat_code_count"] = len(codes)
        crop_audits[crop] = {
            "mapspam_total_production_mt": total,
            "mapspam_positive_stat_code_count": sum(value > 0 for value in production[crop].values()),
            "buckets": buckets,
        }
    return {
        "mapspam_selected_rows": rows,
        "unsd_current_country_area_codes": len(iso_to_m49),
        "faostat_baseline_country_crop_records": len(faostat),
        "baseline_years": sorted(BASELINE_YEARS),
        "faostat_value_field": FAOSTAT_CONSTANT_USD,
        "crops": crop_audits,
        "gate": {
            "spatial_value_weights_authorized": False,
            "reason": "non-ISO MapSPAM stat_codes and missing national baseline values remain unmatched; no renormalization or inferred code mapping is permitted",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mapspam",
        default="data/interim/welfare_weights/mapspam2000_maize_soy_production.csv",
    )
    parser.add_argument(
        "--faostat",
        default="data/interim/welfare_weights/faostat_qv_maize_soy.csv",
    )
    parser.add_argument(
        "--unsd-html",
        default="data/raw/unsd_m49/countries_retrieved_2026-08-26.html",
    )
    parser.add_argument(
        "--out",
        default="data/interim/welfare_weights/mapspam_faostat_crosswalk.audit.json",
    )
    args = parser.parse_args()
    result = audit(Path(args.mapspam), Path(args.faostat), Path(args.unsd_html))
    result.update(
        {
            "schema_version": 1,
            "audited_utc": datetime.now(UTC).isoformat(),
            "unsd_source": "https://unstats.un.org/unsd/methodology/m49/",
            "mapspam_source": "https://doi.org/10.7910/DVN/A50I2T",
            "faostat_source": "https://data.fao.org/catalog/dataset/b1a04191-c86f-4972-a9d7-28b23568deba",
        }
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
