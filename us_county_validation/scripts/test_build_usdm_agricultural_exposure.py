#!/usr/bin/env python3
"""Small deterministic tests for agricultural-area USDM time and geometry logic."""
from __future__ import annotations

from datetime import date

import numpy as np
from shapely.geometry import box

from build_usdm_agricultural_exposure import classify_points, day_allocations


def main() -> None:
    start = date(2000, 10, 1)
    end = date(2013, 9, 30)
    assert day_allocations(date(2000, 9, 26), start, end) == {2001: 2}
    assert day_allocations(date(2001, 9, 25), start, end) == {2001: 6, 2002: 1}
    assert day_allocations(date(2013, 9, 24), start, end) == {2013: 7}

    geometries = {0: box(0, 0, 1, 1), 1: box(1.1, 1.1, 2, 2), 2: box(2.1, 2.1, 3, 3)}
    x = np.asarray([-1, 0.5, 1.5, 2.5])
    y = np.asarray([-1, 0.5, 1.5, 2.5])
    observed, violations = classify_points(geometries, x, y)
    np.testing.assert_array_equal(observed, np.asarray([-1, 0, 1, 2], dtype=np.int8))
    assert violations == {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}

    overlapping = {0: box(0, 0, 3, 3), 1: box(2, 2, 4, 4)}
    _, violations = classify_points(overlapping, np.asarray([2.5]), np.asarray([2.5]))
    assert violations["1"] == 1
    print("agricultural-area USDM helper tests passed")


if __name__ == "__main__":
    main()
