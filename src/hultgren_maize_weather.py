"""Primitive weather basis for the published Hultgren maize benchmark.

This module deliberately starts after crop-calendar alignment: callers must
provide the 4--10 local growing-season monthly precipitation totals and paired
daily minimum and maximum temperatures for the same season.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from math import asin, cos, isfinite, pi
from typing import TYPE_CHECKING, Iterable

from .hultgren_crop_calendar import calendar_months_for_report_year

if TYPE_CHECKING:
    from .hultgren_maize_response import MaizeBasis


@dataclass(frozen=True)
class MaizeWeatherBasis:
    gdd: float
    kdd: float
    prcp_poly_1_bins: tuple[float, float, float]
    prcp_poly_2_bins: tuple[float, float, float]

    def with_moderators(
        self,
        *,
        ln_gdppc: float,
        irrigated_share: float,
        lr_tmax_crop: float,
        lr_prcp_crop: float,
    ) -> "MaizeBasis":
        """Attach declared moderators for the published 49-term response."""
        from .hultgren_maize_response import MaizeBasis

        result = MaizeBasis(
            gdd=self.gdd,
            kdd=self.kdd,
            prcp_poly_1_bins=self.prcp_poly_1_bins,
            prcp_poly_2_bins=self.prcp_poly_2_bins,
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


def build_maize_weather_basis(
    monthly_precipitation_mm: Iterable[float],
    daily_tmin_c: Iterable[float],
    daily_tmax_c: Iterable[float],
    *,
    gdd_base_c: float = 8.0,
    kdd_threshold_c: float = 31.0,
) -> MaizeWeatherBasis:
    """Construct the source-matched maize weather basis without calendar guesses."""

    precipitation = _finite(monthly_precipitation_mm, "monthly_precipitation_mm")
    minimum_temperature = _finite(daily_tmin_c, "daily_tmin_c")
    maximum_temperature = _finite(daily_tmax_c, "daily_tmax_c")
    if not 4 <= len(precipitation) <= 10:
        raise ValueError("maize crop-calendar season must contain 4 through 10 months")
    if any(value < 0 for value in precipitation):
        raise ValueError("monthly precipitation cannot be negative")
    if len(minimum_temperature) != len(maximum_temperature):
        raise ValueError("daily Tmin and Tmax must have identical lengths")
    if any(tmin > tmax for tmin, tmax in zip(minimum_temperature, maximum_temperature, strict=True)):
        raise ValueError("daily Tmin cannot exceed daily Tmax")
    if not gdd_base_c < kdd_threshold_c:
        raise ValueError("gdd_base_c must be below kdd_threshold_c")

    slices = (precipitation[:1], precipitation[1:4], precipitation[4:])
    linear = tuple(sum(values) for values in slices)
    quadratic = tuple(sum(value * value for value in values) for values in slices)
    degree_days_lower = sum(
        _single_sine_degree_days_above(tmin, tmax, gdd_base_c)
        for tmin, tmax in zip(minimum_temperature, maximum_temperature, strict=True)
    )
    kdd = sum(
        _single_sine_degree_days_above(tmin, tmax, kdd_threshold_c)
        for tmin, tmax in zip(minimum_temperature, maximum_temperature, strict=True)
    )
    gdd = degree_days_lower - kdd
    return MaizeWeatherBasis(gdd, kdd, linear, quadratic)


def _single_sine_degree_days_above(tmin_c: float, tmax_c: float, threshold_c: float) -> float:
    """Snyder single-sine area above one threshold, in degree-days."""
    if tmax_c <= threshold_c:
        return 0.0
    if tmin_c >= threshold_c:
        return (tmin_c + tmax_c) / 2.0 - threshold_c
    amplitude = (tmax_c - tmin_c) / 2.0
    if amplitude == 0.0:
        return max(tmax_c - threshold_c, 0.0)
    midpoint = (tmax_c + tmin_c) / 2.0
    theta = asin(max(-1.0, min(1.0, (threshold_c - midpoint) / amplitude)))
    return ((midpoint - threshold_c) * (pi / 2.0 - theta) + amplitude * cos(theta)) / pi


def build_maize_weather_basis_from_daily(
    daily_records: Iterable[tuple[date, float, float, float]],
    *,
    report_year: int,
    plant_month: int,
    harvest_month: int,
    iso: str,
) -> MaizeWeatherBasis:
    """Aggregate complete Gregorian daily weather to the published maize basis.

    Each record is ``(date, precipitation_mm_per_day, daily_tmin_c,
    daily_tmax_c)``. Temperature exposure uses the paper's Snyder single-sine
    interpolation between daily Tmin and Tmax. Records outside the target crop
    season are ignored; every Gregorian day inside each selected whole calendar
    month must occur exactly once.
    """
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
            raise ValueError("daily weather must contain finite nonnegative rain and finite temperatures")
        if tmin > tmax:
            raise ValueError("daily Tmin cannot exceed daily Tmax")
        if record_date in observed:
            raise ValueError(f"duplicate daily weather record: {record_date.isoformat()}")
        observed[record_date] = (rainfall, tmin, tmax)

    monthly_rainfall = []
    daily_tmin = []
    daily_tmax = []
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
        daily_tmin.extend(observed[value][1] for value in expected)
        daily_tmax.extend(observed[value][2] for value in expected)

    return build_maize_weather_basis(monthly_rainfall, daily_tmin, daily_tmax)
