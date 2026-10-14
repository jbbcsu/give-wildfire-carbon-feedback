#!/usr/bin/env python3
"""Focused tests for the EPA component/net and boundary gate."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_component_net_boundary as gate


CONFIG = ROOT / "config/epa_globalaq_component_net_gate_v1.json"


class ComponentNetBoundaryTests(unittest.TestCase):
    def load_config(self):
        return json.loads(CONFIG.read_text())

    def test_real_release_fails_claim_gates_closed(self):
        receipt = gate.reconcile(ROOT, CONFIG)
        self.assertEqual(receipt["source"]["commit"], "1139e7aff1ca7806b6b542268e829f9759dd8808")
        self.assertEqual(set(receipt["released_2pct_ramsey"]["model_reconciliation"]), {"CESM2", "GISS"})
        means = receipt["released_2pct_ramsey"]["model_mean_reconciliation"]
        self.assertAlmostEqual(means["ozone"], 16.671648911048777)
        self.assertAlmostEqual(means["pm25_candidate"], -24.529048760713994)
        self.assertAlmostEqual(means["separate_net"], -34.66761788076073)
        self.assertAlmostEqual(means["net_minus_component_sum"], -26.810218031095513)
        self.assertFalse(receipt["metadata_audit"]["price_year_resolved"])
        self.assertFalse(receipt["metadata_audit"]["repository_machine_verifies_open_burning_exclusion"])
        self.assertFalse(receipt["article_alignment"]["calibration_or_rescaling_performed"])
        self.assertTrue(all(value is False for value in receipt["hard_gates"].values()))

    def test_allows_only_exact_summary_schema(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "component.csv"
            path.write_text("discount.rate,Pollutant,Model,mean_npd\n2.0% Ramsey,Ozone,GISS,1\n")
            with self.assertRaisesRegex(ValueError, "unexpected schema"):
                gate.read_csv_exact(path, gate.COMPONENT_SCHEMA)

    def test_duplicate_component_key_fails(self):
        rows = [
            {"discount.rate": "2.0% Ramsey", "Pollutant": "Ozone", "Model": "GISS"},
            {"discount.rate": "2.0% Ramsey", "Pollutant": "Ozone", "Model": "GISS"},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            gate.validate_unique(rows, ("discount.rate", "Pollutant", "Model"), "component")

    def test_nonfinite_value_fails(self):
        with self.assertRaisesRegex(ValueError, "non-finite"):
            gate.finite_float("nan", "synthetic")

    def test_source_hash_tampering_fails(self):
        config = self.load_config()
        config["bound_files"]["component_summary"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            gate.bind_files(ROOT, config)

    def test_any_open_claim_gate_fails(self):
        config = self.load_config()
        config["hard_gates"]["give_transfer_authorized"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "hard gates"):
                gate.reconcile(ROOT, path)

    def test_burning_metadata_inventory_change_fails(self):
        config = self.load_config()
        config["boundary_metadata_search"]["case_insensitive_phrases"] = ["global"]
        with self.assertRaisesRegex(ValueError, "burning-boundary"):
            gate.validate_source_metadata(gate.bind_files(ROOT, config), config)


if __name__ == "__main__":
    unittest.main()
