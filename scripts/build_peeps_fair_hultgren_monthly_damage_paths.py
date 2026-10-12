#!/usr/bin/env python3
"""Build one-ESM marginal monthly-precipitation maize damage paths."""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_epa_fair_hultgren_quantity_damage_paths import (
    ADAPTATION,
    CONVERGENCE_RELATIVE_TOLERANCE,
    DEMAND_ELASTICITY,
    PULSES,
    SUPPLY_ELASTICITY,
    VALUE,
    adaptation_factors,
    country_market_damage,
)
from build_hultgren_grid_weather_basis import crop_month_keys
from build_hultgren_peeps_monthly_slope_panel import SLOPE_COLUMNS
from build_hultgren_monthly_precip_climatology import CALENDAR_COLUMNS, MAX_MONTHS, RAIN_COLUMNS
from build_hultgren_precip_basis_climatology import FEATURES, require

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["native_lat_index", "native_lon_index"]
LINEAR = [f"prcp_poly_1_bin{phase}" for phase in (1, 2, 3)]
SQUARED = [f"prcp_poly_2_bin{phase}" for phase in (1, 2, 3)]
PHASES = (slice(0, 1), slice(1, 4), slice(4, MAX_MONTHS))
YEARS = np.arange(2020, 2301, dtype=np.int32)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def days_by_month(year: int) -> np.ndarray:
    return np.asarray([calendar.monthrange(year, month)[1] for month in range(1, 13)], dtype=np.float64)


def year_offsets(frame: pd.DataFrame) -> np.ndarray:
    result = np.zeros((len(frame), MAX_MONTHS), dtype=np.int8)
    for index, row in enumerate(frame.itertuples(index=False)):
        keys = crop_month_keys(2000, int(row.plant_month), int(row.harvest_month))
        require(len(keys) == int(row.season_months), "crop calendar length differs")
        for offset, (year, month) in enumerate(keys):
            require(month == int(getattr(row, CALENDAR_COLUMNS[offset])), "calendar month differs")
            result[index, offset] = year - 2000
    require(np.isin(result, (-1, 0)).all(), "crop year offset outside prior/current year")
    return result


def regime_feature_deltas(
    baseline: np.ndarray,
    slopes: np.ndarray,
    months: np.ndarray,
    offsets: np.ndarray,
    fair_lookup: dict[int, float],
    harvest_year: int,
) -> tuple[np.ndarray, float]:
    anomaly = np.zeros_like(baseline)
    active = months > 0
    for relative_year in (-1, 0):
        actual_year = harvest_year + relative_year
        temperature = fair_lookup[actual_year]
        day_counts = days_by_month(actual_year)
        selected = active & offsets.eq(relative_year) if isinstance(offsets, pd.DataFrame) else active & (offsets == relative_year)
        row, column = np.nonzero(selected)
        anomaly[row, column] = slopes[row, column] * 86_400.0 * day_counts[months[row, column] - 1] * temperature
    perturbed = baseline + anomaly
    minimum = float(perturbed[active].min())
    linear = [anomaly[:, selected].sum(axis=1) for selected in PHASES]
    squared = [(2.0 * baseline[:, selected] * anomaly[:, selected] + np.square(anomaly[:, selected])).sum(axis=1) for selected in PHASES]
    return np.column_stack(linear + squared), minimum


def common_physical_support(
    baseline: np.ndarray,
    slopes: np.ndarray,
    months: np.ndarray,
    offsets: np.ndarray,
    fair_paths: dict[float, dict[int, float]],
) -> tuple[np.ndarray, float]:
    """Identify regime rows nonnegative for every registered pulse and year."""
    minimum_factor = np.full((2, 12), np.inf, dtype=np.float64)
    maximum_factor = np.full((2, 12), -np.inf, dtype=np.float64)
    for relative_year in (-1, 0):
        for harvest_year in YEARS:
            actual_year = int(harvest_year) + relative_year
            day_counts = days_by_month(actual_year)
            temperatures = np.asarray([fair_paths[pulse][actual_year] for pulse in PULSES])
            factors = 86_400.0 * day_counts[:, None] * temperatures[None, :]
            minimum_factor[relative_year + 1] = np.minimum(minimum_factor[relative_year + 1], factors.min(axis=1))
            maximum_factor[relative_year + 1] = np.maximum(maximum_factor[relative_year + 1], factors.max(axis=1))
    active = months > 0
    row, column = np.nonzero(active)
    lower = minimum_factor[offsets[row, column] + 1, months[row, column] - 1]
    upper = maximum_factor[offsets[row, column] + 1, months[row, column] - 1]
    minimum_anomaly = np.zeros_like(baseline)
    minimum_anomaly[row, column] = np.where(
        slopes[row, column] >= 0.0,
        slopes[row, column] * lower,
        slopes[row, column] * upper,
    )
    minimum_rain = baseline + minimum_anomaly
    valid = np.all(~active | (minimum_rain >= 0.0), axis=1)
    return valid, float(minimum_rain[active].min())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slope-panel", type=Path, required=True)
    parser.add_argument("--slope-receipt", type=Path, required=True)
    parser.add_argument("--response-panel", type=Path, required=True)
    parser.add_argument("--response-receipt", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--fair-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    slope_receipt = json.loads(args.slope_receipt.read_text())
    response_receipt = json.loads(args.response_receipt.read_text())
    fair_receipt = json.loads(args.fair_receipt.read_text())
    require(slope_receipt["schema"] == "hultgren_peeps_monthly_slope_panel/v1", "slope receipt differs")
    require(response_receipt["schema"] == "hultgren_quantity_response_panel/v1", "response receipt differs")
    require(slope_receipt["output"]["sha256"] == digest(args.slope_panel), "slope panel hash differs")
    require(response_receipt["output"]["sha256"] == digest(args.response_panel), "response panel hash differs")
    require(fair_receipt["paths_sha256"] == digest(args.fair), "FAIR path hash differs")
    require(fair_receipt["zero_pulse_identity"] and fair_receipt["pre_pulse_identity"] and fair_receipt["decreasing_pulse_convergence"], "FAIR gate failed")

    slopes = pd.read_parquet(args.slope_panel)
    response = pd.read_parquet(args.response_panel).sort_values(["iso3", *KEYS]).reset_index(drop=True)
    fair = pd.read_csv(args.fair)
    require(set(fair.pulse_size_gtc.astype(float)) == set(PULSES), "FAIR pulses differ")
    require(set(fair.year.astype(int)) == set(range(1750, 2301)), "FAIR years differ")
    require(not fair.duplicated(["year", "pulse_size_gtc"]).any(), "duplicate FAIR rows")
    fair_paths = {
        pulse: dict(zip(part.year.astype(int), part.difference_k.astype(float), strict=True))
        for pulse in PULSES
        for part in [fair.loc[fair.pulse_size_gtc.eq(pulse)].sort_values("year")]
    }

    cell_table = slopes[KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    cell_table["cell_id"] = np.arange(len(cell_table), dtype=np.int32)
    slopes = slopes.merge(cell_table, on=KEYS, how="left", validate="many_to_one").sort_values(["cell_id", "regime"]).reset_index(drop=True)
    response = response.merge(cell_table, on=KEYS, how="inner", validate="many_to_one")
    retained_value = float(response[VALUE].sum())
    require(len(response) == response_receipt["output"]["rows"], "response support lost in slope join")
    response = response.sort_values(["iso3", *KEYS]).reset_index(drop=True)

    cell_id = slopes.cell_id.to_numpy(dtype=np.int32)
    areas = slopes.mirca_area_ha.to_numpy(dtype=np.float64)
    baseline = slopes[RAIN_COLUMNS].to_numpy(dtype=np.float64)
    slope_values = slopes[SLOPE_COLUMNS].to_numpy(dtype=np.float64)
    months = slopes[CALENDAR_COLUMNS].to_numpy(dtype=np.int16)
    offsets = year_offsets(slopes)
    active = months > 0
    require(np.all(baseline[active] >= 0), "negative historical active-month rainfall")
    require(np.all(baseline[~active] == 0) and np.all(slope_values[~active] == 0), "inactive crop-month padding differs")

    source_area = float(areas.sum())
    source_value = float(response[VALUE].sum())
    valid_regime, unrestricted_minimum = common_physical_support(baseline, slope_values, months, offsets, fair_paths)
    invalid_cells = np.unique(cell_id[~valid_regime])
    valid_cell = np.ones(len(cell_table), dtype=bool)
    valid_cell[invalid_cells] = False
    keep_regime = valid_cell[cell_id]
    excluded_area = float(areas[~keep_regime].sum())
    cell_id, areas = cell_id[keep_regime], areas[keep_regime]
    baseline, slope_values, months, offsets = (
        array[keep_regime] for array in (baseline, slope_values, months, offsets)
    )
    response = response.loc[valid_cell[response.cell_id.to_numpy(dtype=np.int32)]].copy().reset_index(drop=True)
    retained_value = float(response[VALUE].sum())
    require(not response.empty and retained_value > 0, "physical common support empty")
    cell_area = np.bincount(cell_id, weights=areas, minlength=len(cell_table))
    require(np.all(cell_area[valid_cell] > 0), "nonpositive retained combined cell area")

    response_cell = response.cell_id.to_numpy(dtype=np.int32)
    coefficients = response[[f"effective_{feature}" for feature in FEATURES]].to_numpy(dtype=np.float64)
    values = response[VALUE].to_numpy(dtype=np.float64)
    iso = response.iso3.to_numpy()
    country_starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
    country_value = np.add.reduceat(values, country_starts)
    require(np.all(country_value > 0), "nonpositive represented country value")

    records = []
    minimum_perturbed = np.inf
    maximum_abs_response = 0.0
    normalized_damage: dict[tuple[float, str], np.ndarray] = {}
    for pulse in PULSES:
        per_year_damage = {scenario: [] for scenario in ADAPTATION}
        for year in YEARS:
            regime_delta, minimum = regime_feature_deltas(baseline, slope_values, months, offsets, fair_paths[pulse], int(year))
            minimum_perturbed = min(minimum_perturbed, minimum)
            cell_delta = np.zeros((len(cell_table), len(FEATURES)), dtype=np.float64)
            for column in range(len(FEATURES)):
                numerator = np.bincount(cell_id, weights=areas * regime_delta[:, column], minlength=len(cell_table))
                cell_delta[valid_cell, column] = numerator[valid_cell] / cell_area[valid_cell]
            log_response = np.sum(cell_delta[response_cell] * coefficients, axis=1)
            require(np.isfinite(log_response).all(), "nonfinite monthly-pattern response")
            maximum_abs_response = max(maximum_abs_response, float(np.max(np.abs(log_response))))
            factor = {scenario: float(adaptation_factors(np.asarray([year]), scenario)[0]) for scenario in ADAPTATION}
            for scenario in ADAPTATION:
                adapted = np.where(log_response < 0.0, log_response * factor[scenario], log_response)
                country_output = np.add.reduceat(np.exp(adapted) * values, country_starts)
                ratios = country_output / country_value
                require(np.isfinite(ratios).all() and np.all(ratios > 0), "invalid country supply ratio")
                damage = float(country_market_damage(country_value, ratios[:, None]).sum())
                per_year_damage[scenario].append(damage)
                records.append({
                    "climate_model": "PEEPS_MPI-ESM1-2-HR_ssp585",
                    "year": int(year),
                    "pulse_size_gtc": pulse,
                    "adaptation": scenario,
                    "tail_rule": "uncapped",
                    "damage_change_usd_source_price_basis": damage,
                    "total_surplus_change_usd_source_price_basis": -damage,
                    "minimum_country_supply_ratio": float(ratios.min()),
                    "maximum_country_supply_ratio": float(ratios.max()),
                    "represented_country_count": int(len(country_value)),
                    "represented_baseline_maize_value_usd": retained_value,
                })
        if pulse > 0:
            for scenario, damages in per_year_damage.items():
                normalized_damage[(pulse, scenario)] = np.asarray(damages) / pulse

    require(minimum_perturbed >= 0.0, "marginal monthly rainfall becomes negative")
    output = pd.DataFrame(records).sort_values(["adaptation", "pulse_size_gtc", "year"]).reset_index(drop=True)
    require(not output.duplicated(["year", "pulse_size_gtc", "adaptation", "tail_rule"]).any(), "duplicate output path")
    zero_identity = bool((output.loc[output.pulse_size_gtc.eq(0.0), "damage_change_usd_source_price_basis"] == 0.0).all())
    pre_identity = bool((output.loc[output.year.le(2020), "damage_change_usd_source_price_basis"] == 0.0).all())
    require(zero_identity and pre_identity, "pulse identity failed")
    small, next_small = 0.000025, 0.00005
    convergence = {}
    for scenario in ADAPTATION:
        a, b = normalized_damage[(small, scenario)], normalized_damage[(next_small, scenario)]
        scale = max(float(np.max(np.abs(a))), float(np.max(np.abs(b))), 1e-30)
        convergence[scenario] = float(np.max(np.abs(a - b)) / scale)
    maximum_convergence = max(convergence.values())
    require(maximum_convergence <= CONVERGENCE_RELATIVE_TOLERANCE, "shrinking-pulse convergence failed")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    summaries = output.loc[output.pulse_size_gtc.eq(small) & output.year.gt(2020)].groupby("adaptation")["damage_change_usd_source_price_basis"].agg(["min", "median", "mean", "max"]).reset_index().to_dict("records")
    result = {
        "schema": "peeps_fair_hultgren_monthly_damage_paths/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "one_esm_monthly_pattern_damage_paths_not_give_replacement_or_scc",
        "estimand": "published PEEPS MPI monthly precipitation slope times paired FAIR marginal temperature, transported through exact Hultgren monthly first/second moments and separate fully anticipated national maize markets",
        "sources": {
            "slope_panel": {"path": str(args.slope_panel), "sha256": digest(args.slope_panel), "receipt": str(args.slope_receipt), "receipt_sha256": digest(args.slope_receipt)},
            "response_panel": {"path": str(args.response_panel), "sha256": digest(args.response_panel), "receipt": str(args.response_receipt), "receipt_sha256": digest(args.response_receipt)},
            "fair": {"path": str(args.fair), "sha256": digest(args.fair), "receipt": str(args.fair_receipt), "receipt_sha256": digest(args.fair_receipt)},
        },
        "market": {"geography": "separate national maize markets", "supply_elasticity": SUPPLY_ELASTICITY, "demand_elasticity_magnitude": DEMAND_ELASTICITY, "yield_to_supply_mapping": "horizontal_output", "expectations": "fully anticipated"},
        "adaptation": {scenario: {**spec, "base_year": 2020, "application": "attenuate negative cell log-yield responses only"} for scenario, spec in ADAPTATION.items()},
        "support": {"climate_models": 1, "response_rows": len(response), "countries": int(response.iso3.nunique()), "source_combined_crop_cells": len(cell_table), "retained_combined_crop_cells": int(valid_cell.sum()), "excluded_combined_crop_cells": int((~valid_cell).sum()), "source_crop_area_ha": source_area, "excluded_crop_area_ha": excluded_area, "excluded_crop_area_fraction": excluded_area / source_area, "source_response_value_usd": source_value, "retained_response_value_usd": retained_value, "excluded_response_value_usd": source_value - retained_value, "excluded_response_value_fraction": (source_value - retained_value) / source_value, "no_renormalization": True, "years": [2020, 2300], "pulses_gtc": list(PULSES), "rows": len(output)},
        "validation": {"zero_pulse_identity": zero_identity, "pre_2021_identity": pre_identity, "unrestricted_minimum_perturbed_monthly_rainfall_mm": unrestricted_minimum, "minimum_perturbed_monthly_rainfall_mm_on_common_physical_support": minimum_perturbed, "maximum_absolute_cell_log_yield_response": maximum_abs_response, "shrinking_pulse_relative_tolerance": CONVERGENCE_RELATIVE_TOLERANCE, "maximum_relative_normalized_damage_disagreement": maximum_convergence, "convergence_by_adaptation": convergence},
        "smallest_pulse_damage_path_summaries_usd_source_price_basis": summaries,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "limitations": ["One ESM/scenario structural sensitivity; not a probabilistic timing SCC.", "A fixed common physical support excludes an entire crop cell if either irrigation regime would have negative monthly rainfall under any registered pulse/year; excluded area and value are reported without renormalization.", "Monthly means cannot represent daily dry spells, extremes, or drought.", "Only maize and the uncapped published response are included.", "The fixed common-price value base remains in its source price basis; GIVE currency conversion and paired replacement are not yet applied.", "No trade, storage, cross-crop substitution, adaptation costs, or future maize-value growth is modeled."],
        "claim_gates": {"monthly_marginal_response": True, "central_structural_damage_path": True, "currency_aligned_give_damage": False, "agriculture_replacement": False, "scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "support": result["support"], "validation": result["validation"], "summaries": summaries, "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
