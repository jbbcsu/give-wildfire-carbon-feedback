#!/usr/bin/env python3
"""Synthetic gates for temporal FishMIP latitude-band magnitudes."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fishmip_control_adjusted_latitude_band_time_windows import (  # noqa: E402
    summarize_temporal_bands,
)
from evaluate_fishmip_control_adjusted_spatial_time_windows import FUTURE_WINDOWS  # noqa: E402
from evaluate_fishmip_latitude_band_consensus import LATITUDE_BANDS  # noqa: E402
from evaluate_fishmip_spatial_change_distribution import FORCINGS, MODELS, SCENARIOS  # noqa: E402


rows = []
for scenario in SCENARIOS:
    for start, end in FUTURE_WINDOWS:
        for band, _, _ in LATITUDE_BANDS:
            for index, (forcing, model) in enumerate((
                (forcing, model) for forcing in FORCINGS for model in MODELS
            )):
                rows.append({
                    "climate_scenario": scenario,
                    "future_period": {"start_year": start, "end_year": end},
                    "latitude_band": band,
                    "climate_forcing": forcing,
                    "ecosystem_model": model,
                    "band_mean_normalized_control_adjusted_change": -float(index + 1),
                })

summary = summarize_temporal_bands(rows)
assert len(summary) == len(SCENARIOS) * len(LATITUDE_BANDS)
assert all(row["all_four_negative_in_every_window"] for row in summary)
assert all(row["first_window_all_four_negative"] == {"start_year": 2021, "end_year": 2030} for row in summary)

bad = copy.deepcopy(rows)
bad.pop()
try:
    summarize_temporal_bands(bad)
except ValueError:
    pass
else:
    raise AssertionError("incomplete temporal latitude product passed")

bad = copy.deepcopy(rows)
bad.append(copy.deepcopy(rows[0]))
try:
    summarize_temporal_bands(bad)
except ValueError:
    pass
else:
    raise AssertionError("duplicate temporal latitude row passed")

print("FishMIP temporal latitude-band magnitude synthetic tests passed")
