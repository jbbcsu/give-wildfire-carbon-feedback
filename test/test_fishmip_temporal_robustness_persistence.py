#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_fishmip_temporal_robustness_persistence import audit  # noqa: E402


root = Path(__file__).resolve().parents[1]
result = audit(root / "data/provenance/fishmip_robust_scenario_pair_stability_20260904.json")
assert result["temporally_persistent_latitude_band_count"] == 0
assert result["latitude_bands_robust_and_scenario_stable_in_all_windows"] == []
assert [row["robust_scenario_stable_latitude_band_count"] for row in result["by_future_window"]] == [2, 3, 0]
by_band = {
    row["latitude_band"]: row["robust_scenario_stable_window_count"]
    for row in result["by_latitude_band"]
}
assert by_band == {"south_high": 0, "south_mid": 2, "tropics": 1, "north_mid": 1, "north_high": 1}
assert result["common_structural_axis_selected"] is False
assert result["damage_or_scc_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "source.json"
    tampered.write_text(
        (root / "data/provenance/fishmip_robust_scenario_pair_stability_20260904.json")
        .read_text(encoding="utf-8")
        .replace('"fixed_material_dominance_ratio": 1.25', '"fixed_material_dominance_ratio": 1.2'),
        encoding="utf-8",
    )
    try:
        audit(tampered)
    except ValueError as error:
        assert "source hash changed" in str(error)
    else:
        raise AssertionError("tampered source passed")

print("FishMIP temporal robustness persistence tests passed")
