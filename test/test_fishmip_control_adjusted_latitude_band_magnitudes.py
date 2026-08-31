#!/usr/bin/env python3
"""Synthetic gates for control-adjusted latitude-band magnitudes."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fishmip_control_adjusted_latitude_band_magnitudes import (  # noqa: E402
    summarize_band_magnitudes,
)
from evaluate_fishmip_spatial_change_distribution import FORCINGS, MODELS  # noqa: E402


latitude = np.array([-60.0, -30.0, 0.0, 30.0, 60.0])
support = np.ones((5, 2), dtype=bool)
changes = {
    (forcing, model): np.full(support.shape, -float(index + 1))
    for index, (forcing, model) in enumerate((
        (forcing, model) for forcing in FORCINGS for model in MODELS
    ))
}
rows, summaries = summarize_band_magnitudes(changes, support, latitude)
assert len(rows) == len(FORCINGS) * len(MODELS) * 5
assert len(summaries) == 5
assert all(row["area_weighted_cell_share_negative"] == 1.0 for row in rows)
assert all(row["negative_trajectory_count"] == 4 for row in summaries)
for key, expected in changes.items():
    selected = [row for row in rows if (row["climate_forcing"], row["ecosystem_model"]) == key]
    assert np.isclose(sum(float(row["band_contribution_to_global_normalized_change"]) for row in selected), expected[0, 0])

bad = copy.deepcopy(changes)
bad.pop(next(iter(bad)))
try:
    summarize_band_magnitudes(bad, support, latitude)
except ValueError:
    pass
else:
    raise AssertionError("incomplete trajectory product passed")

bad = copy.deepcopy(changes)
bad[next(iter(bad))][0, 0] = np.nan
try:
    summarize_band_magnitudes(bad, support, latitude)
except ValueError:
    pass
else:
    raise AssertionError("nonfinite trajectory passed")

print("FishMIP control-adjusted latitude-band magnitude synthetic tests passed")
