import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from validate_fast_route_screen import (  # noqa: E402
    load_json,
    validate_receipts,
    validate_screen,
)


SCREEN_PATH = ROOT / "config" / "fast_route_screen_v1.json"
RECEIPT_PATH = ROOT / "data" / "provenance" / "source_receipts_20261014.json"


class FastRouteScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.screen = load_json(SCREEN_PATH)
        cls.receipts = load_json(RECEIPT_PATH)
        cls.evidence_ids = validate_receipts(cls.receipts)

    def test_checked_in_negative_screen_is_valid(self):
        result = validate_screen(self.screen, self.evidence_ids)
        self.assertEqual(result["candidates"], 3)
        self.assertEqual(result["qualifying_candidates"], 0)
        self.assertFalse(result["scc_calculated"])

    def test_unresolved_overlap_cannot_be_promoted(self):
        candidate = copy.deepcopy(self.screen)
        candidate["candidates"][0]["ready_for_give"] = True
        with self.assertRaisesRegex(ValueError, "readiness disagrees"):
            validate_screen(candidate, self.evidence_ids)

    def test_allocation_shortcut_is_rejected(self):
        candidate = copy.deepcopy(self.screen)
        candidate["municipal_overlap_boundary"]["allocation_or_renormalization_allowed"] = True
        with self.assertRaisesRegex(ValueError, "must be forbidden"):
            validate_screen(candidate, self.evidence_ids)

    def test_missing_energy_overlap_exclusion_is_rejected(self):
        candidate = copy.deepcopy(self.screen)
        candidate["municipal_overlap_boundary"]["excluded"].remove("give_energy_demand_and_supply_damages")
        with self.assertRaisesRegex(ValueError, "overlap exclusions"):
            validate_screen(candidate, self.evidence_ids)

    def test_unknown_source_binding_is_rejected(self):
        candidate = copy.deepcopy(self.screen)
        candidate["candidates"][1]["gates"]["license"]["evidence_ids"] = ["NOT_A_SOURCE"]
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            validate_screen(candidate, self.evidence_ids)

    def test_missing_gate_is_rejected(self):
        candidate = copy.deepcopy(self.screen)
        del candidate["candidates"][2]["gates"]["marginal_pulse_compatibility"]
        with self.assertRaisesRegex(ValueError, "gate set changed"):
            validate_screen(candidate, self.evidence_ids)

    def test_large_download_claim_is_rejected(self):
        receipts = copy.deepcopy(self.receipts)
        receipts["network_scope"]["large_artifacts_downloaded"] = True
        with self.assertRaisesRegex(ValueError, "exceeds a bounded screen"):
            validate_receipts(receipts)

    def test_scc_authorization_is_rejected(self):
        candidate = copy.deepcopy(self.screen)
        candidate["authorization"]["calculate_or_promote_scc"] = True
        with self.assertRaisesRegex(ValueError, "authorizes estimation"):
            validate_screen(candidate, self.evidence_ids)


if __name__ == "__main__":
    unittest.main()
