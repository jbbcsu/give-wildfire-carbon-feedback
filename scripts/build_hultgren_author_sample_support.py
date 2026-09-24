#!/usr/bin/env python3
"""Summarize the published maize estimation support with bounded memory."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WEATHER = [
    "gdd", "kdd", "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]
MODERATORS = ["ln_gdppc", "irrigated_share", "lr_tmax_crop", "lr_prcp_crop"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunk-rows", type=int, default=20_000)
    args = parser.parse_args()
    if args.output.exists() or args.chunk_rows <= 0:
        raise ValueError("fresh output and positive chunk size required")
    columns = ["ln_yield", *MODERATORS, *WEATHER]
    collected: dict[str, list[np.ndarray]] = {column: [] for column in MODERATORS + WEATHER}
    complete_rows = 0
    source_rows = 0
    with pd.read_stata(args.sample, columns=columns, convert_categoricals=False, iterator=True) as reader:
        while True:
            try:
                chunk = reader.read(args.chunk_rows)
            except StopIteration:
                break
            if chunk.empty:
                break
            source_rows += len(chunk)
            chunk = chunk.dropna()
            values = chunk.to_numpy(dtype=np.float64)
            if not np.isfinite(values).all():
                raise ValueError("nonfinite complete author row")
            complete_rows += len(chunk)
            for column in collected:
                collected[column].append(chunk[column].to_numpy(dtype=np.float64, copy=True))
    if complete_rows == 0:
        raise ValueError("no complete author rows")
    quantiles = {}
    for column, pieces in collected.items():
        values = np.concatenate(pieces)
        quantiles[column] = {
            "minimum": float(values.min()), "p01": float(np.quantile(values, 0.01)),
            "p99": float(np.quantile(values, 0.99)), "maximum": float(values.max()),
        }
    result = {
        "schema": "hultgren_author_sample_support/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "published_estimation_sample_support_summarized",
        "source": {"path": str(args.sample), "bytes": args.sample.stat().st_size, "sha256": digest(args.sample)},
        "source_rows": source_rows, "complete_rows": complete_rows,
        "complete_case_columns": columns, "quantiles": quantiles,
        "method": f"Stata input streamed in chunks of {args.chunk_rows} rows; exact pooled quantiles computed from complete rows",
        "claim_gates": {"author_sample_support_summarized": True, "response_damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "source_rows": source_rows, "complete_rows": complete_rows}, indent=2))


if __name__ == "__main__":
    main()
