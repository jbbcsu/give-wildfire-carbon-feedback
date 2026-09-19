#!/usr/bin/env python3
"""Apply frozen observational SPEI parameters to a bounded GFDL boundary."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
import xarray as xr

import build_spei_grid_chunk as engine
from spei_daily_stream import MonthlyAccumulator
from spei_distribution import GloParameters, standardize_glo
from spei_monthly_engine import _strict_rolling_sum


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("ssp126", "ssp370", "ssp585")
VARIABLES = ("pr", "tasmin", "tasmax")
SCALES = (1, 3, 6)
FIT = ROOT / "data/interim/spei_sparse_fit_block_20260908/spei.nc"
PROTOCOL = ROOT / "GFDL_FUTURE_SPEI_BOUNDARY_PILOT_PROTOCOL_20260919.md"
TOLERANCE_K = 0.00005


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def registered_sources() -> dict[tuple[str, str], dict]:
    boundary = tomllib.loads((ROOT / "data/provenance/isimip3b_gfdl_historical_ssp126_boundary.toml").read_text())
    matrix = tomllib.loads((ROOT / "data/provenance/isimip3b_gfdl_scenario_matrix.toml").read_text())
    extrema = tomllib.loads((ROOT / "data/provenance/isimip3b_gfdl_temperature_extrema.toml").read_text())
    records: dict[tuple[str, str], dict] = {}
    for item in boundary["variable"]:
        if item["name"] == "pr":
            records[("historical", "pr")] = {
                "name": item["historical_file_name"], "bytes": item["historical_bytes"],
                "sha512": item["historical_sha512"],
            }
    for item in matrix["future_cell"]:
        if item["variable"] == "pr":
            records[(item["scenario"], "pr")] = {
                "name": item["file_name"], "bytes": item["bytes"], "sha512": item["sha512"]
            }
    for item in extrema["extreme_cell"]:
        records[(item["scenario"], item["variable"])] = {
            "name": item["file_name"], "bytes": item["bytes"], "sha512": item["sha512"]
        }
    expected = {(scenario, variable) for scenario in ("historical", *SCENARIOS) for variable in VARIABLES}
    if set(records) != expected:
        raise ValueError("registered GFDL source matrix differs")
    return records


def locate_source(record: dict) -> Path:
    matches = list((ROOT / "data/raw/isimip3b/gfdl-esm4").rglob(record["name"]))
    if len(matches) != 1:
        raise ValueError(f"expected one resident source named {record['name']}")
    return matches[0]


def verify_sources(records: dict[tuple[str, str], dict]) -> list[dict]:
    verified = []
    for key in sorted(records):
        record = records[key]
        path = locate_source(record)
        if path.stat().st_size != record["bytes"]:
            raise ValueError(f"source byte count changed: {path}")
        actual = digest(path, "sha512")
        if actual != record["sha512"]:
            raise ValueError(f"source SHA-512 changed: {path}")
        verified.append({
            "scenario": key[0], "variable": key[1], "path": str(path.relative_to(ROOT)),
            "bytes": record["bytes"], "sha512": actual,
        })
    return verified


def read_frozen_fit() -> dict[str, np.ndarray]:
    expected_sha = "c3b526dbca66daecb25112267b0308b1df46f3804bfb43b34955bebe83347606"
    if digest(FIT) != expected_sha:
        raise ValueError("frozen historical candidate block changed")
    names = [
        "latitude", "longitude", "native_lat_index", "native_lon_index",
        "glo_location_xi_mm", "glo_scale_alpha_mm", "glo_shape_kappa",
        "calibration_finite_count", "fit_status_code",
    ]
    with xr.open_dataset(FIT, engine="h5netcdf", cache=False) as dataset:
        result = {name: np.asarray(dataset[name].values) for name in names}
    if result["latitude"].shape != (512,):
        raise ValueError("frozen cell block size changed")
    if not np.all(result["calibration_finite_count"] == 30) or not np.all(result["fit_status_code"] == 0):
        raise ValueError("frozen parameter block contains invalid fits")
    if not (
        np.isfinite(result["glo_location_xi_mm"]).all()
        and (result["glo_scale_alpha_mm"] > 0).all()
        and (np.abs(result["glo_shape_kappa"]) < 1).all()
    ):
        raise ValueError("frozen parameter values invalid")
    return result


def source_path(records: dict[tuple[str, str], dict], scenario: str, variable: str) -> Path:
    return locate_source(records[(scenario, variable)])


def monthly_segment(records: dict, fit: dict, scenario: str, start: int, end: int) -> tuple:
    paths = {variable: source_path(records, scenario, variable) for variable in VARIABLES}
    all_months, all_pr, all_et0, all_counts, all_days = [], [], [], [], []
    with ExitStack() as stack:
        datasets = {
            variable: stack.enter_context(xr.open_dataset(path, engine="h5netcdf", decode_times=True, cache=False))
            for variable, path in paths.items()
        }
        dates = {}
        for variable, dataset in datasets.items():
            if variable not in dataset or dataset[variable].dims != ("time", "lat", "lon"):
                raise ValueError(f"{variable} schema changed")
            expected_units = "kg m-2 s-1" if variable == "pr" else "K"
            if dataset[variable].attrs.get("units") != expected_units:
                raise ValueError(f"{variable} units changed")
            if not np.array_equal(dataset.lat.values, 89.75 - 0.5 * np.arange(360)):
                raise ValueError("latitude grid changed")
            if not np.array_equal(dataset.lon.values, -179.75 + 0.5 * np.arange(720)):
                raise ValueError("longitude grid changed")
            dates[variable] = pd.DatetimeIndex(dataset.time.values).normalize()
        if any(not dates[variable].equals(dates["pr"]) for variable in VARIABLES[1:]):
            raise ValueError("variable chronology differs")
        ii = fit["native_lat_index"].astype(int)
        jj = fit["native_lon_index"].astype(int)
        for year in range(start, end + 1):
            positions = np.flatnonzero(dates["pr"].year == year)
            accumulator = MonthlyAccumulator(year, fit["latitude"])
            if len(positions) != len(accumulator.dates):
                raise ValueError(f"incomplete daily year {year}")
            for position, day in zip(positions, accumulator.dates, strict=True):
                values = {
                    variable: np.asarray(datasets[variable][variable].isel(time=int(position)).values[ii, jj], dtype=np.float64)
                    for variable in VARIABLES
                }
                accumulator.add(day, values["pr"] * 86400.0, values["tasmin"] - 273.15, values["tasmax"] - 273.15)
            months, precipitation, et0, counts, days = accumulator.finish()
            all_months.append(months); all_pr.append(precipitation); all_et0.append(et0)
            all_counts.append(counts); all_days.append(days)
    return (
        pd.DatetimeIndex(np.concatenate([x.values for x in all_months])),
        np.concatenate(all_pr), np.concatenate(all_et0), np.concatenate(all_counts), np.concatenate(all_days),
    )


def standardize(months: pd.DatetimeIndex, precipitation: np.ndarray, et0: np.ndarray, fit: dict) -> tuple:
    balance = precipitation - et0
    accumulated = np.stack([_strict_rolling_sum(balance, scale) for scale in SCALES])
    spei = np.full(accumulated.shape, np.nan, dtype=np.float64)
    probability = np.full(accumulated.shape, np.nan, dtype=np.float64)
    clip = np.full(accumulated.shape, -9, dtype=np.int8)
    for scale_index in range(len(SCALES)):
        for calendar_month in range(1, 13):
            positions = months.month == calendar_month
            for cell in range(accumulated.shape[2]):
                parameters = GloParameters(
                    xi=float(fit["glo_location_xi_mm"][scale_index, calendar_month - 1, cell]),
                    alpha=float(fit["glo_scale_alpha_mm"][scale_index, calendar_month - 1, cell]),
                    kappa=float(fit["glo_shape_kappa"][scale_index, calendar_month - 1, cell]),
                    sample_size=30, beta0=0, beta1=0, beta2=0, l1=0, l2=0, tau3=0,
                )
                output = standardize_glo(accumulated[scale_index, positions, cell], parameters)
                spei[scale_index, positions, cell] = output.spei
                probability[scale_index, positions, cell] = output.probabilities
                clip[scale_index, positions, cell] = output.clip_code
    return balance, accumulated, probability, spei, clip


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out_dir = out_dir.resolve()
    if out_dir.exists():
        raise ValueError("fresh output directory required")
    records = registered_sources()
    fit = read_frozen_fit()
    verified = verify_sources(records)
    historical = monthly_segment(records, fit, "historical", 2011, 2014)
    scenario_arrays = []
    for scenario in SCENARIOS:
        future = monthly_segment(records, fit, scenario, 2015, 2020)
        months = historical[0].append(future[0])
        precipitation = np.concatenate([historical[1], future[1]])
        et0 = np.concatenate([historical[2], future[2]])
        if not months.equals(pd.date_range("2011-01-01", "2020-12-01", freq="MS")):
            raise ValueError("historical/future month boundary changed")
        outputs = standardize(months, precipitation, et0, fit)
        scenario_arrays.append((precipitation, et0, *outputs))
    stacked = [np.stack([scenario[index] for scenario in scenario_arrays]) for index in range(7)]
    precipitation, et0, balance, accumulated, probability, spei, clip = stacked
    for values in (precipitation, et0, balance):
        if not np.array_equal(values[0, :48], values[1, :48], equal_nan=True) or not np.array_equal(values[0, :48], values[2, :48], equal_nan=True):
            raise ValueError("shared historical monthly fields differ by scenario")
    for values in (accumulated, probability, spei, clip):
        if not np.array_equal(values[0, :, :48], values[1, :, :48], equal_nan=True) or not np.array_equal(values[0, :, :48], values[2, :, :48], equal_nan=True):
            raise ValueError("shared historical standardized fields differ by scenario")
    months = pd.date_range("2011-01-01", "2020-12-01", freq="MS")
    dataset = xr.Dataset(
        {
            "precipitation_mm": (("scenario", "month", "cell"), precipitation),
            "et0_hargreaves_mm": (("scenario", "month", "cell"), et0),
            "water_balance_mm": (("scenario", "month", "cell"), balance),
            "accumulated_water_balance_mm": (("scenario", "scale", "month", "cell"), accumulated),
            "glo_cdf_probability": (("scenario", "scale", "month", "cell"), probability),
            "spei": (("scenario", "scale", "month", "cell"), spei),
            "cdf_clip_code": (("scenario", "scale", "month", "cell"), clip),
            "latitude": (("cell",), fit["latitude"]),
            "longitude": (("cell",), fit["longitude"]),
            "native_lat_index": (("cell",), fit["native_lat_index"]),
            "native_lon_index": (("cell",), fit["native_lon_index"]),
        },
        coords={"scenario": list(SCENARIOS), "scale": list(SCALES), "month": months, "cell": np.arange(512)},
        attrs={
            "scientific_role": "bounded frozen-transform engineering pilot; not climate response, damage, or SCC",
            "calibration": "parameters fitted on observational 1982-2011 only; no GFDL refit",
            "protocol_sha256": digest(PROTOCOL),
            **{f"gate_{gate}": "false" for gate in engine.FALSE_GATES},
        },
    )
    out_dir.mkdir(parents=True)
    output = out_dir / "gfdl_boundary_spei.nc"
    engine.write_netcdf_atomic(output, dataset)
    future_mask = months.year >= 2015
    summaries = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        for scale_index, scale in enumerate(SCALES):
            values = spei[scenario_index, scale_index, future_mask]
            finite = np.isfinite(values)
            summaries.append({
                "scenario": scenario, "scale_months": scale, "cell_months": int(values.size),
                "finite": int(finite.sum()), "mean_spei": float(np.mean(values[finite])),
                "fraction_le_minus_1": float(np.mean(values[finite] <= -1)),
                "fraction_le_minus_1_5": float(np.mean(values[finite] <= -1.5)),
                "lower_tail_clips": int(np.count_nonzero(clip[scenario_index, scale_index, future_mask] == -1)),
                "upper_tail_clips": int(np.count_nonzero(clip[scenario_index, scale_index, future_mask] == 1)),
            })
    result = {
        "schema": "gfdl_future_spei_boundary_pilot_v1", "status": "completed_pending_independent_validation",
        "role": "engineering_only_not_climate_change_effect_yield_damage_or_scc",
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": digest(PROTOCOL)},
        "frozen_fit": {"path": str(FIT.relative_to(ROOT)), "sha256": digest(FIT), "cells": 512},
        "sources": verified, "months_per_scenario": 120, "historical_months_identical": True,
        "summaries_2015_2020": summaries,
        "output": {"path": str(output.relative_to(ROOT)), "bytes": output.stat().st_size, "sha256": digest(output)},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
        "gates": {"response": False, "causal": False, "damage": False, "scc": False},
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "output_bytes": result["output"]["bytes"], "summaries": summaries}))


if __name__ == "__main__":
    main()
