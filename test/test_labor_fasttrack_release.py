import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_labor_fasttrack_release as release


CONFIG = ROOT / "config/labor_fasttrack_release_v1.json"


class LaborFasttrackReleaseTests(unittest.TestCase):
    def test_release_is_labor_only_and_reproduces_central_value(self):
        result = release.build_release(ROOT, CONFIG)
        self.assertEqual(result["sector"], "heat-related labor productivity")
        self.assertAlmostEqual(result["estimate"]["central_equal_weight_mean_2020usd_per_tco2"], 40.56425698048089)
        self.assertEqual(result["estimate"]["structural_case_mean_range_2020usd_per_tco2"], [29.2638359626996, 51.86467799826219])
        self.assertIsNone(result["estimate"]["pooled_quantiles"])
        self.assertIsNone(result["estimate"]["pooled_standard_error"])
        self.assertNotIn("agriculture", result["estimate"])
        self.assertNotIn("total", result["estimate"])

    def test_receipt_tampering_fails_closed(self):
        config = json.loads(CONFIG.read_text())
        config["receipts"]["ISO"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                release.build_release(ROOT, path)

    def test_opening_uncertainty_pooling_gate_fails_closed(self):
        config = json.loads(CONFIG.read_text())
        config["accounting_rules"]["allow_cross_function_quantile_pooling"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "quantile pooling"):
                release.build_release(ROOT, path)

    def test_including_updated_agriculture_fails_closed(self):
        config = json.loads(CONFIG.read_text())
        config["accounting_rules"]["include_updated_agriculture"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "labor only"):
                release.build_release(ROOT, path)


if __name__ == "__main__":
    unittest.main()
