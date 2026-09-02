#!/usr/bin/env python3
"""Contract checks for the preregistered nine-county estimator sample."""
from __future__ import annotations

import tempfile
from pathlib import Path

from run_nclimgrid_estimator_spatial_sample import run


root = Path(__file__).resolve().parents[2]
contract = root / "us_county_validation/nclimgrid_estimator_spatial_sample_v1.toml"

with tempfile.TemporaryDirectory() as temporary:
    tampered = Path(temporary) / "contract.toml"
    tampered.write_text(contract.read_text(encoding="utf-8").replace('"31039"', '"31041"'), encoding="utf-8")
    try:
        run(tampered, root)
    except ValueError as error:
        assert "county sample" in str(error)
    else:
        raise AssertionError("changed county sample was accepted")

print("nClimGrid nine-county estimator spatial contract tests passed")
