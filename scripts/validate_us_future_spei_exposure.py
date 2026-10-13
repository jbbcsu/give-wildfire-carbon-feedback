#!/usr/bin/env python3
"""Independently recompute the U.S. future-SPEI aggregation and uncertainty ledger."""
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


class Kahan:
    def __init__(self) -> None:
        self.total = 0.0
        self.correction = 0.0

    def add(self, value: float) -> None:
        adjusted = value - self.correction
        updated = self.total + adjusted
        self.correction = (updated - self.total) - adjusted
        self.total = updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.result if args.result.is_absolute() else ROOT / args.result
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh validation output required")
    saved = json.loads(result_path.read_text())
    require(saved["status"] == "validated_upstream_us_aggregation_pending_independent_validation", "input status changed")
    config_path = ROOT / saved["contract"]["path"]
    require(digest(config_path) == saved["contract"]["sha256"], "contract binding changed")
    contract = tomllib.loads(config_path.read_text())
    auth = contract["authorization"]
    require(not any(auth[k] for k in ("read_crop_outcomes", "fit_crop_outcomes", "bridge_to_nass_response",
                                      "future_yield_projection", "causal_attribution", "damage_calculation", "scc_calculation")),
            "a closed authorization gate opened")
    target = contract["estimand"]
    proxy_path = ROOT / contract["sources"]["country_proxy"]
    proxy_receipt = json.loads((ROOT / contract["sources"]["country_proxy_receipt"]).read_text())
    require(proxy_receipt["output"]["sha256"] == digest(proxy_path), "country proxy binding changed")
    proxy = pd.read_parquet(proxy_path)
    support = frozen_support().loc[lambda x: x.crop.eq(target["crop"])].merge(
        proxy, on=["lat", "lon_360"], how="left", validate="many_to_one"
    )
    support = support.loc[
        support.country_label.eq(target["country_label"]) & support.country_count.eq(target["country_count"])
    ].copy()
    calendars, weights, _ = sources()
    weights = weights.loc[weights.crop.eq(target["crop"]) & weights.irrigation.eq(target["irrigation"])]
    support = support.merge(weights, on=["crop", "lat", "lon_360"], validate="one_to_one")
    support = support.loc[support.rainfed_area_ha.gt(0)].sort_values("cell_id").reset_index(drop=True)
    require(len(support) == saved["support"]["positive_rainfed_cells"], "saved cell count differs")
    require(math.isclose(float(support.rainfed_area_ha.sum()), saved["support"]["rainfed_area_ha"], rel_tol=0, abs_tol=1e-7), "saved area differs")
    observed = {(r["model"], r["scenario"], r["harvest_year"], r["window"], r["scale_months"]): r for r in saved["annual_records"]}
    require(len(observed) == len(saved["annual_records"]) == 1800, "annual-record factorial changed")
    audit = {}
    upstream = {(r["model"], r["scenario"]): r for r in saved["upstream"]}
    calendar = calendars[(target["crop"], target["irrigation"])]
    ids = support.cell_id.to_numpy(dtype=int)
    for model in target["models"]:
        for scenario in target["scenarios"]:
            source = upstream[(model, scenario)]
            result_source = ROOT / source["result"]
            validation_source = ROOT / source["validation"]
            require(digest(result_source) == source["result_sha256"] and digest(validation_source) == source["validation_sha256"], "saved upstream receipt hash differs")
            validation = json.loads(validation_source.read_text())
            require(validation["status"] == "passed" and validation["pair_result_sha256"] == source["result_sha256"], "upstream validation chain failed")
            cube = ROOT / source["cube"]
            require(digest(cube) == source["cube_sha256"] == validation["output_sha256"], "upstream cube changed")
            with h5py.File(cube, "r") as handle:
                months = pd.DatetimeIndex(handle["month"][:].astype("datetime64[ns]"))
                require(tuple(int(v) for v in handle["scale"][:]) == tuple(target["scales_months"]), "scale axis changed")
                require(np.array_equal(support.lat.to_numpy(), handle["latitude"][:][ids]), "latitude mapping differs")
                require(np.array_equal(support.lon_360.to_numpy(), np.mod(handle["longitude"][:], 360)[ids]), "longitude mapping differs")
                values = handle["spei"][:, :, ids]
                clips = handle["cdf_clip_code"][:, :, ids]
            month_lookup = {(month.year, month.month): index for index, month in enumerate(months)}
            accumulators = defaultdict(lambda: {"area": Kahan(), "weighted": Kahan(), "clipped": Kahan(), "cells": 0})
            for local, row in enumerate(support.itertuples(index=False)):
                area = float(row.rainfed_area_ha)
                i, j = calendar["lat"][row.lat], calendar["lon"][row.lon_360]
                for year in target["harvest_years"]:
                    intervals = spans(year, calendar["plant"][i, j], calendar["maturity"][i, j])
                    for scale_index, scale in enumerate(target["scales_months"]):
                        for window in target["windows"]:
                            metric = window_metrics(values[scale_index, :, local], clips[scale_index, :, local], month_lookup, *intervals[window])
                            require(metric["status"] == "complete", "independent crop-window metric incomplete")
                            item = accumulators[(year, window, scale)]
                            item["area"].add(area); item["weighted"].add(area * metric["spei_mean"])
                            item["clipped"].add(area * bool(metric["tail_clipped_months"])); item["cells"] += 1
            for (year, window, scale), item in accumulators.items():
                area = item["area"].total
                audit[(model, scenario, year, window, scale)] = {
                    "rainfed_area_ha": area, "complete_area_fraction": 1.0, "positive_cells": item["cells"],
                    "area_weighted_mean_spei": item["weighted"].total / area,
                    "tail_clipped_area_fraction": item["clipped"].total / area,
                }
    require(set(audit) == set(observed), "independent annual keys differ")
    maximum = 0.0; checks = 0
    for key, expected in audit.items():
        record = observed[key]
        for name in ("rainfed_area_ha", "complete_area_fraction", "area_weighted_mean_spei", "tail_clipped_area_fraction"):
            difference = abs(float(record[name]) - float(expected[name])); maximum = max(maximum, difference)
            require(math.isclose(float(record[name]), float(expected[name]), rel_tol=3e-12, abs_tol=2e-7), f"annual aggregate differs: {key} {name}")
            checks += 1
        require(record["positive_cells"] == expected["positive_cells"], "annual cell count differs"); checks += 1
    # Reconstruct every named-model and ensemble contrast from independently recomputed annual values.
    case = defaultdict(list)
    for (model, scenario, year, window, scale), value in audit.items():
        case[(model, scenario, window, scale)].append(value["area_weighted_mean_spei"])
    means = {key: statistics.fmean(values) for key, values in case.items()}
    saved_contrasts = {(r["contrast"], r["model"], r["window"], r["scale_months"]): r["spei_difference"] for r in saved["named_model_contrasts"]}
    saved_ensemble = {(r["contrast"], r["window"], r["scale_months"]): r for r in saved["ensemble_summaries"]}
    for label, higher in (("ssp370_minus_ssp126", "ssp370"), ("ssp585_minus_ssp126", "ssp585")):
        for window in target["windows"]:
            for scale in target["scales_months"]:
                values = []
                for model in target["models"]:
                    value = means[(model, higher, window, scale)] - means[(model, target["reference_scenario"], window, scale)]
                    require(math.isclose(value, saved_contrasts[(label, model, window, scale)], rel_tol=0, abs_tol=2e-12), "named-model contrast differs")
                    values.append(value); checks += 1
                record = saved_ensemble[(label, window, scale)]
                derived = {"equal_model_mean": statistics.fmean(values), "median": statistics.median(values),
                           "minimum": min(values), "maximum": max(values), "population_sd": statistics.pstdev(values)}
                for name, value in derived.items():
                    require(math.isclose(value, record[name], rel_tol=0, abs_tol=2e-12), f"ensemble {name} differs")
                    checks += 1
                require(record["negative_models"] == sum(v < 0 for v in values) and record["positive_models"] == sum(v > 0 for v in values), "ensemble signs differ")
                checks += 2
    validation_result = {
        "schema": "us_future_spei_exposure_validation_v1", "status": "passed",
        "result_sha256": digest(result_path), "validated_cases": len(upstream),
        "annual_records_recomputed": len(audit), "checks": checks,
        "maximum_numeric_absolute_difference": maximum,
        "support": saved["support"],
        "gates": {"stage1_scenario_exposure": True, "bridge_to_nass_response": False,
                  "future_yield_projection": False, "causal_attribution": False, "damage": False, "scc": False},
        "bridge_blockers": saved["bridge_blockers"],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + ".partial")
    partial.write_text(json.dumps(validation_result, indent=2, sort_keys=True) + "\n")
    partial.replace(output)
    print(json.dumps(validation_result))


if __name__ == "__main__":
    main()
