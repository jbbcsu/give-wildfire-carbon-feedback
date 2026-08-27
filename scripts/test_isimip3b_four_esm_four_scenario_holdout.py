#!/usr/bin/env python3
"""Synthetic identity gates for the four-ESM joint holdout."""
from evaluate_isimip3b_four_esm_four_scenario_holdout import EXPECTED_ESMS, EXPECTED_SCENARIOS


assert EXPECTED_ESMS == {"GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "mri-esm2-0"}
assert EXPECTED_SCENARIOS == {"historical", "ssp126", "ssp370", "ssp585"}
print("joint four-ESM/four-scenario holdout synthetic tests passed")
