#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_rice_weather import (
    build_rice_weather_basis,
    build_rice_weather_basis_from_daily,
)


def daily(start: date, end: date, rainfall=1.0, tmin=20.0, tmax=20.0):
    value = start
    while value <= end:
        yield value, rainfall, tmin, tmax
        value += timedelta(days=1)


def expect_failure(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except (TypeError, ValueError):
        return
    raise AssertionError("invalid rice weather input was accepted")


def main() -> None:
    basis = build_rice_weather_basis(
        [1, 2, 3, 4, 5, 6],
        [10, 11, 12, 13, 14, 15],
        [20, 31, 35],
        [20, 31, 35],
    )
    assert basis.prcp_poly_1_bins == (3.0, 12.0, 6.0)
    assert basis.prcp_poly_2_bins == (5.0, 50.0, 36.0)
    assert basis.tmin == 75.0
    assert basis.gdd == 38.0
    assert basis.kdd == 6.0
    moderated = basis.with_moderators(
        ln_gdppc=9.0,
        irrigated_share=0.4,
        lr_tmax_crop=25.0,
        lr_prcp_crop=400.0,
    )
    primitives = moderated.primitive_values()
    assert primitives["pbarcut_gdd"] == 200.0
    assert primitives["pbarcut_kdd"] == 300.0
    assert primitives["pbarcut_prcp"] == 250.0
    assert primitives["pbarcut_tmin"] == 175.0

    same_year = build_rice_weather_basis_from_daily(
        daily(date(2000, 5, 1), date(2000, 10, 31)),
        report_year=2000,
        plant_month=5,
        harvest_month=10,
        iso="USA",
    )
    assert same_year.prcp_poly_1_bins == (61.0, 92.0, 31.0)
    assert same_year.prcp_poly_2_bins == (
        31.0**2 + 30.0**2,
        31.0**2 + 31.0**2 + 30.0**2,
        31.0**2,
    )
    assert same_year.tmin == 120.0
    assert same_year.gdd == 184 * 6.0
    assert same_year.kdd == 0.0

    cross_year = build_rice_weather_basis_from_daily(
        daily(date(1999, 10, 1), date(2000, 3, 31)),
        report_year=2000,
        plant_month=10,
        harvest_month=3,
        iso="USA",
    )
    assert cross_year.prcp_poly_1_bins == (61.0, 91.0, 31.0)
    assert cross_year.tmin == 120.0

    expect_failure(build_rice_weather_basis, [1] * 5, [20] * 5, [20], [20])
    expect_failure(build_rice_weather_basis, [1] * 13, [20] * 13, [20], [20])
    expect_failure(build_rice_weather_basis, [1] * 6, [20] * 5, [20], [20])
    expect_failure(build_rice_weather_basis, [1, 1, 1, 1, 1, -1], [20] * 6, [20], [20])
    expect_failure(build_rice_weather_basis, [1] * 6, [20] * 6, [21], [20])
    expect_failure(
        build_rice_weather_basis_from_daily,
        daily(date(2000, 5, 2), date(2000, 10, 31)),
        report_year=2000,
        plant_month=5,
        harvest_month=10,
        iso="USA",
    )
    print("published rice primitive-weather basis tests passed")


if __name__ == "__main__":
    main()
