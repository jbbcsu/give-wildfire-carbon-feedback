#!/usr/bin/env python3

from __future__ import annotations

import copy
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_master_ledger as builder
import validate_master_ledger as validator

CONFIG = ROOT / "config/master_ledger_v1.json"
RECEIPT = ROOT / "data/provenance/master_damage_sector_ledger_receipt_v1.json"
LEDGER = ROOT / "data/derived/master_damage_sector_ledger_v1.csv"


class MasterLedgerTests(unittest.TestCase):
    def test_build_inputs_and_rows(self):
        config = builder.load_config(CONFIG)
        payloads, bound = builder.load_evidence(ROOT, config)
        rows = builder.build_rows(config, payloads)
        self.assertEqual(len(bound), 30)
        self.assertEqual(len(rows), 23)
        self.assertFalse(any(row["master_total_eligible"] for row in rows))

    def test_independent_validation_passes(self):
        result = validator.validate(ROOT, CONFIG, RECEIPT)
        self.assertEqual(result["status"], "passed_hash_bound_tiered_ledger_and_no_sum_gate")
        self.assertFalse(result["headline_master_total_authorized"])

    def test_headline_total_gate_cannot_open(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["aggregation_policy"]["headline_master_total_authorized"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "headline total gate opened"):
                builder.load_config(path)

    def test_component_total_gate_cannot_open(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["rows"][0]["master_total_eligible"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "master-total gate opened"):
                builder.load_config(path)

    def test_source_hash_tampering_fails(self):
        config = builder.load_config(CONFIG)
        changed = copy.deepcopy(config)
        changed["evidence"]["labor_integration"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "evidence hash mismatch"):
            builder.load_evidence(ROOT, changed)

    def test_invented_blocked_value_fails(self):
        with LEDGER.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        changed = copy.deepcopy(rows)
        next(row for row in changed if row["component_id"] == "dengue_nonfatal_morbidity")["central_value"] = "1.0"
        with self.assertRaisesRegex(ValueError, "invented value"):
            validator.validate_rows(changed)

    def test_category_promotion_fails(self):
        with LEDGER.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        changed = copy.deepcopy(rows)
        next(row for row in changed if row["component_id"] == "wildfire_smoke_pm25")["category"] = "integrated_pair_tested"
        with self.assertRaisesRegex(ValueError, "category drift"):
            validator.validate_rows(changed)

    def test_tropical_cyclone_is_not_labeled_paired_quantile(self):
        with LEDGER.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        row = next(item for item in rows if item["component_id"] == "tropical_cyclone_macro")
        self.assertEqual(row["statistic"], "difference_of_published_medians_not_paired_component_quantile")
        self.assertFalse(row["master_total_eligible"] == "true")

    def test_winter_recreation_remains_nonadditive_revenue(self):
        with LEDGER.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        row = next(item for item in rows if item["component_id"] == "conus_winter_recreation_revenue")
        self.assertEqual(row["category"], "blocked_nonadditive")
        self.assertIn("lost_revenue_not_welfare", row["statistic"])

    def test_heat_morbidity_has_no_invented_scc(self):
        with LEDGER.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        row = next(item for item in rows if item["component_id"] == "heat_morbidity_direct_medical_costs")
        self.assertEqual(row["central_value"], "")
        self.assertEqual(row["source_status"], "BLOCKED_NO_MARGINAL_SCC")

    def test_grid_direct_cost_is_not_outage_welfare_or_additive(self):
        with LEDGER.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        row = next(item for item in rows if item["component_id"] == "conus_grid_td_direct_cost")
        self.assertEqual(row["category"], "blocked_nonadditive")
        self.assertIn("direct_cost_not_outage_welfare", row["statistic"])
        self.assertEqual(row["master_total_eligible"], "false")

    def test_macro_comparator_is_neither_additive_nor_residual(self):
        with LEDGER.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        row = next(item for item in rows if item["component_id"] == "bilal_kaenzig_global_macro")
        self.assertEqual(row["category"], "mutually_exclusive_comparator")
        self.assertIn("not an omitted-sector residual", row["value_role"])
        self.assertEqual(row["master_total_eligible"], "false")
        self.assertEqual(len(row["incompatibility_codes"].split("|")), 5)

    def test_education_heat_has_no_scc_or_income_conversion(self):
        config = builder.load_config(CONFIG)
        payloads, _ = builder.load_evidence(ROOT, config)
        row = builder.extract("education_heat_learning", payloads)
        self.assertEqual(row["central_value"], "")
        source = payloads["education_heat_readiness"]
        self.assertFalse(source["scc_output_created"])
        self.assertFalse(source["lifetime_income_conversion_authorized"])

    def test_freshwater_angling_scenarios_are_not_scc(self):
        config = builder.load_config(CONFIG)
        payloads, _ = builder.load_evidence(ROOT, config)
        row = builder.extract("freshwater_recreational_angling", payloads)
        self.assertEqual(row["central_value"], "")
        source = payloads["freshwater_angling_readiness"]
        self.assertFalse(source["scc_output_created"])
        self.assertFalse(source["give_addition_authorized"])
        self.assertEqual(source["reported_five_gcm_average_million_2015usd"]["coldwater_fishing|RCP8.5"], -100000.0)


if __name__ == "__main__":
    unittest.main()
