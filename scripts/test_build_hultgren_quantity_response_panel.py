#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from build_hultgren_quantity_response_panel import FEATURES, effective_precip_coefficients
from estimate_hultgren_grid_yield_contrast import MODERATORS, WEATHER, design_matrix
from src.hultgren_maize_response import PublishedEstimate

ROOT = Path(__file__).resolve().parents[1]


class QuantityResponsePanelTests(unittest.TestCase):
    def test_closed_form_matches_direct_design_difference(self) -> None:
        estimate = PublishedEstimate.from_exports(
            ROOT / "data/interim/hultgren_maize_response_20260923/coefficients.csv",
            ROOT / "data/interim/hultgren_maize_response_20260923/covariance.csv",
        )
        row = {feature: value for feature, value in zip(FEATURES, [70.0, 250.0, 90.0, 6500.0, 30000.0, 9000.0], strict=True)}
        row.update({"gdd": 1200.0, "kdd": 40.0, "ln_gdppc": 9.4, "irrigated_share": 0.35, "lr_tmax_crop": 27.0, "lr_prcp_crop": 180.0})
        baseline = pd.DataFrame([row])
        effective = effective_precip_coefficients(baseline, estimate)
        linear = sum(row[feature] * effective[f"effective_{feature}"].iloc[0] for feature in FEATURES[:3])
        squared = sum(row[feature] * effective[f"effective_{feature}"].iloc[0] for feature in FEATURES[3:])
        for change in (-0.12, 0.0, 0.08):
            comparison = baseline.copy()
            comparison[FEATURES[:3]] *= 1.0 + change
            comparison[FEATURES[3:]] *= (1.0 + change) ** 2
            direct = float(((design_matrix(comparison, estimate.terms) - design_matrix(baseline, estimate.terms)) @ estimate.coefficients)[0])
            closed = (linear + 2.0 * squared) * change + squared * change**2
            self.assertAlmostEqual(direct, closed, places=12)


if __name__ == "__main__":
    unittest.main()
