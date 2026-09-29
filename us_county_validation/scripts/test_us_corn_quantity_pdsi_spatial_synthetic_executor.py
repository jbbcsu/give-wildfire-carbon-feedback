#!/usr/bin/env python3
"""Focused tests for the synthetic-only post-authorization corn executor."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import run_us_corn_quantity_pdsi_spatial_synthetic_executor as executor  # noqa: E402


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


class RealPathGateTests(unittest.TestCase):
    def test_real_path_fails_before_loader_or_fit(self) -> None:
        loader, fitter = mock.Mock(), mock.Mock()
        with self.assertRaises(PermissionError):
            executor.execute_real_path(None, loader, fitter)
        loader.assert_not_called()
        fitter.assert_not_called()


class SyntheticInputTests(unittest.TestCase):
    def test_unmarked_loader_is_rejected(self) -> None:
        frame = executor.make_synthetic_fixture()
        frame.attrs.clear()
        with self.assertRaises(ValueError):
            executor.run_synthetic(lambda: frame)

    def test_unpaired_practice_is_rejected(self) -> None:
        frame = executor.make_synthetic_fixture()
        frame = frame.drop(frame.index[0]).copy()
        frame.attrs["source_role"] = "synthetic_fixture_only"
        frame.attrs["contains_real_outcomes"] = False
        with self.assertRaises(ValueError):
            executor.run_synthetic(lambda: frame)

    def test_stacked_family_name_is_rejected(self) -> None:
        frame = executor.make_synthetic_fixture().query("irrigation_practice == 'non_irrigated'")
        with self.assertRaises(ValueError):
            executor.design(frame, "quantity_pdsi")


class SyntheticOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = executor.run_synthetic(executor.make_synthetic_fixture)

    def test_four_separate_full_cells_and_exclusive_terms(self) -> None:
        self.assertEqual(len(self.result["full_sample"]), 4)
        self.assertFalse(self.result["practices_pooled"])
        self.assertFalse(self.result["families_stacked"])
        for cell in self.result["full_sample"]:
            terms = cell["design_terms"]
            if cell["family"] == "quantity":
                self.assertTrue(any("precipitation" in term for term in terms))
                self.assertFalse(any("pdsi" in term for term in terms))
            else:
                self.assertTrue(any("pdsi" in term for term in terms))
                self.assertFalse(any("precipitation" in term for term in terms))

    def test_covariance_plumbing_has_cr1_and_both_cutoffs(self) -> None:
        self.assertEqual(self.result["spatial_cutoffs_km"], [250.0, 500.0])
        for cell in self.result["full_sample"]:
            for contrast in cell["contrasts"]:
                self.assertEqual(
                    set(contrast["standard_errors"]),
                    {"county_cr1", "spatial_250km", "spatial_500km"},
                )
                self.assertTrue(all(value > 0 for value in contrast["standard_errors"].values()))

    def test_leave_state_and_terminal_schemas(self) -> None:
        self.assertEqual(len(self.result["leave_one_state"]), 4)
        self.assertTrue(all(len(block["omissions"]) == 5 for block in self.result["leave_one_state"]))
        self.assertEqual(len(self.result["terminal_validation"]), 4)
        for block in self.result["terminal_validation"]:
            self.assertEqual((block["development"]["year_min"], block["development"]["year_max"]), (1981, 2011))
            self.assertEqual((block["terminal"]["year_min"], block["terminal"]["year_max"]), (2012, 2018))
            self.assertEqual(len(block["development"]["contrasts"]), 3)
            self.assertEqual(len(block["terminal"]["contrasts"]), 3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if args.receipt:
        payload = {
            "schema": "us_corn_quantity_pdsi_spatial_synthetic_executor_tests_v1",
            "status": "passed" if result.wasSuccessful() else "failed",
            "tests_run": int(result.testsRun), "failures": len(result.failures),
            "errors": len(result.errors),
            "test_module": {"path": str(Path(__file__).resolve().relative_to(executor.PROJECT)), "sha256": digest(Path(__file__))},
            "executor": {"path": str(Path(executor.__file__).resolve().relative_to(executor.PROJECT)), "sha256": digest(Path(executor.__file__))},
            "spatial_primitives": {"path": "us_county_validation/scripts/us_corn_spatial_inference_primitives.py", "sha256": digest(SCRIPT_DIR / "us_corn_spatial_inference_primitives.py")},
            "real_outcome_rows_read": 0, "real_response_fits": 0,
        }
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
