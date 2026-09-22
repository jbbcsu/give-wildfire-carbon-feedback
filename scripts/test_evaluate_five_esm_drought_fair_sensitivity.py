import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestDroughtFairSensitivityContract(unittest.TestCase):
    def test_evaluator_parses_and_keeps_science_gates_closed(self):
        source = (ROOT / "scripts/evaluate_five_esm_drought_fair_sensitivity.py").read_text()
        ast.parse(source)
        self.assertIn('len(records) == 13224', source)
        self.assertIn('frame = frame.assign(difference_k=recomputed)', source)
        self.assertIn('maize[0]["combined_predictive_rule_passes"] is True', source)
        self.assertIn('"numerical_fair_interface": False', source)
        self.assertIn('"transient_climate_response": False', source)
        self.assertIn('"yield_response": False', source)
        self.assertIn('"damage": False', source)
        self.assertIn('"scc": False', source)


if __name__ == "__main__":
    unittest.main()
