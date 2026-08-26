#!/usr/bin/env python3
"""Independent numerical and adversarial tests for the SPEI distribution."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from spei_distribution import (
    CDF_CLIP_LOWER,
    CDF_CLIP_MISSING,
    CDF_CLIP_UPPER,
    FIT_STATUS_DEGENERATE,
    FIT_STATUS_INVALID_SHAPE,
    FIT_STATUS_MISSING_CALIBRATION,
    GloFitError,
    GloParameters,
    fit_glo_ubpwm,
    glo_cdf,
    standardize_glo,
    unbiased_probability_weighted_moments,
)


ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "data/fixtures/spei_cran_1_8_1_synthetic_oracle.json"


def rejected(expected_status: int, function, *args, **kwargs) -> None:
    try:
        function(*args, **kwargs)
    except GloFitError as error:
        assert error.status == expected_status, (error.status, error)
    else:
        raise AssertionError(f"invalid fit accepted; expected status {expected_status}")


def synthetic_series() -> tuple[pd.DatetimeIndex, np.ndarray]:
    dates = pd.date_range("1981-01-01", "2019-12-01", freq="MS")
    year = dates.year.to_numpy()
    month = dates.month.to_numpy()
    balance = (
        (month - 6.5) * 1.7
        + (((year - 1980) * 37 + month * 11) % 29 - 14) * 0.9
        + (((year - 1980) * month) % 7) * 0.13
    )
    return dates, balance.astype(np.float64)


def dummy_parameters(xi: float, alpha: float, kappa: float) -> GloParameters:
    return GloParameters(
        xi=xi,
        alpha=alpha,
        kappa=kappa,
        sample_size=30,
        beta0=0.0,
        beta1=0.0,
        beta2=0.0,
        l1=0.0,
        l2=alpha,
        tau3=-kappa,
    )


def main() -> None:
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    assert oracle["reference"]["package"] == "SPEI"
    assert oracle["reference"]["version"] == "1.8.1"
    dates, balance = synthetic_series()
    selected = np.asarray(oracle["selected_one_based_indices"], dtype=int) - 1

    # These frozen values were emitted by an independently installed official
    # CRAN SPEI 1.8.1 environment.  No reference implementation is imported.
    for scale in (1, 3, 6):
        accumulated = pd.Series(balance).rolling(scale, min_periods=scale).sum().to_numpy()
        actual_spei = np.full(accumulated.shape, np.nan)
        actual_parameters: dict[int, tuple[float, float, float]] = {}
        for calendar_month in range(1, 13):
            fit_mask = (
                (dates.year >= 1982)
                & (dates.year <= 2011)
                & (dates.month == calendar_month)
            )
            parameters = fit_glo_ubpwm(accumulated[fit_mask])
            actual_parameters[calendar_month] = (
                parameters.xi,
                parameters.alpha,
                parameters.kappa,
            )
            application_mask = dates.month == calendar_month
            actual_spei[application_mask] = standardize_glo(
                accumulated[application_mask], parameters
            ).spei
        for month, expected in zip(
            oracle["coefficient_columns"],
            oracle["coefficients_by_scale"][str(scale)],
            strict=True,
        ):
            assert np.allclose(actual_parameters[month], expected, rtol=0.0, atol=5e-12)
        expected_scores = np.asarray(
            [np.nan if value is None else value for value in oracle["spei_by_scale"][str(scale)]],
            dtype=np.float64,
        )
        assert np.allclose(actual_spei[selected], expected_scores, rtol=0.0, atol=7e-12, equal_nan=True)

    january = balance[(dates.year >= 1982) & (dates.year <= 2011) & (dates.month == 1)]
    expected_pwm = oracle["jan_scale_1_ubpwm"]["beta"]
    actual_pwm = unbiased_probability_weighted_moments(january[::-1])
    assert np.allclose(actual_pwm, expected_pwm, rtol=0.0, atol=2e-14)

    # Degenerate, incomplete, nonfinite, and maximally skewed calibrations fail
    # with classified statuses rather than being silently imputed or coerced.
    rejected(FIT_STATUS_MISSING_CALIBRATION, fit_glo_ubpwm, np.arange(29.0))
    with_missing = np.arange(30.0)
    with_missing[7] = np.nan
    rejected(FIT_STATUS_MISSING_CALIBRATION, fit_glo_ubpwm, with_missing)
    rejected(FIT_STATUS_DEGENERATE, fit_glo_ubpwm, np.ones(30))
    maximally_skewed = np.zeros(30)
    maximally_skewed[-1] = 1.0
    rejected(FIT_STATUS_INVALID_SHAPE, fit_glo_ubpwm, maximally_skewed)

    # Ordinary logistic limit and generalized-logistic finite supports.
    symmetric = fit_glo_ubpwm(np.arange(30.0))
    assert symmetric.kappa == 0.0
    assert np.isclose(float(glo_cdf(symmetric.xi, symmetric)), 0.5)
    upper_bounded = dummy_parameters(0.0, 1.0, 0.5)
    lower_bounded = dummy_parameters(0.0, 1.0, -0.5)
    assert np.array_equal(glo_cdf([1.999, 2.0, 3.0], upper_bounded)[1:], [1.0, 1.0])
    assert np.array_equal(glo_cdf([-3.0, -2.0, -1.999], lower_bounded)[:2], [0.0, 0.0])
    monotone = glo_cdf(np.linspace(-10.0, 1.99, 1000), upper_bounded)
    assert np.all(np.diff(monotone) >= 0.0)

    clipped = standardize_glo(
        np.array([-3.0, np.nan, 3.0]),
        dummy_parameters(0.0, 1.0, -0.5),
    )
    assert clipped.clip_code.tolist() == [CDF_CLIP_LOWER, CDF_CLIP_MISSING, 0]
    assert np.isfinite(clipped.spei[[0, 2]]).all() and np.isnan(clipped.spei[1])
    clipped_upper = standardize_glo([3.0], upper_bounded)
    assert clipped_upper.clip_code.tolist() == [CDF_CLIP_UPPER]
    assert np.isfinite(clipped_upper.spei).all()

    print("SPEI UBPWM/GLO tests passed against CRAN SPEI 1.8.1 oracle and adversarial cases")


if __name__ == "__main__":
    main()
