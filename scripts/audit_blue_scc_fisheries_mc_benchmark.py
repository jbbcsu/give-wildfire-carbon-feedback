#!/usr/bin/env python3
"""Audit the released Blue-SCC fisheries Monte Carlo SCC benchmark.

The output contains aggregate statistics only.  It does not copy source rows,
create annual damages, harmonize discounting with GIVE, or authorize addition
of the published SCC to a GIVE result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
import tomllib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Any


REQUIRED_COLUMNS = {"t", "scc", "oc_capital", "valuation", "id"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quantile(values: list[float], probability: float) -> float:
    """NumPy-compatible linear quantile for a nonempty ordered sample."""
    require(values, "quantile sample is empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def describe(values: list[float]) -> dict[str, float | int]:
    require(values and all(math.isfinite(value) for value in values), "summary values must be finite")
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "sample_sd": statistics.stdev(values) if len(values) > 1 else 0.0,
        "p05": quantile(values, 0.05),
        "median": quantile(values, 0.50),
        "p95": quantile(values, 0.95),
        "minimum": min(values),
        "maximum": max(values),
    }


def summarize(records: Iterable[Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    records = list(records)
    expected = config["expected"]
    require(len(records) == expected["row_count"], "published Monte Carlo row count changed")
    ids: set[str] = set()
    components: Counter[tuple[str, str]] = Counter()
    by_id: defaultdict[str, dict[tuple[str, str], float]] = defaultdict(dict)
    for row in records:
        require(REQUIRED_COLUMNS.issubset(row), "published Monte Carlo schema is incomplete")
        require(int(row["t"]) == expected["year"], "published Monte Carlo year changed")
        draw_id = str(row["id"])
        component = (str(row["oc_capital"]), str(row["valuation"]))
        value = float(row["scc"])
        require(math.isfinite(value), "published SCC value is nonfinite")
        require(component not in by_id[draw_id], "duplicate draw-component row")
        ids.add(draw_id)
        components[component] += 1
        by_id[draw_id][component] = value
    require(len(ids) == expected["id_count"], "published draw count changed")
    require(len(components) == expected["component_count"], "published component count changed")
    require(all(count == len(ids) for count in components.values()), "draw-component rectangle is incomplete")
    baseline_id = expected["baseline_id"]
    require(baseline_id in ids, "deterministic baseline row is absent")
    draw_ids = sorted(ids - {baseline_id})
    require(len(draw_ids) == expected["monte_carlo_draw_count"], "Monte Carlo count excluding baseline changed")

    market_key = ("Fisheries", expected["fisheries_market_valuation"])
    nutrition_key = ("Fisheries", expected["fisheries_nutrition_valuation"])
    require(market_key in components and nutrition_key in components, "fisheries component labels changed")
    market = [by_id[draw][market_key] for draw in draw_ids]
    nutrition = [by_id[draw][nutrition_key] for draw in draw_ids]
    total = [left + right for left, right in zip(market, nutrition)]
    baseline_market = by_id[baseline_id][market_key]
    baseline_nutrition = by_id[baseline_id][nutrition_key]
    return {
        "published_deterministic_baseline_usd_per_tco2": {
            "market": baseline_market,
            "nutrition_nonmarket": baseline_nutrition,
            "combined": baseline_market + baseline_nutrition,
        },
        "published_monte_carlo_usd_per_tco2": {
            "market": describe(market),
            "nutrition_nonmarket": describe(nutrition),
            "combined": describe(total),
        },
    }


def audit(source_root: Path, config_path: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("contract_id") == "blue_scc_fisheries_mc_benchmark_v1", "wrong contract")
    commit = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    require(commit == config["source"]["repository_commit"], "source commit changed")
    source = (source_root / config["source"]["relative_path"]).resolve()
    require(source.is_file() and not source.is_symlink(), "source parquet is absent or symlinked")
    require(sha256(source) == config["source"]["sha256"], "source parquet hash changed")
    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError("pandas and a parquet engine are required for this source audit") from error
    frame = pd.read_parquet(source)
    result = summarize(frame.to_dict("records"), config)
    return {
        "schema": "blue_scc_fisheries_mc_benchmark_audit_v1",
        "status": "passed_published_external_benchmark_only",
        "contract_id": config["contract_id"],
        "source": config["source"],
        "result": result,
        "scientific_gates": config["scientific_gates"],
        "source_rows_copied": False,
        "give_scc_calculated": False,
        "interpretation": (
            "Published Blue-SCC uncertainty benchmark under its own model settings; "
            "not an annual GIVE damage path and not additive to GIVE until the failed gates pass."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/blue_scc_fisheries_mc_benchmark_v1.toml"))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    payload = audit(args.source_root.resolve(), args.config.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["result"], sort_keys=True))


if __name__ == "__main__":
    main()

