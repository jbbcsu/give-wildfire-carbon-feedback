#!/usr/bin/env python3
"""Small regression checks for multicrop distribution split logic."""
from __future__ import annotations

import unittest

import pandas as pd

from evaluate_crop_response_models import purged_extreme_masks, purged_temporal_masks
from evaluate_multicrop_rainfed_distribution_diagnostic import _purged_masks_low_memory


class SplitTests(unittest.TestCase):
    def test_numeric_endpoint_purge_matches_reference(self) -> None:
        pairs = pd.DataFrame(
            {
                "crop": ["mai"] * 6,
                "irrigation": ["noirr"] * 6,
                "lat": [0, 0, 0, 1, 1, 1],
                "lon_360": [10, 10, 10, 20, 20, 20],
                "pair_start_year": [1982, 1983, 1984, 1982, 1983, 1984],
                "pair_end_year": [1983, 1984, 1985, 1983, 1984, 1985],
                "is_temporal_holdout": [False, False, True, False, False, True],
                "pair_is_climate_extreme": [False, True, False, False, False, True],
            }
        )
        actual = _purged_masks_low_memory(pairs)
        temporal = purged_temporal_masks(pairs)
        extreme = purged_extreme_masks(pairs)
        self.assertTrue(actual["temporal"][0].equals(temporal[0]))
        self.assertTrue(actual["temporal"][1].equals(temporal[1]))
        self.assertTrue(actual["climate_extreme"][0].equals(extreme[0]))
        self.assertTrue(actual["climate_extreme"][1].equals(extreme[1]))
        self.assertEqual(actual["temporal"][2]["endpoint_overlap_count"], 0)
        self.assertEqual(actual["climate_extreme"][2]["endpoint_overlap_count"], 0)


if __name__ == "__main__":
    unittest.main()
