#!/usr/bin/env python3
"""Synthetic identity gates for the five-ESM joint holdout."""
from evaluate_isimip3b_five_esm_four_scenario_holdout import (
    CONFIG_ROLE,
    CONFIG_SCHEMA,
    EXPECTED_ESMS,
    EXPECTED_SCENARIOS,
)


assert CONFIG_SCHEMA == "isimip3b_bounded_five_esm_four_scenario_holdout_config_v1"
assert "not_complete_temporal_emulator_damage_or_scc_input" in CONFIG_ROLE
assert EXPECTED_ESMS == {
    "GFDL-ESM4",
    "IPSL-CM6A-LR",
    "MPI-ESM1-2-HR",
    "mri-esm2-0",
    "UKESM1-0-LL",
}
assert EXPECTED_SCENARIOS == {"historical", "ssp126", "ssp370", "ssp585"}
print("joint five-ESM/four-scenario holdout synthetic tests passed")
