#!/usr/bin/env python3
"""Synthetic identity gates for the three-ESM joint holdout."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_isimip3b_three_esm_four_scenario_holdout import (  # noqa: E402
    EXPECTED_ESMS,
    EXPECTED_SCENARIOS,
)

assert EXPECTED_ESMS == {"GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR"}
assert EXPECTED_SCENARIOS == {"historical", "ssp126", "ssp370", "ssp585"}
print("joint three-ESM/four-scenario holdout synthetic tests passed")
