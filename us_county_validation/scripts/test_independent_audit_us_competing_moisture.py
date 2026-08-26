#!/usr/bin/env python3
"""Adversarial synthetic tests for the independent U.S. moisture audit."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from independent_audit_us_competing_moisture import (
    compare_key_support,
    endpoint_set,
    forbidden_output_keys,
    promotion_summaries,
    purge_endpoints,
    qr_fit_metrics,
)


class IndependentMoistureAuditTests(unittest.TestCase):
    def test_endpoint_purge_removes_both_adjacent_differences_only_within_series(self) -> None:
        frame = pd.DataFrame(
            [
                (county, "corn_grain", "irrigated", year)
                for county in ["01001", "01003"]
                for year in [2001, 2002, 2003, 2004]
            ],
            columns=["county_geoid", "outcome_crop", "irrigation_practice", "harvest_year"],
        )
        test = (
            frame.county_geoid.eq("01001") & frame.harvest_year.eq(2002)
        ).to_numpy(dtype=bool)
        train_before = ~test
        train, removed = purge_endpoints(frame, train_before, test)
        retained = set(
            frame.loc[train, ["county_geoid", "harvest_year"]].itertuples(
                index=False, name=None
            )
        )
        self.assertEqual(removed, 2)
        self.assertNotIn(("01001", 2001), retained)
        self.assertNotIn(("01001", 2003), retained)
        self.assertIn(("01001", 2004), retained)
        self.assertIn(("01003", 2002), retained)
        self.assertFalse(endpoint_set(frame, train) & endpoint_set(frame, test))

    def test_training_only_scale_drops_column_varying_only_in_test(self) -> None:
        count = 16
        years = np.arange(1990, 1990 + count)
        frame = pd.DataFrame({
            "harvest_year": years,
            "x_signal": np.sin(np.arange(count) * 0.73) + np.arange(count) * 0.01,
            "x_test_only": np.r_[np.zeros(12), [10.0, -20.0, 30.0, -40.0]],
        })
        frame["delta_log_yield"] = (
            0.03 * frame.x_signal
            + 0.002 * np.cos(np.arange(count) * 1.17)
            + 0.0001 * (years - years.mean()) ** 2
        )
        train = np.arange(count) < 12
        test = ~train
        first = qr_fit_metrics(frame, ["x_signal", "x_test_only"], train, test, 1e-10, 1e-8, 1e-10)
        frame.loc[test, "x_test_only"] *= 1e100
        second = qr_fit_metrics(frame, ["x_signal", "x_test_only"], train, test, 1e-10, 1e-8, 1e-10)
        self.assertEqual(first["zero_variance_columns_dropped_train_only"], 1)
        self.assertEqual(second["zero_variance_columns_dropped_train_only"], 1)
        self.assertEqual(first["design_columns_including_intercept"], 4)
        for field in ["rmse", "mae", "r2_oos", "correlation"]:
            self.assertAlmostEqual(first[field], second[field], places=15)

    @staticmethod
    def _promotion_rows(blocking_second_state: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for state, distribution_rmse in [
            ("AA", 0.197),
            ("BB", 0.199 if blocking_second_state else 0.197),
        ]:
            for model, rmse in [
                ("direct_quantity", 0.2),
                ("direct_quantity_distribution", distribution_rmse),
                ("pdsi_season_mean", 0.205),
            ]:
                rows.append({
                    "crop": "corn_grain",
                    "irrigation_practice": "irrigated",
                    "split": "development_leave_state_out",
                    "split_id": state,
                    "model": model,
                    "rmse": rmse,
                })
        for split, split_id in [
            ("terminal_temporal_same_counties", "terminal"),
            ("development_precipitation_extreme", "tails"),
        ]:
            for model, rmse in [
                ("direct_quantity", 0.2),
                ("direct_quantity_distribution", 0.19),
                ("pdsi_season_mean", 0.21),
            ]:
                rows.append({
                    "crop": "corn_grain",
                    "irrigation_practice": "irrigated",
                    "split": split,
                    "split_id": split_id,
                    "model": model,
                    "rmse": rmse,
                })
        return rows

    def test_promotion_requires_both_floors_in_every_development_state(self) -> None:
        protocol = {"validation": {
            "distribution_minimum_absolute_rmse_improvement": 0.0001,
            "distribution_minimum_relative_rmse_improvement": 0.01,
        }}
        blocked = promotion_summaries(self._promotion_rows(True), protocol)[0]
        passing = promotion_summaries(self._promotion_rows(False), protocol)[0]
        self.assertFalse(blocked["direct_distribution_selected_on_development_leave_state_out"])
        self.assertAlmostEqual(
            blocked["direct_distribution_required_material_rmse_floor_each_eligible_state"]["BB"],
            0.002,
        )
        self.assertLess(
            blocked["direct_distribution_rmse_excess_over_material_floor_each_eligible_state"]["BB"],
            0,
        )
        self.assertTrue(passing["direct_distribution_selected_on_development_leave_state_out"])

    def test_support_and_serialized_leak_checks_fail_closed(self) -> None:
        columns = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice"]
        left = pd.DataFrame([["01001", "corn_grain", 2001, "irrigated"]], columns=columns)
        right = pd.DataFrame([["01003", "corn_grain", 2001, "irrigated"]], columns=columns)
        with self.assertRaisesRegex(AssertionError, "key support differs"):
            compare_key_support(left, right, "synthetic mismatch")
        leaks = forbidden_output_keys({
            "coefficients_in_output": False,
            "row_predictions_in_output": False,
            "metrics": [{"coefficient_vector": [1.0], "county_prediction": 2.0}],
        })
        self.assertEqual(
            leaks,
            ["metrics[0].coefficient_vector", "metrics[0].county_prediction"],
        )


if __name__ == "__main__":
    unittest.main()
