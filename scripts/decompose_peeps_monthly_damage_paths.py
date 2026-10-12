#!/usr/bin/env python3
"""Decompose PEEPS joint monthly-pattern damages into quantity and timing."""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_epa_fair_hultgren_quantity_damage_paths import ADAPTATION, CONVERGENCE_RELATIVE_TOLERANCE, PULSES, VALUE, adaptation_factors, country_market_damage
from build_hultgren_monthly_precip_climatology import CALENDAR_COLUMNS, MAX_MONTHS, RAIN_COLUMNS
from build_hultgren_peeps_monthly_slope_panel import SLOPE_COLUMNS
from build_hultgren_precip_basis_climatology import FEATURES, require
from build_peeps_fair_hultgren_monthly_damage_paths import KEYS, PHASES, YEARS, common_physical_support, year_offsets


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def monthly_anomaly(slopes: np.ndarray, months: np.ndarray, offsets: np.ndarray, fair: dict[int, float], harvest_year: int) -> np.ndarray:
    result = np.zeros_like(slopes)
    active = months > 0
    for relative_year in (-1, 0):
        year = harvest_year + relative_year
        days = np.asarray([calendar.monthrange(year, month)[1] for month in range(1, 13)], dtype=np.float64)
        selected = active & (offsets == relative_year)
        row, column = np.nonzero(selected)
        result[row, column] = slopes[row, column] * 86_400.0 * days[months[row, column] - 1] * fair[year]
    return result


def feature_delta(baseline: np.ndarray, anomaly: np.ndarray) -> np.ndarray:
    linear = [anomaly[:, selected].sum(axis=1) for selected in PHASES]
    squared = [(2.0 * baseline[:, selected] * anomaly[:, selected] + np.square(anomaly[:, selected])).sum(axis=1) for selected in PHASES]
    return np.column_stack(linear + squared)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joint-paths", type=Path, required=True)
    parser.add_argument("--joint-receipt", type=Path, required=True)
    parser.add_argument("--slope-panel", type=Path, required=True)
    parser.add_argument("--response-panel", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    receipt = json.loads(args.joint_receipt.read_text())
    require(receipt["schema"] == "peeps_fair_hultgren_monthly_damage_paths/v1", "joint receipt differs")
    require(receipt["output"]["sha256"] == digest(args.joint_paths), "joint path hash differs")
    for label, path in (("slope_panel", args.slope_panel), ("response_panel", args.response_panel), ("fair", args.fair)):
        require(receipt["sources"][label]["sha256"] == digest(path), f"{label} hash differs")

    slopes = pd.read_parquet(args.slope_panel)
    response = pd.read_parquet(args.response_panel).sort_values(["iso3", *KEYS]).reset_index(drop=True)
    fair_frame = pd.read_csv(args.fair)
    fair_paths = {pulse: dict(zip(part.year.astype(int), part.difference_k.astype(float), strict=True)) for pulse in PULSES for part in [fair_frame.loc[fair_frame.pulse_size_gtc.eq(pulse)].sort_values("year")]}
    cells = slopes[KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    cells["cell_id"] = np.arange(len(cells), dtype=np.int32)
    slopes = slopes.merge(cells, on=KEYS, how="left", validate="many_to_one").sort_values(["cell_id", "regime"]).reset_index(drop=True)
    response = response.merge(cells, on=KEYS, how="inner", validate="many_to_one").sort_values(["iso3", *KEYS]).reset_index(drop=True)
    cell_id = slopes.cell_id.to_numpy(dtype=np.int32)
    area = slopes.mirca_area_ha.to_numpy(dtype=np.float64)
    baseline = slopes[RAIN_COLUMNS].to_numpy(dtype=np.float64)
    slope_values = slopes[SLOPE_COLUMNS].to_numpy(dtype=np.float64)
    months = slopes[CALENDAR_COLUMNS].to_numpy(dtype=np.int16)
    offsets = year_offsets(slopes)
    valid_regime, _ = common_physical_support(baseline, slope_values, months, offsets, fair_paths)
    invalid_cells = np.unique(cell_id[~valid_regime])
    valid_cell = np.ones(len(cells), dtype=bool)
    valid_cell[invalid_cells] = False
    require(int((~valid_cell).sum()) == receipt["support"]["excluded_combined_crop_cells"], "physical support cell count differs")
    keep = valid_cell[cell_id]
    cell_id, area, baseline, slope_values, months, offsets = (array[keep] for array in (cell_id, area, baseline, slope_values, months, offsets))
    response = response.loc[valid_cell[response.cell_id.to_numpy(dtype=np.int32)]].copy().reset_index(drop=True)
    require(len(response) == receipt["support"]["response_rows"], "retained response rows differ")
    cell_area = np.bincount(cell_id, weights=area, minlength=len(cells))
    season_total = baseline.sum(axis=1)
    require(np.all(season_total > 0), "nonpositive crop-season baseline")

    response_cell = response.cell_id.to_numpy(dtype=np.int32)
    coefficients = response[[f"effective_{feature}" for feature in FEATURES]].to_numpy(dtype=np.float64)
    values = response[VALUE].to_numpy(dtype=np.float64)
    iso = response.iso3.to_numpy()
    starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
    country_value = np.add.reduceat(values, starts)
    quantity_records = []
    minimum_scale = np.inf
    for pulse in PULSES:
        for year in YEARS:
            joint_anomaly = monthly_anomaly(slope_values, months, offsets, fair_paths[pulse], int(year))
            total_anomaly = joint_anomaly.sum(axis=1)
            scale = 1.0 + total_anomaly / season_total
            minimum_scale = min(minimum_scale, float(scale.min()))
            quantity_anomaly = baseline * (total_anomaly / season_total)[:, None]
            regime_delta = feature_delta(baseline, quantity_anomaly)
            cell_delta = np.zeros((len(cells), len(FEATURES)), dtype=np.float64)
            for column in range(len(FEATURES)):
                numerator = np.bincount(cell_id, weights=area * regime_delta[:, column], minlength=len(cells))
                cell_delta[valid_cell, column] = numerator[valid_cell] / cell_area[valid_cell]
            log_response = np.sum(cell_delta[response_cell] * coefficients, axis=1)
            for adaptation in ADAPTATION:
                factor = float(adaptation_factors(np.asarray([year]), adaptation)[0])
                adapted = np.where(log_response < 0.0, log_response * factor, log_response)
                ratios = np.add.reduceat(np.exp(adapted) * values, starts) / country_value
                damage = float(country_market_damage(country_value, ratios[:, None]).sum())
                quantity_records.append({"climate_model": "PEEPS_MPI-ESM1-2-HR_ssp585", "year": int(year), "pulse_size_gtc": pulse, "adaptation": adaptation, "tail_rule": "uncapped", "quantity_reference_damage_usd_source_price_basis": damage})
    require(minimum_scale >= 0.0, "quantity-reference rainfall becomes negative")
    quantity = pd.DataFrame(quantity_records)
    keys = ["climate_model", "year", "pulse_size_gtc", "adaptation", "tail_rule"]
    joint = pd.read_parquet(args.joint_paths, columns=keys + ["damage_change_usd_source_price_basis"])
    output = joint.merge(quantity, on=keys, validate="one_to_one").rename(columns={"damage_change_usd_source_price_basis": "joint_monthly_pattern_damage_usd_source_price_basis"})
    output["timing_increment_damage_usd_source_price_basis"] = output.joint_monthly_pattern_damage_usd_source_price_basis - output.quantity_reference_damage_usd_source_price_basis
    identity_error = float(np.max(np.abs(output.joint_monthly_pattern_damage_usd_source_price_basis - output.quantity_reference_damage_usd_source_price_basis - output.timing_increment_damage_usd_source_price_basis)))
    require(identity_error == 0.0, "joint quantity timing identity differs")
    zero = output.pulse_size_gtc.eq(0.0)
    require((output.loc[zero, ["joint_monthly_pattern_damage_usd_source_price_basis", "quantity_reference_damage_usd_source_price_basis", "timing_increment_damage_usd_source_price_basis"]] == 0.0).all().all(), "zero identity differs")

    convergence = {}
    comparison_keys = ["year", "adaptation", "tail_rule"]
    for channel in ("quantity_reference_damage_usd_source_price_basis", "timing_increment_damage_usd_source_price_basis"):
        small = output.loc[output.pulse_size_gtc.eq(0.000025), comparison_keys + [channel]].rename(columns={channel: "small"})
        next_small = output.loc[output.pulse_size_gtc.eq(0.00005), comparison_keys + [channel]].rename(columns={channel: "next"})
        joined = small.merge(next_small, on=comparison_keys, validate="one_to_one")
        a, b = joined.small.to_numpy() / 0.000025, joined.next.to_numpy() / 0.00005
        convergence[channel] = float(np.max(np.abs(a - b)) / max(np.max(np.abs(a)), np.max(np.abs(b)), 1e-30))
    require(convergence["quantity_reference_damage_usd_source_price_basis"] <= CONVERGENCE_RELATIVE_TOLERANCE, "quantity convergence failed")

    output = output.sort_values(["adaptation", "pulse_size_gtc", "year"]).reset_index(drop=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    smallest = output.loc[output.pulse_size_gtc.eq(0.000025) & output.year.gt(2020)]
    summaries = smallest.groupby("adaptation")[["joint_monthly_pattern_damage_usd_source_price_basis", "quantity_reference_damage_usd_source_price_basis", "timing_increment_damage_usd_source_price_basis"]].mean().reset_index().to_dict("records")
    result = {
        "schema": "peeps_monthly_damage_decomposition/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "one_esm_joint_quantity_timing_damage_decomposition_not_paired_replacement_or_scc",
        "definition": "joint PEEPS monthly-pattern market damage decomposed into a fixed-historical-month-share quantity reference and the exact joint-minus-quantity market-level timing increment",
        "sources": {"joint_paths": {"path": str(args.joint_paths), "sha256": digest(args.joint_paths), "receipt": str(args.joint_receipt), "receipt_sha256": digest(args.joint_receipt)}, "slope_panel": {"path": str(args.slope_panel), "sha256": digest(args.slope_panel)}, "response_panel": {"path": str(args.response_panel), "sha256": digest(args.response_panel)}, "fair": {"path": str(args.fair), "sha256": digest(args.fair)}},
        "support": {"rows": len(output), "physical_common_support_inherited": True, "response_rows": len(response), "countries": int(response.iso3.nunique())},
        "validation": {"minimum_quantity_reference_proportional_rainfall_scale": minimum_scale, "maximum_absolute_decomposition_identity_error_usd": identity_error, "shrinking_pulse_relative_tolerance": CONVERGENCE_RELATIVE_TOLERANCE, "convergence": convergence},
        "smallest_pulse_mean_annual_damage_usd_source_price_basis": summaries,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "limitations": ["The timing increment is joint market damage minus the same-pattern quantity reference; it is not a separately additive damage function.", "One ESM/scenario and maize only.", "Monthly patterns omit daily drought, persistence, and extremes.", "No currency conversion, discounting, or paired GIVE replacement is performed here."],
        "claim_gates": {"matched_quantity_reference": True, "timing_increment_damage": True, "paired_agriculture_replacement": False, "scc": False},
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "validation": result["validation"], "summaries": summaries, "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
