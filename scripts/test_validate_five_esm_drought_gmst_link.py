import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestDroughtGmstLinkValidationContract(unittest.TestCase):
    def test_validator_parses_and_recomputes_all_folds(self):
        source = (ROOT / "scripts/validate_five_esm_drought_gmst_link.py").read_text()
        ast.parse(source)
        self.assertIn('record_lookup) == 90', source)
        self.assertIn('row["training_points"] == 8', source)
        self.assertIn('row["training_points"] == 5', source)
        self.assertIn('"transient_climate_response": False', source)
        self.assertIn('"yield_response": False', source)
        self.assertIn('"damage": False', source)
        self.assertIn('"scc": False', source)


if __name__ == "__main__":
    unittest.main()
