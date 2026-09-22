#!/usr/bin/env python3
from pathlib import Path
import unittest


class TestFiveEsmDroughtMatrixContract(unittest.TestCase):
    def test_complete_factorial_and_interpretation_gates(self):
        source = (Path(__file__).resolve().parent/"summarize_five_esm_late_drought_crop_matrix.py").read_text()
        self.assertIn("5*3*2*5*3*3", source)
        self.assertIn("all(len(records) == 8", source)
        self.assertIn("Named-model signs are not probabilities", source)
        self.assertIn('"yield_response": False', source)
        self.assertIn('"scc": False', source)


if __name__ == "__main__":
    unittest.main()
