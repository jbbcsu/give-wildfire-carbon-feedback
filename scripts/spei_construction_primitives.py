#!/usr/bin/env python3
"""Tested SPEI physical/time primitives; deliberately omits distribution fitting.

The functions here implement only the source-independent steps that are safe
before index-construction authorization: FAO-56 extraterrestrial radiation,
daily Hargreaves-Samani reference ET0, complete calendar-month water balance,
and right-aligned accumulation. They read no project data and fit no SPEI or
outcome model.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


SOLAR_CONSTANT_MJ_M2_MIN = 0.0820
RADIATION_TO_EQUIVALENT_EVAPORATION_MM = 0.408
FLOAT_TOLERANCE_C = 1e-7


def _numeric_array(value: object, label: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not np.isfinite(result).all():
        raise ValueError(f"{label} must be finite")
    return result


def extraterrestrial_radiation_mj_m2_day(
    latitude_degrees: object,
    day_of_year: object,
) -> np.ndarray:
    """Return daily top-of-atmosphere radiation using FAO-56 equations 21-25."""
    latitude = _numeric_array(latitude_degrees, "latitude")
    day = _numeric_array(day_of_year, "day_of_year")
    latitude, day = np.broadcast_arrays(latitude, day)
    if (np.abs(latitude) >= 90).any():
        raise ValueError("latitude must be strictly between -90 and 90 degrees")
    if ((day < 1) | (day > 366) | (day != np.floor(day))).any():
        raise ValueError("day_of_year must contain integers in [1, 366]")

    phi = np.deg2rad(latitude)
    angle = 2 * np.pi * day / 365.0
    inverse_distance = 1 + 0.033 * np.cos(angle)
    solar_declination = 0.409 * np.sin(angle - 1.39)
    sunset_argument = -np.tan(phi) * np.tan(solar_declination)
    sunset_hour_angle = np.arccos(np.clip(sunset_argument, -1.0, 1.0))
    radiation = (
        (24 * 60 / np.pi)
        * SOLAR_CONSTANT_MJ_M2_MIN
        * inverse_distance
        * (
            sunset_hour_angle * np.sin(phi) * np.sin(solar_declination)
            + np.cos(phi) * np.cos(solar_declination) * np.sin(sunset_hour_angle)
        )
    )
    return np.maximum(radiation, 0.0)


def hargreaves_samani_et0_mm_day(
    tmin_c: object,
    tmax_c: object,
    latitude_degrees: object,
    day_of_year: object,
) -> np.ndarray:
    """Return daily Hargreaves-Samani grass-reference ET0 in millimetres."""
    tmin = _numeric_array(tmin_c, "tmin_c")
    tmax = _numeric_array(tmax_c, "tmax_c")
    latitude = _numeric_array(latitude_degrees, "latitude")
    day = _numeric_array(day_of_year, "day_of_year")
    tmin, tmax, latitude, day = np.broadcast_arrays(tmin, tmax, latitude, day)
    if (tmax < tmin - FLOAT_TOLERANCE_C).any():
        raise ValueError("tmax_c must not be lower than tmin_c")
    temperature_range = np.maximum(tmax - tmin, 0.0)
    tmean = (tmin + tmax) / 2.0
    radiation = extraterrestrial_radiation_mj_m2_day(latitude, day)
    et0 = (
        0.0023
        * RADIATION_TO_EQUIVALENT_EVAPORATION_MM
        * radiation
        * (tmean + 17.8)
        * np.sqrt(temperature_range)
    )
    return np.maximum(et0, 0.0)


def complete_monthly_water_balance(
    dates: Iterable[object],
    precipitation_mm_day: object,
    et0_mm_day: object,
) -> pd.DataFrame:
    """Sum complete daily inputs to monthly P, ET0, and P-minus-ET0."""
    index = pd.DatetimeIndex(dates)
    if index.tz is not None:
        raise ValueError("dates must be timezone-naive source day labels")
    if index.hasnans or not index.is_normalized:
        raise ValueError("dates must be finite normalized source day labels")
    precipitation = _numeric_array(precipitation_mm_day, "precipitation_mm_day")
    et0 = _numeric_array(et0_mm_day, "et0_mm_day")
    if precipitation.ndim != 1 or et0.ndim != 1:
        raise ValueError("daily precipitation and ET0 must be one-dimensional")
    if len(index) == 0 or len(index) != len(precipitation) or len(index) != len(et0):
        raise ValueError("dates, precipitation, and ET0 must have the same positive length")
    if (precipitation < 0).any() or (et0 < 0).any():
        raise ValueError("daily precipitation and ET0 must be nonnegative")

    order = np.argsort(index.values, kind="stable")
    index = index[order]
    precipitation = precipitation[order]
    et0 = et0[order]
    if index.has_duplicates:
        raise ValueError("daily dates must be unique")
    expected = pd.date_range(index[0], index[-1], freq="D")
    if not index.equals(expected):
        raise ValueError("daily chronology must be consecutive without gaps")
    if index[0].day != 1 or index[-1].day != index[-1].days_in_month:
        raise ValueError("daily chronology must begin and end on complete calendar months")

    daily = pd.DataFrame(
        {"precipitation_mm": precipitation, "et0_mm": et0}, index=index
    )
    daily["month"] = index.to_period("M")
    counts = daily.groupby("month", observed=True).size()
    expected_counts = counts.index.to_timestamp().days_in_month
    if not np.array_equal(counts.to_numpy(), expected_counts.to_numpy()):
        raise ValueError("every calendar month must contain every source day exactly once")
    monthly = daily.groupby("month", observed=True)[["precipitation_mm", "et0_mm"]].sum()
    monthly.index = monthly.index.to_timestamp()
    monthly.index.name = "month"
    monthly["water_balance_mm"] = monthly["precipitation_mm"] - monthly["et0_mm"]
    return monthly.reset_index()


def right_aligned_balance_accumulation(
    monthly: pd.DataFrame,
    scale_months: int,
) -> pd.DataFrame:
    """Add a right-aligned rectangular water-balance sum at one locked scale."""
    if scale_months not in {1, 3, 6}:
        raise ValueError("scale_months must be one of 1, 3, or 6")
    required = {"month", "water_balance_mm"}
    if missing := required - set(monthly.columns):
        raise ValueError(f"monthly water balance lacks {sorted(missing)}")
    result = monthly.copy()
    result["month"] = pd.to_datetime(result["month"], errors="raise")
    if result["month"].dt.tz is not None or not result["month"].dt.is_month_start.all():
        raise ValueError("month must contain timezone-naive calendar-month starts")
    result = result.sort_values("month", kind="mergesort").reset_index(drop=True)
    if result["month"].duplicated().any():
        raise ValueError("monthly water balance contains duplicate months")
    if result.empty:
        raise ValueError("monthly water balance is empty")
    expected = pd.date_range(result["month"].iloc[0], result["month"].iloc[-1], freq="MS")
    if not result["month"].equals(pd.Series(expected)):
        raise ValueError("monthly chronology must be consecutive without gaps")
    balance = pd.to_numeric(result["water_balance_mm"], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(balance).all():
        raise ValueError("monthly water balance must be finite")
    result[f"water_balance_{scale_months}m_mm"] = (
        pd.Series(balance).rolling(scale_months, min_periods=scale_months).sum()
    )
    return result
