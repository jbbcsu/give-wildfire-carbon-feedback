#!/usr/bin/env python3
"""Synthetic tests for the fail-closed NASS irrigation coverage audit."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_nass_irrigation_practice_coverage.py")
spec = importlib.util.spec_from_file_location("nass_irrigation_audit", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(
    *, commodity: str, practice: str, value: str, county: str,
    statistic: str = "YIELD", source: str = "SURVEY", year: int = 2020,
) -> dict[str, object]:
    util = "GRAIN" if commodity == "CORN" else "ALL UTILIZATION PRACTICES"
    unit = "BU / ACRE" if statistic == "YIELD" else "ACRES"
    return {
        "source_desc": source,
        "sector_desc": "CROPS",
        "commodity_desc": commodity,
        "class_desc": "ALL CLASSES",
        "statisticcat_desc": statistic,
        "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL",
        "domaincat_desc": "NOT SPECIFIED",
        "prodn_practice_desc": practice,
        "util_practice_desc": util,
        "unit_desc": unit,
        "year": year,
        "state_ansi": "01",
        "county_ansi": county,
        "state_alpha": "AL",
        "state_name": "ALABAMA",
        "county_name": f"COUNTY {county}",
        "Value": value,
    }


def write(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"data": rows}), encoding="utf-8")
    return path


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    yield_paths = []
    area_paths = []
    for commodity in ("CORN", "SOYBEANS", "WHEAT"):
        yield_paths.append(write(root / f"{commodity}_ir.json", [
            row(commodity=commodity, practice="IRRIGATED", value="100", county="001"),
            row(commodity=commodity, practice="IRRIGATED", value="(D)", county="003"),
        ]))
        yield_paths.append(write(root / f"{commodity}_rf.json", [
            row(commodity=commodity, practice="NON-IRRIGATED", value="80", county="001"),
            row(commodity=commodity, practice="NON-IRRIGATED", value="70", county="003"),
        ]))
        area_paths.append(write(root / f"{commodity}_area.json", [
            row(
                commodity=commodity, practice="ALL PRODUCTION PRACTICES", value="1,000",
                county="001", statistic="AREA HARVESTED", source="CENSUS", year=2022,
            ),
            row(
                commodity=commodity, practice="IRRIGATED", value="100", county="001",
                statistic="AREA HARVESTED", source="CENSUS", year=2022,
            ),
            row(
                commodity=commodity, practice="ALL PRODUCTION PRACTICES", value="500",
                county="003", statistic="AREA HARVESTED", source="CENSUS", year=2022,
            ),
            row(
                commodity=commodity, practice="IRRIGATED", value="(D)", county="003",
                statistic="AREA HARVESTED", source="CENSUS", year=2022,
            ),
        ]))

    shares, audit = module.run(yield_paths, area_paths)
    assert set(audit["direct_practice_yields"]) == {"corn", "soybeans", "wheat"}
    assert audit["direct_practice_yields"]["corn"]["reported_paired_county_years"] == 1
    assert audit["census_irrigation_share_fallback"]["corn"]["share_eligible_counties"] == 1
    assert "2022 Census shares" in audit["use_boundary"]
    assert audit["census_irrigation_share_fallback"]["corn"]["interpretation"].startswith(
        "fixed 2022"
    )
    corn = shares.loc[shares["crop"] == "corn"].set_index("county_geoid")
    assert abs(float(corn.loc["01001", "irrigation_share"]) - 0.1) < 1e-12
    assert bool(corn.loc["01001", "share_eligible"])
    assert not bool(corn.loc["01003", "share_eligible"])
    assert "not_assumed_zero" in corn.loc["01003", "exclusion_reason"]

    invalid = write(root / "invalid_area.json", [
        row(
            commodity="CORN", practice="ALL PRODUCTION PRACTICES", value="100", county="001",
            statistic="AREA HARVESTED", source="CENSUS", year=2022,
        ),
        row(
            commodity="CORN", practice="IRRIGATED", value="101", county="001",
            statistic="AREA HARVESTED", source="CENSUS", year=2022,
        ),
    ])
    try:
        module.audit_areas([invalid])
    except ValueError as error:
        assert "outside [0,1]" in str(error)
    else:
        raise AssertionError("irrigated area above total should fail")

print("NASS irrigation practice coverage audit tests passed")
