"""Shared invariants for aggregated daily-maximum heat-threshold metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd

from build_crop_heat_features import threshold_name


def validate_thresholds(thresholds: list[float]) -> list[float]:
    if not thresholds or any(not np.isfinite(value) for value in thresholds):
        raise ValueError("Heat thresholds must be nonempty and finite")
    ordered = sorted(set(thresholds))
    names = [threshold_name(value) for value in ordered]
    if len(names) != len(set(names)):
        raise ValueError("Heat thresholds produce colliding metric names")
    return ordered


def metric_columns(thresholds: list[float]) -> set[str]:
    return {
        item
        for threshold in validate_thresholds(thresholds)
        for item in (
            f"{threshold_name(threshold)}_days",
            f"{threshold_name(threshold)}_degree_days",
        )
    }


def validate_threshold_metrics(
    frame: pd.DataFrame,
    thresholds: list[float],
    duration_column: str,
) -> set[str]:
    """Validate per-period threshold summaries and their cross-threshold nesting."""
    ordered = validate_thresholds(thresholds)
    metrics = metric_columns(ordered)
    if not np.isfinite(frame[list(metrics)].to_numpy(dtype=float)).all():
        raise ValueError("Heat threshold metrics contain nonfinite values")
    if (frame[list(metrics)].to_numpy(dtype=float) < 0).any():
        raise ValueError("Heat day or degree-day metric is negative")
    day_counts = [f"{threshold_name(value)}_days" for value in ordered]
    if not np.equal(frame[day_counts], np.floor(frame[day_counts])).all().all():
        raise ValueError("Heat threshold day counts must be integers")
    if (frame[day_counts].to_numpy(dtype=float) > frame[duration_column].to_numpy()[:, None]).any():
        raise ValueError("Heat threshold day count exceeds period length")

    tolerance = 1e-8
    for lower, upper in zip(ordered, ordered[1:]):
        lower_name, upper_name = threshold_name(lower), threshold_name(upper)
        lower_days = frame[f"{lower_name}_days"].to_numpy(dtype=float)
        upper_days = frame[f"{upper_name}_days"].to_numpy(dtype=float)
        if (upper_days > lower_days).any():
            raise ValueError("Hotter-threshold day counts must be nested within cooler thresholds")
        lower_dd = frame[f"{lower_name}_degree_days"].to_numpy(dtype=float)
        upper_dd = frame[f"{upper_name}_degree_days"].to_numpy(dtype=float)
        difference = lower_dd - upper_dd
        gap = upper - lower
        if (
            (difference < gap * upper_days - tolerance).any()
            or (difference > gap * lower_days + tolerance).any()
        ):
            raise ValueError("Cross-threshold degree days violate necessary nesting bounds")
    return metrics
