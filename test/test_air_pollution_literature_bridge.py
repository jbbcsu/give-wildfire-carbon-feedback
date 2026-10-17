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
import build_air_pollution_literature_bridge as builder
import validate_air_pollution_literature_bridge as validator


CONFIG = ROOT / "config/air_pollution_literature_bridge_v1.json"
RECEIPT = ROOT / "data/provenance/air_pollution_literature_bridge_v1.json"


class AirPollutionLiteratureBridgeTests(unittest.TestCase):
    def test_registered_evidence_and_rows_pass(self):
        config = builder.load_config(CONFIG)
        bound = builder.validate_evidence(ROOT, config)
        rows = builder.validate_rows(config)
        self.assertEqual(len(bound), 6)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(not row["additive_to_give"] for row in rows))

    def test_generated_interface_validates(self):
        result = validator.validate(ROOT, CONFIG, RECEIPT)
        self.assertEqual(result["status"], "passed_external_benchmark_interface_only")
        self.assertFalse(result["headline_addition_authorized"])

    def test_hash_tampering_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["bound_evidence"]["epa_article_source"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            builder.validate_evidence(ROOT, changed)

    def test_additive_promotion_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["benchmarks"][0]["additive_to_give"] = True
        with self.assertRaisesRegex(ValueError, "marked additive"):
            builder.validate_rows(changed)

    def test_partial_interval_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["benchmarks"][0]["interval_high_usd_per_tco2"] = None
        with self.assertRaisesRegex(ValueError, "partial interval"):
            builder.validate_rows(changed)

    def test_open_hard_gate_fails(self):
        config = json.loads(CONFIG.read_text())
        config["hard_gates"]["give_transfer_authorized"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hard gates"):
                builder.load_config(path)


if __name__ == "__main__":
    unittest.main()
