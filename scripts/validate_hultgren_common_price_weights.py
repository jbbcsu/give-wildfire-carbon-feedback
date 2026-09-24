#!/usr/bin/env python3
"""Independently reconstruct and validate matched-support common-price weights."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE_VALUE = "maize_gross_production_value_current_usd_rebased_2014_2016_usd"
OUTPUT_VALUE = "maize_gross_production_value_common_price_2014_2016_usd"
PRODUCTION = "matched_maize_production_mt"
KEYS = ["iso3", "native_lat_index", "native_lon_index"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def close(actual: float, expected: float, label: str, *, atol: float = 1e-4) -> None:
    if not math.isclose(actual, expected, rel_tol=2e-12, abs_tol=atol):
        raise AssertionError(f"{label}: {actual!r} != {expected!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if receipt["schema"] != "hultgren_country_cell_maize_value_weights_common_price/v1":
        raise AssertionError("unexpected common-price receipt schema")
    if receipt["claim_gates"]["damage_or_scc"] or receipt["claim_gates"]["welfare"]:
        raise AssertionError("claim gate promoted")

    source_path = Path(receipt["source"]["weights"]["path"])
    source_receipt_path = Path(receipt["source"]["receipt"]["path"])
    output_path = Path(receipt["output"]["path"])
    for path, expected in [
        (source_path, receipt["source"]["weights"]["sha256"]),
        (source_receipt_path, receipt["source"]["receipt"]["sha256"]),
        (output_path, receipt["output"]["sha256"]),
    ]:
        if digest(path) != expected:
            raise AssertionError(f"source hash differs: {path}")
    source_receipt = json.loads(source_receipt_path.read_text(encoding="utf-8"))
    if source_receipt["schema"] != "hultgren_country_cell_maize_value_weights_current_rebased/v1":
        raise AssertionError("upstream receipt schema differs")
    if source_receipt["output"]["sha256"] != digest(source_path):
        raise AssertionError("upstream receipt does not identify source weights")

    source = pd.read_parquet(source_path, columns=KEYS + [PRODUCTION, SOURCE_VALUE]).sort_values(KEYS).reset_index(drop=True)
    output = pd.read_parquet(output_path, columns=KEYS + [PRODUCTION, OUTPUT_VALUE]).sort_values(KEYS).reset_index(drop=True)
    if not source[KEYS].equals(output[KEYS]):
        raise AssertionError("country-cell support differs")
    if not np.array_equal(source[PRODUCTION].to_numpy(), output[PRODUCTION].to_numpy()):
        raise AssertionError("physical production differs")

    total_production = float(source[PRODUCTION].sum())
    source_total = float(source[SOURCE_VALUE].sum())
    price = source_total / total_production
    expected_values = source[PRODUCTION].to_numpy(dtype=np.float64) * price
    actual_values = output[OUTPUT_VALUE].to_numpy(dtype=np.float64)
    maximum_error = float(np.max(np.abs(actual_values - expected_values)))
    if not np.allclose(actual_values, expected_values, rtol=2e-12, atol=1e-8):
        raise AssertionError("cell common-price values differ")
    close(price, float(receipt["audit"]["common_price_usd_per_tonne"]), "common price", atol=1e-10)
    close(float(actual_values.sum()), source_total, "preserved total")
    close(float(receipt["audit"]["output_total_value_usd"]), source_total, "receipt total")

    validation = {
        "schema": "hultgren_country_cell_maize_value_weights_common_price_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "validation": {
            "source_and_output_hashes_checked": True,
            "upstream_receipt_chain_checked": True,
            "country_cell_support_exact": True,
            "physical_production_exact": True,
            "country_cell_rows": int(len(output)),
            "country_count": int(output["iso3"].nunique()),
            "common_price_usd_per_tonne": price,
            "maximum_absolute_cell_value_error_usd": maximum_error,
            "total_value_preserved": True,
            "claim_gates_checked": True,
        },
        "interpretation": "Input reconstruction only; no welfare, damage, agriculture-replacement, or SCC gate is opened.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
