#!/usr/bin/env python3
"""Execution checks for the fixed nine-county, five-month estimator sample."""
from __future__ import annotations

from pathlib import Path

from run_nclimgrid_estimator_spatiotemporal_sample import run


root = Path(__file__).resolve().parents[2]
contract = root / "us_county_validation/nclimgrid_estimator_spatiotemporal_expansion_v2.toml"
result = run(contract, root)
assert result["months"] == [1, 4, 6, 9, 12]
assert result["result_cells"] == 180
assert len(result["monthly_audits"]) == 5
assert result["estimators_declared_equivalent"] is False
assert result["relationship_estimated"] is False
assert result["response_damage_or_scc_authorized"] is False
print("nClimGrid five-month estimator execution tests passed")
