import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "summarize_cuming_two_model_climate_sentinels.py"
SPEC = importlib.util.spec_from_file_location("loca2_two_model", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def fake_receipt(model_mean, observed_mean, quantiles, bias, sd_ratio, qrmse):
    return {
        "comparisons": {
            "x": {
                "model_mean": model_mean,
                "observed_mean": observed_mean,
                "observed_quantiles": quantiles,
                "climatology_bias_model_minus_observed": bias,
                "standard_deviation_ratio": sd_ratio,
                "quantile_rmse": qrmse,
            }
        }
    }


class TwoModelClimateSentinelTests(unittest.TestCase):
    def test_equal_gcm_summary(self):
        receipts = {
            "GFDL-ESM4": fake_receipt(8.0, 10.0, [5.0, 10.0], -2.0, 0.8, 3.0),
            "IPSL-CM6A-LR": fake_receipt(12.0, 10.0, [5.0, 10.0], 2.0, 1.2, 1.0),
        }
        result = MODULE.summarize(receipts)["x"]
        self.assertEqual(result["equal_gcm_mean_model_climatology"], 10.0)
        self.assertEqual(result["equal_gcm_mean_climatology_bias"], 0.0)
        self.assertEqual(result["model_bias_minimum"], -2.0)
        self.assertEqual(result["model_bias_maximum"], 2.0)
        self.assertEqual(result["equal_gcm_mean_of_model_quantile_rmse"], 2.0)

    def test_reference_mismatch_fails_closed(self):
        receipts = {
            "GFDL-ESM4": fake_receipt(8.0, 10.0, [5.0, 10.0], -2.0, 0.8, 3.0),
            "IPSL-CM6A-LR": fake_receipt(12.0, 11.0, [5.0, 11.0], 1.0, 1.2, 1.0),
        }
        with self.assertRaisesRegex(ValueError, "observed mean differs"):
            MODULE.summarize(receipts)


if __name__ == "__main__":
    unittest.main()
