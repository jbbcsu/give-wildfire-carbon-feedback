#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_hultgren_common_price_weights.py"
SOURCE_VALUE = "maize_gross_production_value_current_usd_rebased_2014_2016_usd"
OUTPUT_VALUE = "maize_gross_production_value_common_price_2014_2016_usd"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CommonPriceValidationTests(unittest.TestCase):
    def test_reconstruction_and_hash_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_path = base / "source.parquet"
            output_path = base / "output.parquet"
            source_receipt_path = base / "source.json"
            receipt_path = base / "receipt.json"
            validation_path = base / "validation.json"
            source = pd.DataFrame({
                "iso3": ["AAA", "BBB"],
                "native_lat_index": [1, 2],
                "native_lon_index": [3, 4],
                "matched_maize_production_mt": [1.0, 3.0],
                SOURCE_VALUE: [20.0, 20.0],
            })
            output = source.drop(columns=[SOURCE_VALUE]).copy()
            output[OUTPUT_VALUE] = [10.0, 30.0]
            source.to_parquet(source_path, index=False)
            output.to_parquet(output_path, index=False)
            source_receipt_path.write_text(json.dumps({
                "schema": "hultgren_country_cell_maize_value_weights_current_rebased/v1",
                "output": {"sha256": digest(source_path)},
            }), encoding="utf-8")
            receipt_path.write_text(json.dumps({
                "schema": "hultgren_country_cell_maize_value_weights_common_price/v1",
                "claim_gates": {"welfare": False, "damage_or_scc": False},
                "source": {
                    "weights": {"path": str(source_path), "sha256": digest(source_path)},
                    "receipt": {"path": str(source_receipt_path), "sha256": digest(source_receipt_path)},
                },
                "output": {"path": str(output_path), "sha256": digest(output_path)},
                "audit": {"common_price_usd_per_tonne": 10.0, "output_total_value_usd": 40.0},
            }), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--receipt", str(receipt_path), "--output", str(validation_path)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            self.assertEqual(validation["status"], "pass")
            self.assertEqual(validation["validation"]["maximum_absolute_cell_value_error_usd"], 0.0)
            self.assertTrue(validation["validation"]["total_value_preserved"])


if __name__ == "__main__":
    unittest.main()
