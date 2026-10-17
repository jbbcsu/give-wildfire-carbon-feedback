import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_tropical_cyclone_give_readiness import validate_contract  # noqa: E402


def contract() -> dict[str, object]:
    return json.loads((ROOT / "config/tropical_cyclone_give_readiness_v1.json").read_text(encoding="utf-8"))


class TropicalCycloneReadinessTests(unittest.TestCase):
    def test_contract_is_valid_but_not_additive(self):
        result = validate_contract(contract())
        self.assertTrue(result["contract_valid"])
        self.assertFalse(result["numeric_give_addition_authorized"])

    def test_difference_of_medians_warning_is_required(self):
        candidate = contract()
        candidate["published_benchmark"]["interpretation"] = "tc_scc_median"
        with self.assertRaisesRegex(ValueError, "difference-of-medians"):
            validate_contract(candidate)

    def test_sectoral_additivity_cannot_be_claimed(self):
        candidate = contract()
        candidate["overlap_boundary"]["additive_to_explicit_give_sector_modules"] = True
        with self.assertRaisesRegex(ValueError, "sectoral additivity"):
            validate_contract(candidate)

    def test_macro_additivity_cannot_be_claimed(self):
        candidate = contract()
        candidate["overlap_boundary"]["additive_to_aggregate_macro_damage_function"] = True
        with self.assertRaisesRegex(ValueError, "macro additivity"):
            validate_contract(candidate)

    def test_broad_overlap_risk_cannot_be_downgraded(self):
        candidate = copy.deepcopy(contract())
        candidate["overlap_boundary"]["broad_sectoral_overlap_risk"] = "low"
        with self.assertRaisesRegex(ValueError, "overlap risk"):
            validate_contract(candidate)

    def test_numeric_gate_cannot_be_opened(self):
        candidate = contract()
        candidate["current_gate"]["numeric_give_addition_authorized"] = True
        with self.assertRaisesRegex(ValueError, "numeric GIVE gate"):
            validate_contract(candidate)


if __name__ == "__main__":
    unittest.main()
