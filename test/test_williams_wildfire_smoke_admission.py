#!/usr/bin/env python3
"""Synthetic and local-evidence tests for the Williams admission gate."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_williams_wildfire_smoke_admission as gate


CONTRACT = ROOT / "config/williams_wildfire_smoke_admission_v1.json"
TRACKED_RECEIPT = ROOT / "data/provenance/williams_wildfire_smoke_admission_20261014.json"


class WilliamsWildfireSmokeAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = gate.read_contract(CONTRACT)

    def build_synthetic_manifest(self, root: Path) -> Path:
        groups = {}
        for name, checks in self.contract["required_artifact_groups"].items():
            receipt = {
                "schema": gate.GROUP_RECEIPT_SCHEMA,
                "group": name,
                "validation_passed": True,
                "bound_artifacts": [
                    {
                        "path": f"synthetic/{name}.csv",
                        "bytes": 1,
                        "sha256": hashlib.sha256(b"x").hexdigest(),
                    }
                ],
                "checks": checks,
            }
            receipt_path = root / f"{name}.json"
            payload = (json.dumps(receipt, sort_keys=True) + "\n").encode()
            receipt_path.write_bytes(payload)
            groups[name] = {
                "validation_receipt": {
                    "path": receipt_path.relative_to(root).as_posix(),
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            }
        manifest = {
            "schema": gate.MANIFEST_SCHEMA,
            "calibration_to_reported_values_performed": False,
            "wildfire_co2_project_accessed": False,
            "source_conflict_resolutions": {
                "monte_carlo_trials": {
                    "resolved": True,
                    "draft_reported_trial_count": 100,
                    "admitted_trial_count": 10000,
                    "authority_reference": "synthetic_test_only",
                },
                "projection_horizon": {
                    "resolved": True,
                    "start_year": 2025,
                    "end_year": 2300,
                    "year_count": 276,
                    "authority_reference": "synthetic_test_only",
                },
            },
            "groups": groups,
        }
        path = root / "manifest.json"
        path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def test_current_local_package_rejected_zero_of_eight(self):
        receipt = gate.audit_current(ROOT, CONTRACT)
        admission = receipt["operational_artifact_admission"]
        self.assertEqual(receipt["status"], "rejected_incomplete_local_artifacts")
        self.assertEqual(admission["groups_passed"], 0)
        self.assertEqual(admission["groups_required"], 8)
        self.assertFalse(admission["artifact_package_admitted_for_reproduction"])
        self.assertFalse(receipt["reported_values_used_as_calibration_targets"])
        self.assertFalse(receipt["wildfire_co2_project_files_used"])
        self.assertTrue(all(value is False for value in receipt["hard_gates"].values()))

    def test_tracked_receipt_matches_current_audit(self):
        tracked = json.loads(TRACKED_RECEIPT.read_text())
        current = gate.audit_current(ROOT, CONTRACT)
        current["created_at_utc"] = tracked["created_at_utc"]
        self.assertEqual(current, tracked)

    def test_complete_synthetic_package_passes_admission_only(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            synthetic_root = Path(directory)
            manifest = self.build_synthetic_manifest(synthetic_root)
            result = gate.evaluate_manifest(
                synthetic_root, self.contract, manifest, test_mode=True
            )
            self.assertEqual(result["groups_passed"], 8)
            self.assertTrue(result["artifact_package_admitted_for_reproduction"])
            self.assertFalse(result["reported_partial_scc_reproduced"])
            self.assertFalse(result["give_transfer_authorized"])
            self.assertFalse(result["replacement_or_addition_scc_authorized"])

    def test_missing_group_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            synthetic_root = Path(directory)
            manifest_path = self.build_synthetic_manifest(synthetic_root)
            manifest = json.loads(manifest_path.read_text())
            del manifest["groups"]["mortality_overlap_boundary"]
            manifest_path.write_text(json.dumps(manifest) + "\n")
            result = gate.evaluate_manifest(
                synthetic_root, self.contract, manifest_path, test_mode=True
            )
            self.assertEqual(result["groups_passed"], 7)
            self.assertFalse(result["artifact_package_admitted_for_reproduction"])

    def test_tampered_validation_receipt_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            synthetic_root = Path(directory)
            manifest_path = self.build_synthetic_manifest(synthetic_root)
            manifest = json.loads(manifest_path.read_text())
            spec = manifest["groups"]["simulation_inventory"]["validation_receipt"]
            spec["sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest) + "\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                gate.evaluate_manifest(synthetic_root, self.contract, manifest_path, test_mode=True)

    def test_calibration_and_wildfire_co2_scope_violations_fail(self):
        for field, message in (
            ("calibration_to_reported_values_performed", "calibration forbidden"),
            ("wildfire_co2_project_accessed", "scope violation"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                synthetic_root = Path(directory)
                manifest_path = self.build_synthetic_manifest(synthetic_root)
                manifest = json.loads(manifest_path.read_text())
                manifest[field] = True
                manifest_path.write_text(json.dumps(manifest) + "\n")
                with self.assertRaisesRegex(ValueError, message):
                    gate.evaluate_manifest(
                        synthetic_root, self.contract, manifest_path, test_mode=True
                    )

    def test_unresolved_trial_or_horizon_conflict_rejects(self):
        for conflict in ("monte_carlo_trials", "projection_horizon"):
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                synthetic_root = Path(directory)
                manifest_path = self.build_synthetic_manifest(synthetic_root)
                manifest = json.loads(manifest_path.read_text())
                manifest["source_conflict_resolutions"][conflict]["resolved"] = False
                manifest_path.write_text(json.dumps(manifest) + "\n")
                result = gate.evaluate_manifest(
                    synthetic_root, self.contract, manifest_path, test_mode=True
                )
                self.assertFalse(result["artifact_package_admitted_for_reproduction"])

    def test_production_rejects_synthetic_authority(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            synthetic_root = Path(directory)
            manifest_path = self.build_synthetic_manifest(synthetic_root)
            result = gate.evaluate_manifest(synthetic_root, self.contract, manifest_path)
            self.assertFalse(result["artifact_package_admitted_for_reproduction"])

    def test_group_check_drift_rejects(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            synthetic_root = Path(directory)
            manifest_path = self.build_synthetic_manifest(synthetic_root)
            manifest = json.loads(manifest_path.read_text())
            spec = manifest["groups"]["simulation_inventory"]["validation_receipt"]
            receipt_path = synthetic_root / spec["path"]
            receipt = json.loads(receipt_path.read_text())
            receipt["checks"] = copy.deepcopy(receipt["checks"])
            receipt["checks"]["simulation_count"] = 42
            payload = (json.dumps(receipt, sort_keys=True) + "\n").encode()
            receipt_path.write_bytes(payload)
            spec["bytes"] = len(payload)
            spec["sha256"] = hashlib.sha256(payload).hexdigest()
            manifest_path.write_text(json.dumps(manifest) + "\n")
            result = gate.evaluate_manifest(
                synthetic_root, self.contract, manifest_path, test_mode=True
            )
            self.assertEqual(result["groups_passed"], 7)
            self.assertFalse(result["artifact_package_admitted_for_reproduction"])


if __name__ == "__main__":
    unittest.main()
