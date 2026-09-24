#!/usr/bin/env python3

from __future__ import annotations

import unittest

from validate_hultgren_grid_climate_moderators import month_keys


class MonthKeyTests(unittest.TestCase):
    def test_same_year_season(self) -> None:
        self.assertEqual(month_keys(2000, 4, 7), [(2000, 4), (2000, 5), (2000, 6), (2000, 7)])

    def test_cross_year_season(self) -> None:
        self.assertEqual(month_keys(2000, 10, 2), [(1999, 10), (1999, 11), (1999, 12), (2000, 1), (2000, 2)])


if __name__ == "__main__":
    unittest.main()
