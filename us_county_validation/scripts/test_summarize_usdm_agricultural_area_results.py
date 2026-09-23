#!/usr/bin/env python3
"""Tests for binding the rejected 3.96 km diagnostic into the final summary."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from summarize_usdm_agricultural_area_results import (
    coefficient_movement,
    rejected_diagnostic_summary,
)


def payload() -> dict[str, object]:
    return {
        "schema": "usdm_agricultural_area_spatial_basis_comparison_v1",
        "bases": {"county": {}, "cultivated": {}, "broad": {}},
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "global_transfer_authorized": False,
        "scc_claim_authorized": False,
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "diagnostic.json"
        path.write_text(json.dumps(payload()) + "\n", encoding="utf-8")
        result = rejected_diagnostic_summary(path)
        assert result["status"] == "rejected_by_frozen_native_resolution_sentinel_gate"
        assert result["comparison"]["bases"].keys() == {"county", "cultivated", "broad"}

        invalid = payload()
        invalid["scc_claim_authorized"] = True
        path.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
        try:
            rejected_diagnostic_summary(path)
        except ValueError as error:
            assert "scc_claim_authorized" in str(error)
        else:
            raise AssertionError("open SCC claim gate was accepted")

    left = {"coefficients": [
        {
            "outcome_crop": "corn", "irrigation_class": "dryland",
            "family": "drought_only", "term": "d0_weeks",
            "exact_percent_change_per_equivalent_week": -0.2,
        },
        {
            "outcome_crop": "corn", "irrigation_class": "dryland",
            "family": "drought_only", "term": "d1_weeks",
            "exact_percent_change_per_equivalent_week": -0.5,
        },
    ]}
    right = {"coefficients": [
        {
            "outcome_crop": "corn", "irrigation_class": "dryland",
            "family": "drought_only", "term": "d0_weeks",
            "exact_percent_change_per_equivalent_week": -0.3,
        },
        {
            "outcome_crop": "corn", "irrigation_class": "dryland",
            "family": "drought_only", "term": "d1_weeks",
            "exact_percent_change_per_equivalent_week": -0.1,
        },
    ]}
    movement = coefficient_movement(left, right)
    assert movement["coefficient_count"] == 2
    assert abs(movement["mean_absolute_movement_percentage_point_per_equivalent_week"] - 0.25) < 1e-12
    assert movement["maximum_absolute_movement"]["term"] == "d1_weeks"
    print("agricultural-area summary diagnostic-binding tests passed")


if __name__ == "__main__":
    main()
