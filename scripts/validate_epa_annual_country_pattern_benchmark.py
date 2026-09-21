#!/usr/bin/env python3
"""Independent csv/statistics reconstruction of the EPA country benchmark."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ("data/raw/research_inputs/usepa_pattern_scaling_dac5503/"
                 "pattern_scaling_precipitation_by_country_full_sample.csv")
SOURCE_SHA = "131fa989f43f3d9354da23eecf1cb647dc5c24399671e78fab93230d8902a013"
SCENARIOS = ["ssp1", "ssp2", "ssp3", "ssp4", "ssp5"]
OVERLAP = ["MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def close(actual: float, expected: float, label: str, tolerance: float = 5e-9) -> None:
    if not math.isfinite(actual) or not math.isfinite(expected) or abs(actual - expected) > tolerance:
        raise ValueError(f"EPA independent mismatch {label}: {actual} != {expected}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    benchmark = args.benchmark_dir.resolve()
    out = args.out_dir.resolve()
    if (not benchmark.is_relative_to(ROOT / "data/interim") or not benchmark.is_dir() or
            out.exists() or not out.is_relative_to(ROOT / "data/interim")):
        raise ValueError("valid ignored input and fresh ignored audit output required")
    if sha(SOURCE) != SOURCE_SHA:
        raise ValueError("EPA audit source hash changed")
    groups: dict[tuple[str, str], dict[str, float | None]] = {}
    names: dict[str, tuple[str, str]] = {}
    rows = 0
    with SOURCE.open(newline="") as stream:
        for row in csv.DictReader(stream):
            rows += 1
            key = (row["iso3"], row["source"])
            scenario = row["scenario"]
            value = None if row["patterns.area"] in ("", "NA") else float(row["patterns.area"])
            if key not in groups:
                groups[key] = {}
            if scenario in groups[key] or scenario not in SCENARIOS:
                raise ValueError("EPA audit duplicate or unknown scenario")
            groups[key][scenario] = value
            names[row["iso3"]] = (row["name"], row["continent"])
    if rows != 23920 or len(groups) != 4784 or len(names) != 184:
        raise ValueError("EPA audit source support changed")
    pairs: dict[str, list[tuple[str, float]]] = {iso3: [] for iso3 in names}
    missing_pairs = 0
    for (iso3, model), scenarios in groups.items():
        if sorted(scenarios) != SCENARIOS:
            raise ValueError("EPA audit scenario support incomplete")
        finite = [value for value in scenarios.values() if value is not None and math.isfinite(value)]
        if len(finite) == 0:
            missing_pairs += 1
            continue
        if len(finite) != 5 or any(value != finite[0] for value in finite):
            raise ValueError("EPA audit scenario identity or missingness failed")
        pairs[iso3].append((model, scenarios["ssp2"]))
    if missing_pairs != 81 or sum(map(len, pairs.values())) != 4703:
        raise ValueError("EPA audit missing-pair count changed")

    reported = json.loads((benchmark / "result.json").read_text())
    if (reported["status"] != "epa_annual_country_precipitation_pattern_benchmark_not_damage_or_scc" or
            reported["source_sha256"] != SOURCE_SHA or
            reported["country_summary_sha256"] != sha(benchmark / "country_summary.csv") or
            reported["country_model_slopes_sha256"] != sha(benchmark / "country_model_slopes.csv")):
        raise ValueError("EPA reported benchmark identity invalid")
    with (benchmark / "country_summary.csv").open(newline="") as stream:
        summaries = {row["iso3"]: row for row in csv.DictReader(stream)}
    if set(summaries) != set(pairs):
        raise ValueError("EPA audit country summary keys differ")

    checks = 0
    reconstructed = {}
    for iso3, model_values in pairs.items():
        values = [value for _, value in model_values]
        expected = {
            "available_models": len(values),
            "missing_models": 26 - len(values),
            "minimum_mm_per_year_per_k": min(values),
            "q05_mm_per_year_per_k": quantile(values, 0.05),
            "q25_mm_per_year_per_k": quantile(values, 0.25),
            "median_mm_per_year_per_k": statistics.median(values),
            "q75_mm_per_year_per_k": quantile(values, 0.75),
            "q95_mm_per_year_per_k": quantile(values, 0.95),
            "maximum_mm_per_year_per_k": max(values),
            "mean_mm_per_year_per_k": math.fsum(values) / len(values),
            "sd_mm_per_year_per_k": statistics.stdev(values),
            "positive_model_fraction": sum(value > 0 for value in values) / len(values),
            "negative_model_fraction": sum(value < 0 for value in values) / len(values),
        }
        row = summaries[iso3]
        if int(row["available_models"]) != expected["available_models"] or int(row["missing_models"]) != expected["missing_models"]:
            raise ValueError("EPA audit country model counts differ")
        checks += 2
        for field, value in expected.items():
            if field in ("available_models", "missing_models"):
                continue
            close(float(row[field]), float(value), f"{iso3}/{field}")
            checks += 1
        reconstructed[iso3] = expected

    medians = {iso3: item["median_mm_per_year_per_k"] for iso3, item in reconstructed.items()}
    counts = {
        "countries": len(medians),
        "median_positive": sum(value > 0 for value in medians.values()),
        "median_negative": sum(value < 0 for value in medians.values()),
        "median_zero": sum(value == 0 for value in medians.values()),
        "unanimous_positive": sum(item["positive_model_fraction"] == 1 for item in reconstructed.values()),
        "unanimous_negative": sum(item["negative_model_fraction"] == 1 for item in reconstructed.values()),
        "at_least_80pct_positive": sum(item["positive_model_fraction"] >= 0.8 for item in reconstructed.values()),
        "at_least_80pct_negative": sum(item["negative_model_fraction"] >= 0.8 for item in reconstructed.values()),
        "q05_positive": sum(item["q05_mm_per_year_per_k"] > 0 for item in reconstructed.values()),
        "q95_negative": sum(item["q95_mm_per_year_per_k"] < 0 for item in reconstructed.values()),
    }
    if counts != reported["country_count_summary"]:
        raise ValueError("EPA audit aggregate country counts differ")
    checks += len(counts)
    for model in OVERLAP:
        values = [value for model_values in pairs.values() for name, value in model_values if name == model]
        expected = reported["overlapping_model_country_count_summaries"][model]
        if expected["countries"] != len(values) or expected["missing_countries"] != 184 - len(values):
            raise ValueError("EPA audit overlap model support differs")
        checks += 2
        for field, value in (
            ("q05_mm_per_year_per_k", quantile(values, 0.05)),
            ("median_mm_per_year_per_k", statistics.median(values)),
            ("q95_mm_per_year_per_k", quantile(values, 0.95)),
            ("positive_country_fraction", sum(item > 0 for item in values) / len(values)),
            ("negative_country_fraction", sum(item < 0 for item in values) / len(values)),
        ):
            close(float(expected[field]), float(value), f"{model}/{field}", 1e-12)
            checks += 1
    ranked = sorted(medians, key=lambda iso3: (medians[iso3], iso3))
    if ([row["iso3"] for row in reported["five_smallest_country_medians"]] != ranked[:5] or
            [row["iso3"] for row in reported["five_largest_country_medians"]] != ranked[-5:]):
        raise ValueError("EPA audit country median rank diagnostic differs")
    checks += 10
    outcome = {
        "status": "independent_epa_annual_country_pattern_benchmark_validated",
        "numeric_and_support_checks": checks,
        "source_sha256": sha(SOURCE),
        "benchmark_result_sha256": sha(benchmark / "result.json"),
        "validator_sha256": sha(Path(__file__)),
        "missing_country_model_pairs": missing_pairs,
        "crop_response_estimated": False,
        "economic_damage_or_scc_estimated": False,
    }
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps(outcome))


if __name__ == "__main__":
    main()
