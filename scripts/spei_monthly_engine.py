#!/usr/bin/env python3
"""Outcome-free monthly SPEI construction with frozen calendar-month fits."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from spei_distribution import (
    CALIBRATION_OBSERVATIONS,
    CDF_CLIP_EPSILON,
    CDF_CLIP_MISSING,
    FIT_STATUS_LABELS,
    FIT_STATUS_MISSING_CALIBRATION,
    FIT_STATUS_NUMERICAL_FAILURE,
    FIT_STATUS_VALID,
    GloFitError,
    fit_glo_ubpwm,
    standardize_glo,
)


LOCKED_SCALES = (1, 3, 6)
CALIBRATION_START_YEAR = 1982
CALIBRATION_END_YEAR = 2011


@dataclass(frozen=True)
class MonthlySpeiResult:
    months: pd.DatetimeIndex
    precipitation_mm: np.ndarray
    et0_mm: np.ndarray
    water_balance_mm: np.ndarray
    accumulated_balance_mm: np.ndarray
    cdf_probability: np.ndarray
    spei: np.ndarray
    cdf_clip_code: np.ndarray
    location_xi_mm: np.ndarray
    scale_alpha_mm: np.ndarray
    shape_kappa: np.ndarray
    calibration_finite_count: np.ndarray
    fit_status_code: np.ndarray
    audit: dict[str, Any]


def _monthly_array(value: object, label: str, n_months: int) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if result.ndim < 1 or result.shape[0] != n_months:
        raise ValueError(f"{label} first dimension must have length {n_months}")
    if np.isinf(result).any():
        raise ValueError(f"{label} must not contain infinities")
    if (result[np.isfinite(result)] < 0.0).any():
        raise ValueError(f"{label} finite values must be nonnegative")
    return result


def _validate_months(months: object) -> pd.DatetimeIndex:
    index = pd.DatetimeIndex(months)
    if index.empty or index.hasnans or index.tz is not None:
        raise ValueError("months must be nonempty, finite, and timezone-naive")
    if not index.is_monotonic_increasing or index.has_duplicates:
        raise ValueError("months must be strictly increasing and unique")
    if not (index.day == 1).all():
        raise ValueError("months must use calendar-month-start timestamps")
    expected = pd.date_range(index[0], index[-1], freq="MS")
    if not index.equals(expected):
        raise ValueError("monthly chronology must be consecutive without gaps")
    return index


def _strict_rolling_sum(balance: np.ndarray, scale: int) -> np.ndarray:
    result = np.full(balance.shape, np.nan, dtype=np.float64)
    for position in range(scale - 1, balance.shape[0]):
        window = balance[position - scale + 1 : position + 1]
        complete = np.isfinite(window).all(axis=0)
        summed = np.sum(np.where(np.isfinite(window), window, 0.0), axis=0)
        result[position] = np.where(complete, summed, np.nan)
    return result


def _counts_by_scale(values: np.ndarray, scales: tuple[int, ...]) -> dict[str, int]:
    return {str(scale): int(np.count_nonzero(values[index])) for index, scale in enumerate(scales)}


def construct_monthly_spei(
    months: object,
    precipitation_mm: object,
    et0_mm: object,
    *,
    scales: tuple[int, ...] = LOCKED_SCALES,
    calibration_start_year: int = CALIBRATION_START_YEAR,
    calibration_end_year: int = CALIBRATION_END_YEAR,
    required_calibration_observations: int = CALIBRATION_OBSERVATIONS,
    clip_epsilon: float = CDF_CLIP_EPSILON,
) -> MonthlySpeiResult:
    """Construct SPEI per spatial cell with parameters frozen to 1982--2011."""
    index = _validate_months(months)
    if scales != LOCKED_SCALES:
        raise ValueError("scales must be exactly the locked ordered tuple (1, 3, 6)")
    if (calibration_start_year, calibration_end_year, required_calibration_observations) != (
        CALIBRATION_START_YEAR,
        CALIBRATION_END_YEAR,
        CALIBRATION_OBSERVATIONS,
    ):
        raise ValueError("calibration must remain exactly 1982-2011 with 30 values per month")
    precipitation = _monthly_array(precipitation_mm, "precipitation_mm", len(index))
    et0 = _monthly_array(et0_mm, "et0_mm", len(index))
    if precipitation.shape != et0.shape:
        raise ValueError("precipitation_mm and et0_mm shapes differ")
    if not np.array_equal(np.isnan(precipitation), np.isnan(et0)):
        raise ValueError("monthly precipitation and ET0 missingness must match exactly")
    spatial_shape = precipitation.shape[1:]
    if not spatial_shape or any(length <= 0 for length in spatial_shape):
        raise ValueError("monthly arrays must include at least one nonempty spatial dimension")

    water_balance = precipitation - et0
    accumulated = np.stack([_strict_rolling_sum(water_balance, scale) for scale in scales])
    output_shape = accumulated.shape
    cdf_probability = np.full(output_shape, np.nan, dtype=np.float64)
    spei = np.full(output_shape, np.nan, dtype=np.float64)
    clip_code = np.full(output_shape, CDF_CLIP_MISSING, dtype=np.int8)
    parameter_shape = (len(scales), 12, *spatial_shape)
    xi = np.full(parameter_shape, np.nan, dtype=np.float64)
    alpha = np.full(parameter_shape, np.nan, dtype=np.float64)
    kappa = np.full(parameter_shape, np.nan, dtype=np.float64)
    calibration_count = np.zeros(parameter_shape, dtype=np.int16)
    fit_status = np.full(parameter_shape, FIT_STATUS_NUMERICAL_FAILURE, dtype=np.int8)

    year = index.year.to_numpy()
    calendar_month = index.month.to_numpy()
    calibration_year = (year >= calibration_start_year) & (year <= calibration_end_year)
    for month_number in range(1, 13):
        expected = calibration_year & (calendar_month == month_number)
        if int(np.count_nonzero(expected)) != required_calibration_observations:
            raise ValueError(
                f"source chronology does not contain exactly {required_calibration_observations} "
                f"calibration observations for calendar month {month_number}"
            )

    for scale_index, _scale in enumerate(scales):
        for month_number in range(1, 13):
            fit_positions = calibration_year & (calendar_month == month_number)
            application_positions = calendar_month == month_number
            for spatial_index in np.ndindex(spatial_shape):
                parameter_index = (scale_index, month_number - 1, *spatial_index)
                fit_values = accumulated[(scale_index, fit_positions, *spatial_index)]
                finite_count = int(np.count_nonzero(np.isfinite(fit_values)))
                calibration_count[parameter_index] = finite_count
                if finite_count != required_calibration_observations:
                    fit_status[parameter_index] = FIT_STATUS_MISSING_CALIBRATION
                    continue
                try:
                    parameters = fit_glo_ubpwm(
                        fit_values,
                        required_observations=required_calibration_observations,
                    )
                except GloFitError as error:
                    fit_status[parameter_index] = error.status
                    continue
                fit_status[parameter_index] = FIT_STATUS_VALID
                xi[parameter_index] = parameters.xi
                alpha[parameter_index] = parameters.alpha
                kappa[parameter_index] = parameters.kappa
                all_values = accumulated[(scale_index, application_positions, *spatial_index)]
                standardized = standardize_glo(
                    all_values,
                    parameters,
                    clip_epsilon=clip_epsilon,
                )
                cdf_probability[(scale_index, application_positions, *spatial_index)] = (
                    standardized.probabilities
                )
                spei[(scale_index, application_positions, *spatial_index)] = standardized.spei
                clip_code[(scale_index, application_positions, *spatial_index)] = (
                    standardized.clip_code
                )

    fit_counts = {
        FIT_STATUS_LABELS[code]: int(np.count_nonzero(fit_status == code))
        for code in sorted(FIT_STATUS_LABELS)
    }
    audit: dict[str, Any] = {
        "months": int(len(index)),
        "spatial_cells": int(np.prod(spatial_shape)),
        "monthly_precipitation_missing": int(np.count_nonzero(~np.isfinite(precipitation))),
        "monthly_et0_missing": int(np.count_nonzero(~np.isfinite(et0))),
        "monthly_water_balance_missing": int(np.count_nonzero(~np.isfinite(water_balance))),
        "accumulated_balance_missing_by_scale": _counts_by_scale(
            ~np.isfinite(accumulated), scales
        ),
        "spei_missing_by_scale": _counts_by_scale(~np.isfinite(spei), scales),
        "cdf_lower_clips_by_scale": _counts_by_scale(clip_code == -1, scales),
        "cdf_upper_clips_by_scale": _counts_by_scale(clip_code == 1, scales),
        "cdf_exact_zero_by_scale": _counts_by_scale(cdf_probability == 0.0, scales),
        "cdf_exact_one_by_scale": _counts_by_scale(cdf_probability == 1.0, scales),
        "cdf_finite_min_by_scale": {
            str(scale): (
                None
                if not np.isfinite(cdf_probability[index]).any()
                else float(np.nanmin(cdf_probability[index]))
            )
            for index, scale in enumerate(scales)
        },
        "cdf_finite_max_by_scale": {
            str(scale): (
                None
                if not np.isfinite(cdf_probability[index]).any()
                else float(np.nanmax(cdf_probability[index]))
            )
            for index, scale in enumerate(scales)
        },
        "fit_status_counts": fit_counts,
        "calibration_start_year": calibration_start_year,
        "calibration_end_year": calibration_end_year,
        "required_observations_per_calendar_month": required_calibration_observations,
        "post_2011_values_used_in_fit": 0,
        "outcomes_used_in_fit": 0,
        "imputed_values": 0,
    }
    return MonthlySpeiResult(
        months=index,
        precipitation_mm=precipitation,
        et0_mm=et0,
        water_balance_mm=water_balance,
        accumulated_balance_mm=accumulated,
        cdf_probability=cdf_probability,
        spei=spei,
        cdf_clip_code=clip_code,
        location_xi_mm=xi,
        scale_alpha_mm=alpha,
        shape_kappa=kappa,
        calibration_finite_count=calibration_count,
        fit_status_code=fit_status,
        audit=audit,
    )
