#!/usr/bin/env python3
"""Small synthetic invariants for post-result U.S. sensitivity helpers."""
from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd

from compare_us_county_weather_estimators import moments
from evaluate_us_county_average_irrigation_screens import key_digest, selector
from validate_us_county_average_irrigation_screens import source_selector
from validate_us_paired_practice_weather_route import check


def main() -> None:
    summary = moments(np.array([1.0, 2.0, np.nan]), np.array([2.0, 4.0, 3.0]))
    assert summary["n"] == 2 and summary["missing_or_nonfinite_pairs"] == 1
    assert abs(summary["mean_new_minus_old"] - 1.5) < 1e-12
    assert abs(summary["p95_absolute_difference"] - 1.95) < 1e-12
    assert abs(summary["rmse_difference"] - np.sqrt(2.5)) < 1e-12
    assert abs(summary["pearson_correlation"] - 1) < 1e-12
    assert moments(np.array([np.nan]), np.array([1.0]))["statistics"] is None

    keys = pd.DataFrame({"outcome_crop": ["corn_grain", "soybeans"],
                         "county_geoid": ["01001", "01003"], "harvest_year": [2018, 2019]})
    assert key_digest(keys) == key_digest(keys.iloc[::-1])
    altered = keys.copy()
    altered.loc[0, "county_geoid"] = "01005"
    assert key_digest(keys) != key_digest(altered)

    census = pd.DataFrame({"crop": ["corn", "soybeans", "corn", "rice"],
                           "census_year": [2017]*4,
                           "county_geoid": ["01001", "01003", "01005", "01007"],
                           "irrigation_share": [0.1, 0.2, np.nan, 0.0],
                           "share_eligible": [True, True, False, True]})
    with patch("pandas.read_csv", return_value=census.copy()):
        fixed = selector(2017)
        assert len(fixed) == 3
        assert fixed.share_eligible.tolist() == [True, True, False]
        assert fixed.irrigation_share.isna().sum() == 1
        selected = source_selector(2017, 20)
        assert set(selected.county_geoid) == {"01001", "01003"}
    assert check(1.0, 1.0, "equal") == 0
    try:
        check(1.0, 1.1, "altered")
    except ValueError:
        pass
    else:
        raise AssertionError("independent numerical mismatch was accepted")
    print("post-result U.S. sensitivity synthetic invariants passed")


if __name__ == "__main__":
    main()
