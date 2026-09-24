#!/usr/bin/env python3

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from build_mapspam_halfdegree_maize_weights import FIELDS, aggregate, halfdegree_key


class MapspamAggregationTests(unittest.TestCase):
    def test_halfdegree_key(self) -> None:
        self.assertEqual(halfdegree_key(89.75, -179.75), (0, 0))
        self.assertEqual(halfdegree_key(-89.75, 179.75), (359, 719))
        self.assertEqual(halfdegree_key(38.4583333328, 70.8749999990), (103, 501))

    def test_aggregation_and_system_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mapspam.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["latitude", "longitude", *FIELDS])
                writer.writeheader()
                writer.writerow(dict(latitude=38.45, longitude=70.80, maize_total_mt=10, maize_rainfed_high_mt=2, maize_rainfed_low_mt=3, maize_irrigated_mt=4, maize_rainfed_subsistence_mt=1))
                writer.writerow(dict(latitude=38.40, longitude=70.90, maize_total_mt=5, maize_rainfed_high_mt=1, maize_rainfed_low_mt=1, maize_irrigated_mt=2, maize_rainfed_subsistence_mt=1))
            cells, audit = aggregate(path)
            self.assertEqual(len(cells), 1)
            self.assertEqual(cells[(103, 501)][0], 15.0)
            self.assertEqual(audit["source_maize_total_mt"], 15.0)
            self.assertEqual(audit["system_component_relative_difference"], 0.0)


if __name__ == "__main__":
    unittest.main()
