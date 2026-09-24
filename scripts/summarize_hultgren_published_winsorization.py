#!/usr/bin/env python3
"""Apply a published-style 1% tail rule to cell precipitation log responses.

Hultgren et al. report winsorizing projected log-yield impacts at the top and
bottom 1% over region--GCM--years by RCP and crop.  This diagnostic applies the
same percentile rule to our different cell--ESM--year precipitation contrast.
It is an analogous benchmark, not an exact replication or welfare estimate.
"""

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


def summarize(frame: pd.DataFrame, lower: float, upper: float) -> dict[str, float | int]:
    weights = frame.analysis_weight.to_numpy(dtype=np.float64)
    raw = frame.precipitation_delta_log_yield.to_numpy(dtype=np.float64)
    capped = np.clip(raw, lower, upper)
    total = float(weights.sum())
    years = int(frame.harvest_year.nunique())
    baseline = total / years
    raw_exact = 100.0 * np.expm1(raw)
    capped_exact = 100.0 * np.expm1(capped)
    mean_log = float(np.dot(weights, capped) / total)
    mean_exact = float(np.dot(weights, capped_exact) / total)
    return {
        "cell_year_rows": len(frame),
        "harvest_years": years,
        "baseline_weight_per_year": baseline,
        "winsorized_low_rows": int(np.count_nonzero(raw < lower)),
        "winsorized_high_rows": int(np.count_nonzero(raw > upper)),
        "winsorized_weight_fraction": float(weights[(raw < lower) | (raw > upper)].sum() / total),
        "raw_weighted_mean_delta_log_yield": float(np.dot(weights, raw) / total),
        "raw_percent_from_weighted_mean_log": 100.0 * math.expm1(float(np.dot(weights, raw) / total)),
        "raw_weighted_mean_cell_exact_percent": float(np.dot(weights, raw_exact) / total),
        "winsorized_weighted_mean_delta_log_yield": mean_log,
        "winsorized_percent_from_weighted_mean_log": 100.0 * math.expm1(mean_log),
        "winsorized_weighted_mean_cell_exact_percent": mean_exact,
        "winsorized_fixed_price_gross_output_change": baseline * mean_exact / 100.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    frames = []
    sources = []
    for path in args.input:
        frame = pd.read_parquet(path)
        required = {"climate_model", "harvest_year", "native_lat_index", "native_lon_index", "analysis_weight", "precipitation_delta_log_yield"}
        require(required <= set(frame.columns), f"cell schema differs: {path}")
        require(frame.climate_model.nunique() == 1, f"multiple models: {path}")
        require(np.isfinite(frame[["analysis_weight", "precipitation_delta_log_yield"]]).all().all() and frame.analysis_weight.gt(0).all(), f"invalid cells: {path}")
        frames.append(frame)
        sources.append({"path": str(path), "sha256": digest(path), "rows": len(frame), "climate_model": frame.climate_model.iloc[0]})
    models = [frame.climate_model.iloc[0] for frame in frames]
    require(len(models) == len(set(models)) == 5, "five unique climate models required")
    pooled = pd.concat(frames, ignore_index=True)
    values = pooled.precipitation_delta_log_yield.to_numpy(dtype=np.float64)
    lower, upper = np.quantile(values, [0.01, 0.99], method="linear")
    require(math.isfinite(lower) and math.isfinite(upper) and lower < upper, "invalid winsorization thresholds")
    by_model = {
        model: summarize(frame, float(lower), float(upper))
        for model, frame in zip(models, frames, strict=True)
    }
    result = {
        "schema": "hultgren_precipitation_published_style_winsorization/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "published_style_tail_sensitivity_not_exact_replication_welfare_damage_or_scc",
        "sources": sources,
        "rule": {
            "lower_quantile": 0.01, "upper_quantile": 0.99,
            "lower_delta_log_yield": float(lower), "upper_delta_log_yield": float(upper),
            "pooling": "all cell-ESM-harvest-year precipitation log-response contrasts",
            "published_analogue": "Hultgren et al. Methods SI: projected log-yield impacts winsorized at top and bottom 1% over region-GCM-years by RCP-crop",
            "nonreplication_warning": "our units are half-degree cells, five ISIMIP3b ESMs, and an SSP585-minus-SSP126 precipitation-only contrast",
        },
        "by_climate_model": by_model,
        "interpretation": "fixed-price gross-output changes hold prices and baseline weights fixed; they are accounting exposures, not market welfare, damages, marginal pulse effects, or SCC",
        "claim_gates": {"published_style_tail_sensitivity": True, "exact_published_replication": False, "welfare": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "rule": result["rule"], "by_climate_model": by_model}, indent=2))


if __name__ == "__main__":
    main()
