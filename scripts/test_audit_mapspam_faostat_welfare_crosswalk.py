#!/usr/bin/env python3
"""Synthetic coverage tests for the MapSPAM--FAOSTAT crosswalk gate."""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_mapspam_faostat_welfare_crosswalk",
    PROJECT / "scripts" / "audit_mapspam_faostat_welfare_crosswalk.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

HTML = """
<div id="ENG_COUNTRIES"><table>
<tr><th>Country or Area</th><th>M49 code</th><th>ISO-alpha3 code</th></tr>
<tr><td>United States of America</td><td>840</td><td>USA</td></tr>
<tr><td>Brazil</td><td>076</td><td>BRA</td></tr>
""" + "".join(
    f"<tr><td>Fixture {i}</td><td>{i:03d}</td><td>{chr(65 + i // 676)}{chr(65 + (i // 26) % 26)}{chr(65 + i % 26)}</td></tr>"
    for i in range(200)
    if i not in {76}
) + "</table></div>"

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    html = root / "m49.html"
    html.write_text(HTML, encoding="utf-8")
    iso_to_m49, _ = MODULE.parse_unsd_m49(html)
    assert iso_to_m49["USA"] == "840" and iso_to_m49["BRA"] == "076"

    mapspam = root / "mapspam.csv"
    with mapspam.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["stat_code", "maize_total_mt", "soybean_total_mt"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            [
                {"stat_code": "USA", "maize_total_mt": "80", "soybean_total_mt": "40"},
                {"stat_code": "BRA", "maize_total_mt": "10", "soybean_total_mt": "50"},
                {"stat_code": "KE01", "maize_total_mt": "10", "soybean_total_mt": "10"},
            ]
        )

    faostat = root / "faostat.csv"
    fields = [
        "item_code",
        "m49_code",
        "year",
        MODULE.FAOSTAT_CONSTANT_USD,
        MODULE.FAOSTAT_CONSTANT_USD + "_flag",
    ]
    with faostat.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            [
                {"item_code": "56", "m49_code": "840", "year": str(year), MODULE.FAOSTAT_CONSTANT_USD: "100", MODULE.FAOSTAT_CONSTANT_USD + "_flag": "Estimated value"}
                for year in (1999, 2000, 2001)
            ]
            + [
                {"item_code": "236", "m49_code": "76", "year": "2000", MODULE.FAOSTAT_CONSTANT_USD: "200", MODULE.FAOSTAT_CONSTANT_USD + "_flag": "Estimated value"}
            ]
        )
    result = MODULE.audit(mapspam, faostat, html)
    maize = result["crops"]["maize"]["buckets"]
    assert abs(maize["matched_faostat_value"]["production_share"] - 0.8) < 1e-12
    assert abs(maize["current_iso3_without_faostat_baseline_value"]["production_share"] - 0.1) < 1e-12
    assert abs(maize["not_current_iso3"]["production_share"] - 0.1) < 1e-12
    soy = result["crops"]["soybean"]["buckets"]
    assert abs(soy["matched_faostat_value"]["production_share"] - 0.5) < 1e-12
    assert result["gate"]["spatial_value_weights_authorized"] is False

print("MapSPAM--FAOSTAT crosswalk audit tests passed")
