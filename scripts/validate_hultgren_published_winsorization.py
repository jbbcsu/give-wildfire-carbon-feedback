#!/usr/bin/env python3
"""Independently validate the published-style precipitation tail sensitivity."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(left: float, right: float, tolerance: float = 1e-10) -> None:
    require(abs(left - right) <= tolerance * max(1.0, abs(left), abs(right)), f"values differ: {left}, {right}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.receipt.exists(), "fresh receipt required")
    result = json.loads(args.input.read_text(encoding="utf-8"))
    require(result["status"] == "published_style_tail_sensitivity_not_exact_replication_welfare_damage_or_scc", "status differs")
    frames = []
    for source in result["sources"]:
        path = Path(source["path"])
        require(digest(path) == source["sha256"], f"source hash differs: {path}")
        frame = pd.read_parquet(path)
        require(len(frame) == source["rows"] and frame.climate_model.nunique() == 1, "source dimensions differ")
        require(frame.climate_model.iloc[0] == source["climate_model"], "source model differs")
        frames.append(frame)
    all_values = np.concatenate([frame.precipitation_delta_log_yield.to_numpy(dtype=np.float64) for frame in frames])
    lower, upper = np.quantile(all_values, [0.01, 0.99], method="linear")
    close(float(lower), result["rule"]["lower_delta_log_yield"])
    close(float(upper), result["rule"]["upper_delta_log_yield"])
    for frame in frames:
        model = frame.climate_model.iloc[0]
        saved = result["by_climate_model"][model]
        weight = frame.analysis_weight.to_numpy(dtype=np.float64)
        raw = frame.precipitation_delta_log_yield.to_numpy(dtype=np.float64)
        capped = np.minimum(np.maximum(raw, lower), upper)
        total = math.fsum(weight)
        years = frame.harvest_year.nunique()
        exact = 100.0 * np.expm1(capped)
        mean_log = math.fsum((weight * capped).tolist()) / total
        mean_exact = math.fsum((weight * exact).tolist()) / total
        close(saved["baseline_weight_per_year"], total / years)
        close(saved["winsorized_weighted_mean_delta_log_yield"], mean_log)
        close(saved["winsorized_weighted_mean_cell_exact_percent"], mean_exact)
        close(saved["winsorized_fixed_price_gross_output_change"], total / years * mean_exact / 100.0)
        require(saved["winsorized_low_rows"] == int(np.count_nonzero(raw < lower)), "low-tail count differs")
        require(saved["winsorized_high_rows"] == int(np.count_nonzero(raw > upper)), "high-tail count differs")
    receipt = {
        "schema": "hultgren_precipitation_published_style_winsorization_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "independent_winsorization_arithmetic_validation_passed",
        "input": {"path": str(args.input), "sha256": digest(args.input)},
        "checks": {"source_hashes": True, "pooled_quantiles": True, "tail_counts": True, "weighted_log_means": True, "cell_first_level_aggregation": True},
        "interpretation": "validates arithmetic and source identity, not response transport, economic welfare, marginal pulse mapping, or SCC",
        "claim_gates": {"winsorization_arithmetic_validated": True, "damage_or_scc_validated": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
