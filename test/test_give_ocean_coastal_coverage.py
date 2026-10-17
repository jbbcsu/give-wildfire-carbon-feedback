import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_give_ocean_coastal_coverage import validate_contract  # noqa: E402


def contract() -> dict[str, object]:
    return json.loads((ROOT / "config/give_ocean_coastal_coverage_v1.json").read_text(encoding="utf-8"))


class OceanCoastalCoverageTests(unittest.TestCase):
    def test_contract_is_valid_and_fail_closed(self):
        result = validate_contract(contract())
        self.assertTrue(result["contract_valid"])
        self.assertFalse(result["numeric_give_addition_authorized"])

    def test_generic_coastal_module_is_rejected(self):
        candidate = contract()
        candidate["coverage"]["coastal_sea_level_rise"]["generic_additional_coastal_flood_module_authorized"] = True
        with self.assertRaisesRegex(ValueError, "double-count"):
            validate_contract(candidate)

    def test_headline_scc_addition_is_rejected(self):
        candidate = contract()
        candidate["claim_gates"]["published_headline_scc_may_be_added"] = True
        with self.assertRaisesRegex(ValueError, "gate opened"):
            validate_contract(candidate)

    def test_only_recreation_is_selected(self):
        candidate = copy.deepcopy(contract())
        candidate["candidate_decisions"][1]["decision"] = "selected_research_target_but_not_yet_additive"
        with self.assertRaisesRegex(ValueError, "candidate selection changed"):
            validate_contract(candidate)

    def test_ph_damage_connection_cannot_be_invented(self):
        candidate = contract()
        candidate["coverage"]["ocean_acidification"]["damage_aggregator_connection_present"] = True
        with self.assertRaisesRegex(ValueError, "unsupported pH damage connection"):
            validate_contract(candidate)


if __name__ == "__main__":
    unittest.main()
