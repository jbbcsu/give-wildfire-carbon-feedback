import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class FreshwaterAnglingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "config/freshwater_angling_contract_v1.json").read_text())

    def test_not_authorized_as_scc_or_global_transfer(self):
        self.assertFalse(self.cfg["scope"]["give_addition_authorized"])
        self.assertFalse(self.cfg["scope"]["global_transfer_authorized"])

    def test_excludes_prior_endpoints(self):
        excluded = " ".join(self.cfg["scope"]["excluded"]).lower()
        self.assertIn("ocean fisheries", excluded)
        self.assertIn("fredi water-quality", excluded)

    def test_reported_table_structure(self):
        path = ROOT / self.cfg["reported_benchmark"]["path"]
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 24)
        self.assertEqual({r["endpoint"] for r in rows}, {"all_fishing", "coldwater_fishing"})

    def test_no_results_directory(self):
        path = ROOT / "results"
        self.assertFalse(path.exists() and any(path.iterdir()))

if __name__ == "__main__":
    unittest.main()
