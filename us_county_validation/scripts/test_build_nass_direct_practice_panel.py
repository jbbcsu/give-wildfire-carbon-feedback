#!/usr/bin/env python3
"""Synthetic invariants for the complete direct-practice support builder."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).with_name("build_nass_direct_practice_panel.py")
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("direct_panel", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def frame(crop: str, practice: str, rows: list[tuple[int, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "crop": crop,
            "year": [row[0] for row in rows],
            "county_geoid": [row[1] for row in rows],
            "practice": practice,
            "yield_eligible": [row[2] > 0 for row in rows],
            "analysis_value": [row[2] if row[2] > 0 else pd.NA for row in rows],
            "value_raw": [str(row[2]) for row in rows],
            "state_alpha": "NE",
            "county_name": ["CUMING" if row[1] == "31039" else "BURT" for row in rows],
        }
    )


frames = []
for crop in ("corn", "soybeans", "wheat"):
    frames.extend(
        [
            frame(crop, "IRRIGATED", [(1981, "31039", 100), (1980, "31021", 80)]),
            frame(crop, "NON-IRRIGATED", [(1981, "31039", 70), (1980, "31021", 60)]),
        ]
    )

panel, audit = module.build_panel(frames, 1981, 2019)
assert len(panel) == 6
assert audit["paired_county_years_total"] == 3
assert audit["long_practice_rows_total"] == 6
assert set(panel.outcome_crop) == {"corn_grain", "soybeans", "wheat_all_classes"}
assert set(panel.irrigation_practice) == {"irrigated", "non_irrigated"}
assert panel.harvest_year.eq(1981).all()
assert not panel.feature_construction_eligible.any()
assert not panel.response_estimation_authorized.any()
assert not panel.scc_authorized.any()
assert panel.loc[
    panel.outcome_crop.eq("wheat_all_classes"), "calendar_mapping_status"
].eq("blocked_all_classes_wheat_requires_class_weights").all()

# One unmatched practice is excluded rather than converted into a pair.
partial = [item.copy() for item in frames]
partial[1] = partial[1].iloc[1:].copy()
partial_panel, partial_audit = module.build_panel(partial, 1980, 2019)
assert len(partial_panel) == 10
assert partial_audit["paired_county_years_total"] == 5

# Duplicated keys, incomplete crop inputs, and an empty window fail closed.
bad_duplicate = frames + [frames[0].iloc[[0]].copy()]
for bad, message in [
    (bad_duplicate, "Duplicate"),
    (frames[:-2], "exactly corn"),
]:
    try:
        module.build_panel(bad, 1981, 2019)
    except ValueError as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError(f"Invalid panel should fail: {message}")

try:
    module.build_panel(frames, 2020, 2021)
except ValueError as error:
    assert "No eligible" in str(error)
else:
    raise AssertionError("Empty requested year window must fail")

print("complete NASS direct-practice panel tests passed")
