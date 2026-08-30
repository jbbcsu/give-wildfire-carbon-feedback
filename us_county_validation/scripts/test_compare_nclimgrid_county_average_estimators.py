#!/usr/bin/env python3
"""Synthetic gates for county-average estimator comparison."""
from __future__ import annotations

import numpy as np

from compare_nclimgrid_county_average_estimators import summarize_difference


polygon = np.asarray([1.0, 2.0, 4.0])
source = np.asarray([0.5, 2.5, 3.0])
summary = summarize_difference(polygon, source)
assert abs(summary["mean_difference"] - (0.5 - 0.5 + 1.0) / 3) < 1e-12
assert abs(summary["mean_absolute_difference"] - 2.0 / 3) < 1e-12
assert summary["maximum_absolute_difference"] == 1.0
assert summarize_difference(np.ones(3), np.ones(3))["pearson_correlation"] is None

for bad_left, bad_right in [
    ([1.0], [1.0, 2.0]),
    ([1.0, np.nan], [1.0, 2.0]),
    ([], []),
]:
    try:
        summarize_difference(np.asarray(bad_left), np.asarray(bad_right))
    except ValueError:
        pass
    else:
        raise AssertionError("invalid daily comparison passed")

print("nClimGrid county-average estimator comparison tests passed")
