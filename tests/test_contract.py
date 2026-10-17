import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class EducationHeatContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "config/education_heat_contract_v1.json").read_text())

    def test_no_scc_authorization(self):
        self.assertFalse(self.cfg["scope"]["give_addition_authorized"])
        self.assertFalse(self.cfg["scope"]["lifetime_income_conversion_authorized"])

    def test_marginal_and_valuation_gates_closed(self):
        gates = self.cfg["claim_gates"]
        self.assertFalse(gates["matched_marginal_school_day_climate_response"])
        self.assertFalse(gates["consumer_welfare_measure_available"])

    def test_registry_contains_cross_context_evidence(self):
        path = ROOT / self.cfg["sources"]["evidence_registry"]["path"]
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual({r["study_id"] for r in rows}, {"park_2020", "park_2021", "graff_zivin_2018", "garg_2020"})

    def test_no_scc_results(self):
        results = ROOT / "results"
        self.assertFalse(results.exists() and any(results.iterdir()))

if __name__ == "__main__":
    unittest.main()
