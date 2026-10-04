import importlib.util
import unittest
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "preflight_historical_climate_sentinel.py"
SPEC = importlib.util.spec_from_file_location("loca2_preflight", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class HistoricalClimatePreflightTests(unittest.TestCase):
    def test_chunk_ids_are_unique_and_sorted(self):
        self.assertEqual(MODULE.chunk_ids(np.array([468, 0, 467, 936, 469]), 468), [0, 1, 2])

    def test_empty_indices_fail(self):
        with self.assertRaisesRegex(ValueError, "invalid chunk inputs"):
            MODULE.chunk_ids(np.array([], dtype=int), 468)


if __name__ == "__main__":
    unittest.main()
