import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_sector_transfer as transfer


CONTRACT_PATH = ROOT / "config" / "moore_sector_transfer_v1.json"


class SectorTransferTests(unittest.TestCase):
    def test_real_bound_receipts_build_only_allowed_interface(self):
        result = transfer.build_transfer(ROOT, CONTRACT_PATH)
        self.assertEqual(set(result["sectors"]), {"labor", "agriculture"})
        self.assertEqual(result["sectors"]["agriculture"]["disposition"], "replacement_only")
        self.assertAlmostEqual(
            result["sectors"]["labor"]["equal_weight_structural_mean_2020usd_per_tco2"],
            40.56425698048089,
        )
        self.assertFalse(result["overlap_and_claim_gates"]["combined_scc_authorized"])
        self.assertNotIn("total", result["sectors"])

    def test_receipt_hash_tampering_fails_closed(self):
        contract = json.loads(CONTRACT_PATH.read_text())
        contract["receipts"]["ISO"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(contract))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                transfer.build_transfer(ROOT, path)

    def test_forbidden_total_transfer_fails_closed(self):
        contract = json.loads(CONTRACT_PATH.read_text())
        contract["transfer_sectors"].append("total")
        with self.assertRaisesRegex(ValueError, "exactly labor and agriculture"):
            transfer.validate_contract(contract)

    def test_agriculture_addition_fails_closed(self):
        contract = json.loads(CONTRACT_PATH.read_text())
        contract["sector_rules"]["agriculture"]["disposition"] = "candidate_addition"
        with self.assertRaisesRegex(ValueError, "replacement_only"):
            transfer.validate_contract(contract)

    def test_open_combined_claim_gate_fails_closed(self):
        contract = json.loads(CONTRACT_PATH.read_text())
        contract["hard_gates"]["allow_combined_scc_claim"] = True
        with self.assertRaisesRegex(ValueError, "all hard gates"):
            transfer.validate_contract(contract)

    def test_invariant_mismatch_fails_closed(self):
        receipt = json.loads((ROOT / "data/provenance/labor_ag_sectoral_scc_n10000_iso_20261011.json").read_text())
        receipt["pulse_year"] = 2020
        invariants = json.loads(CONTRACT_PATH.read_text())["common_invariants"]
        with self.assertRaisesRegex(ValueError, "pulse_year"):
            transfer.validate_receipt(receipt, "ISO", invariants)

    def test_nonadditive_sector_summary_fails_closed(self):
        receipt = json.loads((ROOT / "data/provenance/labor_ag_sectoral_scc_n10000_iso_20261011.json").read_text())
        receipt["summary"]["total"]["expected_scc_2020usd_per_tco2"] += 1
        invariants = json.loads(CONTRACT_PATH.read_text())["common_invariants"]
        with self.assertRaisesRegex(ValueError, "do not sum"):
            transfer.validate_receipt(receipt, "ISO", invariants)


if __name__ == "__main__":
    unittest.main()
