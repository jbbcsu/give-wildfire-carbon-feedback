import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestDroughtGmstLinkContract(unittest.TestCase):
    def test_script_parses_and_keeps_claim_boundaries(self):
        source = (ROOT / "scripts/evaluate_five_esm_drought_gmst_link.py").read_text()
        ast.parse(source)
        self.assertIn('range(2092, 2100)', source)
        self.assertIn('rmse < zero', source)
        self.assertIn('"training_points": 8', source)
        self.assertIn('"training_points": 5', source)
        self.assertIn('"transient_climate_response": False', source)
        self.assertIn('"yield_response": False', source)
        self.assertIn('"damage": False', source)
        self.assertIn('"scc": False', source)


if __name__ == "__main__":
    unittest.main()
