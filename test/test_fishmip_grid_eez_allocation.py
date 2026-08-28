#!/usr/bin/env python3
"""Synthetic failure-mode tests for FishMIP maritime allocation."""

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_fishmip_grid_eez_allocation import validate  # noqa: E402


support = pd.DataFrame(
    [
        {"grid_lat_index": 1, "grid_lon_index": 2, "grid_lat": 10.5, "grid_lon": 20.5, "cell_area_weight": 2.0},
        {"grid_lat_index": 1, "grid_lon_index": 3, "grid_lat": 10.5, "grid_lon": 21.5, "cell_area_weight": 1.0},
    ]
)
allocation = pd.DataFrame(
    [
        {"grid_lat_index": 1, "grid_lon_index": 2, "grid_lat": 10.5, "grid_lon": 20.5, "allocation_entity": "USA", "entity_type": "sovereign_eez", "iso3": "USA", "area_fraction": 0.75, "source_version": "v1", "source_license": "CC-BY-4.0", "country_aggregation_eligible": True},
        {"grid_lat_index": 1, "grid_lon_index": 2, "grid_lat": 10.5, "grid_lon": 20.5, "allocation_entity": "HIGH_SEAS", "entity_type": "high_seas", "iso3": "", "area_fraction": 0.25, "source_version": "v1", "source_license": "CC-BY-4.0", "country_aggregation_eligible": False},
        {"grid_lat_index": 1, "grid_lon_index": 3, "grid_lat": 10.5, "grid_lon": 21.5, "allocation_entity": "JOINT_1", "entity_type": "joint_or_disputed", "iso3": "", "area_fraction": 1.0, "source_version": "v1", "source_license": "CC-BY-4.0", "country_aggregation_eligible": False},
    ]
)
crosswalk = pd.DataFrame([{"iso3": "USA", "fund_region": "USA"}])

result = validate(support, allocation, crosswalk, source_version="v1", source_license="CC-BY-4.0")
assert result["status"] == "passed_geometry_accounting_only"
assert result["fishmip_support_cells"] == 2
assert result["mapped_sovereign_iso3"] == ["USA"]
assert result["high_seas_country_aggregation_eligible"] is False


def expect_failure(frame: pd.DataFrame, message: str) -> None:
    try:
        validate(support, frame, crosswalk, source_version="v1", source_license="CC-BY-4.0")
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"expected failure containing {message!r}")


bad_sum = allocation.copy()
bad_sum.loc[0, "area_fraction"] = 0.5
expect_failure(bad_sum, "fractions do not sum")

bad_iso = allocation.copy()
bad_iso.loc[0, "iso3"] = "ZZZ"
expect_failure(bad_iso, "mapped GIVE ISO3")

bad_joint = allocation.copy()
bad_joint.loc[2, "country_aggregation_eligible"] = True
expect_failure(bad_joint, "only sovereign EEZ")

missing_cell = allocation.loc[allocation.grid_lon_index.eq(2)].copy()
expect_failure(missing_cell, "exactly cover")

print("FishMIP grid/EEZ allocation preflight tests passed")
