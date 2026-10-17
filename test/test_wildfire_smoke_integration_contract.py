#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_wildfire_smoke_integration_contract as builder
import validate_wildfire_smoke_integration_contract as validator

CONFIG = ROOT / "config/wildfire_smoke_additive_integration_v1.json"
RECEIPT = ROOT / "data/provenance/wildfire_smoke_integration_contract_v1.json"
SOURCE_PDF = Path("/Users/jbb/Downloads/Fire_SC_CO2_draft (1).pdf")


class WildfireSmokeIntegrationContractTests(unittest.TestCase):
    def test_source_evidence_and_row_pass(self):
        config = builder.load_config(CONFIG)
        bound = builder.validate_evidence(ROOT, config, SOURCE_PDF)
        row = builder.build_row(config)
        self.assertEqual(len(bound), 5)
        self.assertEqual(row["detailed_mean_usd_per_tco2"], 50.04)
        self.assertFalse(row["additive_to_baseline_give"])

    def test_independent_validator_rechecks_source_pdf(self):
        result = validator.validate(ROOT, CONFIG, RECEIPT, SOURCE_PDF)
        self.assertEqual(result["status"], "passed_source_normalization_and_fail_closed_additivity")
        self.assertTrue(result["source_pdf_reverified"])
        self.assertFalse(result["headline_addition_authorized"])

    def test_baseline_additive_promotion_fails(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["admission_gates"]["additive_to_baseline_give"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe admission gate open"):
                builder.load_config(path)

    def test_nonwildfire_additive_promotion_fails(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["admission_gates"]["additive_to_nonwildfire_air_pollution"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe admission gate open"):
                builder.load_config(path)

    def test_joint_health_function_promotion_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["boundary_assessment"]["wildfire_smoke_vs_nonwildfire_pm_joint_health_function_consistency_cleared"] = True
        with self.assertRaisesRegex(ValueError, "joint PM health-function gate opened"):
            builder.build_row(changed)

    def test_temperature_mortality_promotion_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["boundary_assessment"]["wildfire_smoke_vs_give_temperature_mortality_overlap_cleared"] = True
        with self.assertRaisesRegex(ValueError, "temperature mortality gate opened"):
            builder.build_row(changed)

    def test_source_mean_change_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["component"]["source_detailed_mean_usd_per_tco2"] = 50.0
        with self.assertRaisesRegex(ValueError, "source detailed mean changed"):
            builder.build_row(changed)

    def test_price_conversion_invention_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["target_normalization"]["price_conversion_factor"] = 0.9
        with self.assertRaisesRegex(ValueError, "unnecessary price conversion introduced"):
            builder.build_row(changed)

    def test_wrong_pdf_fails(self):
        config = builder.load_config(CONFIG)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "not-source.pdf"
            path.write_bytes(b"not the source")
            with self.assertRaisesRegex(ValueError, "source PDF hash mismatch"):
                builder.validate_evidence(ROOT, config, path)


if __name__ == "__main__":
    unittest.main()
