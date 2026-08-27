#!/usr/bin/env python3
"""Independent validator for the bounded five-ESM/four-scenario holdout."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import validate_isimip3b_four_esm_four_scenario_holdout as validator
from evaluate_isimip3b_five_esm_four_scenario_holdout import (
    CONFIG_ROLE,
    EXPECTED_ESMS,
    EXPECTED_SCENARIOS,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--esm-holdouts", type=Path, required=True)
    parser.add_argument("--scenario-holdouts", type=Path, required=True)
    args = parser.parse_args()

    validator.AUDIT_SCHEMA = "isimip3b_bounded_five_esm_four_scenario_holdout_v1"
    validator.IMPLEMENTATION_RECEIPT_COUNT = 5
    validator.CONFIG_ROLE = CONFIG_ROLE
    validator.EXPECTED_ESMS = EXPECTED_ESMS
    validator.EXPECTED_SCENARIOS = EXPECTED_SCENARIOS
    result = validator.validate(
        args.audit.resolve(),
        args.training.resolve(),
        args.esm_holdouts.resolve(),
        args.scenario_holdouts.resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
