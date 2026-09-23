"""Exact month and reporting-year rules from Hultgren replication source."""

from __future__ import annotations

import math


MONTH_START_THRESHOLDS = (32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 336)


def source_month_from_day(day_of_year: float) -> int:
    """Map the source's median day value to month using its fixed thresholds."""
    value = float(day_of_year)
    if not math.isfinite(value) or value < 0.0 or value > 366.0:
        raise ValueError("day_of_year must be finite and in [0, 366]")
    for month, threshold in enumerate(MONTH_START_THRESHOLDS, start=1):
        if value < threshold:
            return month
    return 12


def normalized_plant_month(plant_month: int, harvest_month: int) -> int:
    """Apply the source's equal-month sentinel used to represent 12 months."""
    plant = int(plant_month)
    harvest = int(harvest_month)
    if not 1 <= plant <= 12 or not 1 <= harvest <= 12:
        raise ValueError("plant and harvest months must be in 1..12")
    return plant + 1 if plant == harvest else plant


def season_months(plant_month: int, harvest_month: int) -> tuple[int, ...]:
    """Return the inclusive source growing-season months in planting order."""
    plant = int(plant_month)
    harvest = int(harvest_month)
    if not 1 <= harvest <= 12 or not 1 <= plant <= 13:
        raise ValueError("source plant month must be in 1..13 and harvest in 1..12")
    if plant < harvest:
        months = tuple(range(plant, harvest + 1))
    else:
        months = tuple(range(plant, 13)) + tuple(range(1, harvest + 1))
    if not months:
        raise ValueError("source calendar produced an empty season")
    return months


def month_of_season(month: int, plant_month: int, harvest_month: int) -> int:
    """Return the one-based month-of-season index used by the source code."""
    month_value = int(month)
    months = season_months(plant_month, harvest_month)
    try:
        return months.index(month_value) + 1
    except ValueError as error:
        raise ValueError("month is outside the source growing season") from error


def source_report_year(
    calendar_year: int,
    month: int,
    plant_month: int,
    harvest_month: int,
    iso: str,
) -> int:
    """Map a calendar month to the source regression/reporting year.

    Non-India seasons are labeled by harvest year. India follows the explicit
    agricultural-year transformation in ``collapse_clim.do``.
    """
    year = int(calendar_year)
    month_value = int(month)
    plant = int(plant_month)
    harvest = int(harvest_month)
    if month_value not in season_months(plant, harvest):
        raise ValueError("month is outside the source growing season")
    if iso == "IND":
        if month_value <= 6:
            year -= 1
        if month_value <= 6 and harvest > 6 and plant <= 6:
            year += 1
    elif month_value >= plant and plant >= harvest:
        year += 1
    return year


def calendar_months_for_report_year(
    report_year: int,
    plant_month: int,
    harvest_month: int,
    iso: str,
) -> tuple[tuple[int, int], ...]:
    """Return ``(calendar_year, month)`` pairs for one source reporting year."""
    target = int(report_year)
    result = []
    for month in season_months(plant_month, harvest_month):
        candidates = [
            year
            for year in (target - 1, target, target + 1)
            if source_report_year(year, month, plant_month, harvest_month, iso) == target
        ]
        if len(candidates) != 1:
            raise ValueError("source reporting-year rule did not produce one calendar month")
        result.append((candidates[0], month))
    return tuple(result)
