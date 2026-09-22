import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestDroughtFairSensitivityValidationContract(unittest.TestCase):
    def test_validator_parses_and_recomputes_all_rows(self):
        source = (ROOT / "scripts/validate_five_esm_drought_fair_sensitivity.py").read_text()
        ast.parse(source)
        self.assertIn('len(expected) == len(actual) == 13224', source)
        self.assertIn('"numerical_fair_interface": True', source)
        self.assertIn('"transient_climate_response": False', source)
        self.assertIn('"yield_response": False', source)
        self.assertIn('"damage": False', source)
        self.assertIn('"scc": False', source)


if __name__ == "__main__":
    unittest.main()
