#!/usr/bin/env python3
"""Audit MapSPAM ``stat_code`` values against official GEC/GENC codes.

This is a country-code and welfare-coverage diagnostic, not a weight builder.
It uses the National Geospatial-Intelligence Agency's official GENC-to-GEC
crosswalk to resolve the country prefix of legacy FIPS/GEC ``AAXX`` codes.
Every mapping is checked against the current UN M49 ISO-alpha3 table and the
MapSPAM ``admin2_fips`` prefix.  Missing national values are retained, and the
result never authorizes a welfare weight or an SCC calculation.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from audit_mapspam_faostat_welfare_crosswalk import (
    CROPS,
    parse_unsd_m49,
    read_faostat_baseline,
)


SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELATIONSHIP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_RELATIONSHIP_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
FOUR_CHARACTER_GEC = re.compile(r"^[A-Z]{2}[0-9]{2}$")
THREE_CHARACTER_CODE = re.compile(r"^[A-Z]{3}$")


def _column(cell_reference: str) -> str:
    match = re.match(r"^[A-Z]+", cell_reference)
    if match is None:
        raise ValueError(f"Invalid XLSX cell reference: {cell_reference!r}")
    return match.group(0)


def _sheet_rows(archive: ZipFile, sheet_path: str, shared: list[str]) -> list[dict[str, str]]:
    namespace = {"m": SPREADSHEET_NS}
    root = ET.fromstring(archive.read(sheet_path))
    rows: list[dict[str, str]] = []
    for row in root.findall(".//m:sheetData/m:row", namespace):
        values: dict[str, str] = {}
        for cell in row.findall("m:c", namespace):
            reference = cell.get("r")
            if reference is None:
                raise ValueError("NGA workbook contains a cell without a reference")
            cell_type = cell.get("t")
            if cell_type == "inlineStr":
                value = "".join(
                    part.text or ""
                    for part in cell.findall(".//m:t", namespace)
                )
            else:
                element = cell.find("m:v", namespace)
                value = "" if element is None or element.text is None else element.text
                if cell_type == "s" and value:
                    try:
                        value = shared[int(value)]
                    except (IndexError, ValueError) as error:
                        raise ValueError("NGA workbook has an invalid shared-string index") from error
            values[_column(reference)] = value.strip()
        rows.append(values)
    return rows


def parse_nga_genc_gec(path: Path) -> dict[str, object]:
    """Parse the official NGA GENC/GEC crosswalk without an XLSX dependency."""
    if not path.is_file():
        raise ValueError(f"Missing NGA GENC/GEC workbook: {path}")
    spreadsheet_namespace = {"m": SPREADSHEET_NS, "r": RELATIONSHIP_NS}
    package_namespace = {"p": PACKAGE_RELATIONSHIP_NS}
    with ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/sharedStrings.xml",
        }
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"NGA workbook lacks required members: {missing}")

        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = [
            "".join(
                part.text or ""
                for part in item.iter(f"{{{SPREADSHEET_NS}}}t")
            )
            for item in shared_root.findall("m:si", {"m": SPREADSHEET_NS})
        ]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            relation.get("Id"): relation.get("Target")
            for relation in relationships.findall("p:Relationship", package_namespace)
        }
        sheet_paths: dict[str, str] = {}
        sheets = workbook.find("m:sheets", spreadsheet_namespace)
        if sheets is None:
            raise ValueError("NGA workbook has no sheets")
        for sheet in sheets:
            name = sheet.get("name")
            relation_id = sheet.get(f"{{{RELATIONSHIP_NS}}}id")
            target = targets.get(relation_id)
            if name is None or target is None:
                raise ValueError("NGA workbook has an unresolved sheet relationship")
            sheet_paths[name] = "xl/" + target.lstrip("/")

        expected_sheets = {"Codes_for_GE_Names", "Codes_for_AS_Names"}
        if not expected_sheets.issubset(sheet_paths):
            raise ValueError(f"NGA workbook sheet names differ: {sorted(sheet_paths)}")
        entity_rows = _sheet_rows(
            archive, sheet_paths["Codes_for_GE_Names"], shared
        )
        subdivision_rows = _sheet_rows(
            archive, sheet_paths["Codes_for_AS_Names"], shared
        )

    if len(entity_rows) < 4 or len(subdivision_rows) < 4:
        raise ValueError("NGA workbook tables are unexpectedly short")
    if entity_rows[2].get("A") != "3-character Code" or entity_rows[2].get("H") != "GEC":
        raise ValueError("NGA geopolitical-entity table header differs")
    if subdivision_rows[2].get("B") != "6-character Code" or subdivision_rows[2].get("F") != "GEC":
        raise ValueError("NGA administrative-subdivision table header differs")

    gec_to_genc: dict[str, str] = {}
    for row in entity_rows[3:]:
        gec = row.get("H", "")
        genc = row.get("A", "")
        if not gec or not genc:
            continue
        if set(gec) == {"-"}:
            # NGA uses ``--`` when a GENC entity has no former GEC code.
            continue
        if not re.fullmatch(r"[A-Z]{2}", gec) or not THREE_CHARACTER_CODE.fullmatch(genc):
            raise ValueError(f"Invalid NGA GEC/GENC entity pair: {gec!r}, {genc!r}")
        if gec in gec_to_genc and gec_to_genc[gec] != genc:
            raise ValueError(f"Conflicting NGA GEC entity mapping for {gec}")
        gec_to_genc[gec] = genc

    gec_admin_codes: set[str] = set()
    for row in subdivision_rows[3:]:
        gec = row.get("F", "")
        if not gec:
            continue
        if set(gec) == {"-"}:
            # NGA uses ``----`` when a current subdivision has no GEC code.
            continue
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{1,2}", gec):
            raise ValueError(f"Invalid NGA GEC subdivision code: {gec!r}")
        if gec in gec_admin_codes:
            raise ValueError(f"Duplicate NGA GEC subdivision code: {gec}")
        gec_admin_codes.add(gec)

    return {
        "entity_title": entity_rows[0].get("A", ""),
        "subdivision_title": subdivision_rows[0].get("A", ""),
        "gec_to_genc": gec_to_genc,
        "gec_admin_codes": gec_admin_codes,
    }


def _add(bucket: dict[str, object], value: float, stat_code: str) -> None:
    bucket["production_mt"] = float(bucket["production_mt"]) + value
    codes = bucket["stat_codes"]
    assert isinstance(codes, set)
    codes.add(stat_code)


def audit(
    mapspam_path: Path,
    faostat_path: Path,
    unsd_html_path: Path,
    nga_xlsx_path: Path,
    minimum_nga_entity_mappings: int = 200,
) -> dict[str, object]:
    nga = parse_nga_genc_gec(nga_xlsx_path)
    gec_to_genc = nga["gec_to_genc"]
    gec_admin_codes = nga["gec_admin_codes"]
    assert isinstance(gec_to_genc, dict) and isinstance(gec_admin_codes, set)
    if len(gec_to_genc) < minimum_nga_entity_mappings:
        raise ValueError(
            f"NGA GEC entity crosswalk unexpectedly short: {len(gec_to_genc)}"
        )
    iso_to_m49, _ = parse_unsd_m49(unsd_html_path)
    faostat = read_faostat_baseline(faostat_path)

    rows = 0
    direct_three_character_rows = 0
    direct_prefix_crosscheck_rows = 0
    direct_prefix_unavailable_rows = 0
    four_character_rows = 0
    four_character_exact_admin_rows = 0
    genc_non_unsd_rows = 0
    unresolved_rows = 0
    per_code: dict[str, dict[str, object]] = {}
    production: dict[str, dict[str, float]] = {
        crop: defaultdict(float) for crop in CROPS
    }

    with mapspam_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "stat_code",
            "admin2_fips",
            *(definition["mapspam"] for definition in CROPS.values()),
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("MapSPAM selected table lacks GEC-audit columns")
        for row_number, row in enumerate(reader, start=2):
            rows += 1
            stat_code = row["stat_code"]
            admin2_fips = row["admin2_fips"]
            if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]+", admin2_fips):
                raise ValueError(f"Invalid MapSPAM admin2_fips at row {row_number}")
            prefix = admin2_fips[:2]
            exact_admin = False
            if FOUR_CHARACTER_GEC.fullmatch(stat_code):
                four_character_rows += 1
                if stat_code[:2] != prefix:
                    raise ValueError(
                        f"MapSPAM stat_code/admin2_fips prefix mismatch at row {row_number}"
                    )
                resolved = gec_to_genc.get(prefix)
                if resolved is None or resolved not in iso_to_m49:
                    raise ValueError(
                        f"Four-character MapSPAM code lacks a current UN country mapping at row {row_number}"
                    )
                exact_admin = stat_code in gec_admin_codes
                four_character_exact_admin_rows += int(exact_admin)
                resolution = (
                    "gec_admin1_exact_current_nga"
                    if exact_admin
                    else "gec_country_prefix_nga_legacy_admin1"
                )
            elif THREE_CHARACTER_CODE.fullmatch(stat_code) and stat_code in iso_to_m49:
                direct_three_character_rows += 1
                resolved = stat_code
                if prefix in gec_to_genc:
                    direct_prefix_crosscheck_rows += 1
                    if gec_to_genc[prefix] != stat_code:
                        raise ValueError(
                            f"Direct MapSPAM ISO3 disagrees with NGA GEC prefix at row {row_number}"
                        )
                else:
                    direct_prefix_unavailable_rows += 1
                resolution = "direct_current_unsd_iso3"
            elif THREE_CHARACTER_CODE.fullmatch(stat_code) and gec_to_genc.get(prefix) == stat_code:
                resolved = stat_code
                genc_non_unsd_rows += 1
                resolution = "genc_three_character_not_current_unsd"
            else:
                resolved = None
                unresolved_rows += 1
                resolution = "unresolved"

            detail = per_code.setdefault(
                stat_code,
                {
                    "stat_code": stat_code,
                    "admin2_fips_prefix": prefix,
                    "resolved_iso3": resolved,
                    "resolution": resolution,
                    "nga_current_admin1_exact": exact_admin,
                    "row_count": 0,
                    **{f"{crop}_production_mt": 0.0 for crop in CROPS},
                },
            )
            if (
                detail["admin2_fips_prefix"] != prefix
                or detail["resolved_iso3"] != resolved
                or detail["resolution"] != resolution
            ):
                raise ValueError(f"Inconsistent resolution for MapSPAM stat_code {stat_code}")
            detail["row_count"] = int(detail["row_count"]) + 1
            for crop, definition in CROPS.items():
                try:
                    value = float(row[str(definition["mapspam"])])
                except ValueError as error:
                    raise ValueError(f"Invalid MapSPAM production at row {row_number}") from error
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"Invalid MapSPAM production at row {row_number}")
                production[crop][stat_code] += value
                key = f"{crop}_production_mt"
                detail[key] = float(detail[key]) + value
    if rows == 0:
        raise ValueError("MapSPAM selected table is empty")

    crop_audits: dict[str, object] = {}
    for crop, definition in CROPS.items():
        total = sum(production[crop].values())
        if total <= 0:
            raise ValueError(f"No positive MapSPAM production for {crop}")
        buckets: dict[str, dict[str, object]] = {
            name: {"production_mt": 0.0, "stat_codes": set()}
            for name in (
                "direct_current_iso3_with_value",
                "direct_current_iso3_without_value",
                "gec_admin1_mapped_with_value",
                "gec_admin1_mapped_without_value",
                "genc_not_current_unsd",
                "unresolved",
            )
        }
        for stat_code, value in production[crop].items():
            if value <= 0:
                continue
            detail = per_code[stat_code]
            resolution = str(detail["resolution"])
            resolved = detail["resolved_iso3"]
            if resolution == "direct_current_unsd_iso3":
                assert isinstance(resolved, str)
                has_value = (
                    int(definition["faostat_item"]), iso_to_m49[resolved]
                ) in faostat
                bucket = (
                    "direct_current_iso3_with_value"
                    if has_value
                    else "direct_current_iso3_without_value"
                )
            elif resolution.startswith("gec_"):
                assert isinstance(resolved, str)
                has_value = (
                    int(definition["faostat_item"]), iso_to_m49[resolved]
                ) in faostat
                bucket = (
                    "gec_admin1_mapped_with_value"
                    if has_value
                    else "gec_admin1_mapped_without_value"
                )
            elif resolution == "genc_three_character_not_current_unsd":
                bucket = "genc_not_current_unsd"
            else:
                bucket = "unresolved"
            _add(buckets[bucket], value, stat_code)

        for bucket in buckets.values():
            bucket["production_share"] = float(bucket["production_mt"]) / total
            codes = bucket["stat_codes"]
            assert isinstance(codes, set)
            bucket["positive_stat_code_count"] = len(codes)
            bucket["stat_codes"] = sorted(codes)
        matched = (
            float(buckets["direct_current_iso3_with_value"]["production_mt"])
            + float(buckets["gec_admin1_mapped_with_value"]["production_mt"])
        )
        crop_audits[crop] = {
            "mapspam_total_production_mt": total,
            "authoritative_country_mapping_plus_faostat_value_share": matched / total,
            "buckets": buckets,
        }

    return {
        "mapspam_selected_rows": rows,
        "nga_entity_title": nga["entity_title"],
        "nga_subdivision_title": nga["subdivision_title"],
        "nga_gec_entity_mappings": len(gec_to_genc),
        "nga_gec_admin1_codes": len(gec_admin_codes),
        "direct_three_character_rows": direct_three_character_rows,
        "direct_rows_with_nga_prefix_crosscheck": direct_prefix_crosscheck_rows,
        "direct_rows_without_nga_prefix_crosscheck": direct_prefix_unavailable_rows,
        "four_character_rows": four_character_rows,
        "four_character_exact_current_nga_admin1_rows": four_character_exact_admin_rows,
        "four_character_legacy_admin1_rows": four_character_rows
        - four_character_exact_admin_rows,
        "four_character_stat_codes": sum(
            FOUR_CHARACTER_GEC.fullmatch(code) is not None for code in per_code
        ),
        "four_character_prefixes": sorted(
            {code[:2] for code in per_code if FOUR_CHARACTER_GEC.fullmatch(code)}
        ),
        "genc_non_unsd_rows": genc_non_unsd_rows,
        "unresolved_rows": unresolved_rows,
        "per_stat_code": [per_code[code] for code in sorted(per_code)],
        "crops": crop_audits,
        "gate": {
            "four_character_country_mapping_resolved": unresolved_rows == 0,
            "spatial_value_weights_authorized": False,
            "reason": (
                "legacy MapSPAM country prefixes are now source-resolved, but some mapped "
                "countries lack baseline value and TWN lacks a current-UN M49 route; no "
                "missing-value rule or weight construction is authorized"
            ),
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
        "--nga-xlsx",
        default="data/raw/nga_genc_gec/GENC_ED3U11_GEC_XWALK.xlsx",
    )
    parser.add_argument(
        "--out",
        default="data/interim/welfare_weights/mapspam_gec_resolution.audit.json",
    )
    args = parser.parse_args()
    result = audit(
        Path(args.mapspam),
        Path(args.faostat),
        Path(args.unsd_html),
        Path(args.nga_xlsx),
    )
    result.update(
        {
            "schema_version": 1,
            "audited_utc": datetime.now(UTC).isoformat(),
            "mapspam_source": "https://doi.org/10.7910/DVN/A50I2T",
            "nga_crosswalk_source": (
                "https://geonames.nga.mil/geonames/GNSSearch/GNSDocs/"
                "pdfdocs/gec/GENC_ED3U11_GEC_XWALK.xlsx"
            ),
            "unsd_source": "https://unstats.un.org/unsd/methodology/m49/",
        }
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
