#!/usr/bin/env python3
"""Replace country-specific maize values with one matched-support common price.

The total value and physical-production support are inherited from the
validated current-USD, GDP-deflator-rebased input.  This removes cross-country
price dispersion without filling countries that were absent from that input.
It is a price-basis sensitivity, not a welfare, damage, or SCC calibration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE_VALUE = "maize_gross_production_value_current_usd_rebased_2014_2016_usd"
OUTPUT_VALUE = "maize_gross_production_value_common_price_2014_2016_usd"
PRODUCTION = "matched_maize_production_mt"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def common_price_weights(frame: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    required = {"iso3", "native_lat_index", "native_lon_index", PRODUCTION, SOURCE_VALUE}
    if not required <= set(frame.columns):
        raise ValueError("source columns differ")
    if frame.empty or frame.duplicated(["iso3", "native_lat_index", "native_lon_index"]).any():
        raise ValueError("empty or duplicate country-cell source")
    production = frame[PRODUCTION].astype(float)
    value = frame[SOURCE_VALUE].astype(float)
    if not production.gt(0.0).all() or not value.gt(0.0).all():
        raise ValueError("nonpositive source production or value")
    total_production = float(production.sum())
    total_value = float(value.sum())
    price = total_value / total_production
    if not math.isfinite(price) or price <= 0.0:
        raise ValueError("invalid common price")
    output = frame.drop(columns=[SOURCE_VALUE]).copy()
    output[OUTPUT_VALUE] = production * price
    return output, price


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--weights-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.receipt.exists():
        raise ValueError("fresh outputs required")

    source_receipt = json.loads(args.weights_receipt.read_text(encoding="utf-8"))
    if source_receipt["schema"] != "hultgren_country_cell_maize_value_weights_current_rebased/v1":
        raise ValueError("source receipt schema differs")
    if source_receipt["output"]["sha256"] != digest(args.weights):
        raise ValueError("source weight hash differs")
    frame = pd.read_parquet(args.weights)
    output, price = common_price_weights(frame)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False)

    source_total = float(frame[SOURCE_VALUE].sum())
    output_total = float(output[OUTPUT_VALUE].sum())
    if not math.isclose(output_total, source_total, rel_tol=1e-13, abs_tol=1e-4):
        raise ValueError("common-price total does not preserve source value")
    country_totals = output.groupby("iso3", sort=True)[OUTPUT_VALUE].sum()
    result = {
        "schema": "hultgren_country_cell_maize_value_weights_common_price/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "matched_support_common_price_sensitivity_not_welfare_damage_or_scc",
        "value_column": OUTPUT_VALUE,
        "units": "US dollars at a single matched-support 2014-2016-basis maize price",
        "method": "divide total rebased current-USD value by total matched physical production, then value every retained tonne at that common price",
        "source": {
            "weights": {"path": str(args.weights), "sha256": digest(args.weights)},
            "receipt": {"path": str(args.weights_receipt), "sha256": digest(args.weights_receipt)},
        },
        "audit": {
            "country_count": int(output["iso3"].nunique()),
            "country_cell_rows": int(len(output)),
            "matched_maize_production_mt": float(output[PRODUCTION].sum()),
            "source_total_value_usd": source_total,
            "output_total_value_usd": output_total,
            "common_price_usd_per_tonne": price,
            "venezuela_common_price_value_usd": float(country_totals.get("VEN", 0.0)),
            "venezuela_share": float(country_totals.get("VEN", 0.0) / output_total),
        },
        "output": {"path": str(args.output), "sha256": digest(args.output), "bytes": args.output.stat().st_size},
        "limitations": [
            "The common price is an accounting sensitivity, not a country-specific farm-gate price series.",
            "Support is inherited unchanged from the complete-current-USD input; missing countries are not filled.",
            "This builds weights only and does not authorize welfare, damage, or SCC calculation.",
        ],
        "claim_gates": {"price_basis_sensitivity": True, "welfare": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "audit": result["audit"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
