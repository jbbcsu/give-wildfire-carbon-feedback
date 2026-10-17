import csv
import json
import subprocess
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TransportPartialSCCTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        validation_path = Path(cls.tempdir.name) / "validation.json"
        subprocess.run(
            ["python3", "scripts/validate_fredi_transport_conus_partial_scc.py", "--output", str(validation_path)],
            cwd=ROOT, check=True, capture_output=True,
        )
        cls.config = json.loads((ROOT / "config/fredi_transport_conus_partial_scc_v1.json").read_text())
        cls.validation = json.loads(validation_path.read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tempdir.cleanup()

    def test_validation_passes(self):
        self.assertEqual(self.validation["status"], "PASS")
        self.assertTrue(self.validation["independent_raw_table_recomputation"])

    def test_scope_is_fail_closed(self):
        self.assertFalse(self.config["scope"]["global_extrapolation_authorized"])
        self.assertFalse(self.config["scope"]["additivity_to_other_give_sectors_authorized"])
        self.assertEqual(self.validation["global_extrapolation"], "PROHIBITED")
        self.assertEqual(self.validation["cross_sector_additivity"], "NOT_AUTHORIZED")

    def test_common_support_is_truncated(self):
        self.assertEqual(self.validation["common_support_years"], [2025, 2092])
        self.assertEqual(self.validation["first_excluded_year"], 2093)

    def test_primary_result_is_positive_and_bounded(self):
        path = ROOT / self.config["outputs"]["summary"]
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        primary = next(row for row in rows if row["variant"] == "Reactive" and row["component"] == "Roads_plus_Rail")
        low = Decimal(primary["min_partial_scc_2020usd_per_tco2"])
        mean = Decimal(primary["mean_partial_scc_2020usd_per_tco2"])
        high = Decimal(primary["max_partial_scc_2020usd_per_tco2"])
        self.assertLessEqual(low, mean)
        self.assertLessEqual(mean, high)
        self.assertGreater(mean, 0)

    def test_adaptation_sensitivity_is_reported(self):
        path = ROOT / self.config["outputs"]["summary"]
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual({row["variant"] for row in rows}, {"NoAdapt", "Proactive", "Reactive"})
        self.assertEqual(len(rows), 9)


if __name__ == "__main__":
    unittest.main()
