#!/usr/bin/env python3
"""Synthetic tests for the source-exact Hultgren month/year calendar."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import (
    calendar_months_for_report_year,
    month_of_season,
    normalized_plant_month,
    season_months,
    source_month_from_day,
    source_report_year,
)


class TestHultgrenCalendar(unittest.TestCase):
    def test_source_day_boundaries(self) -> None:
        self.assertEqual(source_month_from_day(31.999), 1)
        self.assertEqual(source_month_from_day(32), 2)
        self.assertEqual(source_month_from_day(59.999), 2)
        self.assertEqual(source_month_from_day(60), 3)
        self.assertEqual(source_month_from_day(336), 12)

    def test_same_and_cross_year_seasons(self) -> None:
        self.assertEqual(season_months(4, 9), (4, 5, 6, 7, 8, 9))
        self.assertEqual(season_months(10, 3), (10, 11, 12, 1, 2, 3))
        self.assertEqual(month_of_season(1, 10, 3), 4)

    def test_equal_month_twelve_month_sentinel(self) -> None:
        plant = normalized_plant_month(12, 12)
        self.assertEqual(plant, 13)
        self.assertEqual(season_months(plant, 12), tuple(range(1, 13)))

    def test_non_india_harvest_year(self) -> None:
        self.assertEqual(source_report_year(1999, 10, 10, 3, "USA"), 2000)
        self.assertEqual(source_report_year(2000, 3, 10, 3, "USA"), 2000)
        self.assertEqual(source_report_year(2000, 7, 4, 9, "USA"), 2000)
        self.assertEqual(
            calendar_months_for_report_year(2000, 10, 3, "USA"),
            ((1999, 10), (1999, 11), (1999, 12), (2000, 1), (2000, 2), (2000, 3)),
        )

    def test_india_agricultural_year(self) -> None:
        self.assertEqual(source_report_year(2000, 11, 10, 3, "IND"), 2000)
        self.assertEqual(source_report_year(2001, 3, 10, 3, "IND"), 2000)
        self.assertEqual(source_report_year(2000, 5, 5, 10, "IND"), 2000)
        self.assertEqual(source_report_year(2000, 10, 5, 10, "IND"), 2000)
        self.assertEqual(
            calendar_months_for_report_year(2000, 10, 3, "IND"),
            ((2000, 10), (2000, 11), (2000, 12), (2001, 1), (2001, 2), (2001, 3)),
        )


if __name__ == "__main__":
    unittest.main()
