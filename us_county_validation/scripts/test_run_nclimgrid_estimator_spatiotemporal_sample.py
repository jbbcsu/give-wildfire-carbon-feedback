#!/usr/bin/env python3
"""Contract checks for the fixed nine-county, three-month estimator sample."""
from __future__ import annotations

import tempfile
from pathlib import Path

from run_nclimgrid_estimator_spatiotemporal_sample import run


root = Path(__file__).resolve().parents[2]
contract = root / "us_county_validation/nclimgrid_estimator_spatiotemporal_sample_v1.toml"


def must_fail(old: str, new: str, message: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        tampered = Path(temporary) / "contract.toml"
        tampered.write_text(contract.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        try:
            run(tampered, root)
        except ValueError as error:
            assert message in str(error)
        else:
            raise AssertionError("changed contract was accepted")


must_fail("months = [1, 6, 12]", "months = [1, 7, 12]", "registered months")
must_fail('"31039"', '"31041"', "county sample")
must_fail("outcomes_read = false", "outcomes_read = true", "closed gate")

print("nClimGrid spatiotemporal estimator contract tests passed")
