import json
import unittest
from pathlib import Path

from scripts.audit_readiness import legacy_release, stock_conserving_release

ROOT = Path(__file__).resolve().parents[1]


class AmazonFeedbackContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "config/amazon_dieback_feedback_contract_v1.json").read_text())

    def test_no_integration_or_scalar_authority(self):
        self.assertFalse(self.cfg["scope"]["give_integration_authorized"])
        self.assertFalse(self.cfg["scope"]["scc_adjustment_authorized"])

    def test_adjacent_sector_exclusions(self):
        exclusions = " ".join(self.cfg["scope"]["excluded"]).lower()
        for term in ("forestry", "wildfire", "biodiversity", "agricultural"):
            self.assertIn(term, exclusions)

    def test_continuous_duration_exposes_legacy_overshoot(self):
        total = self.cfg["meta_2021"]["central_parameters"]["maximum_release_GtCO2"]
        _, emitted = legacy_release(total, 50.5)
        self.assertGreater(emitted, total)

    def test_corrected_schedule_exactly_conserves_stock(self):
        total = self.cfg["meta_2021"]["central_parameters"]["maximum_release_GtCO2"]
        releases = stock_conserving_release(total, 50.5)
        self.assertAlmostEqual(sum(releases), total, places=9)
        self.assertLess(releases[-1], releases[0])

    def test_overlap_and_hazard_gates_closed(self):
        gates = self.cfg["claim_gates"]
        self.assertFalse(gates["generic_fair_land_sink_overlap_reconciled"])
        self.assertFalse(gates["gmt_only_hazard_validated_against_current_precipitation_and_drought_science"])

    def test_no_results(self):
        results = ROOT / "results"
        self.assertFalse(results.exists() and any(results.iterdir()))


if __name__ == "__main__":
    unittest.main()
