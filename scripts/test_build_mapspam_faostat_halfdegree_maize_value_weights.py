#!/usr/bin/env python3

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from build_mapspam_faostat_halfdegree_maize_value_weights import allocate


class ValueWeightTests(unittest.TestCase):
    def test_country_value_conservation_and_missing_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mapspam.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["stat_code", "latitude", "longitude", "maize_total_mt"])
                writer.writeheader()
                writer.writerow(dict(stat_code="AA", latitude=10.25, longitude=20.25, maize_total_mt=25))
                writer.writerow(dict(stat_code="AA", latitude=10.20, longitude=20.20, maize_total_mt=75))
                writer.writerow(dict(stat_code="BB", latitude=0.25, longitude=0.25, maize_total_mt=50))
            cells, audit = allocate(path, {"AA": "AAA", "BB": "BBB"}, {"AAA": 2.0})
            self.assertEqual(len(cells), 1)
            self.assertAlmostEqual(next(iter(cells.values()))[1], 2000.0)
            self.assertAlmostEqual(audit["matched_maize_production_fraction"], 2.0 / 3.0)
            self.assertEqual(audit["matched_country_count"], 1)


if __name__ == "__main__":
    unittest.main()
