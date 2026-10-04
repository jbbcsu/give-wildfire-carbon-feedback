import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "validate_manuscript_sentinel_evidence.py"
SPEC = importlib.util.spec_from_file_location("loca2_manuscript_sentinel", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ManuscriptSentinelEvidenceTests(unittest.TestCase):
    def test_current_manuscript_matches_receipts_and_closed_gates(self):
        result = MODULE.validate()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["independent_checks"], 400)
        self.assertEqual(result["support"]["years"], list(range(2001, 2013)))
        self.assertFalse(result["support"]["outcome_columns_read"])
        for gate in ("multi_model_validation", "outcome_response", "causal_damage", "SCC"):
            self.assertFalse(result["claim_gates"][gate])


if __name__ == "__main__":
    unittest.main()
