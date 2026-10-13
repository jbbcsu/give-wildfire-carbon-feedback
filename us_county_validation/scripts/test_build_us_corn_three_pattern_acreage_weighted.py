#!/usr/bin/env python3
"""Unit checks for the acreage-weighted U.S. transport aggregator."""

import numpy as np
import pandas as pd

from build_us_corn_three_pattern_acreage_weighted import acreage_weighted_vector


def test_counties_are_weighted_after_within_county_averaging() -> None:
    rows = []
    for county, weight, values in (("001", 1.0, [1.0, 3.0]), ("003", 3.0, [5.0])):
        for value in values:
            row = {"county_geoid": county, "acres": weight}
            row.update({f"contrast_{index}": value + index for index in range(8)})
            rows.append(row)
    result = acreage_weighted_vector(pd.DataFrame(rows), "acres")
    # County means are 2 and 5; acreage-weighted mean is (1*2 + 3*5)/4 = 4.25.
    assert np.allclose(result, np.arange(8, dtype=float) + 4.25)


if __name__ == "__main__":
    test_counties_are_weighted_after_within_county_averaging()
    print("ok")
