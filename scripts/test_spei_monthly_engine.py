#!/usr/bin/env python3
"""Leakage, missingness, and degeneracy tests for monthly SPEI construction."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from spei_distribution import (
    FIT_STATUS_DEGENERATE,
    FIT_STATUS_MISSING_CALIBRATION,
    FIT_STATUS_VALID,
)
from spei_monthly_engine import construct_monthly_spei


ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "data/fixtures/spei_cran_1_8_1_synthetic_oracle.json"


def rejected(expected: str, *args, **kwargs) -> None:
    try:
        construct_monthly_spei(*args, **kwargs)
    except ValueError as error:
        assert expected.lower() in str(error).lower(), error
    else:
        raise AssertionError(f"invalid construction accepted; expected {expected!r}")


def synthetic_inputs() -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray]:
    dates = pd.date_range("1981-01-01", "2019-12-01", freq="MS")
    year = dates.year.to_numpy()
    month = dates.month.to_numpy()
    balance = (
        (month - 6.5) * 1.7
        + (((year - 1980) * 37 + month * 11) % 29 - 14) * 0.9
        + (((year - 1980) * month) % 7) * 0.13
    )
    et0 = np.full((len(dates), 1, 1), 100.0)
    precipitation = et0 + balance[:, None, None]
    return dates, precipitation, et0


def main() -> None:
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    dates, precipitation, et0 = synthetic_inputs()
    result = construct_monthly_spei(dates, precipitation, et0)
    assert result.accumulated_balance_mm.shape == (3, len(dates), 1, 1)
    assert result.spei.shape == result.accumulated_balance_mm.shape
    assert np.all(result.fit_status_code == FIT_STATUS_VALID)
    assert np.all(result.calibration_finite_count == 30)
    selected = np.asarray(oracle["selected_one_based_indices"], dtype=int) - 1
    for scale_index, scale in enumerate((1, 3, 6)):
        expected = np.asarray(
            [np.nan if value is None else value for value in oracle["spei_by_scale"][str(scale)]],
            dtype=float,
        )
        assert np.allclose(
            result.spei[scale_index, selected, 0, 0],
            expected,
            atol=7e-12,
            rtol=0.0,
            equal_nan=True,
        )

    # Holdout climate is transformed with frozen parameters: arbitrary changes
    # beginning in 2012 cannot alter any fit or any pre-2012 score.
    altered_precipitation = precipitation.copy()
    altered_precipitation[dates.year >= 2012] += 1000.0
    altered = construct_monthly_spei(dates, altered_precipitation, et0)
    assert np.array_equal(result.location_xi_mm, altered.location_xi_mm)
    assert np.array_equal(result.scale_alpha_mm, altered.scale_alpha_mm)
    assert np.array_equal(result.shape_kappa, altered.shape_kappa)
    pre_holdout = dates.year < 2012
    assert np.allclose(
        result.spei[:, pre_holdout],
        altered.spei[:, pre_holdout],
        atol=0.0,
        rtol=0.0,
        equal_nan=True,
    )
    assert not np.allclose(
        result.spei[:, ~pre_holdout],
        altered.spei[:, ~pre_holdout],
        equal_nan=True,
    )
    assert altered.audit["post_2011_values_used_in_fit"] == 0
    assert altered.audit["outcomes_used_in_fit"] == 0
    assert altered.audit["imputed_values"] == 0

    # A single missing calibration month invalidates only the calendar-month
    # fits whose right-aligned windows contain it; no value is imputed.
    missing_p = precipitation.copy()
    missing_e = et0.copy()
    missing_position = dates.get_loc("1985-01-01")
    missing_p[missing_position, 0, 0] = np.nan
    missing_e[missing_position, 0, 0] = np.nan
    missing = construct_monthly_spei(dates, missing_p, missing_e)
    invalid_months_by_scale = {
        0: {1},
        1: {1, 2, 3},
        2: {1, 2, 3, 4, 5, 6},
    }
    for scale_index, invalid_months in invalid_months_by_scale.items():
        for calendar_month in range(1, 13):
            expected_status = (
                FIT_STATUS_MISSING_CALIBRATION
                if calendar_month in invalid_months
                else FIT_STATUS_VALID
            )
            assert missing.fit_status_code[scale_index, calendar_month - 1, 0, 0] == expected_status
    assert missing.audit["imputed_values"] == 0

    # A missing application value after calibration does not contaminate the
    # fit; the affected accumulation and score remain missing.
    application_p = precipitation.copy()
    application_e = et0.copy()
    holdout_position = dates.get_loc("2015-08-01")
    application_p[holdout_position, 0, 0] = np.nan
    application_e[holdout_position, 0, 0] = np.nan
    application = construct_monthly_spei(dates, application_p, application_e)
    assert np.all(application.fit_status_code == FIT_STATUS_VALID)
    assert np.isnan(application.spei[0, holdout_position, 0, 0])
    assert np.isnan(application.spei[1, holdout_position : holdout_position + 3, 0, 0]).all()
    assert np.isnan(application.spei[2, holdout_position : holdout_position + 6, 0, 0]).all()

    constant = np.ones_like(precipitation)
    degenerate = construct_monthly_spei(dates, constant, constant)
    assert np.all(degenerate.fit_status_code == FIT_STATUS_DEGENERATE)
    assert np.isnan(degenerate.spei).all()

    mismatched = precipitation.copy()
    mismatched[0, 0, 0] = np.nan
    rejected("missingness", dates, mismatched, et0)
    rejected("consecutive", dates.delete(4), precipitation[:-1], et0[:-1])
    rejected("nonnegative", dates, -precipitation, et0)
    rejected("locked", dates, precipitation, et0, scales=(1, 3))

    print("Monthly SPEI engine tests passed; frozen-fit and fail-closed audits verified")


if __name__ == "__main__":
    main()
