#!/usr/bin/env python3
"""Build an outcome-blind U.S. rainfed-maize SPEI scenario exposure benchmark."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import tomllib

import h5py
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from build_spei_tile_crop_features import spans  # noqa: E402
from spei_crop_window_metrics import window_metrics  # noqa: E402
from summarize_isimip3b_late_drought_crop_windows import frozen_support, sources  # noqa: E402


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_contract(contract: dict) -> None:
    auth = contract["authorization"]
    require(not auth["read_crop_outcomes"] and not auth["fit_crop_outcomes"], "outcome access must remain closed")
    require(not auth["bridge_to_nass_response"] and not auth["future_yield_projection"], "response bridge must remain closed")
    require(not auth["causal_attribution"] and not auth["damage_calculation"] and not auth["scc_calculation"], "downstream gates must remain closed")
    require(contract["method"]["direct_rainfall_relationship"] == "competing_family_never_stacked_or_added", "moisture-family rule changed")


def load_contract(path: Path) -> dict:
    contract = tomllib.loads(path.read_text())
    validate_contract(contract)
    return contract


def us_support(contract: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict, list[dict]]:
    paths = contract["sources"]
    proxy_path = ROOT / paths["country_proxy"]
    receipt_path = ROOT / paths["country_proxy_receipt"]
    receipt = json.loads(receipt_path.read_text())
    require(receipt["output"]["sha256"] == digest(proxy_path), "country proxy hash changed")
    support = frozen_support()
    target = contract["estimand"]
    support = support.loc[support.crop.eq(target["crop"])].copy()
    proxy = pd.read_parquet(proxy_path)
    require(not proxy.duplicated(["lat", "lon_360"]).any(), "country proxy coordinates duplicated")
    support = support.merge(proxy, on=["lat", "lon_360"], how="left", validate="many_to_one")
    support = support.loc[
        support.country_label.eq(target["country_label"])
        & support.country_count.eq(target["country_count"])
    ].sort_values("cell_id").reset_index(drop=True)
    require(not support.empty and not support.duplicated(["crop", "cell_id"]).any(), "U.S. support is empty or duplicated")
    calendars, weights, bindings = sources()
    weights = weights.loc[
        weights.crop.eq(target["crop"]) & weights.irrigation.eq(target["irrigation"])
    ].copy()
    support = support.merge(weights, on=["crop", "lat", "lon_360"], how="left", validate="one_to_one")
    require(support.rainfed_area_ha.notna().all(), "U.S. support lacks rainfed weights")
    support = support.loc[support.rainfed_area_ha.gt(0)].copy()
    require(support.noirr_calendar_valid.all(), "positive-area U.S. cell has invalid rainfed calendar")
    minimum = contract["minimum_support"]
    require(len(support) >= minimum["positive_rainfed_cells"], "U.S. cell support below frozen floor")
    require(float(support.rainfed_area_ha.sum()) >= minimum["rainfed_area_ha"], "U.S. rainfed area below frozen floor")
    return support, weights, calendars, bindings


def aggregate_case(cube: Path, support: pd.DataFrame, calendars: dict, contract: dict) -> list[dict]:
    target = contract["estimand"]
    years = tuple(target["harvest_years"])
    windows = tuple(target["windows"])
    scales = tuple(target["scales_months"])
    with h5py.File(cube, "r") as handle:
        months = pd.DatetimeIndex(handle["month"][:].astype("datetime64[ns]"))
        require(tuple(int(v) for v in handle["scale"][:]) == scales, "SPEI scale axis changed")
        require(months.equals(pd.date_range("2091-01-01", "2100-12-01", freq="MS")), "future month axis changed")
        ids = support.cell_id.to_numpy(dtype=int)
        require(np.all(np.diff(ids) > 0), "cell IDs must be strictly increasing")
        require(np.array_equal(support.lat.to_numpy(), handle["latitude"][:][ids]), "support latitude mapping changed")
        require(np.array_equal(support.lon_360.to_numpy(), np.mod(handle["longitude"][:], 360)[ids]), "support longitude mapping changed")
        values = handle["spei"][:, :, ids]
        clips = handle["cdf_clip_code"][:, :, ids]
    month_lookup = {(month.year, month.month): index for index, month in enumerate(months)}
    calendar = calendars[(target["crop"], target["irrigation"])]
    accumulators = defaultdict(lambda: {"area": 0.0, "weighted": 0.0, "clipped": 0.0, "cells": 0})
    for local, row in enumerate(support.itertuples(index=False)):
        area = float(row.rainfed_area_ha)
        i, j = calendar["lat"][row.lat], calendar["lon"][row.lon_360]
        for year in years:
            intervals = spans(year, calendar["plant"][i, j], calendar["maturity"][i, j])
            for window in windows:
                for scale_index, scale in enumerate(scales):
                    metric = window_metrics(values[scale_index, :, local], clips[scale_index, :, local], month_lookup, *intervals[window])
                    require(metric["status"] == "complete", "incomplete U.S. crop-window metric")
                    item = accumulators[(year, window, scale)]
                    item["area"] += area
                    item["weighted"] += area * metric["spei_mean"]
                    item["clipped"] += area * bool(metric["tail_clipped_months"])
                    item["cells"] += 1
    records = []
    declared = float(support.rainfed_area_ha.sum())
    for (year, window, scale), item in sorted(accumulators.items()):
        records.append({
            "harvest_year": year, "window": window, "scale_months": scale,
            "rainfed_area_ha": item["area"], "complete_area_fraction": item["area"] / declared,
            "positive_cells": item["cells"], "area_weighted_mean_spei": item["weighted"] / item["area"],
            "tail_clipped_area_fraction": item["clipped"] / item["area"],
        })
    require(len(records) == len(years) * len(windows) * len(scales), "case factorial incomplete")
    return records


def derive_summaries(annual_records: list[dict], contract: dict) -> tuple[list[dict], list[dict], list[dict]]:
    target = contract["estimand"]
    by_case = defaultdict(list)
    for record in annual_records:
        key = (record["model"], record["scenario"], record["window"], record["scale_months"])
        by_case[key].append(record)
    case_means = []
    lookup = {}
    for key, records in sorted(by_case.items()):
        require(len(records) == len(target["harvest_years"]), "case lacks frozen harvest years")
        weight = math.fsum(r["rainfed_area_ha"] for r in records)
        mean = math.fsum(r["rainfed_area_ha"] * r["area_weighted_mean_spei"] for r in records) / weight
        lookup[key] = mean
        case_means.append({"model": key[0], "scenario": key[1], "window": key[2], "scale_months": key[3],
                           "area_year_weighted_mean_spei": mean,
                           "annual_min_spei": min(r["area_weighted_mean_spei"] for r in records),
                           "annual_max_spei": max(r["area_weighted_mean_spei"] for r in records)})
    contrasts = []
    pairs = (("ssp370_minus_ssp126", "ssp370"), ("ssp585_minus_ssp126", "ssp585"))
    for label, higher in pairs:
        for model in target["models"]:
            for window in target["windows"]:
                for scale in target["scales_months"]:
                    value = lookup[(model, higher, window, scale)] - lookup[(model, target["reference_scenario"], window, scale)]
                    contrasts.append({"contrast": label, "model": model, "window": window, "scale_months": scale,
                                      "spei_difference": value})
    grouped = defaultdict(list)
    for record in contrasts:
        grouped[(record["contrast"], record["window"], record["scale_months"])].append((record["model"], record["spei_difference"]))
    ensemble = []
    for key, rows in sorted(grouped.items()):
        rows = sorted(rows); values = [value for _, value in rows]
        require([model for model, _ in rows] == sorted(target["models"]), "ensemble model set changed")
        ensemble.append({"contrast": key[0], "window": key[1], "scale_months": key[2],
                         "named_model_spei_differences": dict(rows), "equal_model_mean": statistics.fmean(values),
                         "median": statistics.median(values), "minimum": min(values), "maximum": max(values),
                         "population_sd": statistics.pstdev(values), "negative_models": sum(v < 0 for v in values),
                         "positive_models": sum(v > 0 for v in values), "zero_models": sum(v == 0 for v in values)})
    return case_means, contrasts, ensemble


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/us_future_spei_exposure_v1.toml")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh output required")
    contract = load_contract(config_path)
    support, _, calendars, bindings = us_support(contract)
    target = contract["estimand"]
    pair_root = ROOT / contract["sources"]["pair_root"]
    annual_records = []
    upstream = []
    for model in target["models"]:
        for scenario in target["scenarios"]:
            directory = pair_root / f"{model}_{scenario}"
            result_path, validation_path = directory / "result.json", directory / "validation.json"
            result, validation = json.loads(result_path.read_text()), json.loads(validation_path.read_text())
            require(validation["status"] == "passed" and validation["pair_result_sha256"] == digest(result_path), "upstream pair validation failed")
            cube = ROOT / result["output"]["path"]
            require(digest(cube) == result["output"]["sha256"] == validation["output_sha256"], "upstream cube hash changed")
            records = aggregate_case(cube, support, calendars, contract)
            for record in records:
                record.update(model=model, scenario=scenario)
            annual_records.extend(records)
            upstream.append({"model": model, "scenario": scenario, "result": str(result_path.relative_to(ROOT)),
                             "result_sha256": digest(result_path), "validation": str(validation_path.relative_to(ROOT)),
                             "validation_sha256": digest(validation_path), "cube": str(cube.relative_to(ROOT)),
                             "cube_sha256": digest(cube)})
    require(len(upstream) == contract["minimum_support"]["required_validated_cases"], "upstream case count changed")
    case_means, contrasts, ensemble = derive_summaries(annual_records, contract)
    bridge = contract["bridge_gates"]
    bridge_passed = all(value for key, value in bridge.items() if key != "all_required_before_response_composition")
    require(not bridge_passed, "bridge unexpectedly opened; separate review required")
    result = {
        "schema": "us_future_spei_exposure_v1", "status": "validated_upstream_us_aggregation_pending_independent_validation",
        "role": "outcome_blind_us_rainfed_maize_scenario_exposure_not_nass_yield_projection",
        "contract": {"path": str(config_path.relative_to(ROOT)), "sha256": digest(config_path)},
        "support": {"positive_rainfed_cells": len(support), "rainfed_area_ha": float(support.rainfed_area_ha.sum()),
                    "latitude_range": [float(support.lat.min()), float(support.lat.max())],
                    "longitude_360_range": [float(support.lon_360.min()), float(support.lon_360.max())]},
        "upstream": upstream, "source_bindings": bindings, "annual_records": annual_records,
        "case_means": case_means, "named_model_contrasts": contrasts, "ensemble_summaries": ensemble,
        "primary": next(r for r in ensemble if r["contrast"] == "ssp585_minus_ssp126" and r["window"] == target["primary_window"] and r["scale_months"] == target["primary_scale_months"]),
        "gates": {"stage1_scenario_exposure": False, "independent_validation": False,
                  "bridge_to_nass_response": False, "future_yield_projection": False,
                  "causal_attribution": False, "damage": False, "scc": False},
        "bridge_blockers": [key for key, value in bridge.items() if key != "all_required_before_response_composition" and not value],
        "interpretation": ["Named-model spread is retained and is not a confidence interval or probability distribution.",
                           "SSP contrasts include internal variability and multiple forcings; they are scenario exposures, not causal attribution.",
                           "SPEI is a competing moisture family and must not be added to direct-rainfall effects."],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + ".partial")
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    partial.replace(output)
    print(json.dumps({"status": result["status"], "support": result["support"], "primary": result["primary"]}))


if __name__ == "__main__":
    main()
