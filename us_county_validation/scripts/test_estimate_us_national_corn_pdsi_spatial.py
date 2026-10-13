#!/usr/bin/env python3
"""Unit checks for national PDSI contrast construction and promotion logic."""

import numpy as np

from estimate_us_national_corn_pdsi_spatial import contrast, spatial_excludes_zero


def test_quadratic_contrast() -> None:
    assert np.array_equal(contrast(0, -2), np.array([-2.0, 4.0]))
    assert np.array_equal(contrast(-1, -2), np.array([-1.0, 3.0]))


def test_spatial_gate() -> None:
    assert spatial_excludes_zero(-0.1, {"county_cr1": .01, "spatial_250km": .02, "spatial_500km": .03})
    assert not spatial_excludes_zero(-0.1, {"county_cr1": .01, "spatial_250km": .02, "spatial_500km": .06})
    assert not spatial_excludes_zero(-0.1, {"county_cr1": .01})


if __name__ == "__main__":
    test_quadratic_contrast()
    test_spatial_gate()
    print("ok")
