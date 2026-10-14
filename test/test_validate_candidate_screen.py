import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_candidate_screen", ROOT / "python" / "validate_candidate_screen.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CandidateScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(
            (ROOT / "config" / "candidate_screen_v1.json").read_text(encoding="utf-8")
        )

    def test_preserved_screen_is_valid_and_closed(self):
        self.assertEqual(MODULE.validate(self.document), [])
        self.assertEqual(self.document["ready_candidates"], [])

    def test_undeclared_all_pass_candidate_is_rejected(self):
        mutated = copy.deepcopy(self.document)
        mutated["candidates"][0]["gates"] = {
            gate: "pass" for gate in mutated["required_gates"]
        }
        errors = MODULE.validate(mutated)
        self.assertTrue(any("ready_candidates" in error for error in errors))

    def test_missing_gate_is_rejected(self):
        mutated = copy.deepcopy(self.document)
        del mutated["candidates"][0]["gates"]["marginal_pulse_compatible"]
        errors = MODULE.validate(mutated)
        self.assertTrue(any("exactly match" in error for error in errors))

    def test_failed_candidate_requires_blocker(self):
        mutated = copy.deepcopy(self.document)
        mutated["candidates"][0]["blocker"] = ""
        errors = MODULE.validate(mutated)
        self.assertTrue(any("require a blocker" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
