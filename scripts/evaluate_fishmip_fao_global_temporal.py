#!/usr/bin/env python3
"""Compare normalized global FishMIP history with provisional FAO tonnage."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import tomllib

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "FISHMIP_FAO_GLOBAL_TEMPORAL_DIAGNOSTIC_PROTOCOL_20260921.md"
FAO = ROOT / "data/derived/fao/fishstat_capture_wide_1950_2024.csv"
FAO_CONTRACT = ROOT / "data/provenance/fao_fishstat_capture_headless_export_v1.toml"
FAO_SHA = "ca58247c4f6044948b01048e4a808d21a4975c9f4171e3d0d1fbc321e46ebb52"
CONTRACT_SHA = "dc5221915bd3d2fab2d72c203351f908f2f95286fde57a7c4dd7c0353f4bd6ec"
PATHS = {
    "gfdl-esm4/boats": (ROOT / "data/raw/fishmip/gfdl-esm4/boats/boats_gfdl-esm4_nobasd_historical_histsoc_default_tc_global_monthly_1950_2014.nc", "22214dba88ee0c5b8beec120c3f58c1e14ba23f5ee582e89d1558eaf35f286b7"),
    "gfdl-esm4/ecoocean": (ROOT / "data/raw/fishmip/gfdl-esm4/ecoocean/ecoocean_gfdl-esm4_nobasd_historical_histsoc_default_tc_global_monthly_1950_2014.nc", "ff8aca2f3d70205aa2807e17b5103b655dca3f84cae4067b649337ef6782b28d"),
    "ipsl-cm6a-lr/boats": (ROOT / "data/raw/fishmip/ipsl-cm6a-lr/boats/boats_ipsl-cm6a-lr_nobasd_historical_histsoc_default_tc_global_monthly_1950_2014.nc", "39a395fdb0293344c5ca0db23d637e6cd99a5ab25e9119b36d56801395d3d518"),
    "ipsl-cm6a-lr/ecoocean": (ROOT / "data/raw/fishmip/ipsl-cm6a-lr/ecoocean/ecoocean_ipsl-cm6a-lr_nobasd_historical_histsoc_default_tc_global_monthly_1950_2014.nc", "94cefddffbd91b9dc49fa87b95f7acd52dc3ccd1789b4b1621308fe70317c9b4"),
}
YEARS = np.arange(1950, 2015, dtype=int)
PERIODS = ((1950, 2014), (1980, 2014))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    require(len(x) == len(y) and len(x) >= 3, "invalid correlation inputs")
    xc, yc = x - x.mean(), y - y.mean()
    denominator = math.sqrt(float(xc @ xc) * float(yc @ yc))
    require(denominator > 0, "constant correlation input")
    return float((xc @ yc) / denominator)


def slope(years: np.ndarray, values: np.ndarray) -> float:
    x = years.astype(float) - float(years.mean())
    return float((x @ (values - values.mean())) / (x @ x))


def metrics(years: np.ndarray, observed: np.ndarray, modeled: np.ndarray) -> dict[str, float | int]:
    require(np.isfinite(observed).all() and np.isfinite(modeled).all() and
            (observed > 0).all() and (modeled > 0).all(), "invalid normalized series")
    residual = modeled - observed
    d_observed, d_modeled = np.diff(observed), np.diff(modeled)
    return {
        "years": len(years),
        "level_pearson": pearson(observed, modeled),
        "level_mean_bias": float(residual.mean()),
        "level_rmse": float(np.sqrt(np.mean(residual**2))),
        "level_log_rmse": float(np.sqrt(np.mean((np.log(modeled) - np.log(observed))**2))),
        "first_difference_pearson": pearson(d_observed, d_modeled),
        "first_difference_rmse": float(np.sqrt(np.mean((d_modeled - d_observed)**2))),
        "first_difference_sign_agreement": float(np.mean(np.sign(d_modeled) == np.sign(d_observed))),
        "observed_normalized_slope_per_year": slope(years, observed),
        "modeled_normalized_slope_per_year": slope(years, modeled),
    }


def observed_tonnage() -> np.ndarray:
    contract = tomllib.loads(FAO_CONTRACT.read_text())
    require(contract["schema"] == "fao_fishstat_capture_headless_export_contract_v1", "FAO contract changed")
    require(contract["boundaries"]["marine_tonnage_filter_authorized"] is False, "provisional filter boundary changed")
    totals = {int(year): 0.0 for year in YEARS}
    with FAO.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames is not None, "FAO header missing")
        for row in reader:
            if row["environment_class"] != "marine" or row["measure_code"] != "Q_tlw":
                continue
            for year in YEARS:
                value = float(row[f"value_{year}"])
                status = row[f"status_{year}"]
                require(value >= 0 and status in contract["export"]["required_status_codes"], "invalid FAO value/status")
                if value > 0:
                    totals[int(year)] += value
    values = np.asarray([totals[int(year)] for year in YEARS], dtype=float)
    require((values > 0).all(), "FAO annual marine tonnage is nonpositive")
    return values


def common_support() -> tuple[np.ndarray, np.ndarray]:
    support = None
    latitude = None
    for path, expected_sha in PATHS.values():
        require(sha(path) == expected_sha, "FishMIP input hash changed")
        with xr.open_dataset(path, engine="h5netcdf", decode_times=False,
                             decode_cf=False, mask_and_scale=False) as dataset:
            require(np.isclose(float(dataset["tc"].attrs.get("_FillValue")), 1e20, rtol=1e-6) and
                    np.isclose(float(dataset["tc"].attrs.get("missing_value")), 1e20, rtol=1e-6),
                    "FishMIP missing-value declaration changed")
            current_lat = np.asarray(dataset["lat"].values, dtype=float)
            first = np.asarray(dataset["tc"].isel(time=0).values, dtype=float)
            current = np.isfinite(first) & (first < 1e19)
            if support is None:
                support, latitude = current, current_lat
            else:
                require(np.array_equal(current_lat, latitude) and current.shape == support.shape, "FishMIP grids differ")
                support &= current
    assert support is not None and latitude is not None
    require(bool(support.any()), "common support empty")
    return support, latitude


def annual_model(path: Path, support: np.ndarray, latitude: np.ndarray) -> np.ndarray:
    weight = np.where(support, np.cos(np.deg2rad(latitude))[:, None], 0.0)
    denominator = float(weight.sum())
    values = []
    with xr.open_dataset(path, engine="h5netcdf", decode_times=False,
                         decode_cf=False, mask_and_scale=False) as dataset:
        require(dataset.sizes["time"] == 780, "FishMIP historical time support changed")
        for index in range(len(YEARS)):
            block = np.asarray(dataset["tc"].isel(time=slice(index * 12, index * 12 + 12)).values, dtype=float)
            require(block.shape == (12, *support.shape), "FishMIP annual block shape changed")
            require(np.isfinite(block[:, support]).all() and
                    (block[:, support] >= 0).all() and (block[:, support] < 1e19).all(),
                    "FishMIP support changed")
            values.append(float(((np.where(support[None, :, :], block, 0.0) * weight).sum(axis=(1, 2)) / denominator).mean()))
    result = np.asarray(values)
    require((result > 0).all(), "FishMIP annual density is nonpositive")
    return result


def normalize(values: np.ndarray) -> tuple[np.ndarray, float]:
    reference = float(values[(YEARS >= 2005) & (YEARS <= 2014)].mean())
    require(reference > 0, "reference mean nonpositive")
    return values / reference, reference


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(not out.exists() and out.is_relative_to(ROOT / "data/interim") and out.suffix == ".json",
            "fresh ignored JSON output required")
    require(sha(FAO) == FAO_SHA and sha(FAO_CONTRACT) == CONTRACT_SHA, "FAO input hash changed")
    observed_raw = observed_tonnage()
    observed, observed_reference = normalize(observed_raw)
    support, latitude = common_support()
    paths = []
    annual_output = [{"year": int(year), "observed_tonnes": float(value),
                      "observed_normalized": float(index)}
                     for year, value, index in zip(YEARS, observed_raw, observed)]
    for identifier, (path, _) in PATHS.items():
        raw = annual_model(path, support, latitude)
        modeled, reference = normalize(raw)
        comparisons = []
        for start, end in PERIODS:
            mask = (YEARS >= start) & (YEARS <= end)
            comparisons.append({"start_year": start, "end_year": end,
                                **metrics(YEARS[mask], observed[mask], modeled[mask])})
        paths.append({"path_id": identifier, "file": path.name,
                      "reference_2005_2014_mean_density": reference,
                      "comparisons": comparisons})
        for row, raw_value, index in zip(annual_output, raw, modeled):
            row[f"{identifier}_mean_density"] = float(raw_value)
            row[f"{identifier}_normalized"] = float(index)
    result = {
        "status": "fishmip_fao_global_historical_temporal_diagnostic_not_calibration_or_scc",
        "protocol_sha256": sha(PROTOCOL), "code_sha256": sha(Path(__file__)),
        "fao_csv_sha256": sha(FAO), "fao_contract_sha256": sha(FAO_CONTRACT),
        "fishmip_sha256": {identifier: expected for identifier, (_, expected) in PATHS.items()},
        "common_finite_grid_cells": int(support.sum()),
        "observed_reference_2005_2014_tonnes": observed_reference,
        "paths": paths, "annual": annual_output,
        "fishstat_gui_menu_export_reconciled": False,
        "model_selected_or_weighted": False, "climate_attribution_estimated": False,
        "matched_co2_pulse": False, "welfare_or_damage_estimated": False, "scc_estimated": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "common_cells": result["common_finite_grid_cells"],
                      "paths": len(paths)}))


if __name__ == "__main__":
    main()
