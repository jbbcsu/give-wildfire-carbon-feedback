import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "build_historical_climate_sentinel.py"
SPEC = importlib.util.spec_from_file_location("loca2_historical_sentinel", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class HistoricalSentinelTests(unittest.TestCase):
    def test_distribution_comparison(self):
        years = [2001, 2002, 2003]
        model = pd.DataFrame({"harvest_year": years})
        observed = pd.DataFrame({"harvest_year": years})
        for index, feature in enumerate(MODULE.FEATURES, start=1):
            observed[feature] = [index, index + 1, index + 2]
            model[feature] = [index + 1, index + 2, index + 3]
        result = MODULE.compare_distributions(model, observed)
        self.assertAlmostEqual(result["precip_mm"]["climatology_bias_model_minus_observed"], 1.0)
        self.assertAlmostEqual(result["precip_mm"]["standard_deviation_ratio"], 1.0)
        self.assertAlmostEqual(result["precip_mm"]["quantile_rmse"], 1.0)

    def test_year_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "years differ"):
            MODULE.compare_distributions(pd.DataFrame({"harvest_year": [1]}), pd.DataFrame({"harvest_year": [2]}))


if __name__ == "__main__":
    unittest.main()
