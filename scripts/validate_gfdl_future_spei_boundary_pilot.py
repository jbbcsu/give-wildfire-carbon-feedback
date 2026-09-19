#!/usr/bin/env python3
"""Independent saved-array and aggregate audit for the GFDL SPEI pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("ssp126", "ssp370", "ssp585")
SCALES = (1, 3, 6)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def close(a: float, b: float, tolerance: float = 1e-13) -> bool:
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_result = json.loads((args.input_dir / "result.json").read_text())
    if source_result["status"] != "completed_pending_independent_validation":
        raise ValueError("builder result status changed")
    path = ROOT / source_result["output"]["path"]
    if path.stat().st_size != source_result["output"]["bytes"] or sha256(path) != source_result["output"]["sha256"]:
        raise ValueError("saved output identity changed")
    checks = 0
    maximum_summary_error = 0.0
    with xr.open_dataset(path, engine="h5netcdf", cache=False) as dataset:
        if tuple(dataset.scenario.values.astype(str)) != SCENARIOS or tuple(dataset.scale.values.tolist()) != SCALES:
            raise ValueError("scenario/scale coordinates changed")
        months = pd.DatetimeIndex(dataset.month.values)
        if not months.equals(pd.date_range("2011-01-01", "2020-12-01", freq="MS")):
            raise ValueError("month coordinate changed")
        expected_shapes = {
            "precipitation_mm": (3, 120, 512), "et0_hargreaves_mm": (3, 120, 512),
            "water_balance_mm": (3, 120, 512),
            "accumulated_water_balance_mm": (3, 3, 120, 512),
            "glo_cdf_probability": (3, 3, 120, 512), "spei": (3, 3, 120, 512),
            "cdf_clip_code": (3, 3, 120, 512),
        }
        for name, shape in expected_shapes.items():
            if dataset[name].shape != shape:
                raise ValueError(f"{name} shape changed")
            checks += 1
        for attribute, value in dataset.attrs.items():
            if attribute.startswith("gate_") and value != "false":
                raise ValueError(f"scientific-use gate opened: {attribute}")
        precipitation = dataset.precipitation_mm.values
        et0 = dataset.et0_hargreaves_mm.values
        balance = dataset.water_balance_mm.values
        accumulated = dataset.accumulated_water_balance_mm.values
        probability = dataset.glo_cdf_probability.values
        spei = dataset.spei.values
        clip = dataset.cdf_clip_code.values
        if not np.allclose(balance, precipitation - et0, rtol=0, atol=2e-13, equal_nan=True):
            raise ValueError("saved water balance does not reconcile")
        checks += int(balance.size)
        for values in (precipitation, et0, balance):
            if not np.array_equal(values[0, :48], values[1, :48], equal_nan=True) or not np.array_equal(values[0, :48], values[2, :48], equal_nan=True):
                raise ValueError("historical monthly identity failed")
            checks += int(values[0, :48].size * 2)
        for values in (accumulated, probability, spei, clip):
            if not np.array_equal(values[0, :, :48], values[1, :, :48], equal_nan=True) or not np.array_equal(values[0, :, :48], values[2, :, :48], equal_nan=True):
                raise ValueError("historical transformed identity failed")
            checks += int(values[0, :, :48].size * 2)
        for scale_index, scale in enumerate(SCALES):
            missing = ~np.isfinite(spei[:, scale_index])
            expected = np.zeros(missing.shape, dtype=bool)
            expected[:, : scale - 1] = True
            if not np.array_equal(missing, expected):
                raise ValueError(f"unexpected SPEI missingness for scale {scale}")
            if not np.array_equal(np.isnan(accumulated[:, scale_index]), expected):
                raise ValueError(f"unexpected accumulation missingness for scale {scale}")
            checks += int(missing.size * 2)
        finite_probability = np.isfinite(probability)
        if ((probability[finite_probability] < 0) | (probability[finite_probability] > 1)).any():
            raise ValueError("CDF probability outside [0,1]")
        if not set(np.unique(clip)).issubset({-9, -1, 0, 1}):
            raise ValueError("clip code outside registry")
        checks += int(finite_probability.sum() + clip.size)
        expected_summary = {(x["scenario"], x["scale_months"]): x for x in source_result["summaries_2015_2020"]}
        if len(expected_summary) != 9:
            raise ValueError("summary registry changed")
        future = months.year >= 2015
        for scenario_index, scenario in enumerate(SCENARIOS):
            for scale_index, scale in enumerate(SCALES):
                values = spei[scenario_index, scale_index, future]
                finite = np.isfinite(values)
                current = {
                    "cell_months": int(values.size), "finite": int(finite.sum()),
                    "mean_spei": float(np.mean(values[finite])),
                    "fraction_le_minus_1": float(np.mean(values[finite] <= -1)),
                    "fraction_le_minus_1_5": float(np.mean(values[finite] <= -1.5)),
                    "lower_tail_clips": int(np.count_nonzero(clip[scenario_index, scale_index, future] == -1)),
                    "upper_tail_clips": int(np.count_nonzero(clip[scenario_index, scale_index, future] == 1)),
                }
                saved = expected_summary[(scenario, scale)]
                for field, value in current.items():
                    if isinstance(value, float):
                        error = abs(value - saved[field])
                        maximum_summary_error = max(maximum_summary_error, error)
                        if not close(value, saved[field]):
                            raise ValueError(f"summary mismatch: {scenario}/{scale}/{field}")
                    elif value != saved[field]:
                        raise ValueError(f"summary count mismatch: {scenario}/{scale}/{field}")
                    checks += 1
    result = {
        "schema": "gfdl_future_spei_boundary_pilot_validation_v1",
        "status": "passed",
        "input_result_sha256": sha256(args.input_dir / "result.json"),
        "output_sha256": sha256(path),
        "checks": checks,
        "maximum_summary_absolute_error": maximum_summary_error,
        "historical_identity": True,
        "post_warmup_missing_values": 0,
        "gates_confirmed_false": ["response", "causal", "damage", "scc"],
        "limitation": "Independent saved-array and aggregate validation; not an independent climate source or drought-impact estimate.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
