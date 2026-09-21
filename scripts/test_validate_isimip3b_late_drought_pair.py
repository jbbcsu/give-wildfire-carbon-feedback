#!/usr/bin/env python3
from pathlib import Path
import unittest


class TestLateDroughtValidatorContract(unittest.TestCase):
    def test_validator_is_independent_of_builder(self):
        source = (Path(__file__).resolve().parent/"validate_isimip3b_late_drought_pair.py").read_text()
        self.assertNotIn("from build_isimip3b_late_drought_pair", source)
        self.assertIn("standardize_glo", source)
        self.assertIn("fixed_sample_cells", source)
        self.assertIn("digest(path, \"sha512\")", source)


if __name__ == "__main__":
    unittest.main()
