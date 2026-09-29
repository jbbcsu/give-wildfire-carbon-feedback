#!/usr/bin/env python3
"""Synthetic-only tests for the frozen corn spatial-inference protocol."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tomllib
import unittest
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from us_corn_spatial_inference_primitives import (  # noqa: E402
    county_cr1_meat,
    county_plus_spatial_covariance,
    influence_gate,
    spatial_cross_county_meat,
    terminal_stability_gate,
)
from validate_us_corn_quantity_pdsi_spatial_protocol import validate_contract  # noqa: E402


PROTOCOL = PROJECT / "us_county_validation/us_corn_quantity_pdsi_spatial_inference_v1.toml"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = tomllib.loads(PROTOCOL.read_text(encoding="utf-8"))

    def test_canonical_contract_passes(self) -> None:
        validate_contract(self.contract)

    def test_real_fit_gate_cannot_open(self) -> None:
        changed = copy.deepcopy(self.contract)
        changed["real_response_fit_authorized"] = True
        with self.assertRaises(ValueError):
            validate_contract(changed)

    def test_family_stacking_cannot_open(self) -> None:
        changed = copy.deepcopy(self.contract)
        changed["family_separation"]["stacking_direct_rainfall_and_pdsi"] = True
        with self.assertRaises(ValueError):
            validate_contract(changed)

    def test_distribution_cannot_be_promoted(self) -> None:
        changed = copy.deepcopy(self.contract)
        changed["preidentified_influence"]["distribution_family_status"] = "eligible"
        with self.assertRaises(ValueError):
            validate_contract(changed)


class SpatialMeatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.x = np.array([[1.0, -1.0], [1.0, 0.0], [1.0, 1.0], [1.0, 2.0]])
        self.residual = np.array([1.0, -0.5, 0.75, -0.25])
        self.counties = np.array(["A", "B", "A", "B"])
        self.years = np.array([2000, 2000, 2001, 2001])

    def test_distant_counties_reduce_to_county_cr1(self) -> None:
        latitude = np.array([0.0, 0.0, 0.0, 0.0])
        longitude = np.array([0.0, 20.0, 0.0, 20.0])
        covariance = county_plus_spatial_covariance(
            self.x, self.residual, self.counties, self.years,
            latitude, longitude, 250.0,
        )
        bread = np.linalg.inv(self.x.T @ self.x)
        expected = bread @ county_cr1_meat(self.x, self.residual, self.counties) @ bread
        np.testing.assert_allclose(covariance, expected, rtol=0, atol=1e-14)

    def test_spatial_addition_matches_ordered_pair_definition(self) -> None:
        x = np.ones((2, 1))
        residual = np.ones(2)
        counties = np.array(["A", "B"])
        years = np.array([2000, 2000])
        latitude = np.array([0.0, 0.0])
        longitude = np.array([0.0, 1.0])
        distance = 111.1950802335329
        cutoff = 2 * distance
        meat = spatial_cross_county_meat(
            x, residual, counties, years, latitude, longitude, cutoff
        )
        np.testing.assert_allclose(meat, np.array([[1.0]]), rtol=0, atol=2e-12)

    def test_same_county_pair_is_excluded(self) -> None:
        meat = spatial_cross_county_meat(
            np.ones((2, 1)), np.ones(2), np.array(["A", "A"]),
            np.array([2000, 2000]), np.array([0.0, 0.0]),
            np.array([0.0, 0.1]), 250.0,
        )
        np.testing.assert_array_equal(meat, np.zeros((1, 1)))

    def test_row_order_invariance(self) -> None:
        latitude = np.array([40.0, 40.5, 40.0, 40.5])
        longitude = np.array([-100.0, -100.5, -100.0, -100.5])
        original = spatial_cross_county_meat(
            self.x, self.residual, self.counties, self.years,
            latitude, longitude, 250.0,
        )
        order = np.array([2, 0, 3, 1])
        shuffled = spatial_cross_county_meat(
            self.x[order], self.residual[order], self.counties[order], self.years[order],
            latitude[order], longitude[order], 250.0,
        )
        np.testing.assert_allclose(original, shuffled, rtol=0, atol=1e-14)


class GateTests(unittest.TestCase):
    def test_influence_dfbeta_and_sign(self) -> None:
        passing = influence_gate(0.20, 0.10, np.array([0.18, 0.23]), 1.0)
        self.assertTrue(passing["all_pass"])
        failing = influence_gate(0.20, 0.10, np.array([-0.01, 0.21]), 1.0)
        self.assertFalse(failing["all_pass"])
        self.assertFalse(failing["sign_pass"])

    def test_terminal_difference_and_sign(self) -> None:
        passing = terminal_stability_gate(0.20, 0.10, 0.15, 0.10, 1.96)
        self.assertTrue(passing["all_pass"])
        failing = terminal_stability_gate(0.20, 0.05, -0.10, 0.05, 1.96)
        self.assertFalse(failing["all_pass"])
        self.assertFalse(failing["sign_pass"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if args.receipt:
        payload = {
            "schema": "us_corn_quantity_pdsi_spatial_synthetic_tests_v1",
            "status": "passed" if result.wasSuccessful() else "failed",
            "tests_run": int(result.testsRun),
            "failures": int(len(result.failures)),
            "errors": int(len(result.errors)),
            "protocol": {"path": str(PROTOCOL.relative_to(PROJECT)), "sha256": digest(PROTOCOL)},
            "test_module": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
            "inference_primitives": {
                "path": "us_county_validation/scripts/us_corn_spatial_inference_primitives.py",
                "sha256": digest(SCRIPT_DIR / "us_corn_spatial_inference_primitives.py"),
            },
            "real_outcome_rows_read": 0,
            "real_response_fits": 0,
        }
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
