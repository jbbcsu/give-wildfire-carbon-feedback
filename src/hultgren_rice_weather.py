"""Source-matched primitive weather basis for the published rice response."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Iterable

from .hultgren_crop_calendar import calendar_months_for_report_year
from .hultgren_maize_weather import _single_sine_degree_days_above
from .hultgren_rice_response import RiceBasis


@dataclass(frozen=True)
class RiceWeatherBasis:
    gdd: float
    kdd: float
    prcp_poly_1_bins: tuple[float, float, float]
    prcp_poly_2_bins: tuple[float, float, float]
    tmin: float

    def with_moderators(
        self,
        *,
        ln_gdppc: float,
        irrigated_share: float,
        lr_tmax_crop: float,
        lr_prcp_crop: float,
    ) -> RiceBasis:
        result = RiceBasis(
            gdd=self.gdd,
            kdd=self.kdd,
            prcp_poly_1_bins=self.prcp_poly_1_bins,
            prcp_poly_2_bins=self.prcp_poly_2_bins,
            tmin=self.tmin,
            ln_gdppc=ln_gdppc,
            irrigated_share=irrigated_share,
            lr_tmax_crop=lr_tmax_crop,
            lr_prcp_crop=lr_prcp_crop,
        )
        result.primitive_values()
        return result


def _finite(values: Iterable[float], name: str) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result or not all(isfinite(value) for value in result):
        raise ValueError(f"{name} must contain finite values")
    return result


def build_rice_weather_basis(
    monthly_precipitation_mm: Iterable[float],
    monthly_mean_daily_tmin_c: Iterable[float],
    daily_tmin_c: Iterable[float],
    daily_tmax_c: Iterable[float],
    *,
    gdd_base_c: float = 14.0,
    kdd_threshold_c: float = 30.0,
) -> RiceWeatherBasis:
    """Build the published 2/3/remainder rainfall phases and temperature basis.

    At least six months are required so every published phase is nonempty. The
    source configuration permits at most twelve crop-season months. Monthly
    precipitation is squared before summing within phase; this is not the
    square of a phase total. The Tmin primitive is the sum of monthly mean
    daily minima, matching the source collapse logic.
    """
    precipitation = _finite(monthly_precipitation_mm, "monthly_precipitation_mm")
    monthly_tmin = _finite(monthly_mean_daily_tmin_c, "monthly_mean_daily_tmin_c")
    daily_tmin = _finite(daily_tmin_c, "daily_tmin_c")
    daily_tmax = _finite(daily_tmax_c, "daily_tmax_c")
    if not 6 <= len(precipitation) <= 12:
        raise ValueError("rice crop-calendar season must contain 6 through 12 months")
    if len(monthly_tmin) != len(precipitation):
        raise ValueError("monthly precipitation and Tmin must have identical lengths")
    if any(value < 0.0 for value in precipitation):
        raise ValueError("monthly precipitation cannot be negative")
    if len(daily_tmin) != len(daily_tmax):
        raise ValueError("daily Tmin and Tmax must have identical lengths")
    if any(lo > hi for lo, hi in zip(daily_tmin, daily_tmax, strict=True)):
        raise ValueError("daily Tmin cannot exceed daily Tmax")
    if not gdd_base_c < kdd_threshold_c:
        raise ValueError("gdd_base_c must be below kdd_threshold_c")

    slices = (precipitation[:2], precipitation[2:5], precipitation[5:])
    linear = tuple(sum(values) for values in slices)
    quadratic = tuple(sum(value * value for value in values) for values in slices)
    above_base = sum(
        _single_sine_degree_days_above(lo, hi, gdd_base_c)
        for lo, hi in zip(daily_tmin, daily_tmax, strict=True)
    )
    kdd = sum(
        _single_sine_degree_days_above(lo, hi, kdd_threshold_c)
        for lo, hi in zip(daily_tmin, daily_tmax, strict=True)
    )
    return RiceWeatherBasis(
        gdd=above_base - kdd,
        kdd=kdd,
        prcp_poly_1_bins=linear,
        prcp_poly_2_bins=quadratic,
        tmin=sum(monthly_tmin),
    )


def build_rice_weather_basis_from_daily(
    daily_records: Iterable[tuple[date, float, float, float]],
    *,
    report_year: int,
    plant_month: int,
    harvest_month: int,
    iso: str,
) -> RiceWeatherBasis:
    """Aggregate complete whole-month daily records to the rice basis."""
    crop_months = calendar_months_for_report_year(
        report_year, plant_month, harvest_month, iso
    )
    month_keys = set(crop_months)
    observed: dict[date, tuple[float, float, float]] = {}
    for record_date, precipitation, minimum_temperature, maximum_temperature in daily_records:
        if not isinstance(record_date, date):
            raise TypeError("daily record date must be datetime.date compatible")
        if (record_date.year, record_date.month) not in month_keys:
            continue
        rainfall = float(precipitation)
        tmin = float(minimum_temperature)
        tmax = float(maximum_temperature)
        if not isfinite(rainfall) or rainfall < 0.0 or not isfinite(tmin) or not isfinite(tmax):
            raise ValueError(
                "daily weather must contain finite nonnegative rain and finite temperatures"
            )
        if tmin > tmax:
            raise ValueError("daily Tmin cannot exceed daily Tmax")
        if record_date in observed:
            raise ValueError(f"duplicate daily weather record: {record_date.isoformat()}")
        observed[record_date] = (rainfall, tmin, tmax)

    monthly_rainfall: list[float] = []
    monthly_mean_tmin: list[float] = []
    daily_tmin: list[float] = []
    daily_tmax: list[float] = []
    for year, month in crop_months:
        days = calendar.monthrange(year, month)[1]
        expected = [date(year, month, day) for day in range(1, days + 1)]
        missing = [value for value in expected if value not in observed]
        if missing:
            raise ValueError(
                f"incomplete daily weather for {year:04d}-{month:02d}: "
                f"{len(missing)} missing day(s)"
            )
        monthly_rainfall.append(sum(observed[value][0] for value in expected))
        monthly_mean_tmin.append(sum(observed[value][1] for value in expected) / days)
        daily_tmin.extend(observed[value][1] for value in expected)
        daily_tmax.extend(observed[value][2] for value in expected)

    return build_rice_weather_basis(
        monthly_rainfall, monthly_mean_tmin, daily_tmin, daily_tmax
    )
