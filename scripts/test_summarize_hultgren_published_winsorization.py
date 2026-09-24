#!/usr/bin/env python3

from __future__ import annotations

import unittest

import pandas as pd

from summarize_hultgren_published_winsorization import summarize


class PublishedWinsorizationTests(unittest.TestCase):
    def test_weighted_cell_first_transform(self) -> None:
        frame = pd.DataFrame({
            "harvest_year": [1, 1, 2, 2],
            "analysis_weight": [1.0, 3.0, 1.0, 3.0],
            "precipitation_delta_log_yield": [-10.0, 0.0, 10.0, 0.0],
        })
        result = summarize(frame, -1.0, 1.0)
        self.assertEqual(result["winsorized_low_rows"], 1)
        self.assertEqual(result["winsorized_high_rows"], 1)
        self.assertEqual(result["baseline_weight_per_year"], 4.0)
        self.assertAlmostEqual(result["winsorized_weighted_mean_delta_log_yield"], 0.0)
        self.assertGreater(result["winsorized_weighted_mean_cell_exact_percent"], 0.0)


if __name__ == "__main__":
    unittest.main()
