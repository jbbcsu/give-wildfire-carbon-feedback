import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "config/water_quality_conus_partial_scc_v1.json").read_text())

    def test_scope_fails_closed(self):
        self.assertFalse(self.config["scope"]["global_extrapolation_authorized"])
        self.assertFalse(self.config["scope"]["cross_sector_additivity_authorized"])
        self.assertFalse(self.config["claim_gates"]["additive_give_scc_allowed"])

    def test_nonmarket_endpoint_is_distinct(self):
        endpoint = self.config["scope"]["endpoint"].lower()
        self.assertIn("willingness-to-pay", endpoint)
        excluded = " ".join(self.config["overlap_exclusions"])
        self.assertIn("commercial_agriculture", excluded)
        self.assertIn("marine_fisheries", excluded)

    def test_results_exist_and_are_bounded(self):
        with (ROOT / self.config["outputs"]["summary"]).open(newline="") as stream:
            summary = list(csv.DictReader(stream))
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["scope"], "CONUS_48_plus_DC")
        self.assertEqual(summary[0]["gcm_count"], "5")

    def test_validation_passed(self):
        result = json.loads((ROOT / self.config["outputs"]["validation"]).read_text())
        self.assertTrue(result["passed"])


if __name__ == "__main__": unittest.main()
