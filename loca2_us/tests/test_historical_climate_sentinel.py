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

    def test_variable_serial_basis_matches_full_basis(self):
        rng = np.random.default_rng(20261013)
        days, cells = 170, 7
        rain = rng.gamma(1.3, 2.5, size=(days, cells))
        rain[rng.random((days, cells)) < 0.7] = 0.0
        tmin = rng.normal(11.0, 5.0, size=(days, cells))
        tmax = tmin + rng.uniform(3.0, 17.0, size=(days, cells))
        positions = np.arange(cells)
        full = MODULE.build_basis_frame(rain, tmin, tmax, positions, 1.0)[MODULE.FEATURES]
        serial = MODULE.build_variable_serial_basis_frame(
            rain, tmin.mean(axis=0), tmax.mean(axis=0), positions, 1.0
        )[MODULE.FEATURES]
        self.assertTrue(np.allclose(full.to_numpy(), serial.to_numpy(), rtol=0, atol=1e-12))

    def test_direct_zarr_reader_reconstructs_selected_cells(self):
        class Array:
            def __init__(self, values):
                self.values = values
            def __getitem__(self, key):
                return self.values[key]
        values = np.arange(1 * 8 * 4 * 6, dtype=float).reshape(1, 8, 4, 6)
        times = np.array([1, 2, 5, 6])
        lat = np.array([0, 1, 1])
        lon = np.array([3, 4, 5])
        result = MODULE.read_zarr_selected_cells(Array(values), 0, times, lat, lon, (1, 4, 2, 3))
        expected = values[0, times][:, lat, lon]
        self.assertTrue(np.array_equal(result, expected))


if __name__ == "__main__":
    unittest.main()
