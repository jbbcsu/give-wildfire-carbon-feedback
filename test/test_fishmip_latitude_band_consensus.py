#!/usr/bin/env python3
"""Synthetic gates for fixed latitude-band FishMIP sign consensus."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fishmip_latitude_band_consensus import (  # noqa: E402
    LATITUDE_BANDS,
    summarize_bands,
)


assert LATITUDE_BANDS == (
    ("south_high", -90.0, -40.0),
    ("south_mid", -40.0, -20.0),
    ("tropics", -20.0, 20.0),
    ("north_mid", 20.0, 40.0),
    ("north_high", 40.0, 90.0),
)

latitude = np.array([-60.0, -30.0, 0.0, 30.0, 60.0])
support = np.ones((5, 2), dtype=bool)
changes = [
    np.full((5, 2), -1.0),
    np.full((5, 2), -2.0),
    np.full((5, 2), -3.0),
    np.array([[-1.0, -1.0], [-1.0, -1.0], [1.0, 1.0], [-1.0, -1.0], [-1.0, -1.0]]),
]
results = summarize_bands(changes, support, latitude)
assert [row["latitude_band"] for row in results] == [row[0] for row in LATITUDE_BANDS]
assert sum(int(row["common_finite_grid_cells"]) for row in results) == 10
assert np.isclose(sum(float(row["area_weighted_share_of_global_common_support"]) for row in results), 1.0)
assert np.isclose(results[2]["area_weighted_cell_share_unanimously_lower"], 0.0)
assert np.isclose(results[2]["area_weighted_cell_share_at_least_three_lower"], 1.0)

try:
    summarize_bands(changes, np.zeros_like(support), latitude)
except ValueError as exc:
    assert "global common-support weight is empty" in str(exc)
else:
    raise AssertionError("empty global support should fail")

print("FishMIP latitude-band consensus synthetic tests passed")
