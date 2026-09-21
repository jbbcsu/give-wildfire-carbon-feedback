#!/usr/bin/env python3
"""Synthetic, outcome-free checks for the NOAA county-average feature basis."""
import numpy as np

from build_us_county_average_crop_year_features import features_for_window, max_dry_run, rx5


def run() -> None:
    rain = np.asarray([
        [0.0] * 31,
        [2.0] * 5 + [0.0] * 6 + [3.0] * 20,
    ])
    tavg = np.full(rain.shape, 20.0)
    tmax = np.full(rain.shape, 31.0)
    values = features_for_window(rain, tavg, tmax)
    assert np.allclose(values["precip_mm"], [0.0, 70.0])
    assert np.allclose(values["wet_days_ge_1mm"], [0, 25])
    assert np.allclose(values["cdd_max_days"], [31, 6])
    assert np.allclose(values["rx5day_mm"], [0.0, 15.0])
    assert np.allclose(values["zero_precipitation_season"], [1, 0])
    assert np.allclose(sum(values[f"stage{s}_precip_mm"] for s in (1, 2, 3)),
                       values["precip_mm"])
    assert np.allclose(sum(values[f"stage{s}_precip_share"] for s in (1, 2, 3)), [0, 1])
    assert np.allclose(values["tmax_exceedance_29c_c_days"], 62)
    assert np.allclose(values["tmax_exceedance_30c_c_days"], 31)
    assert np.allclose(values["tmax_days_gt_29c"], 31)
    assert np.allclose(values["tmean_c"], 20)
    assert np.array_equal(max_dry_run(np.asarray([[0.0, 1.0, 0.0, 0.0, 1.0]])), [2])
    assert np.allclose(rx5(np.ones((1, 6))), [5])
    for bad in (np.ones((1, 29)), np.full((1, 30), np.nan)):
        try:
            features_for_window(bad, np.ones_like(bad), np.ones_like(bad))
        except ValueError:
            pass
        else:
            raise AssertionError("invalid feature input unexpectedly passed")
    print("14 synthetic feature assertions passed")


if __name__ == "__main__":
    run()
