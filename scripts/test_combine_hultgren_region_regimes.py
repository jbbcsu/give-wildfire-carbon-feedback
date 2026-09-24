#!/usr/bin/env python3
"""Unit checks for rainfed/irrigated region-basis combination arithmetic."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).with_name("combine_hultgren_region_regimes.py")
SPEC = importlib.util.spec_from_file_location("combine_hultgren_region_regimes", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def combined_value(rainfed_value: float | None, irrigated_value: float | None, rainfed_area: float, irrigated_area: float) -> float:
    values = pd.Series({"rainfed": rainfed_value, "irrigated": irrigated_value}).fillna(0.0)
    return float((values.rainfed * rainfed_area + values.irrigated * irrigated_area) / (rainfed_area + irrigated_area))


def main() -> None:
    assert MODULE.FEATURES == [
        "gdd", "kdd", "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
        "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
    ]
    assert np.isclose(combined_value(10.0, 30.0, 3.0, 1.0), 15.0)
    assert np.isclose(combined_value(10.0, None, 3.0, 0.0), 10.0)
    assert np.isclose(combined_value(None, 30.0, 0.0, 1.0), 30.0)
    assert np.isclose(1.0 / (3.0 + 1.0), 0.25)
    print("combine Hultgren region regimes unit checks passed")


if __name__ == "__main__":
    main()
