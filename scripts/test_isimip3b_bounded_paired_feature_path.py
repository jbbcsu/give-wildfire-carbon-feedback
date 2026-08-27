#!/usr/bin/env python3
"""Synthetic contract checks for the bounded paired feature-path smoke."""
from evaluate_isimip3b_bounded_paired_feature_path import (
    CONFIG_ROLE,
    CONFIG_SCHEMA,
    support,
)


assert CONFIG_SCHEMA == "isimip3b_bounded_paired_feature_path_config_v1"
assert "not_fair_pulse_production_emulator_damage_or_scc" in CONFIG_ROLE
assert support(-1.0, 0.0, 1.0) == "below"
assert support(0.0, 0.0, 1.0) == "within"
assert support(1.0, 0.0, 1.0) == "within"
assert support(2.0, 0.0, 1.0) == "above"
print("bounded paired feature-path synthetic tests passed")
