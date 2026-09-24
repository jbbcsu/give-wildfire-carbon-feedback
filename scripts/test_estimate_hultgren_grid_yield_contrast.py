#!/usr/bin/env python3

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from estimate_hultgren_grid_yield_contrast import adaptation_factor, design_matrix, quantity_counterfactual


class YieldTransportTests(unittest.TestCase):
    def basis(self, rain: tuple[float, float, float], squares: tuple[float, float, float]) -> pd.DataFrame:
        return pd.DataFrame({
            "gdd": [10.0], "kdd": [1.0],
            "prcp_poly_1_bin1": [rain[0]], "prcp_poly_1_bin2": [rain[1]], "prcp_poly_1_bin3": [rain[2]],
            "prcp_poly_2_bin1": [squares[0]], "prcp_poly_2_bin2": [squares[1]], "prcp_poly_2_bin3": [squares[2]],
            "ln_gdppc": [9.0], "irrigated_share": [0.2], "lr_tmax_crop": [25.0], "lr_prcp_crop": [100.0],
        })

    def test_design_interaction(self) -> None:
        frame = self.basis((1.0, 2.0, 3.0), (1.0, 4.0, 9.0))
        result = design_matrix(frame, ["gdd", "c.gdd#c.ln_gdppc", "_cons"])
        np.testing.assert_allclose(result, [[10.0, 90.0, 1.0]])

    def test_quantity_path_matches_total_and_scales_squares(self) -> None:
        reference = self.basis((1.0, 2.0, 3.0), (1.0, 4.0, 9.0))
        comparison = self.basis((2.0, 4.0, 6.0), (4.0, 16.0, 36.0))
        result, common = quantity_counterfactual(reference, comparison)
        self.assertTrue(common[0])
        self.assertAlmostEqual(result[["prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3"]].sum(axis=1).iloc[0], 12.0)
        self.assertAlmostEqual(result.prcp_poly_2_bin3.iloc[0], 36.0)

    def test_adaptation_defaults(self) -> None:
        self.assertEqual(adaptation_factor(2100, "fixed"), 1.0)
        self.assertEqual(adaptation_factor(2100, "trend"), 0.76)
        self.assertAlmostEqual(adaptation_factor(2100, "upper"), 0.44)


if __name__ == "__main__":
    unittest.main()
