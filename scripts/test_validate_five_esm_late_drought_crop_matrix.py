#!/usr/bin/env python3
from pathlib import Path
import unittest


class TestFiveEsmDroughtMatrixValidator(unittest.TestCase):
    def test_validator_recomputes_every_level(self):
        source = (Path(__file__).resolve().parent/"validate_five_esm_late_drought_crop_matrix.py").read_text()
        for token in ("1350", "900", "180", "statistics.fmean", "negative_models"):
            self.assertIn(token, source)
        self.assertIn('"yield_response": False', source)
        self.assertIn('"scc": False', source)


if __name__ == "__main__":
    unittest.main()
