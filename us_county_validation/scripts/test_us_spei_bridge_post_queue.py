#!/usr/bin/env python3
"""Synthetic-only tests for the fail-closed post-queue SPEI bridge."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd
import h5py
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BUILDER_PATH = ROOT / "us_county_validation/scripts/build_us_spei_bridge_post_queue.py"
VALIDATOR_PATH = ROOT / "us_county_validation/scripts/validate_us_spei_bridge_post_queue.py"
BUILDER = load_module("post_queue_builder", BUILDER_PATH)
VALIDATOR = load_module("post_queue_validator", VALIDATOR_PATH)
CONFIG = ROOT / "config/us_spei_bridge_post_queue_v1.toml"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PostQueueBridgeTests(unittest.TestCase):
    def setUp(self):
        self.contract = BUILDER.load_contract(CONFIG)
        self.months = pd.date_range("2001-01-01", periods=6, freq="MS")
        self.weights = pd.DataFrame([
            {"county_geoid": "00001", "native_lat_index": 1, "native_lon_index": 1,
             "spatial_weight_within_available": 0.25},
            {"county_geoid": "00001", "native_lat_index": 3, "native_lon_index": 3,
             "spatial_weight_within_available": 0.75},
            {"county_geoid": "00002", "native_lat_index": 2, "native_lon_index": 2,
             "spatial_weight_within_available": 1.0},
        ])

    def synthetic_chunks(self):
        base = np.empty((3, 6, 2), dtype=float)
        extension = np.empty((3, 6, 1), dtype=float)
        for scale in range(3):
            for month in range(6):
                base[scale, month, 0] = 10 * (scale + 1) + month
                base[scale, month, 1] = 100 * (scale + 1) + month
                extension[scale, month, 0] = 20 * (scale + 1) + month
        base[1, :2] = np.nan; extension[1, :2] = np.nan
        base[2, :5] = np.nan; extension[2, :5] = np.nan
        return [([(1, 1), (2, 2)], base, self.months), ([(3, 3)], extension, self.months)]

    def test_contract_keeps_every_authorization_closed(self):
        self.assertTrue(all(value is False for value in self.contract["authorization"].values()))
        self.assertEqual(self.contract["future"]["expected_cases"], 15)
        self.assertEqual(self.contract["historical"]["merged_cells"], 31219)
        self.assertEqual(self.contract["outputs"]["expected_historical_season_rows"], 7013)
        self.assertEqual(self.contract["outputs"]["expected_future_season_rows"], 43320)

    def _write_incomplete_receipts(self, directory: Path, include_last: bool, last_passes: bool = True):
        future = self.contract["future"]
        ordered = [(model, scenario) for model in future["models"] for scenario in future["scenarios"]]
        queue = {"case_count": 15, "cases": [{"esm": model, "scenario": scenario} for model, scenario in ordered]}
        queue_path = directory / "queue.json"; queue_path.write_text(json.dumps(queue))
        extension_root = directory / "extensions"
        limit = len(ordered) if include_last else len(ordered) - 1
        for index, (model, scenario) in enumerate(ordered[:limit]):
            case = extension_root / f"{model}_{scenario}"; case.mkdir(parents=True)
            result = {"schema": "us_spei_bridge_future_case_result_v1", "esm": model, "scenario": scenario,
                      "cells": 11, "months": 120, "scales": [1, 3, 6],
                      "gates": {name: False for name in BUILDER.FALSE_GATES},
                      "output": {"path": "not-opened.nc", "sha256": "not-opened"}}
            result_path = case / "result.json"; result_path.write_text(json.dumps(result))
            validation = {"status": "passed" if (index < 14 or last_passes) else "failed",
                          "pair_result_sha256": sha256(result_path), "esm": model, "scenario": scenario,
                          "gates": {name: False for name in BUILDER.FALSE_GATES},
                          "output_sha256": "not-opened"}
            (case / "validation.json").write_text(json.dumps(validation))
        test_contract = copy.deepcopy(self.contract)
        test_contract["future"]["queue_manifest"] = str(queue_path)
        test_contract["future"]["queue_manifest_sha256"] = sha256(queue_path)
        test_contract["future"]["extension_root"] = str(extension_root)
        test_contract["future"]["base_root"] = str(directory / "base-must-not-be-opened")
        return test_contract

    def test_missing_fifteenth_case_stops_before_bulk_access(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self._write_incomplete_receipts(Path(directory), include_last=False)
            original = BUILDER.digest

            def guarded(path):
                if Path(path).suffix in {".nc", ".h5", ".parquet", ".shp"}:
                    raise AssertionError("bulk artifact touched before all-15 gate")
                return original(path)

            with mock.patch.object(BUILDER, "digest", side_effect=guarded):
                with self.assertRaisesRegex(ValueError, "all-15 extension gate closed"):
                    BUILDER.collect_upstream_registry(contract)

    def test_failed_fifteenth_validation_stops_before_bulk_access(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self._write_incomplete_receipts(Path(directory), include_last=True, last_passes=False)
            original = BUILDER.digest

            def guarded(path):
                if Path(path).suffix in {".nc", ".h5", ".parquet", ".shp"}:
                    raise AssertionError("bulk artifact touched before all-15 gate")
                return original(path)

            with mock.patch.object(BUILDER, "digest", side_effect=guarded):
                with self.assertRaisesRegex(ValueError, "not independently validated"):
                    BUILDER.collect_upstream_registry(contract)

    def test_base_plus_extension_spatial_merge(self):
        values, months, counties = BUILDER.accumulate_county_monthly(self.synthetic_chunks(), self.weights, 3)
        self.assertEqual(counties, ["00001", "00002"])
        self.assertTrue(months.equals(self.months))
        self.assertAlmostEqual(values[0, 0, 0], 0.25 * 10 + 0.75 * 20)
        self.assertAlmostEqual(values[0, 4, 1], 104)
        self.assertTrue(np.isnan(values[1, :2]).all())
        self.assertTrue(np.isnan(values[2, :5]).all())
        self.assertTrue(np.isfinite(values[2, 5]).all())

    def test_partial_cell_missingness_is_not_renormalized(self):
        chunks = self.synthetic_chunks()
        chunks[1][1][0, 3, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "partial spatial coverage"):
            BUILDER.accumulate_county_monthly(chunks, self.weights, 3)

    def test_duplicate_or_missing_extension_cell_fails(self):
        chunks = self.synthetic_chunks()
        chunks[1] = ([(1, 1)], chunks[1][1], self.months)
        with self.assertRaisesRegex(ValueError, "source cell appears more than once"):
            BUILDER.accumulate_county_monthly(chunks, self.weights, 3)

    def test_future_merge_requires_same_historical_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); months = pd.date_range("2091-01-01", "2100-12-01", freq="MS")
            base = root / "base.h5"
            with h5py.File(base, "w") as handle:
                handle.create_dataset("month", data=months.to_numpy().astype("datetime64[ns]").astype("int64"))
                handle.create_dataset("scale", data=np.asarray([1, 3, 6], dtype=np.int16))
                handle.create_dataset("native_lat_index", data=np.asarray([1, 2]))
                handle.create_dataset("native_lon_index", data=np.asarray([1, 2]))
                handle.create_dataset("spei", data=np.zeros((3, 120, 2), dtype=np.float32))
            extension = root / "extension.nc"
            xr.Dataset({
                "spei": (("scale", "month", "cell"), np.zeros((3, 120, 1))),
                "native_lat_index": (("cell",), [3]), "native_lon_index": (("cell",), [3]),
            }, coords={"scale": [1, 3, 6], "month": months, "cell": [0]}).to_netcdf(extension, engine="h5netcdf")
            contract = copy.deepcopy(self.contract)
            contract["future"].update(base_cells=2, extension_cells=1, merged_cells=3)
            case = {"base_cube": base, "extension_cube": extension}
            with self.assertRaisesRegex(ValueError, "differs from the historical"):
                list(BUILDER._future_chunks(case, contract, {(1, 1), (3, 3)}, {(1, 1), (2, 2), (4, 4)}))

    def test_calendar_aggregation_and_independent_validator_agree(self):
        values, months, counties = BUILDER.accumulate_county_monthly(self.synthetic_chunks(), self.weights, 3)
        calendar_rows = pd.DataFrame([
            {"county_geoid": county, "state": "AA", "harvest_year": 2001,
             "season_start": pd.Timestamp("2001-06-01"), "season_end": pd.Timestamp("2001-06-30"),
             "calendar_source_id": "synthetic", "calendar_vintage": "v1",
             "calendar_boundary_rule": "frozen", "stage_definition": "season"}
            for county in counties
        ])
        monthly = BUILDER.build_monthly_panel(values, months, counties, {county: "AA" for county in counties})
        season = BUILDER.build_season_panel(values, months, counties, calendar_rows)
        checks = []
        VALIDATOR.validate_panel_pair(monthly, season, 12, 2, [], checks)
        self.assertGreater(len(checks), 10)
        damaged = season.copy(); damaged.loc[0, "spei_3_day_weighted_mean"] += 0.1
        with self.assertRaisesRegex(ValueError, "seasonal mean"):
            VALIDATOR.validate_panel_pair(monthly, damaged, 12, 2, [], [])

    def test_cross_month_calendar_day_weighting(self):
        group = pd.DataFrame({"date": pd.to_datetime(["2001-01-01", "2001-02-01"]),
                              "spei_1": [1.0, 3.0]})
        mean, minimum, count = VALIDATOR.independent_metrics(
            group, pd.Timestamp("2001-01-16"), pd.Timestamp("2001-02-14"), 1
        )
        self.assertAlmostEqual(mean, (16 * 1.0 + 14 * 3.0) / 30)
        self.assertEqual((minimum, count), (1.0, 2))

    def test_future_calendar_is_exact_county_by_eight_years(self):
        sample = pd.DataFrame([
            {"county_geoid": "00001", "state": "AA", "season_start": pd.Timestamp("1981-04-10"),
             "season_end": pd.Timestamp("1981-09-20"), "calendar_source_id": "source",
             "calendar_vintage": "2010", "calendar_boundary_rule": "frozen", "stage_definition": "proxy"},
            {"county_geoid": "00001", "state": "AA", "season_start": pd.Timestamp("1982-04-10"),
             "season_end": pd.Timestamp("1982-09-20"), "calendar_source_id": "source",
             "calendar_vintage": "2010", "calendar_boundary_rule": "frozen", "stage_definition": "proxy"},
            {"county_geoid": "00002", "state": "BB", "season_start": pd.Timestamp("1981-05-01"),
             "season_end": pd.Timestamp("1981-10-01"), "calendar_source_id": "source",
             "calendar_vintage": "2010", "calendar_boundary_rule": "frozen", "stage_definition": "proxy"},
        ])
        future = BUILDER.future_calendar(sample, list(range(2092, 2100)))
        self.assertEqual(len(future), 16)
        self.assertEqual(set(future.harvest_year), set(range(2092, 2100)))
        self.assertEqual(set(future.loc[future.county_geoid == "00001", "season_start"].dt.strftime("%m-%d")), {"04-10"})

    def test_production_access_order_and_no_fit_import(self):
        source = BUILDER_PATH.read_text()
        validator_source = VALIDATOR_PATH.read_text()
        self.assertLess(source.index("registry = collect_upstream_registry(contract)"), source.index("sample = load_sample(contract)"))
        self.assertIn("pd.read_parquet(path, columns=SAMPLE_COLUMNS)", source)
        self.assertIn("pd.read_parquet(sample_path, columns=SAMPLE_COLUMNS)", validator_source)
        for forbidden in ("statsmodels", "sklearn", "yield_bu_acre]", "source_value_raw]"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
