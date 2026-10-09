import importlib.util
import unittest
from pathlib import Path

import numpy as np
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

    def test_spatial_partition_accumulator_is_bit_exact(self):
        rng = np.random.default_rng(20261004)
        days, cells = 170, 11
        rain = rng.gamma(1.4, 3.0, size=(days, cells))
        rain[rng.random((days, cells)) < 0.65] = 0.0
        tmin = rng.normal(12.0, 4.0, size=(days, cells))
        tmax = tmin + rng.uniform(4.0, 18.0, size=(days, cells))
        weights = rng.uniform(size=cells)
        weights /= weights.sum()
        legacy_basis = pd.DataFrame([
            MODULE.build_cell_basis(
                rain[:, cell],
                (tmin[:, cell] + tmax[:, cell]) / 2,
                tmin[:, cell],
                tmax[:, cell],
                1.0,
            )
            for cell in range(cells)
        ])
        full = {
            column: float(np.dot(legacy_basis[column].to_numpy(dtype=float), weights))
            for column in legacy_basis.columns
        }
        split = MODULE.aggregate_spatial_partitions(
            rain,
            tmin,
            tmax,
            weights,
            [np.array([0, 1, 4, 8]), np.array([2, 3, 6]), np.array([5, 7, 9, 10])],
            1.0,
        )
        self.assertEqual(full, split)

    def test_spatial_partition_accumulator_rejects_missing_cell(self):
        values = np.ones((170, 3))
        with self.assertRaisesRegex(ValueError, "overlap or omit"):
            MODULE.aggregate_spatial_partitions(
                values, values, values + 1, np.full(3, 1 / 3), [np.array([0, 2])], 1.0
            )


if __name__ == "__main__":
    unittest.main()
