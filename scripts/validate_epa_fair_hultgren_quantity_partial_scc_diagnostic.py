#!/usr/bin/env python3
"""Independently validate the standard-GIVE-baseline partial-SCC diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

MOLECULAR_C_TO_CO2 = 12.0 / 44.0
PRICE_2005_TO_2020 = 113.648 / 87.504


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require(receipt["schema"] == "epa_fair_hultgren_quantity_partial_scc_diagnostic/v1", "receipt differs")
    result_path = Path(receipt["output"]["path"])
    market_path = Path(receipt["sources"]["market_paths"]["path"])
    cpc_path = Path(receipt["sources"]["give_cpc"]["path"])
    require(digest(result_path) == receipt["output"]["sha256"], "result hash differs")
    require(digest(market_path) == receipt["sources"]["market_paths"]["sha256"], "market hash differs")
    require(digest(cpc_path) == receipt["sources"]["give_cpc"]["sha256"], "CPC hash differs")

    cpc = pd.read_csv(cpc_path)
    base = float(cpc.loc[cpc.year.eq(2020), "net_cpc_2005usd_per_person"].iloc[0])
    rates = receipt["discounting"]["rates"]
    discount = {
        row["label"]: {
            int(value.year): (base / float(value.net_cpc_2005usd_per_person)) ** float(row["eta"])
            / (1.0 + float(row["prtp"])) ** (int(value.year) - 2020)
            for value in cpc.itertuples(index=False)
        }
        for row in rates
    }
    group_columns = [
        "climate_model", "pulse_size_gtc", "adaptation", "tail_rule",
        "elasticity_id", "yield_to_supply_mapping",
    ]
    terms: dict[tuple[object, ...], list[list[float]]] = defaultdict(lambda: [[] for _ in rates])
    columns = group_columns + ["year", "damage_change_billion_usd2005"]
    source_rows = 0
    for batch in pq.ParquetFile(market_path).iter_batches(batch_size=65_536, columns=columns):
        frame = batch.to_pandas()
        source_rows += len(frame)
        for row in frame.loc[frame.pulse_size_gtc.gt(0.0)].itertuples(index=False):
            key = tuple(getattr(row, column) for column in group_columns)
            normalized = float(row.damage_change_billion_usd2005) * MOLECULAR_C_TO_CO2 / float(row.pulse_size_gtc)
            for index, rate in enumerate(rates):
                terms[key][index].append(discount[rate["label"]][int(row.year)] * normalized)
    require(source_rows == receipt["support"]["source_rows"], "source rows differ")
    require({len(values) for paths in terms.values() for values in paths} == {281}, "annual path length differs")

    expected = {}
    for key, paths in terms.items():
        for index, rate in enumerate(rates):
            expected[key + (rate["label"],)] = math.fsum(paths[index])
    output = pd.read_csv(result_path)
    require(len(output) == receipt["support"]["output_rows"], "output rows differ")
    maximum_2005_error = 0.0
    maximum_2020_error = 0.0
    for row in output.itertuples(index=False):
        key = tuple(getattr(row, column) for column in group_columns) + (row.discount_rate_label,)
        value = expected.pop(key)
        maximum_2005_error = max(maximum_2005_error, abs(value - row.partial_scc_diagnostic_usd2005_per_tco2))
        maximum_2020_error = max(maximum_2020_error, abs(value * PRICE_2005_TO_2020 - row.partial_scc_diagnostic_usd2020_per_tco2))
        require(row.annual_year_count == 281, "reported annual count differs")
    require(not expected, "unreported diagnostic keys")
    require(maximum_2005_error <= 1e-15 and maximum_2020_error <= 1e-15, "independent SCC reconstruction differs")

    result = {
        "schema": "epa_fair_hultgren_quantity_partial_scc_diagnostic_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "scope": "Independent full-path reconstruction with math.fsum of every deterministic discount diagnostic.",
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "validation": {
            "source_rows_streamed": source_rows,
            "diagnostic_rows_reconstructed": len(output),
            "annual_years_per_path": 281,
            "maximum_absolute_usd2005_per_tco2_error": maximum_2005_error,
            "maximum_absolute_usd2020_per_tco2_error": maximum_2020_error,
        },
        "interpretation": "Arithmetic validation of a standard-GIVE-baseline discount diagnostic; it does not validate a paired agriculture replacement or an official GIVE SCC.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
