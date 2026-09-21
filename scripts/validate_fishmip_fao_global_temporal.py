#!/usr/bin/env python3
"""Independent h5netcdf/csv reconstruction of FishMIP--FAO diagnostics."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import tomllib

import h5netcdf
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FAO = ROOT / "data/derived/fao/fishstat_capture_wide_1950_2024.csv"
CONTRACT = ROOT / "data/provenance/fao_fishstat_capture_headless_export_v1.toml"
PATHS = {
    "gfdl-esm4/boats": ROOT / "data/raw/fishmip/gfdl-esm4/boats/boats_gfdl-esm4_nobasd_historical_histsoc_default_tc_global_monthly_1950_2014.nc",
    "gfdl-esm4/ecoocean": ROOT / "data/raw/fishmip/gfdl-esm4/ecoocean/ecoocean_gfdl-esm4_nobasd_historical_histsoc_default_tc_global_monthly_1950_2014.nc",
    "ipsl-cm6a-lr/boats": ROOT / "data/raw/fishmip/ipsl-cm6a-lr/boats/boats_ipsl-cm6a-lr_nobasd_historical_histsoc_default_tc_global_monthly_1950_2014.nc",
    "ipsl-cm6a-lr/ecoocean": ROOT / "data/raw/fishmip/ipsl-cm6a-lr/ecoocean/ecoocean_ipsl-cm6a-lr_nobasd_historical_histsoc_default_tc_global_monthly_1950_2014.nc",
}
YEARS = np.arange(1950, 2015, dtype=int)
PERIODS = ((1950, 2014), (1980, 2014))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def close(actual: float, expected: float, label: str, tolerance: float = 2e-12) -> None:
    scale = max(1.0, abs(actual), abs(expected))
    if not math.isfinite(actual) or not math.isfinite(expected) or abs(actual - expected) > tolerance * scale:
        raise ValueError(f"temporal diagnostic mismatch {label}: {actual} != {expected}")


def correlation(x: np.ndarray, y: np.ndarray) -> float:
    xc, yc = x - x.mean(), y - y.mean()
    return float(np.sum(xc * yc) / math.sqrt(float(np.sum(xc**2) * np.sum(yc**2))))


def slope(x: np.ndarray, y: np.ndarray) -> float:
    xc = x.astype(float) - x.mean()
    return float(np.sum(xc * (y - y.mean())) / np.sum(xc**2))


def calculate_metrics(years: np.ndarray, observed: np.ndarray, modeled: np.ndarray) -> dict[str, float | int]:
    difference = modeled - observed
    d_observed, d_modeled = observed[1:] - observed[:-1], modeled[1:] - modeled[:-1]
    return {
        "years": len(years),
        "level_pearson": correlation(observed, modeled),
        "level_mean_bias": float(np.mean(difference)),
        "level_rmse": float(math.sqrt(float(np.mean(difference**2)))),
        "level_log_rmse": float(math.sqrt(float(np.mean((np.log(modeled) - np.log(observed))**2)))),
        "first_difference_pearson": correlation(d_observed, d_modeled),
        "first_difference_rmse": float(math.sqrt(float(np.mean((d_modeled - d_observed)**2)))),
        "first_difference_sign_agreement": float(np.mean(np.sign(d_modeled) == np.sign(d_observed))),
        "observed_normalized_slope_per_year": slope(years, observed),
        "modeled_normalized_slope_per_year": slope(years, modeled),
    }


def observed() -> np.ndarray:
    contract = tomllib.loads(CONTRACT.read_text())
    totals = np.zeros(len(YEARS), dtype=float)
    with FAO.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["environment_class"] != "marine" or row["measure_code"] != "Q_tlw":
                continue
            for index, year in enumerate(YEARS):
                value = float(row[f"value_{year}"])
                if value > 0:
                    totals[index] += value
                if row[f"status_{year}"] not in contract["export"]["required_status_codes"]:
                    raise ValueError("unknown FAO status in independent audit")
    return totals


def support_and_latitude() -> tuple[np.ndarray, np.ndarray]:
    support = None
    latitude = None
    for path in PATHS.values():
        with h5netcdf.File(path, "r") as source:
            current_latitude = np.asarray(source.variables["lat"][:], dtype=float)
            first = np.asarray(source.variables["tc"][0, :, :], dtype=float)
        current = np.isfinite(first) & (first < 1e19)
        if support is None:
            support, latitude = current, current_latitude
        else:
            if not np.array_equal(latitude, current_latitude):
                raise ValueError("independent FishMIP latitude mismatch")
            support &= current
    assert support is not None and latitude is not None
    return support, latitude


def annual(path: Path, support: np.ndarray, latitude: np.ndarray) -> np.ndarray:
    weight = np.where(support, np.cos(np.deg2rad(latitude))[:, None], 0.0)
    denominator = float(np.sum(weight))
    output = []
    with h5netcdf.File(path, "r") as source:
        variable = source.variables["tc"]
        if variable.shape != (780, 180, 360):
            raise ValueError("independent FishMIP shape mismatch")
        for index in range(len(YEARS)):
            block = np.asarray(variable[index * 12:index * 12 + 12, :, :], dtype=float)
            if not np.isfinite(block[:, support]).all() or np.any(block[:, support] < 0) or np.any(block[:, support] >= 1e19):
                raise ValueError("independent FishMIP support mismatch")
            monthly = np.sum(np.where(support[None, :, :], block, 0.0) * weight, axis=(1, 2)) / denominator
            output.append(float(np.sum(monthly) / 12))
    return np.asarray(output)


def normalize(values: np.ndarray) -> tuple[np.ndarray, float]:
    reference = float(np.sum(values[-10:]) / 10)
    return values / reference, reference


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source, out = args.input.resolve(), args.out.resolve()
    if (not source.is_file() or not source.is_relative_to(ROOT / "data/interim") or
            out.exists() or not out.is_relative_to(ROOT / "data/interim")):
        raise ValueError("valid ignored diagnostic and fresh ignored audit output required")
    reported = json.loads(source.read_text())
    if (reported["status"] != "fishmip_fao_global_historical_temporal_diagnostic_not_calibration_or_scc" or
            reported["fishstat_gui_menu_export_reconciled"] is not False or
            reported["model_selected_or_weighted"] is not False or reported["scc_estimated"] is not False):
        raise ValueError("reported temporal diagnostic identity invalid")
    observed_raw = observed()
    observed_index, observed_reference = normalize(observed_raw)
    support, latitude = support_and_latitude()
    close(reported["observed_reference_2005_2014_tonnes"], observed_reference, "observed reference")
    if reported["common_finite_grid_cells"] != int(np.sum(support)):
        raise ValueError("common support count differs")
    checks = 2
    annual_rows = {int(row["year"]): row for row in reported["annual"]}
    if set(annual_rows) != set(map(int, YEARS)):
        raise ValueError("reported annual support differs")
    for index, year in enumerate(YEARS):
        close(annual_rows[int(year)]["observed_tonnes"], observed_raw[index], f"observed tonnes/{year}")
        close(annual_rows[int(year)]["observed_normalized"], observed_index[index], f"observed index/{year}")
        checks += 2
    reported_paths = {row["path_id"]: row for row in reported["paths"]}
    if set(reported_paths) != set(PATHS):
        raise ValueError("reported path support differs")
    for identifier, path in PATHS.items():
        raw = annual(path, support, latitude)
        modeled, reference = normalize(raw)
        row = reported_paths[identifier]
        close(row["reference_2005_2014_mean_density"], reference, f"reference/{identifier}")
        checks += 1
        comparison = {(item["start_year"], item["end_year"]): item for item in row["comparisons"]}
        for start, end in PERIODS:
            mask = (YEARS >= start) & (YEARS <= end)
            expected = calculate_metrics(YEARS[mask], observed_index[mask], modeled[mask])
            actual = comparison[(start, end)]
            for field, value in expected.items():
                if field == "years":
                    if actual[field] != value:
                        raise ValueError("metric year count differs")
                else:
                    close(actual[field], value, f"{identifier}/{start}/{field}")
                checks += 1
        for index, year in enumerate(YEARS):
            close(annual_rows[int(year)][f"{identifier}_mean_density"], raw[index], f"density/{identifier}/{year}")
            close(annual_rows[int(year)][f"{identifier}_normalized"], modeled[index], f"index/{identifier}/{year}")
            checks += 2
    outcome = {
        "status": "fishmip_fao_global_historical_temporal_diagnostic_independently_validated",
        "checks": checks,
        "diagnostic_sha256": sha(source),
        "validator_sha256": sha(Path(__file__)),
        "common_finite_grid_cells": int(np.sum(support)),
        "model_selected_or_weighted": False,
        "climate_attribution_estimated": False,
        "welfare_or_damage_estimated": False,
        "scc_estimated": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps(outcome))


if __name__ == "__main__":
    main()
