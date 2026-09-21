#!/usr/bin/env python3
"""Synthetic algebra checks for the county-fixed-effect prediction benchmark."""
import numpy as np
import pandas as pd

from estimate_us_county_average_terminal_prediction import (
    MODELS, bootstrap_rmse_difference, design, fit_within, metrics, predict,
    row_dot as estimator_row_dot,
)
from validate_us_county_average_terminal_prediction import row_dot as audit_row_dot


def run() -> None:
    counties = np.repeat(np.asarray(["a", "b", "c"]), 12)
    years = np.tile(np.arange(1990, 2002), 3)
    x = np.column_stack([(years - 2000) / 10, np.tile(np.linspace(-1, 1, 12), 3)])
    x[:, 1] += np.repeat([0.0, 0.2, -0.3], 12) + np.tile([0.0, 0.1, -0.1], 12)
    beta = np.asarray([0.3, -0.6])
    intercept = np.repeat([1.0, 2.0, 3.0], 12)
    y = intercept + x @ beta
    fitted = fit_within(y, x, counties)
    assert np.allclose(fitted["beta"], beta, atol=1e-10)
    assert np.allclose(predict(fitted, x, counties), y, atol=1e-10)
    score = metrics(y, y + 0.2)
    assert np.isclose(score["rmse_log_yield"], 0.2)
    boot = bootstrap_rmse_difference(y, y + 0.2, y + 0.1,
                                     np.repeat(["AA", "BB", "CC"], 12), seed=7, replicates=30)
    assert np.isclose(boot["point_difference"], 0.1)
    frame = pd.DataFrame({"harvest_year": [2000, 2001], "precip_mm": [100, 200],
                          "tmean_c": [20, 21], "tmax_exceedance_29c_c_days": [30, 40],
                          "wet_days_ge_1mm": [10, 20], "cdd_max_days": [5, 6],
                          "rx5day_mm": [22, 23], "stage1_precip_share": [0.2, 0.3],
                          "stage2_precip_share": [0.4, 0.5]})
    assert [design(frame, model)[0].shape[1] for model in MODELS] == [1, 5, 10]
    matrix = np.asarray([[1.0, 2.0], [-3.0, 4.0]])
    assert np.allclose(estimator_row_dot(matrix, np.asarray([0.5, -2.0])), [-3.5, -9.5])
    assert np.allclose(audit_row_dot(matrix, np.asarray([0.5, -2.0])), [-3.5, -9.5])
    for bad_matrix, bad_vector in ((matrix, np.asarray([1.0])),
                                   (np.asarray([[np.nan, 1.0]]), np.ones(2))):
        try:
            estimator_row_dot(bad_matrix, bad_vector)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid estimator row-dot input was accepted")
        try:
            audit_row_dot(bad_matrix, bad_vector)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid independent row-dot input was accepted")
    print("synthetic fixed-effect, prediction, bootstrap and design checks passed")


if __name__ == "__main__":
    run()
