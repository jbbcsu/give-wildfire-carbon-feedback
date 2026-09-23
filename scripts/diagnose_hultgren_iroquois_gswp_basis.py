#!/usr/bin/env python3
"""One-cell GSWP diagnostic against published Iroquois GMFD maize features."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import source_month_from_day
from src.hultgren_maize_weather import build_maize_weather_basis_from_daily

CLIMATE_DIR = ROOT / "data/raw/isimip3a_gswp3_w5e5_v1_3"
PR_PATH = CLIMATE_DIR / "gswp3-w5e5_obsclim_pr_global_daily_1981_1990.nc"
TMAX_PATH = CLIMATE_DIR / "gswp3-w5e5_obsclim_tasmax_global_daily_1981_1990.nc"
TMIN_PATH = CLIMATE_DIR / "gswp3-w5e5_obsclim_tasmin_global_daily_1981_1990.nc"
CALENDAR_PATH = ROOT / "data/raw/crop_calendars/ggcmi-crop-calendar-phase3_2015soc_mai_noirr.nc"
HULTGREN_PATH = ROOT / "data/raw/hultgren_response/historical_git/dae5fe8d0d4a260328e4baa45b547368bd6790b3/corn_gmfd_v1_ready.dta"
DEFAULT_OUTPUT = ROOT / "data/provenance/hultgren_iroquois_gswp_basis_diagnostic_20260923.json"

SOURCE = {
    "pr": {
        "bytes": 2_351_177_152,
        "sha512": "c2b0688e59196088a1eaeac6fdc25b0bf1419f78c8662e9c21038c63b58aa6c40df5f22cc723d0ad9e24104a081bd215b9760f9003f0fc557b947341dc2d03f2",
    },
    "tasmax": {
        "bytes": 2_045_681_376,
        "sha512": "b22a9d2be2fc6f36fd37452adf74b04737c29fed89611a73b3209dc159c514e674c09fd7940782035b1f1e3c52284e0684c231a3f83452312640cb0eb323ab42",
    },
    "tasmin": {
        "bytes": 2_056_386_729,
        "sha512": "51b056a9601417e124801f18878951d794ebe6a42153946e6172d13ade8d00748cff70e2cf15ff23b04c76ae0a3a1e62fee0baa6c8f21642886b0d8d7e579678",
    },
}

FEATURES = (
    "gdd", "kdd",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
)


def read_hultgren() -> pd.DataFrame:
    columns = [
        "iso", "adm2", "year", "median_plant_date", "median_harvest_date",
        "GMFD_tmax_poly_1",
    ] + list(FEATURES)
    pieces = []
    with pd.read_stata(HULTGREN_PATH, columns=columns, iterator=True, convert_categoricals=False) as reader:
        while True:
            try:
                chunk = reader.read(50_000)
            except StopIteration:
                break
            if chunk.empty:
                break
            keep = chunk[(chunk["iso"] == "USA") & (chunk["adm2"] == "iroquois")]
            if not keep.empty:
                pieces.append(keep)
    result = pd.concat(pieces, ignore_index=True)
    result = result[(result["year"] >= 1981) & (result["year"] <= 1990)].sort_values("year")
    if result["year"].astype(int).tolist() != list(range(1981, 1991)):
        raise AssertionError("published Iroquois overlap is not exactly 1981 through 1990")
    return result


def read_gswp_cell(latitude: float, longitude: float) -> tuple[list[tuple[object, float, float, float]], dict[str, object]]:
    for path, variable in ((PR_PATH, "pr"), (TMIN_PATH, "tasmin"), (TMAX_PATH, "tasmax")):
        if path.stat().st_size != SOURCE[variable]["bytes"]:
            raise AssertionError(f"resident {variable} file size differs from source contract")

    with xr.open_dataset(PR_PATH, decode_timedelta=False) as pr_ds, xr.open_dataset(TMIN_PATH, decode_timedelta=False) as tn_ds, xr.open_dataset(TMAX_PATH, decode_timedelta=False) as tx_ds:
        if pr_ds["pr"].attrs.get("units") != "kg m-2 s-1" or tn_ds["tasmin"].attrs.get("units") != "K" or tx_ds["tasmax"].attrs.get("units") != "K":
            raise AssertionError("unexpected GSWP precipitation or temperature units")
        if not np.array_equal(pr_ds["time"].values, tn_ds["time"].values) or not np.array_equal(pr_ds["time"].values, tx_ds["time"].values):
            raise AssertionError("GSWP precipitation, Tmin and Tmax dates differ")
        if not np.array_equal(pr_ds["lat"].values, tn_ds["lat"].values) or not np.array_equal(pr_ds["lat"].values, tx_ds["lat"].values) or not np.array_equal(pr_ds["lon"].values, tn_ds["lon"].values) or not np.array_equal(pr_ds["lon"].values, tx_ds["lon"].values):
            raise AssertionError("GSWP precipitation, Tmin and Tmax grids differ")
        lat_index = int(np.abs(pr_ds["lat"].values - latitude).argmin())
        lon_index = int(np.abs(pr_ds["lon"].values - longitude).argmin())
        selected_lat = float(pr_ds["lat"].values[lat_index])
        selected_lon = float(pr_ds["lon"].values[lon_index])
        dates = pd.DatetimeIndex(pr_ds["time"].values)
        indices = np.flatnonzero((dates.month >= 5) & (dates.month <= 10))
        rain = pr_ds["pr"].isel(time=indices, lat=lat_index, lon=lon_index).load().values.astype(np.float64) * 86_400.0
        tmin = tn_ds["tasmin"].isel(time=indices, lat=lat_index, lon=lon_index).load().values.astype(np.float64) - 273.15
        tmax = tx_ds["tasmax"].isel(time=indices, lat=lat_index, lon=lon_index).load().values.astype(np.float64) - 273.15
        selected_dates = dates[indices]

    if len(selected_dates) != 1_840 or not np.isfinite(rain).all() or not np.isfinite(tmin).all() or not np.isfinite(tmax).all():
        raise AssertionError("GSWP May-October daily cell support is incomplete or nonfinite")
    records = [
        (stamp.date(), float(pr), float(tn), float(tx))
        for stamp, pr, tn, tx in zip(selected_dates, rain, tmin, tmax, strict=True)
    ]
    metadata = {
        "requested_latitude": latitude,
        "requested_longitude": longitude,
        "selected_latitude": selected_lat,
        "selected_longitude": selected_lon,
        "daily_records": len(records),
    }
    return records, metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latitude", type=float, default=40.75)
    parser.add_argument("--longitude", type=float, default=-87.75)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = read_hultgren()
    plant_months = {source_month_from_day(value) for value in source["median_plant_date"]}
    harvest_months = {source_month_from_day(value) for value in source["median_harvest_date"]}
    if plant_months != {5} or harvest_months != {10}:
        raise AssertionError("Iroquois source calendar is not consistently May through October")

    records, spatial = read_gswp_cell(args.latitude, args.longitude)
    with xr.open_dataset(CALENDAR_PATH, decode_timedelta=False) as calendar_ds:
        calendar_cell = calendar_ds.sel(
            lat=spatial["selected_latitude"], lon=spatial["selected_longitude"]
        )
        planting_day = float(calendar_cell["planting_day"])
        maturity_day = float(calendar_cell["maturity_day"])
    if source_month_from_day(planting_day) != 5 or source_month_from_day(maturity_day) != 10:
        raise AssertionError("GGCMI proxy cell does not share the source May-October month window")

    constructed = []
    for year in range(1981, 1991):
        season_records = [
            record for record in records
            if record[0].year == year and 5 <= record[0].month <= 10
        ]
        basis = build_maize_weather_basis_from_daily(
            records,
            report_year=year,
            plant_month=5,
            harvest_month=10,
            iso="USA",
        )
        constructed.append({
            "year": year,
            "mean_daily_tmax_c": float(np.mean([record[3] for record in season_records])),
            "gdd": basis.gdd,
            "kdd": basis.kdd,
            **{f"prcp_poly_1_bin{i + 1}": value for i, value in enumerate(basis.prcp_poly_1_bins)},
            **{f"prcp_poly_2_bin{i + 1}": value for i, value in enumerate(basis.prcp_poly_2_bins)},
        })
    gswp = pd.DataFrame(constructed).sort_values("year")

    direct_tmax_only = []
    for year in range(1981, 1991):
        values = np.asarray([
            record[3] for record in records
            if record[0].year == year and 5 <= record[0].month <= 10
        ])
        direct_tmax_only.append({
            "year": year,
            "gdd": float(np.minimum(np.maximum(values - 8.0, 0.0), 23.0).sum()),
            "kdd": float(np.maximum(values - 31.0, 0.0).sum()),
        })
    direct_tmax_only = pd.DataFrame(direct_tmax_only).sort_values("year")

    comparisons = {}
    for feature in FEATURES:
        observed = source[feature].to_numpy(dtype=np.float64)
        candidate = gswp[feature].to_numpy(dtype=np.float64)
        difference = candidate - observed
        correlation = float(np.corrcoef(candidate, observed)[0, 1])
        comparisons[feature] = {
            "published_gmfd_mean": float(observed.mean()),
            "gswp_proxy_mean": float(candidate.mean()),
            "gswp_minus_published_mean": float(difference.mean()),
            "rmse": float(np.sqrt(np.mean(difference * difference))),
            "pearson_correlation": correlation if math.isfinite(correlation) else None,
        }

    observed_tmax = source["GMFD_tmax_poly_1"].to_numpy(dtype=np.float64)
    candidate_tmax = gswp["mean_daily_tmax_c"].to_numpy(dtype=np.float64)
    tmax_difference = candidate_tmax - observed_tmax
    comparisons["season_mean_tmax"] = {
        "published_gmfd_mean": float(observed_tmax.mean()),
        "gswp_proxy_mean": float(candidate_tmax.mean()),
        "gswp_minus_published_mean": float(tmax_difference.mean()),
        "rmse": float(np.sqrt(np.mean(tmax_difference * tmax_difference))),
        "pearson_correlation": float(np.corrcoef(candidate_tmax, observed_tmax)[0, 1]),
    }

    observed_rain = source[[f"prcp_poly_1_bin{i}" for i in (1, 2, 3)]].sum(axis=1).to_numpy(dtype=np.float64)
    candidate_rain = gswp[[f"prcp_poly_1_bin{i}" for i in (1, 2, 3)]].sum(axis=1).to_numpy(dtype=np.float64)
    rain_difference = candidate_rain - observed_rain
    comparisons["season_total_precipitation"] = {
        "published_gmfd_mean": float(observed_rain.mean()),
        "gswp_proxy_mean": float(candidate_rain.mean()),
        "gswp_minus_published_mean": float(rain_difference.mean()),
        "rmse": float(np.sqrt(np.mean(rain_difference * rain_difference))),
        "pearson_correlation": float(np.corrcoef(candidate_rain, observed_rain)[0, 1]),
    }

    rejected_direct_tmax = {}
    for feature in ("gdd", "kdd"):
        observed = source[feature].to_numpy(dtype=np.float64)
        candidate = direct_tmax_only[feature].to_numpy(dtype=np.float64)
        difference = candidate - observed
        rejected_direct_tmax[feature] = {
            "published_gmfd_mean": float(observed.mean()),
            "direct_tmax_only_mean": float(candidate.mean()),
            "direct_tmax_only_minus_published_mean": float(difference.mean()),
            "rmse": float(np.sqrt(np.mean(difference * difference))),
            "pearson_correlation": float(np.corrcoef(candidate, observed)[0, 1]),
        }

    gates = {
        "published_overlap_1981_1990_complete": len(source) == 10,
        "resident_daily_support_complete": spatial["daily_records"] == 1_840,
        "source_and_proxy_month_window_match": True,
        "all_constructed_features_finite": bool(np.isfinite(gswp[list(FEATURES)].to_numpy()).all()),
        "comparison_is_diagnostic_not_source_replication": True,
        "direct_tmax_only_candidate_rejected_by_source_method": True,
    }
    if not all(gates.values()):
        raise AssertionError(f"Iroquois GSWP diagnostic gate failed: {gates}")

    payload = {
        "schema": "hultgren_iroquois_gswp_basis_diagnostic/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "role": "one_cell_different_product_implementation_diagnostic_not_gmfd_replication",
        "sources": {
            "published_historical_dataset": str(HULTGREN_PATH.relative_to(ROOT)),
            "gswp_pr": {"path": str(PR_PATH.relative_to(ROOT)), **SOURCE["pr"]},
            "gswp_tasmin": {"path": str(TMIN_PATH.relative_to(ROOT)), **SOURCE["tasmin"]},
            "gswp_tasmax": {"path": str(TMAX_PATH.relative_to(ROOT)), **SOURCE["tasmax"]},
            "ggcmi_calendar": str(CALENDAR_PATH.relative_to(ROOT)),
        },
        "spatial_proxy": spatial,
        "calendar": {
            "published_plant_day": float(source["median_plant_date"].iloc[0]),
            "published_harvest_day": float(source["median_harvest_date"].iloc[0]),
            "ggcmi_planting_day": planting_day,
            "ggcmi_maturity_day": maturity_day,
            "whole_month_window": [5, 10],
        },
        "comparisons": comparisons,
        "rejected_direct_tmax_only_candidate": {
            "reason": (
                "The paper requires Snyder sinusoidal interpolation between daily Tmin and Tmax; "
                "thresholding daily Tmax alone is not the published construction."
            ),
            "comparisons": rejected_direct_tmax,
        },
        "validation_gates": gates,
        "claim_gates": {
            "primitive_daily_pipeline_operational_on_resident_weather": True,
            "gmfd_features_reproduced": False,
            "administrative_unit_crop_weighting_validated": False,
            "aggregation_choice_frozen": False,
            "future_climate_projection_validated": False,
            "damage_estimate_validated": False,
            "scc_estimate_validated": False,
        },
        "interpretation": (
            "The exact calendar-to-basis code runs on a complete resident GSWP3-W5E5 daily cell and "
            "produces a ten-year comparison with published Iroquois GMFD administrative-unit features. "
            "Because both the weather product and spatial aggregation differ, correlations and errors are "
            "diagnostic only and cannot validate or replace the published GMFD features."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "spatial_proxy": spatial, "comparisons": comparisons}, indent=2))


if __name__ == "__main__":
    main()
