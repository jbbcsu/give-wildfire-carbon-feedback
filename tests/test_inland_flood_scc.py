import csv
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_inland_flood_scc import interpolate  # noqa: E402


class InlandFloodTests(unittest.TestCase):
    def test_interpolation_and_extrapolation(self):
        curve = {Decimal(0): Decimal(0), Decimal(1): Decimal(10), Decimal(2): Decimal(30)}
        self.assertEqual(interpolate(curve, Decimal("0.5")), Decimal(5))
        self.assertEqual(interpolate(curve, Decimal("2.5")), Decimal(40))

    def test_source_contract(self):
        with (ROOT / "data/reference/InlandFlooding_scaledimpacts.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 245)
        self.assertEqual({row["sector"] for row in rows}, {"InlandFlooding"})
        self.assertEqual({row["model"] for row in rows}, {"GCM Ensemble"})
        self.assertEqual(len({row["postal"] for row in rows}), 49)

    def test_claim_gates(self):
        config = json.loads((ROOT / "config/inland_flood_scc_v1.json").read_text())
        self.assertFalse(config["claim_gates"]["global_scc_authorized"])
        self.assertFalse(config["claim_gates"]["pluvial_flooding_included"])
        self.assertIn("roads and rail", config["scope"]["excluded"])

    def test_finished_result_if_present(self):
        path = ROOT / "results/inland_flood_partial_scc_summary_v1.csv"
        if not path.exists():
            self.skipTest("run the benchmark first")
        with path.open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([int(row["horizon"]) for row in rows], [2092, 2246, 2300])
        self.assertAlmostEqual(float(rows[-1]["partial_scc_2020usd_per_tco2"]), 0.014246408098, places=12)


if __name__ == "__main__":
    unittest.main()
