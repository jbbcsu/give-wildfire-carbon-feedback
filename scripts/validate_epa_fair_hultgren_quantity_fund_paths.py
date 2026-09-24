#!/usr/bin/env python3
"""Stream-validate currency-aligned FUND-region damage differences."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if receipt["schema"] != "epa_fair_hultgren_quantity_fund_paths/v1":
        raise AssertionError("unexpected receipt schema")
    if receipt["claim_gates"]["agriculture_replacement"] or receipt["claim_gates"]["scc"]:
        raise AssertionError("claim gate promoted")
    path = Path(receipt["output"]["path"])
    if digest(path) != receipt["output"]["sha256"]:
        raise AssertionError("regional output identity differs")
    for source in receipt["sources"].values():
        if digest(Path(source["path"])) != source["sha256"]:
            raise AssertionError(f"source identity differs: {source['path']}")
    with Path(receipt["sources"]["fund_order"]["path"]).open(newline="", encoding="utf-8") as stream:
        regions = [row["fund_region"] for row in csv.DictReader(stream)]
    if regions != receipt["support"]["fund_regions"]:
        raise AssertionError("FUND order differs")
    global_source = receipt["sources"]["damage_paths"]
    global_paths = pd.read_parquet(global_source["path"]).set_index(
        ["climate_model", "year", "pulse_size_gtc", "adaptation", "tail_rule"]
    )["damage_change_usd_source_price_basis"]
    if not global_paths.index.is_unique:
        raise AssertionError("global keys differ")
    scalar = float(receipt["currency"]["central_scalar"])
    columns = [
        "climate_model", "year", "pulse_size_gtc", "adaptation", "tail_rule", "fund_region",
        "marginal_damage_difference_usd_source_price_basis", "marginal_damage_difference_billion_usd2005",
    ]
    parquet = pq.ParquetFile(path)
    if parquet.metadata.num_rows != receipt["support"]["rows"]:
        raise AssertionError("row count differs")
    pending = pd.DataFrame(columns=columns)
    checked_groups = 0
    maximum_global_error = 0.0
    maximum_currency_error = 0.0
    zero_identity = True
    pre_identity = True
    for batch in parquet.iter_batches(batch_size=65_536, columns=columns, use_threads=False):
        frame = pd.concat([pending, batch.to_pandas()], ignore_index=True)
        complete = len(frame) - (len(frame) % len(regions))
        work, pending = frame.iloc[:complete], frame.iloc[complete:].copy()
        numeric = work[["marginal_damage_difference_usd_source_price_basis", "marginal_damage_difference_billion_usd2005"]].to_numpy(dtype=np.float64)
        if not np.isfinite(numeric).all():
            raise AssertionError("nonfinite regional damage")
        converted = numeric[:, 0] * scalar / 1e9
        maximum_currency_error = max(maximum_currency_error, float(np.max(np.abs(converted - numeric[:, 1]))))
        for start in range(0, len(work), len(regions)):
            group = work.iloc[start:start + len(regions)]
            keys = group[["climate_model", "year", "pulse_size_gtc", "adaptation", "tail_rule"]].drop_duplicates()
            if len(keys) != 1 or group.fund_region.tolist() != regions:
                raise AssertionError("regional key product or order differs")
            key_row = keys.iloc[0]
            key = (str(key_row.climate_model), int(key_row.year), float(key_row.pulse_size_gtc), str(key_row.adaptation), str(key_row.tail_rule))
            observed = float(group.marginal_damage_difference_usd_source_price_basis.sum())
            expected = float(global_paths.loc[key])
            maximum_global_error = max(maximum_global_error, abs(observed - expected))
            if key[2] == 0.0:
                zero_identity &= bool((group.marginal_damage_difference_usd_source_price_basis == 0.0).all())
            if key[1] <= 2020:
                pre_identity &= bool((group.marginal_damage_difference_usd_source_price_basis == 0.0).all())
            checked_groups += 1
    if len(pending):
        raise AssertionError("trailing incomplete FUND product")
    if checked_groups != len(global_paths):
        raise AssertionError("global/regional key count differs")
    if maximum_global_error > 2e-3 or maximum_currency_error > 1e-24 or not zero_identity or not pre_identity:
        raise AssertionError("regional arithmetic validation failed")

    result = {
        "schema": "epa_fair_hultgren_quantity_fund_paths_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "validation": {
            "all_source_and_output_hashes_checked": True,
            "streamed_rows": int(parquet.metadata.num_rows),
            "complete_global_path_keys": checked_groups,
            "full_ordered_16_region_product_per_key": True,
            "maximum_absolute_global_reconciliation_error_source_usd": maximum_global_error,
            "maximum_absolute_currency_conversion_error_billion_usd2005": maximum_currency_error,
            "zero_pulse_identity": zero_identity,
            "pre_2021_identity": pre_identity,
            "claim_gates_checked": True,
        },
        "scope": "Streaming validation of every regional row, key product, global sum, and currency conversion.",
        "interpretation": "Currency-aligned marginal-difference validation only; no paired agriculture level, GIVE replacement, discounting, or SCC gate is opened.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
