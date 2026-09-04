#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_fishmip_metric_disagreement_materiality import audit  # noqa: E402


def cell(index: int, agrees: bool, material: bool) -> tuple[dict[str, object], dict[str, object]]:
    scenario = "ssp126" if index < 15 else "ssp585"
    period_index = (index // 5) % 3
    start = (2021, 2041, 2081)[period_index]
    band = ("south_high", "south_mid", "tropics", "north_mid", "north_high")[index % 5]
    base = {"climate_scenario": scenario, "future_period": {"start_year": start, "end_year": start + 9}, "latitude_band": band}
    return ({**base, "larger_axis_agrees_across_metrics": agrees}, {**base, "material_dominance_at_fixed_ratio": material, "larger_to_smaller_rms_ratio": 1.3 if material else 1.1})


metric_cells = []
dominance_cells = []
for index in range(30):
    left, right = cell(index, agrees=index < 20, material=index % 2 == 0)
    metric_cells.append(left)
    dominance_cells.append(right)

with tempfile.TemporaryDirectory() as temporary:
    metric_path = Path(temporary) / "metric.json"
    dominance_path = Path(temporary) / "dominance.json"
    metric_path.write_text(json.dumps({"cells": metric_cells, "preferred_metric_selected": False, "scc_authorized": False}))
    dominance_path.write_text(json.dumps({"cells": dominance_cells, "material_dominance_ratio_threshold": 1.25, "probability_or_variance_decomposition": False, "scc_authorized": False}))
    result = audit(metric_path, dominance_path)
    assert result["cells"] == 30
    assert sum(result["cross_tabulation"].values()) == 30
    assert result["preferred_metric_selected"] is False

print("FishMIP metric-disagreement materiality tests passed")
