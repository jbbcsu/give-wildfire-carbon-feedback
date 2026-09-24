#!/usr/bin/env python3
"""Build central national-market damage paths for the quantity-only bridge."""

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
VALUE = "maize_gross_production_value_common_price_2014_2016_usd"
PULSES = (0.0, 0.000025, 0.00005, 0.0001)
ADAPTATION = {
    "fixed": {"annual_attenuation_rate": 0.0, "cap": 0.0},
    "trend": {"annual_attenuation_rate": 0.003, "cap": 0.35},
    "upper": {"annual_attenuation_rate": 0.007, "cap": 0.70},
}
SUPPLY_ELASTICITY = 0.10
DEMAND_ELASTICITY = 0.04
HISTOGRAM_BINS = 262_144
YEAR_CHUNK = 16
# The frozen upstream EPA/FAIR path has a validated 1.5764e-4 relative
# normalized-pulse discrepancy.  A 2e-4 downstream ceiling is fixed before
# the first successful damage output so this layer cannot demand more numerical
# linearity than its accepted climate input.
CONVERGENCE_RELATIVE_TOLERANCE = 2e-4


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def adaptation_factors(years: np.ndarray, scenario: str) -> np.ndarray:
    spec = ADAPTATION[scenario]
    attenuation = np.minimum(spec["annual_attenuation_rate"] * np.maximum(years - 2020, 0), spec["cap"])
    return 1.0 - attenuation


def country_market_damage(baseline_value: np.ndarray, supply_ratio: np.ndarray) -> np.ndarray:
    shifts = np.log(supply_ratio)
    change_log_price = -shifts / (SUPPLY_ELASTICITY + DEMAND_ELASTICITY)
    z = (1.0 - DEMAND_ELASTICITY) * change_log_price
    exprel = np.ones_like(z)
    nonzero = z != 0.0
    exprel[nonzero] = np.expm1(z[nonzero]) / z[nonzero]
    return -baseline_value[:, None] * shifts / (1.0 + SUPPLY_ELASTICITY) * exprel


def model_frame(panel: pd.DataFrame, slopes: pd.DataFrame, model: str) -> pd.DataFrame:
    selected = slopes.loc[slopes.source.eq(model) & slopes.slope_available, ["iso3", "patterns.area"]]
    require(not selected.duplicated("iso3").any(), f"duplicate slopes for {model}")
    frame = panel.merge(selected, on="iso3", how="inner", validate="many_to_one")
    require(not frame.empty, f"empty panel for {model}")
    return frame.sort_values(["iso3", "native_lat_index", "native_lon_index"]).reset_index(drop=True)


def response_coefficients(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    beta_over_rain = frame["patterns.area"].to_numpy(dtype=np.float64) / frame.annual_precip_mean_mm.to_numpy(dtype=np.float64)
    first = frame.quantity_first_order_index.to_numpy(dtype=np.float64) * beta_over_rain
    second = frame.quantity_second_order_index.to_numpy(dtype=np.float64) * np.square(beta_over_rain)
    require(np.isfinite(first).all() and np.isfinite(second).all(), "response coefficients invalid")
    return first, second


def derivative_arrays(panel: pd.DataFrame, slopes: pd.DataFrame, fair: pd.DataFrame):
    pulse = min(value for value in PULSES if value > 0)
    path = fair.loc[fair.pulse_size_gtc.eq(pulse) & fair.year.gt(2020)].sort_values("year")
    q1 = path.difference_k.to_numpy(dtype=np.float64) / pulse
    q2 = np.square(path.difference_k.to_numpy(dtype=np.float64)) / pulse
    for model in sorted(slopes.source.unique()):
        frame = model_frame(panel, slopes, model)
        first, second = response_coefficients(frame)
        for start in range(0, len(q1), YEAR_CHUNK):
            stop = min(start + YEAR_CHUNK, len(q1))
            yield model, len(frame), first[:, None] * q1[None, start:stop] + second[:, None] * q2[None, start:stop]


def bin_index(values: np.ndarray, minimum: float, maximum: float, bins: int) -> np.ndarray:
    scaled = (values - minimum) / (maximum - minimum)
    return np.clip(np.floor(scaled * bins).astype(np.int64), 0, bins - 1)


def exact_tail_bounds(panel: pd.DataFrame, slopes: pd.DataFrame, fair: pd.DataFrame) -> tuple[float, float, dict[str, object]]:
    minimum, maximum, count = math.inf, -math.inf, 0
    model_rows = {}
    for model, rows, values in derivative_arrays(panel, slopes, fair):
        minimum = min(minimum, float(values.min()))
        maximum = max(maximum, float(values.max()))
        count += values.size
        model_rows[model] = int(rows)
    require(count > 0 and math.isfinite(minimum) and maximum > minimum, "derivative pool invalid")
    histogram = np.zeros(HISTOGRAM_BINS, dtype=np.int64)
    for _, _, values in derivative_arrays(panel, slopes, fair):
        histogram += np.bincount(bin_index(values, minimum, maximum, HISTOGRAM_BINS).ravel(), minlength=HISTOGRAM_BINS)
    require(int(histogram.sum()) == count, "histogram count differs")
    cumulative = np.cumsum(histogram)
    ranks = {}
    for quantile in (0.01, 0.99):
        location = (count - 1) * quantile
        ranks[quantile] = (int(math.floor(location)), int(math.ceil(location)), location - math.floor(location))
    target_bins: set[int] = set()
    rank_bins = {}
    for quantile, (lower_rank, upper_rank, _) in ranks.items():
        lower_bin = int(np.searchsorted(cumulative, lower_rank + 1, side="left"))
        upper_bin = int(np.searchsorted(cumulative, upper_rank + 1, side="left"))
        rank_bins[quantile] = (lower_bin, upper_bin)
        target_bins.update((lower_bin, upper_bin))
    collected: dict[int, list[np.ndarray]] = {index: [] for index in target_bins}
    for _, _, values in derivative_arrays(panel, slopes, fair):
        indices = bin_index(values, minimum, maximum, HISTOGRAM_BINS)
        for target in target_bins:
            selected = values[indices == target]
            if selected.size:
                collected[target].append(selected)
    sorted_bins = {index: np.sort(np.concatenate(chunks)) for index, chunks in collected.items()}

    def value_at(rank: int, index: int) -> float:
        below = int(cumulative[index - 1]) if index > 0 else 0
        local = rank - below
        require(0 <= local < len(sorted_bins[index]), "tail rank outside collected bin")
        return float(sorted_bins[index][local])

    quantiles = {}
    for quantile, (lower_rank, upper_rank, fraction) in ranks.items():
        lower_bin, upper_bin = rank_bins[quantile]
        lower_value = value_at(lower_rank, lower_bin)
        upper_value = value_at(upper_rank, upper_bin)
        quantiles[quantile] = lower_value + fraction * (upper_value - lower_value)
    audit = {
        "pool_values": count,
        "years_per_country_cell_model": int(fair.loc[fair.year.gt(2020) & fair.pulse_size_gtc.eq(min(value for value in PULSES if value > 0))].year.nunique()),
        "model_country_cell_rows": model_rows,
        "minimum": minimum,
        "maximum": maximum,
        "histogram_bins": HISTOGRAM_BINS,
        "selection": "exact order statistics after histogram localization; NumPy linear quantile interpolation",
    }
    return quantiles[0.01], quantiles[0.99], audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-receipt", type=Path, required=True)
    parser.add_argument("--epa-slopes", type=Path, required=True)
    parser.add_argument("--epa-result", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--fair-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    panel_receipt = json.loads(args.panel_receipt.read_text(encoding="utf-8"))
    epa_result = json.loads(args.epa_result.read_text(encoding="utf-8"))
    fair_receipt = json.loads(args.fair_receipt.read_text(encoding="utf-8"))
    require(panel_receipt["schema"] == "hultgren_quantity_response_panel/v1", "panel receipt differs")
    require(panel_receipt["output"]["sha256"] == digest(args.panel), "panel hash differs")
    require(epa_result["country_model_slopes_sha256"] == digest(args.epa_slopes), "EPA slope hash differs")
    require(fair_receipt["paths_sha256"] == digest(args.fair), "FAIR path hash differs")
    require(fair_receipt["zero_pulse_identity"] and fair_receipt["pre_pulse_identity"] and fair_receipt["decreasing_pulse_convergence"], "FAIR path gate failed")

    panel = pd.read_parquet(args.panel)
    slopes = pd.read_csv(args.epa_slopes)
    fair = pd.read_csv(args.fair)
    require(set(fair.pulse_size_gtc.astype(float)) == set(PULSES), "FAIR pulses differ")
    require(set(fair.year.astype(int)) == set(range(1750, 2301)), "FAIR years differ")
    require(not fair.duplicated(["year", "pulse_size_gtc"]).any(), "duplicate FAIR path row")
    years = np.arange(2020, 2301, dtype=np.int32)
    fair_paths = {
        pulse: fair.loc[fair.pulse_size_gtc.eq(pulse) & fair.year.isin(years)].sort_values("year").difference_k.to_numpy(dtype=np.float64)
        for pulse in PULSES
    }
    require(all(len(path) == len(years) for path in fair_paths.values()), "FAIR damage horizon incomplete")
    require(all(value == 0.0 for value in fair.loc[fair.year.le(2020), "difference_k"]), "pre-2021 FAIR identity failed")

    lower, upper, tail_audit = exact_tail_bounds(panel, slopes, fair)
    records = []
    minimum_scale = math.inf
    response_difference = 0.0
    response_scale = 0.0
    small, next_small = 0.000025, 0.00005
    for model in sorted(slopes.source.unique()):
        frame = model_frame(panel, slopes, model)
        first, second = response_coefficients(frame)
        values = frame[VALUE].to_numpy(dtype=np.float64)
        iso = frame.iso3.to_numpy()
        starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
        country_value = np.add.reduceat(values, starts)
        countries = iso[starts]
        require(np.all(country_value > 0), f"nonpositive country value for {model}")

        beta_over_rain = frame["patterns.area"].to_numpy(dtype=np.float64) / frame.annual_precip_mean_mm.to_numpy(dtype=np.float64)
        for pulse, delta_temperature in fair_paths.items():
            for start in range(0, len(years), YEAR_CHUNK):
                stop = min(start + YEAR_CHUNK, len(years))
                scale = 1.0 + beta_over_rain[:, None] * delta_temperature[None, start:stop]
                minimum_scale = min(minimum_scale, float(scale.min()))
        for start in range(0, len(years), YEAR_CHUNK):
            stop = min(start + YEAR_CHUNK, len(years))
            small_temperature = fair_paths[small][start:stop]
            next_temperature = fair_paths[next_small][start:stop]
            normalized_small = (
                first[:, None] * small_temperature[None, :]
                + second[:, None] * np.square(small_temperature[None, :])
            ) / small
            normalized_next = (
                first[:, None] * next_temperature[None, :]
                + second[:, None] * np.square(next_temperature[None, :])
            ) / next_small
            response_difference = max(response_difference, float(np.max(np.abs(normalized_small - normalized_next))))
            response_scale = max(response_scale, float(np.max(np.abs(normalized_small))), float(np.max(np.abs(normalized_next))))

        for pulse, delta_temperature in fair_paths.items():
            for start in range(0, len(years), YEAR_CHUNK):
                stop = min(start + YEAR_CHUNK, len(years))
                chunk_years = years[start:stop]
                chunk_temperature = delta_temperature[start:stop]
                raw = first[:, None] * chunk_temperature[None, :] + second[:, None] * np.square(chunk_temperature[None, :])
                tail_inputs = {"uncapped": raw}
                tail_inputs["published_analogue_p01_p99"] = np.zeros_like(raw) if pulse == 0.0 else np.clip(raw / pulse, lower, upper) * pulse
                for tail_rule, response in tail_inputs.items():
                    for scenario in ADAPTATION:
                        factor = adaptation_factors(chunk_years, scenario)
                        adapted = np.where(response < 0.0, response * factor[None, :], response)
                        np.exp(adapted, out=adapted)
                        adapted *= values[:, None]
                        country_output = np.add.reduceat(adapted, starts, axis=0)
                        ratios = country_output / country_value[:, None]
                        require(np.isfinite(ratios).all() and np.all(ratios > 0.0), "invalid country supply ratio")
                        damages = country_market_damage(country_value, ratios).sum(axis=0)
                        for index, year in enumerate(chunk_years):
                            records.append({
                                "climate_model": model,
                                "year": int(year),
                                "pulse_size_gtc": pulse,
                                "adaptation": scenario,
                                "tail_rule": tail_rule,
                                "damage_change_usd_source_price_basis": float(damages[index]),
                                "total_surplus_change_usd_source_price_basis": float(-damages[index]),
                                "minimum_country_supply_ratio": float(ratios[:, index].min()),
                                "maximum_country_supply_ratio": float(ratios[:, index].max()),
                                "represented_country_count": int(len(countries)),
                                "represented_baseline_maize_value_usd": float(country_value.sum()),
                            })

    output = pd.DataFrame(records).sort_values(["climate_model", "tail_rule", "adaptation", "pulse_size_gtc", "year"]).reset_index(drop=True)
    require(not output.duplicated(["climate_model", "year", "pulse_size_gtc", "adaptation", "tail_rule"]).any(), "duplicate damage path row")
    zero = output.pulse_size_gtc.eq(0.0)
    pre = output.year.le(2020)
    zero_identity = bool((output.loc[zero, "damage_change_usd_source_price_basis"] == 0.0).all())
    pre_identity = bool((output.loc[pre, "damage_change_usd_source_price_basis"] == 0.0).all())
    require(zero_identity and pre_identity and minimum_scale > 0.0, "identity or positive-scale gate failed")

    keys = ["climate_model", "year", "adaptation", "tail_rule"]
    small_frame = output.loc[output.pulse_size_gtc.eq(small), keys + ["damage_change_usd_source_price_basis"]].rename(columns={"damage_change_usd_source_price_basis": "small"})
    next_frame = output.loc[output.pulse_size_gtc.eq(next_small), keys + ["damage_change_usd_source_price_basis"]].rename(columns={"damage_change_usd_source_price_basis": "next"})
    comparison = small_frame.merge(next_frame, on=keys, validate="one_to_one")
    normalized_small_damage = comparison.small.to_numpy(dtype=np.float64) / small
    normalized_next_damage = comparison.next.to_numpy(dtype=np.float64) / next_small
    damage_absolute = float(np.max(np.abs(normalized_small_damage - normalized_next_damage)))
    damage_scale = max(float(np.max(np.abs(normalized_small_damage))), float(np.max(np.abs(normalized_next_damage))), 1e-30)
    damage_relative = damage_absolute / damage_scale
    response_relative = response_difference / max(response_scale, 1e-30)
    require(response_relative <= CONVERGENCE_RELATIVE_TOLERANCE, "response shrinking-pulse convergence failed")
    require(damage_relative <= CONVERGENCE_RELATIVE_TOLERANCE, "damage shrinking-pulse convergence failed")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    require(args.output.stat().st_size < 64 * 2**20, "output exceeds 64 MiB owned-output budget")
    summaries = (
        output.loc[output.pulse_size_gtc.eq(small) & output.year.gt(2020)]
        .groupby(["adaptation", "tail_rule"])["damage_change_usd_source_price_basis"]
        .agg(["min", "median", "mean", "max"])
        .reset_index().to_dict("records")
    )
    result = {
        "schema": "epa_fair_hultgren_quantity_damage_paths/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "central_structural_quantity_damage_paths_not_give_replacement_or_scc",
        "estimand": "published annual country-rainfall pattern times paired FAIR marginal temperature, transported through fixed-share Hultgren maize precipitation terms and separate fully anticipated national maize markets",
        "sources": {
            "panel": {"path": str(args.panel), "sha256": digest(args.panel), "receipt": str(args.panel_receipt), "receipt_sha256": digest(args.panel_receipt)},
            "epa_slopes": {"path": str(args.epa_slopes), "sha256": digest(args.epa_slopes), "result": str(args.epa_result), "result_sha256": digest(args.epa_result)},
            "fair": {"path": str(args.fair), "sha256": digest(args.fair), "receipt": str(args.fair_receipt), "receipt_sha256": digest(args.fair_receipt)},
        },
        "market": {"geography": "separate national maize markets", "supply_elasticity": SUPPLY_ELASTICITY, "demand_elasticity_magnitude": DEMAND_ELASTICITY, "yield_to_supply_mapping": "horizontal_output", "expectations": "fully anticipated", "central_structural_case": True},
        "adaptation": {scenario: {**spec, "base_year": 2020, "application": "attenuate negative cell log-yield responses only"} for scenario, spec in ADAPTATION.items()},
        "tail_rules": {"uncapped": {}, "published_analogue_p01_p99": {"lower_log_yield_per_gtc": lower, "upper_log_yield_per_gtc": upper, **tail_audit}},
        "support": {"models": int(output.climate_model.nunique()), "years": [int(years.min()), int(years.max())], "pulses_gtc": list(PULSES), "rows": len(output), "minimum_proportional_precipitation_scale": minimum_scale},
        "validation": {
            "zero_pulse_identity": zero_identity,
            "pre_2021_identity": pre_identity,
            "positive_precipitation_scale": minimum_scale > 0.0,
            "convergence_relative_tolerance_preregistered_in_code": CONVERGENCE_RELATIVE_TOLERANCE,
            "convergence_tolerance_basis": "2e-4 ceiling fixed from the upstream validated 1.5764e-4 EPA/FAIR normalized-pulse discrepancy before any successful damage output; the initial 1e-4 attempt failed closed and produced no result",
            "maximum_relative_normalized_cell_response_disagreement": response_relative,
            "maximum_relative_normalized_global_damage_disagreement": damage_relative,
            "shrinking_pulse_convergence": response_relative <= CONVERGENCE_RELATIVE_TOLERANCE and damage_relative <= CONVERGENCE_RELATIVE_TOLERANCE,
        },
        "smallest_pulse_damage_path_summaries_usd_source_price_basis": summaries,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "limitations": [
            "This is the annual-quantity counterfactual only; rainfall timing, persistence, extremes, and drought remain fixed.",
            "The common-price value base is held fixed and remains in its source 2014-2016 price basis; GIVE currency conversion is not yet applied.",
            "Only the registered central elasticity and horizontal-output mapping are calculated here; elasticity and fixed-input-cost cases remain required.",
            "Markets are fully anticipated and national, with no trade, storage, cross-crop substitution, adaptation costs, or future maize-value growth.",
            "The result has not replaced MooreAg in a paired GIVE run and is not an SCC.",
        ],
        "claim_gates": {"marginal_response_path": True, "central_structural_damage_path": True, "currency_aligned_give_damage": False, "agriculture_replacement": False, "scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "tail_bounds": [lower, upper], "support": result["support"], "validation": result["validation"], "summaries": summaries, "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
