import csv, json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
class TestContract(unittest.TestCase):
    def setUp(self): self.cfg = json.loads((ROOT / "config/heat_morbidity_contract_v1.json").read_text())
    def test_fail_closed(self):
        self.assertEqual(self.cfg["status"], "BLOCKED_NO_MARGINAL_SCC")
        self.assertFalse(self.cfg["scope"]["give_addition_authorized"])
    def test_forbidden_overlap(self):
        excluded = set(self.cfg["scope"]["excluded"])
        self.assertTrue({"mortality", "lost wages", "labor productivity", "air pollution", "infectious disease"}.issubset(excluded))
    def test_reported_values(self):
        with (ROOT / self.cfg["sources"]["lay_2018"]["reported_evidence"]).open(newline="") as f: rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 4); self.assertEqual(int(rows[-1]["incremental_ed_visits"]), 65136)
        self.assertEqual(float(rows[-1]["meps_direct_medical_cost_million_2015usd"]), 118.5)
    def test_no_scc_results(self): self.assertFalse(list((ROOT / "results").glob("*scc*.csv")))

if __name__ == "__main__": unittest.main()
