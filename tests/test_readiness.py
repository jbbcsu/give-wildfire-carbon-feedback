import csv
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit", ROOT / "scripts/audit_infectious_disease_readiness.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config/infectious_disease_readiness_v1.json").read_text())

    def test_audit_passes_but_scc_stays_closed(self):
        receipt = AUDIT.run_audit(write=False)
        self.assertTrue(receipt["audit_pass"])
        self.assertFalse(receipt["additive_scc_allowed"])

    def test_release_invariant(self):
        gates = self.config["claim_gates"]
        prerequisites = [key for key in gates if key not in {
            "peer_reviewed_response", "source_code_pinned_and_hash_verified",
            "study_domain_respected", "additive_scc_allowed"
        }]
        self.assertFalse(gates["additive_scc_allowed"])
        self.assertTrue(any(not gates[key] for key in prerequisites))

    def test_no_mortality_or_lost_wages_in_allowed_channels(self):
        allowed = " ".join(self.config["allowed_damage_channels"]).lower()
        self.assertNotIn("mortality", allowed)
        self.assertNotIn("lost_wages", allowed)

    def test_contract_is_header_only_and_contains_pulse_pair(self):
        path = ROOT / "contracts/dengue_marginal_pulse_contract_v1.csv"
        with path.open(newline="") as stream:
            rows = [row for row in csv.reader(stream) if row]
        self.assertEqual(len(rows), 1)
        header = rows[0]
        for required in ["temperature_base_c", "temperature_pulse_c", "cases_base", "cases_pulse"]:
            self.assertIn(required, header)

    def test_give_target_audit_is_pinned(self):
        manifest = json.loads((ROOT / "provenance/source_manifest_v1.json").read_text())
        audited = manifest["give_target_audit"]["files"]
        self.assertEqual(len(audited), 2)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in audited))


if __name__ == "__main__":
    unittest.main()
