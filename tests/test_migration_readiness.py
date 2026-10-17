import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MigrationReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(ROOT / "scripts/audit_migration_readiness.py")], check=True, capture_output=True)
        cls.config = json.loads((ROOT / "config/migration_readiness_v1.json").read_text())
        cls.result = json.loads((ROOT / "results/migration_readiness_result_v1.json").read_text())

    def test_fail_closed(self):
        self.assertFalse(self.config["target"]["numeric_scc_authorized"])
        self.assertFalse(self.result["numeric_scc_produced"])
        self.assertEqual(self.result["status"], "BLOCKED_NO_ADDITIVE_SCC")

    def test_ciam_overlap_gate(self):
        coastal = self.config["existing_give_coverage"]["coastal_relocation"]
        self.assertEqual(coastal["status"], "included inside CIAM OptimalCost")
        self.assertTrue(coastal["do_not_add_again"])

    def test_no_candidate_is_admitted(self):
        for candidate in self.config["candidates"]:
            self.assertGreater(len(candidate["failed_gates"]), 0, candidate["id"])

    def test_forbidden_shortcuts(self):
        forbidden = " ".join(self.config["forbidden_shortcuts"])
        for phrase in ("cost_per_migrant", "CIAM", "GDP loss", "local disaster"):
            self.assertIn(phrase, forbidden)


if __name__ == "__main__":
    unittest.main()

