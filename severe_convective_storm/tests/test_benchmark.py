import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_benchmark


class HailBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row, cls.readiness = build_benchmark.build()
        cls.source = build_benchmark.load_json(ROOT / "config" / "published_benchmark.json")
        cls.contract = build_benchmark.load_json(ROOT / "contracts" / "hail_property_contract.json")

    def test_published_arithmetic(self):
        self.assertEqual(self.row["difference_chf_per_year"], 16_000_000)
        self.assertAlmostEqual(float(self.row["exact_relative_change"]), 16 / 74, places=11)
        self.assertEqual(round(float(self.row["exact_relative_change"]), 2), 0.22)

    def test_fails_closed_for_scc(self):
        self.assertFalse(self.source["scc_ready"])
        self.assertFalse(self.contract["additive_to_give"])
        self.assertEqual(self.readiness["status"], "BLOCKED_FROM_SCC_BY_DESIGN")
        self.assertGreaterEqual(len(self.readiness["missing"]), 6)

    def test_currency_price_year_is_not_invented(self):
        self.assertIsNone(self.source["currency_price_year"])

    def test_required_exclusions(self):
        exclusions = " ".join(self.contract["excluded_endpoints"]).lower()
        for term in ("agricultural", "vehicle", "tornado", "flood", "tropical cyclone", "wildfire", "roads", "grid"):
            self.assertIn(term, exclusions)

    def test_no_scc_like_output_fields(self):
        with (ROOT / "results" / "swiss_hail_benchmark.csv").open(encoding="utf-8") as stream:
            fields = csv.DictReader(stream).fieldnames
        lowered = " ".join(fields).lower()
        self.assertNotIn("usd", lowered)
        self.assertNotIn("tco2", lowered)
        self.assertNotIn("global", lowered)


if __name__ == "__main__":
    unittest.main()
