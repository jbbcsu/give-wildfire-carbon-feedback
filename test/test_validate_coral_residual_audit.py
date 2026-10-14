import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_coral_residual_audit import validate_contract  # noqa: E402


def contract() -> dict[str, object]:
    return json.loads((ROOT / "config/coral_residual_candidate_audit_v1.json").read_text(encoding="utf-8"))


class CoralResidualContractTests(unittest.TestCase):
    def test_current_contract_is_valid_but_blocked(self):
        result = validate_contract(contract())
        self.assertTrue(result["contract_valid"])
        self.assertEqual(result["candidate_count"], 5)
        self.assertEqual(result["author_artifact_group_count"], 7)
        self.assertFalse(result["damage_or_scc_authorized"])

    def test_give_authorization_fails(self):
        candidate = contract()
        candidate["target_component"]["authorized_for_give"] = True
        with self.assertRaisesRegex(ValueError, "GIVE must remain unauthorized"):
            validate_contract(candidate)

    def test_scc_calibration_fails(self):
        candidate = contract()
        candidate["target_component"]["published_scc_may_be_used_as_calibration"] = True
        with self.assertRaisesRegex(ValueError, "published SCC cannot be calibration"):
            validate_contract(candidate)

    def test_allocation_fails(self):
        candidate = contract()
        candidate["target_component"]["allocation_or_renormalization_allowed"] = True
        with self.assertRaisesRegex(ValueError, "allocation and renormalization"):
            validate_contract(candidate)

    def test_missing_fisheries_exclusion_fails(self):
        candidate = contract()
        candidate["mandatory_exclusions"].remove("reef_fisheries_and_aquaculture")
        with self.assertRaisesRegex(ValueError, "overlap exclusions"):
            validate_contract(candidate)

    def test_missing_ciam_exclusion_fails(self):
        candidate = contract()
        candidate["mandatory_exclusions"].remove("ciam_coastal_impacts")
        with self.assertRaisesRegex(ValueError, "overlap exclusions"):
            validate_contract(candidate)

    def test_recreation_value_cannot_be_substituted_with_bundle(self):
        candidate = contract()
        candidate["blue_repository"]["nonmarket_bundle_int2020_per_ha_year"]["opportunities_for_recreation_and_tourism"] = 36186
        with self.assertRaisesRegex(ValueError, "service bundle does not sum|recreation source value changed"):
            validate_contract(candidate)

    def test_claimed_source_admission_fails(self):
        candidate = copy.deepcopy(contract())
        candidate["primary_sources"][0]["residual_transfer_status"] = "ready"
        with self.assertRaisesRegex(ValueError, "source improperly admitted"):
            validate_contract(candidate)


if __name__ == "__main__":
    unittest.main()
