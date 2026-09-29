#!/usr/bin/env python3
"""Focused tests for the U.S. corn untracked-source manifest validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("validate_us_corn_untracked_source_reproducibility.py")
SPEC = importlib.util.spec_from_file_location("validator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ManifestValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MODULE.DEFAULT_MANIFEST.read_text())

    def write_variant(self, value: dict) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(value, handle)
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def test_real_manifest_validates_without_tabular_reader(self) -> None:
        result = MODULE.validate(MODULE.DEFAULT_MANIFEST)
        self.assertEqual(result["artifact_count"], 10)
        self.assertEqual(result["parquet_data_pages_read"], 0)
        self.assertFalse(result["outcome_columns_opened"])

    def test_duplicate_path_fails_closed(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["artifacts"][1]["path"] = bad["artifacts"][0]["path"]
        with self.assertRaisesRegex(AssertionError, "ten unique"):
            MODULE.validate(self.write_variant(bad))

    def test_hash_drift_fails_closed(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["artifacts"][2]["sha256"] = "0" * 64
        with self.assertRaisesRegex(AssertionError, "SHA-256 changed"):
            MODULE.validate(self.write_variant(bad))

    def test_outcome_read_claim_fails_closed(self) -> None:
        bad = copy.deepcopy(self.manifest)
        bad["inspection_policy"]["outcome_columns_opened"] = True
        with self.assertRaisesRegex(AssertionError, "metadata-only"):
            MODULE.validate(self.write_variant(bad))


if __name__ == "__main__":
    unittest.main()
