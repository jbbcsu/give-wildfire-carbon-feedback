#!/usr/bin/env python3

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from build_hultgren_country_maize_value_weights import allocate_country_cells


class CountryValueWeightTests(unittest.TestCase):
    def test_country_values_and_shared_cell_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mapspam.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["stat_code", "latitude", "longitude", "maize_total_mt"])
                writer.writeheader()
                writer.writerows([
                    {"stat_code": "AAA", "latitude": 0.01, "longitude": 0.01, "maize_total_mt": 1},
                    {"stat_code": "AAA", "latitude": 0.02, "longitude": 0.02, "maize_total_mt": 3},
                    {"stat_code": "BBB", "latitude": 0.03, "longitude": 0.03, "maize_total_mt": 2},
                    {"stat_code": "ZZZ", "latitude": 5.0, "longitude": 5.0, "maize_total_mt": 4},
                ])
            frame, audit = allocate_country_cells(path, {"AAA": "AAA", "BBB": "BBB", "ZZZ": None}, {"AAA": 8.0, "BBB": 5.0})
            self.assertEqual(len(frame), 2)
            self.assertEqual(audit["matched_country_count"], 2)
            self.assertEqual(audit["cells_shared_by_multiple_countries"], 1)
            self.assertAlmostEqual(audit["matched_maize_production_fraction"], 0.6)
            values = frame.groupby("iso3").maize_gross_production_value_constant_2014_2016_usd.sum().to_dict()
            self.assertAlmostEqual(values["AAA"], 8000.0)
            self.assertAlmostEqual(values["BBB"], 5000.0)


if __name__ == "__main__":
    unittest.main()
