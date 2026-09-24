#!/usr/bin/env python3
"""Independently validate central quantity-only marginal damage paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

VALUE = "maize_gross_production_value_common_price_2014_2016_usd"
SUPPLY = 0.10
DEMAND = 0.04
YEAR_CHUNK = 16


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def model_panel(panel: pd.DataFrame, slopes: pd.DataFrame, model: str) -> pd.DataFrame:
    selected = slopes.loc[slopes.source.eq(model) & slopes.slope_available, ["iso3", "patterns.area"]]
    return panel.merge(selected, on="iso3", how="inner", validate="many_to_one").sort_values(
        ["iso3", "native_lat_index", "native_lon_index"]
    ).reset_index(drop=True)


def coefficients(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    scaled = frame["patterns.area"].to_numpy(dtype=np.float64) / frame.annual_precip_mean_mm.to_numpy(dtype=np.float64)
    return (
        frame.quantity_first_order_index.to_numpy(dtype=np.float64) * scaled,
        frame.quantity_second_order_index.to_numpy(dtype=np.float64) * scaled**2,
    )


def derivative_chunks(panel: pd.DataFrame, slopes: pd.DataFrame, fair: pd.DataFrame):
    pulse = 0.000025
    temperatures = fair.loc[fair.pulse_size_gtc.eq(pulse) & fair.year.gt(2020)].sort_values("year").difference_k.to_numpy(dtype=np.float64)
    for model in sorted(slopes.source.unique()):
        first, second = coefficients(model_panel(panel, slopes, model))
        for start in range(0, len(temperatures), YEAR_CHUNK):
            values = temperatures[start:start + YEAR_CHUNK]
            yield first[:, None] * values[None, :] / pulse + second[:, None] * values[None, :] ** 2 / pulse


def validate_tail_rank(panel: pd.DataFrame, slopes: pd.DataFrame, fair: pd.DataFrame, probability: float, bound: float, count: int) -> dict[str, float | int]:
    below = 0
    lower_neighbor = -math.inf
    upper_neighbor = math.inf
    exact = 0
    for values in derivative_chunks(panel, slopes, fair):
        below += int(np.count_nonzero(values < bound))
        exact += int(np.count_nonzero(values == bound))
        lower_values = values[values < bound]
        upper_values = values[values > bound]
        if lower_values.size:
            lower_neighbor = max(lower_neighbor, float(lower_values.max()))
        if upper_values.size:
            upper_neighbor = min(upper_neighbor, float(upper_values.min()))
    location = (count - 1) * probability
    lower_rank = int(math.floor(location))
    fraction = location - lower_rank
    if exact != 0 or below != lower_rank + 1:
        raise AssertionError(f"tail rank differs at {probability}: below={below}, exact={exact}, expected={lower_rank + 1}")
    reconstructed = lower_neighbor + fraction * (upper_neighbor - lower_neighbor)
    if not math.isclose(reconstructed, bound, rel_tol=2e-12, abs_tol=1e-15):
        raise AssertionError(f"tail interpolation differs at {probability}: {reconstructed} != {bound}")
    return {
        "probability": probability,
        "values_strictly_below": below,
        "values_equal": exact,
        "lower_neighbor": lower_neighbor,
        "upper_neighbor": upper_neighbor,
        "reconstructed_linear_quantile": reconstructed,
        "absolute_error": abs(reconstructed - bound),
    }


def recompute_case(
    panel: pd.DataFrame, slopes: pd.DataFrame, fair: pd.DataFrame, model: str, year: int,
    pulse: float, scenario: str, tail_rule: str, lower: float, upper: float,
) -> dict[str, float | int]:
    frame = model_panel(panel, slopes, model)
    first, second = coefficients(frame)
    temperature = float(fair.loc[fair.year.eq(year) & fair.pulse_size_gtc.eq(pulse), "difference_k"].iloc[0])
    response = first * temperature + second * temperature**2
    if tail_rule == "published_analogue_p01_p99":
        response = np.zeros_like(response) if pulse == 0 else np.clip(response / pulse, lower, upper) * pulse
    spec = {"fixed": (0.0, 0.0), "trend": (0.003, 0.35), "upper": (0.007, 0.70)}[scenario]
    factor = 1.0 - min(spec[0] * max(year - 2020, 0), spec[1])
    response = np.where(response < 0.0, response * factor, response)
    frame = frame.assign(shifted_value=frame[VALUE].to_numpy(dtype=np.float64) * np.exp(response))
    grouped = frame.groupby("iso3", sort=True).agg(baseline=(VALUE, "sum"), shifted=("shifted_value", "sum"))
    ratios = grouped.shifted.to_numpy(dtype=np.float64) / grouped.baseline.to_numpy(dtype=np.float64)
    shifts = np.log(ratios)
    price = -shifts / (SUPPLY + DEMAND)
    z = (1.0 - DEMAND) * price
    multiplier = np.ones_like(z)
    nonzero = z != 0.0
    multiplier[nonzero] = np.expm1(z[nonzero]) / z[nonzero]
    damage = -grouped.baseline.to_numpy(dtype=np.float64) * shifts / (1.0 + SUPPLY) * multiplier
    return {
        "damage": float(damage.sum()),
        "minimum_ratio": float(ratios.min()),
        "maximum_ratio": float(ratios.max()),
        "countries": int(len(grouped)),
        "value": float(grouped.baseline.sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if receipt["schema"] != "epa_fair_hultgren_quantity_damage_paths/v1":
        raise AssertionError("unexpected receipt schema")
    if receipt["claim_gates"]["agriculture_replacement"] or receipt["claim_gates"]["scc"]:
        raise AssertionError("claim gate promoted")
    output_path = Path(receipt["output"]["path"])
    if digest(output_path) != receipt["output"]["sha256"]:
        raise AssertionError("damage output hash differs")
    for source in receipt["sources"].values():
        if digest(Path(source["path"])) != source["sha256"]:
            raise AssertionError(f"source identity differs: {source['path']}")
        metadata_path = Path(source.get("receipt", source.get("result")))
        metadata_hash = source.get("receipt_sha256", source.get("result_sha256"))
        if digest(metadata_path) != metadata_hash:
            raise AssertionError(f"source metadata identity differs: {metadata_path}")

    paths = pd.read_parquet(output_path)
    keys = ["climate_model", "year", "pulse_size_gtc", "adaptation", "tail_rule"]
    if len(paths) != receipt["support"]["rows"] or paths.duplicated(keys).any():
        raise AssertionError("damage path support differs")
    numeric = ["damage_change_usd_source_price_basis", "minimum_country_supply_ratio", "maximum_country_supply_ratio", "represented_baseline_maize_value_usd"]
    if not np.isfinite(paths[numeric].to_numpy()).all() or not paths.minimum_country_supply_ratio.gt(0).all():
        raise AssertionError("damage path numeric support invalid")
    if not paths.loc[paths.pulse_size_gtc.eq(0), "damage_change_usd_source_price_basis"].eq(0).all():
        raise AssertionError("zero-pulse identity differs")
    if not paths.loc[paths.year.le(2020), "damage_change_usd_source_price_basis"].eq(0).all():
        raise AssertionError("pre-2021 identity differs")

    panel = pd.read_parquet(receipt["sources"]["panel"]["path"])
    slopes = pd.read_csv(receipt["sources"]["epa_slopes"]["path"])
    fair = pd.read_csv(receipt["sources"]["fair"]["path"])
    tail = receipt["tail_rules"]["published_analogue_p01_p99"]
    count = int(tail["pool_values"])
    tail_checks = [
        validate_tail_rank(panel, slopes, fair, 0.01, float(tail["lower_log_yield_per_gtc"]), count),
        validate_tail_rank(panel, slopes, fair, 0.99, float(tail["upper_log_yield_per_gtc"]), count),
    ]

    models = sorted(paths.climate_model.unique())
    cases = [
        (models[0], 2021, 0.000025, "fixed", "uncapped"),
        (models[len(models) // 4], 2030, 0.00005, "trend", "published_analogue_p01_p99"),
        (models[len(models) // 2], 2100, 0.0001, "upper", "uncapped"),
        (models[3 * len(models) // 4], 2200, 0.000025, "trend", "published_analogue_p01_p99"),
        (models[-1], 2300, 0.00005, "fixed", "published_analogue_p01_p99"),
    ]
    errors = {"damage": 0.0, "minimum_ratio": 0.0, "maximum_ratio": 0.0, "value": 0.0}
    case_records = []
    for model, year, pulse, scenario, tail_rule in cases:
        expected = recompute_case(
            panel, slopes, fair, model, year, pulse, scenario, tail_rule,
            float(tail["lower_log_yield_per_gtc"]), float(tail["upper_log_yield_per_gtc"]),
        )
        row = paths.loc[
            paths.climate_model.eq(model) & paths.year.eq(year) & paths.pulse_size_gtc.eq(pulse)
            & paths.adaptation.eq(scenario) & paths.tail_rule.eq(tail_rule)
        ].iloc[0]
        observed = {
            "damage": float(row.damage_change_usd_source_price_basis),
            "minimum_ratio": float(row.minimum_country_supply_ratio),
            "maximum_ratio": float(row.maximum_country_supply_ratio),
            "countries": int(row.represented_country_count),
            "value": float(row.represented_baseline_maize_value_usd),
        }
        if expected["countries"] != observed["countries"]:
            raise AssertionError("sentinel country count differs")
        for field in errors:
            errors[field] = max(errors[field], abs(float(expected[field]) - float(observed[field])))
        case_records.append({"model": model, "year": year, "pulse_size_gtc": pulse, "adaptation": scenario, "tail_rule": tail_rule})
    if errors["damage"] > 2e-3 or errors["minimum_ratio"] > 2e-14 or errors["maximum_ratio"] > 2e-14 or errors["value"] > 1e-4:
        raise AssertionError(f"sentinel path reconstruction differs: {errors}")

    result = {
        "schema": "epa_fair_hultgren_quantity_damage_paths_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "validation": {
            "all_source_metadata_and_output_hashes_checked": True,
            "all_output_keys_and_finite_values_checked": True,
            "zero_pulse_and_pre_2021_identity_checked": True,
            "tail_order_statistics_independently_ranked": tail_checks,
            "market_path_sentinel_cases": case_records,
            "maximum_absolute_errors": errors,
            "claim_gates_checked": True,
        },
        "scope": "Full artifact identity/support checks, independent exact tail-rank verification over the full derivative pool, and independent pandas-grouped national-market reconstruction for five fixed cases.",
        "interpretation": "Central structural source-price-basis damage-path validation only; no currency-aligned GIVE damage, agriculture replacement, or SCC gate is opened.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
