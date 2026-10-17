import csv
import hashlib
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ForestryBenchmarkTests(unittest.TestCase):
    def test_contract_is_fail_closed(self):
        contract = json.loads((ROOT / "contracts/forestry_market_contract.json").read_text())
        self.assertFalse(contract["additive_to_GIVE"])
        self.assertEqual(contract["positive_sign"], "damage")
        self.assertIn("nonmarket_ecosystem_services", contract["excluded_endpoints"])
        self.assertGreaterEqual(len(contract["blocking_gates"]), 3)

    def test_manifest_is_pinned_and_unique(self):
        with (ROOT / "config/source_manifest.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 5)
        self.assertEqual({r["version"] for r in rows}, {"v3.13.0"})
        self.assertEqual(len({r["commit"] for r in rows}), 1)
        self.assertEqual(len({r["path"] for r in rows}), len(rows))
        for row in rows:
            self.assertEqual(len(row["sha256"]), 64)

    def test_currency_multiplier(self):
        with (ROOT / "config/currency.csv").open() as handle:
            row = next(csv.DictReader(handle))
        expected = float(row["target_index"]) / float(row["source_index"])
        self.assertAlmostEqual(float(row["multiplier"]), expected, places=12)

    def test_results_when_present(self):
        path = ROOT / "results/summary.csv"
        if not path.exists():
            self.skipTest("benchmark has not been run")
        with path.open() as handle:
            values = {r["metric"]: float(r["value"]) for r in csv.DictReader(handle)}
        self.assertLess(values["central_fixed_0p020_2020usd"], 0.0)
        self.assertLess(values["pulse_linearity_relative_error"], 1e-4)
        horizon_change = abs(values["fixed_2pct_horizon_3000_2020usd"] /
                             values["central_fixed_0p020_2020usd"] - 1)
        self.assertLess(horizon_change, 0.005)

        sensitivity_path = ROOT / "results/parameter_sensitivity_fixed_2pct_2020usd.csv"
        self.assertTrue(sensitivity_path.exists())
        with sensitivity_path.open() as handle:
            sensitivity = list(csv.DictReader(handle))
        self.assertEqual(len(sensitivity), 9)
        self.assertEqual(sum(r["scenario"] == "central" for r in sensitivity), 1)


if __name__ == "__main__":
    unittest.main()
