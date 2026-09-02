#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from validate_nclimgrid_estimator_spatiotemporal_expansion_contract import validate


root = Path(__file__).resolve().parents[2]
contract = root / "us_county_validation/nclimgrid_estimator_spatiotemporal_expansion_v2.toml"
result = validate(contract)
assert result["status"] == "preregistered_before_official_series_acquisition_or_comparison"
assert len(result["planned_official_urls"]) == 10
assert result["response_damage_or_scc_authorized"] is False

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(contract.read_text().replace("months = [1, 4, 6, 9, 12]", "months = [1, 5, 6, 9, 12]"), encoding="utf-8")
    try:
        validate(tampered)
    except ValueError as error:
        assert "fixed months" in str(error)
    else:
        raise AssertionError("changed months were accepted")

print("nClimGrid five-month estimator expansion contract tests passed")
