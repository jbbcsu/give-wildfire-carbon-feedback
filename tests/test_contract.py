import json
import unittest
from pathlib import Path

from scripts.audit_readiness import delta_wetland_emissions, normal_probability_below_zero

ROOT = Path(__file__).resolve().parents[1]


class WetlandMethaneContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "config/wetland_methane_feedback_contract_v1.json").read_text())

    def test_no_integration_or_scalar_authority(self):
        self.assertFalse(self.cfg["scope"]["give_integration_authorized"])
        self.assertFalse(self.cfg["scope"]["scc_adjustment_authorized"])

    def test_feedback_anomaly_units(self):
        self.assertEqual(delta_wetland_emissions(1.0, 30.0), 30.0)
        self.assertEqual(delta_wetland_emissions(0.0, 30.0), 0.0)

    def test_normal_distribution_has_negative_tail(self):
        probability = normal_probability_below_zero(30.0, 13.0)
        self.assertGreater(probability, 0.01)
        self.assertLess(probability, 0.011)

    def test_biogenic_feedback_never_targets_fossil_input(self):
        target = self.cfg["unit_contract"]["target_input"]
        self.assertIn("natural_emiss_CH4", target)
        self.assertIn("never fossil", target)

    def test_key_overlap_gates_closed(self):
        gates = self.cfg["claim_gates"]
        self.assertFalse(gates["wetland_share_of_give_natural_baseline_identified"])
        self.assertFalse(gates["biogenic_methane_oxidation_routing_validated"])
        self.assertFalse(gates["methane_lifetime_and_feedback_calibration_reconciled"])

    def test_no_results(self):
        results = ROOT / "results"
        self.assertFalse(results.exists() and any(results.iterdir()))


if __name__ == "__main__":
    unittest.main()
