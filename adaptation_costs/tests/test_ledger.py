import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_ledger


class AdaptationLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.readiness, cls.benchmark = build_ledger.build()

    def row(self, model, scenario):
        return next(r for r in self.rows if r["model"] == model and r["scenario"] == scenario)

    def test_agriculture_free_adaptation_fails_closed(self):
        for scenario in ("trend", "upper"):
            row = self.row("precipitation replacement", scenario)
            self.assertEqual(row["cost_treatment"], "explicitly_zero_unpriced")
            self.assertEqual(row["net_scc_ready"], "false")
        self.assertEqual(self.readiness["agriculture_net_adaptation_scc_status"], "BLOCKED")

    def test_fredi_costs_are_not_added_twice(self):
        for model in ("FrEDI Roads", "FrEDI Rail", "FrEDI ElecTD"):
            for scenario in ("Reactive", "Proactive"):
                row = self.row(model, scenario)
                self.assertEqual(row["cost_treatment"], "embedded_in_total")
                rule = row["double_count_rule"].lower()
                self.assertTrue("add" in rule or "once" in rule)

    def test_ciam_is_explicit_and_single_counted(self):
        row = self.row("GIVE CIAM", "Optimized protection-retreat-no-adapt")
        self.assertEqual(row["cost_treatment"], "explicit_modeled")
        self.assertEqual(row["net_scc_ready"], "true")
        self.assertIn("once", row["double_count_rule"].lower())

    def test_inland_flood_is_not_adapted(self):
        row = self.row("FrEDI Inland Flooding", "NoAdapt")
        self.assertEqual(row["cost_treatment"], "not_applicable_baseline")

    def test_bounded_cost_evidence_is_not_mapped(self):
        self.assertEqual(self.benchmark["give_mapping_available"], "false")
        self.assertEqual(self.benchmark["scc_ready"], "false")
        self.assertLess(self.benchmark["low_billion_usd_per_year"], self.benchmark["high_billion_usd_per_year"])


if __name__ == "__main__":
    unittest.main()
