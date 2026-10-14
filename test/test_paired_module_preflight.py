import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_paired_module_preflight as preflight


CONTRACT_PATH = ROOT / "config" / "moore_paired_module_preflight_v1.json"


class PairedModulePreflightTests(unittest.TestCase):
    def load_contract(self):
        return json.loads(CONTRACT_PATH.read_text())

    def test_real_source_and_receipts_pass_as_two_separate_cases(self):
        result = preflight.validate_contract(ROOT, CONTRACT_PATH)
        self.assertEqual(set(result["structural_cases"]), {"LANCET", "ISO"})
        self.assertTrue(result["gates"]["paired_replacement_addition_source_graph_verified"])
        self.assertTrue(result["gates"]["case_outputs_remain_separate"])
        self.assertFalse(result["gates"]["cross_case_quantile_pooling_allowed"])
        self.assertFalse(result["gates"]["replacement_delta_promoted"])
        self.assertFalse(result["gates"]["combined_give_scc_authorized"])
        self.assertNotIn("pooled", result["structural_cases"])

    def test_source_hash_tampering_fails_closed(self):
        contract = self.load_contract()
        contract["source_files"]["get_model"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(contract))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                preflight.validate_contract(ROOT, path)

    def test_missing_iso_case_fails_closed(self):
        contract = self.load_contract()
        del contract["structural_cases"]["ISO"]
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(contract))
            with self.assertRaisesRegex(ValueError, "exactly LANCET and ISO"):
                preflight.validate_contract(ROOT, path)

    def test_quantile_pooling_gate_cannot_open(self):
        contract = self.load_contract()
        contract["output_contract"]["allow_cross_case_quantile_pooling"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(contract))
            with self.assertRaisesRegex(ValueError, "quantile_pooling"):
                preflight.validate_contract(ROOT, path)

    def test_agriculture_cannot_be_additive(self):
        contract = self.load_contract()
        contract["output_contract"]["allow_agriculture_addition"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(contract))
            with self.assertRaisesRegex(ValueError, "allow_agriculture_addition"):
                preflight.validate_contract(ROOT, path)

    def test_precipitation_cannot_be_stacked(self):
        contract = self.load_contract()
        contract["output_contract"]["allow_precipitation_stacking"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(contract))
            with self.assertRaisesRegex(ValueError, "allow_precipitation_stacking"):
                preflight.validate_contract(ROOT, path)

    def test_duplicate_or_reordered_component_installation_fails(self):
        contract = self.load_contract()
        contract["module_installation"]["replacement_components_added_in_order"] = [
            "AgricultureShare", "Agriculture", "Labor"
        ]
        with self.assertRaisesRegex(ValueError, "installation order"):
            preflight.validate_source_graph(contract, {
                name: (ROOT / spec["path"]).read_text()
                for name, spec in contract["source_files"].items()
            })

    def test_receipt_case_label_mismatch_fails(self):
        receipt = json.loads((ROOT / self.load_contract()["structural_cases"]["ISO"]["receipt"]["path"]).read_text())
        receipt["labor_function"] = "LANCET"
        with self.assertRaisesRegex(ValueError, "mislabeled"):
            preflight.validate_receipt(
                receipt, "ISO", self.load_contract()["execution_invariants"]
            )


if __name__ == "__main__":
    unittest.main()
