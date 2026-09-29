#!/usr/bin/env python3
"""Focused fail-closed and metadata-only tests for the corn dry-run adapter."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import build_us_corn_quantity_pdsi_spatial_dry_run as adapter  # noqa: E402


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


class AuthorizationGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = adapter.load_config()

    def test_canonical_real_run_fails_before_outcome_or_fit(self) -> None:
        with (
            mock.patch.object(adapter, "_open_real_outcome_columns") as outcome,
            mock.patch.object(adapter, "_invoke_real_fit") as fit,
            self.assertRaises(PermissionError),
        ):
            adapter.execute_real_run(self.config, None)
        outcome.assert_not_called()
        fit.assert_not_called()

    def test_missing_authorization_fails_even_if_contract_flags_are_mutated(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["authorization"]["real_run_enabled"] = True
        changed["real_outcome_read_authorized"] = True
        changed["real_response_fit_authorized"] = True
        with self.assertRaises(PermissionError):
            adapter.require_real_run_authorization(changed, None)

    def test_invalid_hash_binding_fails(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["authorization"]["real_run_enabled"] = True
        changed["real_outcome_read_authorized"] = True
        changed["real_response_fit_authorized"] = True
        with self.assertRaises((PermissionError, FileNotFoundError)):
            adapter.require_real_run_authorization(changed, Path("does-not-exist.json"))


class MetadataDryRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = adapter.build_manifest(adapter.DEFAULT_CONFIG)

    def test_no_outcome_or_data_pages_are_read(self) -> None:
        self.assertEqual(self.manifest["outcome_columns_opened"], [])
        self.assertEqual(self.manifest["data_pages_read"], 0)
        self.assertEqual(self.manifest["real_response_fits"], 0)
        for name in ("direct", "pdsi"):
            self.assertFalse(self.manifest["inputs"][name]["outcome_column_opened"])
            self.assertFalse(self.manifest["inputs"][name]["data_pages_read"])

    def test_all_four_cells_remain_blocked(self) -> None:
        self.assertEqual(len(self.manifest["planned_run_cells"]), 4)
        self.assertTrue(all("blocked" in cell["status"] for cell in self.manifest["planned_run_cells"]))

    def test_practice_separation_uses_bound_receipt(self) -> None:
        evidence = self.manifest["readiness_evidence"]
        self.assertTrue(evidence["exact_practice_pairs_and_exposures"])
        self.assertTrue(evidence["evidence_reused_without_row_read"])
        self.assertEqual(evidence["paired_exposure_rows"], 11857)

    def test_coordinate_schema_is_header_only(self) -> None:
        coordinate = self.manifest["inputs"]["coordinates"]
        self.assertEqual(coordinate["dbf_record_count_from_header"], 3233)
        self.assertEqual(coordinate["coordinate_records_read"], 0)
        self.assertEqual(coordinate["geometry_records_read"], 0)
        self.assertTrue({"GEOID", "INTPTLAT", "INTPTLON"}.issubset(coordinate["dbf_fields_from_header"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if args.receipt:
        config = adapter.DEFAULT_CONFIG
        payload = {
            "schema": "us_corn_quantity_pdsi_spatial_dry_run_tests_v1",
            "status": "passed" if result.wasSuccessful() else "failed",
            "tests_run": int(result.testsRun), "failures": len(result.failures), "errors": len(result.errors),
            "test_module": {"path": str(Path(__file__).resolve().relative_to(adapter.PROJECT)), "sha256": digest(Path(__file__))},
            "adapter": {"path": str(Path(adapter.__file__).resolve().relative_to(adapter.PROJECT)), "sha256": digest(Path(adapter.__file__))},
            "config": {"path": str(config.relative_to(adapter.PROJECT)), "sha256": digest(config)},
            "real_outcome_rows_read": 0, "real_response_fits": 0,
        }
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
