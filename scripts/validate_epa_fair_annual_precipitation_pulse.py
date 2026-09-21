#!/usr/bin/env python3
"""Independent csv/math reconstruction of the EPA/FAIR pulse benchmark."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
SLOPES = ROOT / "data/interim/epa_annual_country_pattern_benchmark_20260921/country_model_slopes.csv"
FAIR = ROOT / "data/interim/give_fair_temperature_path_smoke/temperature_paths.csv"
SLOPES_SHA = "e6bc9a4dbc0af19650f2f243802e0e1974d3599292cf2704aad0e746bf0c0572"
FAIR_SHA = "aedf6b66dd296337e1cb6105d2aa56ec94f3e15e5ac92c2abcdf74b6a42b6067"
YEARS = [2021, 2030, 2050, 2100, 2200, 2300]
PULSES = [0.0001, 0.00005, 0.000025]


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


def close(actual: float, expected: float, label: str, tolerance: float = 1e-15) -> None:
    scale = max(1.0, abs(actual), abs(expected))
    if not math.isfinite(actual) or not math.isfinite(expected) or abs(actual - expected) > tolerance * scale:
        raise ValueError(f"EPA/FAIR independent mismatch {label}: {actual} != {expected}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    benchmark = args.benchmark_dir.resolve()
    out = args.out_dir.resolve()
    if (not benchmark.is_relative_to(ROOT / "data/interim") or not benchmark.is_dir() or
            out.exists() or not out.is_relative_to(ROOT / "data/interim")):
        raise ValueError("valid ignored benchmark and fresh ignored audit output required")
    if sha(SLOPES) != SLOPES_SHA or sha(FAIR) != FAIR_SHA:
        raise ValueError("EPA or FAIR audit input hash changed")

    beta: list[float] = []
    beta_by_country: dict[str, list[float]] = {}
    with SLOPES.open(newline="") as stream:
        slope_rows = list(csv.DictReader(stream))
    for row in slope_rows:
        if row["slope_available"] == "True":
            value = float(row["patterns.area"])
            beta.append(value)
            beta_by_country.setdefault(row["iso3"], []).append(value)
        elif row["slope_available"] != "False":
            raise ValueError("EPA slope availability flag changed")
    if len(slope_rows) != 4784 or len(beta) != 4703 or len(beta_by_country) != 184:
        raise ValueError("EPA audit support changed")

    fair: dict[tuple[int, float], dict[str, float]] = {}
    baselines: dict[int, set[float]] = {}
    with FAIR.open(newline="") as stream:
        fair_rows = list(csv.DictReader(stream))
    for row in fair_rows:
        year, pulse = int(row["year"]), float(row["pulse_size_gtc"])
        values = {name: float(row[name]) for name in
                  ("baseline_temperature_c", "pulse_temperature_c", "difference_k")}
        if (year, pulse) in fair:
            raise ValueError("duplicate FAIR audit row")
        fair[(year, pulse)] = values
        baselines.setdefault(year, set()).add(values["baseline_temperature_c"])
        close(values["difference_k"], values["pulse_temperature_c"] - values["baseline_temperature_c"],
              f"temperature identity/{year}/{pulse}")
    if (len(fair_rows) != 2204 or any(len(values) != 1 for values in baselines.values()) or
            any(fair[(year, 0.0)]["difference_k"] != 0 for year in range(1750, 2301)) or
            any(fair[(year, pulse)]["difference_k"] != 0
                for year in range(1750, 2021) for pulse in PULSES)):
        raise ValueError("FAIR audit support or identity changed")

    reported = json.loads((benchmark / "result.json").read_text())
    if (reported["status"] != "published_epa_fair_annual_precipitation_pulse_benchmark_not_damage_or_scc" or
            reported["epa_slope_table_sha256"] != SLOPES_SHA or
            reported["fair_temperature_paths_sha256"] != FAIR_SHA or
            reported["finite_country_model_pairs"] != 4703 or reported["countries"] != 184):
        raise ValueError("reported EPA/FAIR benchmark identity invalid")
    indexed = {(int(row["year"]), float(row["pulse_size_gtc"])): row
               for row in reported["selected_year_summaries"]}
    if set(indexed) != {(year, pulse) for year in YEARS for pulse in PULSES}:
        raise ValueError("reported selected pulse/year support differs")

    checks = 0
    for year in YEARS:
        for pulse in PULSES:
            delta_t = fair[(year, pulse)]["difference_k"]
            values = [value * delta_t for value in beta]
            country_medians = [statistics.median(value * delta_t for value in country_values)
                               for country_values in beta_by_country.values()]
            expected = {
                "temperature_difference_k": delta_t,
                "minimum_mm_per_year": min(values),
                "q05_mm_per_year": quantile(values, 0.05),
                "q25_mm_per_year": quantile(values, 0.25),
                "median_mm_per_year": statistics.median(values),
                "q75_mm_per_year": quantile(values, 0.75),
                "q95_mm_per_year": quantile(values, 0.95),
                "maximum_mm_per_year": max(values),
                "mean_mm_per_year": math.fsum(values) / len(values),
                "positive_pair_fraction": sum(value > 0 for value in values) / len(values),
                "negative_pair_fraction": sum(value < 0 for value in values) / len(values),
            }
            row = indexed[(year, pulse)]
            for field, value in expected.items():
                close(float(row[field]), value, f"{year}/{pulse}/{field}")
                checks += 1
            counts = {
                "positive_country_medians": sum(value > 0 for value in country_medians),
                "negative_country_medians": sum(value < 0 for value in country_medians),
                "zero_country_medians": sum(value == 0 for value in country_medians),
            }
            for field, value in counts.items():
                if int(row[field]) != value:
                    raise ValueError(f"EPA/FAIR count mismatch {year}/{pulse}/{field}")
                checks += 1

    small, next_small = PULSES[-1], PULSES[-2]
    absolute: list[float] = []
    relative: list[float] = []
    for year in range(2021, 2301):
        small_value = fair[(year, small)]["difference_k"] / small
        next_value = fair[(year, next_small)]["difference_k"] / next_small
        difference = abs(small_value - next_value)
        absolute.append(difference)
        relative.append(difference / max(abs(small_value), abs(next_value), 1e-15))
    convergence = reported["convergence"]
    convergence_expected = {
        "maximum_absolute_normalized_temperature_disagreement_k_per_gtc": max(absolute),
        "maximum_relative_normalized_temperature_disagreement": max(relative),
        "maximum_absolute_normalized_precipitation_disagreement_mm_per_year_per_gtc":
            max(absolute) * max(abs(value) for value in beta),
        "maximum_relative_normalized_precipitation_disagreement": max(relative),
    }
    for field, value in convergence_expected.items():
        close(float(convergence[field]), value, field)
        checks += 1

    outcome = {
        "status": "independent_epa_fair_annual_precipitation_pulse_benchmark_validated",
        "numeric_and_support_checks": checks,
        "benchmark_result_sha256": sha(benchmark / "result.json"),
        "epa_slope_table_sha256": sha(SLOPES),
        "fair_temperature_paths_sha256": sha(FAIR),
        "validator_sha256": sha(Path(__file__)),
        "daily_timing_or_extremes_represented": False,
        "crop_response_estimated": False,
        "economic_damage_or_scc_estimated": False,
    }
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps(outcome))


if __name__ == "__main__":
    main()
