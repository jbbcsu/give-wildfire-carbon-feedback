#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_air_pollution_target_interface as builder
import validate_air_pollution_target_interface as validator

CONFIG = ROOT / "config/air_pollution_target_interface_v1.json"
RECEIPT = ROOT / "data/provenance/air_pollution_target_interface_v1.json"


class AirPollutionTargetInterfaceTests(unittest.TestCase):
    def test_evidence_and_target_rows_pass(self):
        config = builder.load_config(CONFIG)
        bound, factor = builder.validate_evidence(ROOT, config)
        rows = builder.validate_and_transform(config, factor)
        self.assertEqual(len(bound), 5)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1]["target_price_mean_usd_per_tco2"], "19.298741")

    def test_generated_interface_validates(self):
        result = validator.validate(ROOT, CONFIG, RECEIPT)
        self.assertEqual(result["status"], "passed_price_harmonization_and_fail_closed_gates")
        self.assertFalse(result["headline_addition_authorized"])

    def test_additive_promotion_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["components"][0]["additive_to_baseline_give"] = True
        with self.assertRaisesRegex(ValueError, "promoted to additive"):
            builder.validate_and_transform(changed, Decimal("0.8390757005104031468225214393"))

    def test_mortality_overlap_promotion_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["components"][0]["mortality_overlap_cleared"] = True
        with self.assertRaisesRegex(ValueError, "mortality overlap promoted"):
            builder.validate_and_transform(changed, Decimal("1"))

    def test_invented_annual_paths_fail(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["components"][0]["annual_marginal_paths_available"] = True
        with self.assertRaisesRegex(ValueError, "annual paths invented"):
            builder.validate_and_transform(changed, Decimal("1"))

    def test_false_pulse_harmonization_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["components"][1]["blocker_codes"].remove("PULSE_YEAR_UNHARMONIZED")
        with self.assertRaisesRegex(ValueError, "pulse-year blocker inconsistent"):
            builder.validate_and_transform(changed, Decimal("0.8390757005104031468225214393"))

    def test_open_portfolio_gate_fails(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["portfolio_gates"]["any_component_additive_to_baseline_give"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "portfolio gates"):
                builder.load_config(path)


if __name__ == "__main__":
    unittest.main()
