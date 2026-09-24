#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_maize_weather import (
    _single_sine_degree_days_above,
    build_maize_weather_basis,
    build_maize_weather_basis_from_daily,
    single_sine_degree_days_above_array,
)


def daily(
    start: date,
    end: date,
    rainfall: float = 1.0,
    tmin: float = 20.0,
    tmax: float = 20.0,
):
    value = start
    while value <= end:
        yield value, rainfall, tmin, tmax
        value += timedelta(days=1)


def main() -> None:
    tmin = np.array([-5.0, 8.0, 10.0, 15.0, 31.0, 33.0])
    tmax = np.array([5.0, 8.0, 20.0, 35.0, 31.0, 40.0])
    for threshold in (8.0, 31.0):
        expected = np.array([
            _single_sine_degree_days_above(float(lo), float(hi), threshold)
            for lo, hi in zip(tmin, tmax, strict=True)
        ])
        actual = single_sine_degree_days_above_array(tmin, tmax, threshold)
        assert np.allclose(actual, expected, rtol=0.0, atol=1e-12)

    temperatures = [5, 8, 20, 31, 35]
    basis = build_maize_weather_basis([1, 2, 3, 4, 5, 6], temperatures, temperatures)
    assert basis.prcp_poly_1_bins == (1.0, 9.0, 11.0)
    assert basis.prcp_poly_2_bins == (1.0, 29.0, 61.0)
    assert basis.gdd == 58.0
    assert basis.kdd == 4.0
    response_basis = basis.with_moderators(
        ln_gdppc=9.0,
        irrigated_share=0.25,
        lr_tmax_crop=24.0,
        lr_prcp_crop=300.0,
    )
    assert response_basis.prcp_poly_2_bins == (1.0, 29.0, 61.0)
    assert response_basis.primitive_values()["pbarcut_prcp"] == 250.0
    try:
        basis.with_moderators(
            ln_gdppc=9.0,
            irrigated_share=1.1,
            lr_tmax_crop=24.0,
            lr_prcp_crop=300.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid moderator combination accepted")
    for rainfall in ([1, 2, 3], [1] * 11, [1, 2, 3, -1]):
        try:
            build_maize_weather_basis(rainfall, [20], [20])
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid rainfall accepted: {rainfall}")

    same_year = build_maize_weather_basis_from_daily(
        daily(date(2000, 1, 1), date(2000, 12, 31)),
        report_year=2000,
        plant_month=5,
        harvest_month=10,
        iso="USA",
    )
    assert same_year.prcp_poly_1_bins == (31.0, 92.0, 61.0)
    assert same_year.prcp_poly_2_bins == (31.0**2, 30.0**2 + 31.0**2 + 31.0**2, 30.0**2 + 31.0**2)
    assert same_year.gdd == 184 * 12.0
    assert same_year.kdd == 0.0

    cross_year = build_maize_weather_basis_from_daily(
        daily(date(1999, 10, 1), date(2000, 3, 31)),
        report_year=2000,
        plant_month=10,
        harvest_month=3,
        iso="USA",
    )
    assert cross_year.prcp_poly_1_bins == (31.0, 92.0, 60.0)

    india = build_maize_weather_basis_from_daily(
        daily(date(2000, 10, 1), date(2001, 3, 31)),
        report_year=2000,
        plant_month=10,
        harvest_month=3,
        iso="IND",
    )
    assert india.prcp_poly_1_bins == (31.0, 92.0, 59.0)
    assert india.gdd == 182 * 12.0

    try:
        build_maize_weather_basis_from_daily(
            daily(date(2000, 5, 2), date(2000, 10, 31)),
            report_year=2000,
            plant_month=5,
            harvest_month=10,
            iso="USA",
        )
    except ValueError as error:
        assert "missing day" in str(error)
    else:
        raise AssertionError("incomplete daily weather accepted")
    print("published maize primitive-weather basis tests passed")


if __name__ == "__main__":
    main()
