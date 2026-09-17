"""Synthetic vector-grid OLS checks for the monthly climate benchmark."""
import numpy as np

from fit_pangeo_monthly_pattern import ols_from_sums


def main():
    x = [-1.0, 0.0, 1.0, 2.0]
    intercept = np.array([[2.0, 4.0], [6.0, 8.0]])
    slope = np.array([[1.0, -1.0], [0.5, 2.0]])
    y = [intercept + v*slope for v in x]
    sy = sum(y)
    sxy = sum(v*field for v, field in zip(x, y))
    got_intercept, got_slope = ols_from_sums(sy, sxy, x, 4, np)
    assert np.allclose(got_intercept, intercept)
    assert np.allclose(got_slope, slope)
    try:
        ols_from_sums(sy, sxy, [0.0]*4, 4, np)
    except ValueError:
        pass
    else:
        raise AssertionError("degenerate GMT accepted")
    print("monthly GMT pattern synthetic OLS checks pass")


if __name__ == "__main__":
    main()
