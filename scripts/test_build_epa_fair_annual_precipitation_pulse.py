#!/usr/bin/env python3
"""Synthetic tests for EPA/FAIR pulse distribution arithmetic."""
import numpy as np

from build_epa_fair_annual_precipitation_pulse import distribution


def main() -> None:
    values = np.asarray([-2.0, -1.0, 1.0, 2.0])
    result = distribution(values)
    assert result["median_mm_per_year"] == 0
    assert result["mean_mm_per_year"] == 0
    assert result["positive_pair_fraction"] == 0.5
    assert result["negative_pair_fraction"] == 0.5
    try:
        distribution(np.asarray([np.nan]))
    except ValueError:
        pass
    else:
        raise AssertionError("nonfinite pulse distribution was accepted")
    print("EPA/FAIR pulse distribution synthetic checks passed")


if __name__ == "__main__":
    main()
