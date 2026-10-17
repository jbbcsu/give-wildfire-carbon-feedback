import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_labor_give_integration as integration


CONFIG = ROOT / "config/labor_give_integration_v1.json"


class LaborGiveIntegrationTests(unittest.TestCase):
    def test_exact_target_mean_bridge_completes(self):
        result = integration.build_integration(ROOT, CONFIG)
        self.assertEqual(result["status"], "complete_mean_integration_with_case_specific_uncertainty")
        central = result["equal_weight_structural_result"]
        self.assertAlmostEqual(central["additive_labor_mean_2020usd_per_tco2"], 40.56425698048089)
        self.assertAlmostEqual(central["target_without_labor_mean_2020usd_per_tco2"], 138.59385734211905)
        self.assertAlmostEqual(central["target_with_labor_mean_2020usd_per_tco2"], 179.15811432259994)
        self.assertAlmostEqual(central["mean_additivity_residual_2020usd_per_tco2"], 0.0)
        self.assertIsNone(central["pooled_uncertainty_interval"])

    def test_cases_retain_valid_same_run_total_uncertainty(self):
        result = integration.build_integration(ROOT, CONFIG)
        self.assertAlmostEqual(result["cases"]["ISO"]["full_target_uncertainty_within_case"]["q95"], 364.9383136120538)
        self.assertAlmostEqual(result["cases"]["LANCET"]["full_target_uncertainty_within_case"]["q95"], 310.7450886048792)
        self.assertFalse(result["validation"]["cross_function_uncertainty_pooled"])

    def test_active_sector_overlap_fails_closed(self):
        config = json.loads(CONFIG.read_text())
        config["target_model"]["preexisting_labor_in_original_give"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "overlap gate"):
                integration.build_integration(ROOT, path)

    def test_relaxed_additivity_tolerance_fails_closed(self):
        config = json.loads(CONFIG.read_text())
        config["validation"]["component_mean_additivity_absolute_tolerance"] = 0.01
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "too loose"):
                integration.build_integration(ROOT, path)

    def test_uncertainty_pooling_fails_closed(self):
        config = json.loads(CONFIG.read_text())
        config["validation"]["allow_cross_function_quantile_pooling"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "hard gate"):
                integration.build_integration(ROOT, path)


if __name__ == "__main__":
    unittest.main()
