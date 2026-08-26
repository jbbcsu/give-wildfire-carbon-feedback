#!/usr/bin/env python3
"""Synthetic fail-closed tests for the MapSPAM legacy-GEC audit."""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_mapspam_gec_resolution",
    PROJECT / "scripts" / "audit_mapspam_gec_resolution.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_xlsx(path: Path) -> None:
    strings = [
        "(30 June 2019) GENC Standard Codes for Names of Geopolitical Entities, Edition 3.0, Update 11",
        "3-character Code",
        "GEC",
        "USA",
        "US",
        "KEN",
        "KE",
        "BRA",
        "BR",
        "TWN",
        "TW",
        "(30 June 2019) GENC Standard Codes for Names of Administrative Subdivisions, Edition 3.0, Update 11",
        "6-character Code",
        "KE-100",
        "KE01",
    ]

    def cell(reference: str, index: int) -> str:
        return f'<c r="{reference}" t="s"><v>{index}</v></c>'

    shared = "".join(f"<si><t>{value}</t></si>" for value in strings)
    entity = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        f'<row r="1">{cell("A1", 0)}</row><row r="2"/>'
        f'<row r="3">{cell("A3", 1)}{cell("H3", 2)}</row>'
        f'<row r="4">{cell("A4", 3)}{cell("H4", 4)}</row>'
        f'<row r="5">{cell("A5", 5)}{cell("H5", 6)}</row>'
        f'<row r="6">{cell("A6", 7)}{cell("H6", 8)}</row>'
        f'<row r="7">{cell("A7", 9)}{cell("H7", 10)}</row>'
        "</sheetData></worksheet>"
    )
    subdivision = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        f'<row r="1">{cell("A1", 11)}</row><row r="2"/>'
        f'<row r="3">{cell("B3", 12)}{cell("F3", 2)}</row>'
        f'<row r="4">{cell("B4", 13)}{cell("F4", 14)}</row>'
        "</sheetData></worksheet>"
    )
    workbook = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Codes_for_GE_Names" sheetId="1" r:id="rId1"/>'
        '<sheet name="Codes_for_AS_Names" sheetId="2" r:id="rId2"/></sheets></workbook>'
    )
    relationships = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>'
    )
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr(
            "xl/sharedStrings.xml",
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            + shared
            + "</sst>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", entity)
        archive.writestr("xl/worksheets/sheet2.xml", subdivision)


HTML = (
    '<div id="ENG_COUNTRIES"><table><tr><th>Country or Area</th><th>M49 code</th>'
    '<th>ISO-alpha3 code</th></tr><tr><td>United States</td><td>840</td><td>USA</td></tr>'
    '<tr><td>Kenya</td><td>404</td><td>KEN</td></tr>'
    '<tr><td>Brazil</td><td>076</td><td>BRA</td></tr>'
    + "".join(
        f"<tr><td>Fixture {i}</td><td>{i:03d}</td><td>Q{chr(65 + i // 26)}{chr(65 + i % 26)}</td></tr>"
        for i in range(200)
        if i not in {76}
    )
    + "</table></div>"
)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    xlsx = root / "gec.xlsx"
    write_xlsx(xlsx)
    parsed = MODULE.parse_nga_genc_gec(xlsx)
    assert parsed["gec_to_genc"] == {"US": "USA", "KE": "KEN", "BR": "BRA", "TW": "TWN"}
    assert parsed["gec_admin_codes"] == {"KE01"}

    unsd = root / "m49.html"
    unsd.write_text(HTML, encoding="utf-8")
    mapspam = root / "mapspam.csv"
    fields = ["stat_code", "admin2_fips", "maize_total_mt", "soybean_total_mt"]
    with mapspam.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            [
                {"stat_code": "USA", "admin2_fips": "US01001", "maize_total_mt": "60", "soybean_total_mt": "30"},
                {"stat_code": "KE01", "admin2_fips": "KE01001", "maize_total_mt": "20", "soybean_total_mt": "10"},
                {"stat_code": "KE99", "admin2_fips": "KE99001", "maize_total_mt": "10", "soybean_total_mt": "5"},
                {"stat_code": "BRA", "admin2_fips": "BR01001", "maize_total_mt": "5", "soybean_total_mt": "50"},
                {"stat_code": "TWN", "admin2_fips": "TW01001", "maize_total_mt": "5", "soybean_total_mt": "5"},
            ]
        )
    faostat = root / "faostat.csv"
    value = "gross_production_value_constant_20142016_1000_us_usd"
    with faostat.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["item_code", "m49_code", "year", value, value + "_flag"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            [
                {"item_code": "56", "m49_code": "840", "year": "2000", value: "1", value + "_flag": "E"},
                {"item_code": "56", "m49_code": "404", "year": "2000", value: "1", value + "_flag": "E"},
                {"item_code": "236", "m49_code": "076", "year": "2000", value: "1", value + "_flag": "E"},
            ]
        )
    result = MODULE.audit(mapspam, faostat, unsd, xlsx, minimum_nga_entity_mappings=1)
    assert result["four_character_rows"] == 2
    assert result["four_character_exact_current_nga_admin1_rows"] == 1
    assert result["direct_rows_with_nga_prefix_crosscheck"] == 2
    assert result["genc_non_unsd_rows"] == 1
    assert result["unresolved_rows"] == 0
    assert result["gate"]["four_character_country_mapping_resolved"] is True
    assert result["gate"]["spatial_value_weights_authorized"] is False
    maize = result["crops"]["maize"]["buckets"]
    assert maize["gec_admin1_mapped_with_value"]["production_mt"] == 30
    assert maize["genc_not_current_unsd"]["production_mt"] == 5
    assert abs(result["crops"]["maize"]["authoritative_country_mapping_plus_faostat_value_share"] - 0.9) < 1e-12

    bad = root / "bad.csv"
    with mapspam.open("r", encoding="utf-8", newline="") as source, bad.open(
        "w", encoding="utf-8", newline=""
    ) as target:
        rows = list(csv.DictReader(source))
        rows[1]["admin2_fips"] = "UG01001"
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    try:
        MODULE.audit(bad, faostat, unsd, xlsx, minimum_nga_entity_mappings=1)
    except ValueError as error:
        assert "prefix mismatch" in str(error)
    else:
        raise AssertionError("A conflicting MapSPAM FIPS prefix was accepted")

print("MapSPAM GEC-resolution audit tests passed")
