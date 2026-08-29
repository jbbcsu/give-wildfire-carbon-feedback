#!/usr/bin/env python3
"""Synthetic checks for the nClimGrid county-area-average source preflight."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from audit_nclimgrid_county_average_sample import VARIABLES, audit


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    crosswalk = root / "crosswalk.csv"
    crosswalk.write_text("state_name,postal_code,NCEI_code,FIPS_code\nKentucky,KY,15,21\n", encoding="utf-8")
    version = root / "version.txt"
    version.write_text("synthetic complete\n", encoding="utf-8")
    paths = {}
    values = {
        "PRCP": [1.0] * 31,
        "TMIN": [0.0] * 31,
        "TMAX": [2.0] * 31,
        "TAVG": [1.0] * 31,
    }
    for variable in VARIABLES:
        path = root / f"{variable}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(["cty", "15221", "KY: Trigg County", "1981", "01", variable, *values[variable]])
        paths[variable] = path
    result = audit(paths, version, crosswalk, "21221")
    assert result["target_ncei_county_code"] == "15221"
    assert result["target_precipitation_sum_mm"] == 31.0
    bad = root / "bad.csv"
    bad.write_text(paths["TAVG"].read_text(encoding="utf-8").replace(",1.0,", ",9.0,", 1), encoding="utf-8")
    bad_paths = dict(paths)
    bad_paths["TAVG"] = bad
    try:
        audit(bad_paths, version, crosswalk, "21221")
    except ValueError:
        pass
    else:
        raise AssertionError("temperature midpoint failure passed")

print("nClimGrid county-area-average source tests passed")
