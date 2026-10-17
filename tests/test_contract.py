import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PermafrostFeedbackContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "config/permafrost_feedback_contract_v1.json").read_text())

    def test_no_integration_or_scalar_authority(self):
        self.assertFalse(self.cfg["scope"]["give_integration_authorized"])
        self.assertFalse(self.cfg["scope"]["scc_adjustment_authorized"])

    def test_wildfire_and_local_damage_excluded(self):
        exclusions = " ".join(self.cfg["scope"]["excluded"]).lower()
        self.assertIn("wildfire", exclusions)
        self.assertIn("infrastructure", exclusions)

    def test_percx_parameter_artifact_has_765_rows(self):
        path = ROOT / self.cfg["percx"]["parameter_path"]
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(rows), 765)

    def test_biogenic_methane_gate_closed(self):
        self.assertFalse(self.cfg["claim_gates"]["biogenic_ch4_routing_validated"])

    def test_no_results(self):
        results = ROOT / "results"
        self.assertFalse(results.exists() and any(results.iterdir()))

if __name__ == "__main__":
    unittest.main()
