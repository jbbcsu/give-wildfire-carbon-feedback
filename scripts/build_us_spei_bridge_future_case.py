#!/usr/bin/env python3
"""Reduce one registered future case to the 11 U.S. SPEI bridge cells."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_spei_grid_chunk as engine  # noqa: E402
from build_isimip3b_late_drought_pair import (EXPECTED_MONTHS, SCALES, extrema_record, locate,  # noqa: E402
                                               source_record, standardize_vectorized, stream_monthly)
from spei_monthly_engine import _strict_rolling_sum  # noqa: E402

FALSE_GATES = ("future_exact_361_county_support", "future_county_spei_panel", "bridge_to_nass_response",
               "fit_outcomes", "future_yield_projection", "causal_claim", "damage", "scc")


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esm", required=True)
    parser.add_argument("--scenario", choices=("ssp126", "ssp370", "ssp585"), required=True)
    parser.add_argument("--raw-root", type=Path, default=ROOT / "data/raw/isimip3b")
    parser.add_argument("--historical-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raw_root = args.raw_root if args.raw_root.is_absolute() else ROOT / args.raw_root
    historical_dir = args.historical_dir if args.historical_dir.is_absolute() else ROOT / args.historical_dir
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    require(not output_dir.exists(), "fresh output directory required")
    historical_result_path = historical_dir / "result.json"
    historical_validation_path = historical_dir / "validation.json"
    historical_result = json.loads(historical_result_path.read_text())
    historical_validation = json.loads(historical_validation_path.read_text())
    require(historical_validation["status"] == "passed"
            and historical_validation["result"]["sha256"] == digest(historical_result_path),
            "historical 11-cell validation failed")
    historical_path = ROOT / historical_result["output"]["path"]
    require(digest(historical_path) == historical_result["output"]["sha256"], "historical 11-cell output changed")
    records = {name: source_record(args.esm, args.scenario, name) for name in ("pr", "tas")}
    records.update({name: extrema_record(args.esm, args.scenario, name) for name in ("tasmin", "tasmax")})
    paths = {name: locate(raw_root, record) for name, record in records.items()}
    with xr.open_dataset(historical_path, engine="h5netcdf", cache=False) as historical:
        latitudes = np.asarray(historical.latitude.values, dtype=np.float64)
        longitudes = np.asarray(historical.longitude.values, dtype=np.float64)
        rows = np.asarray(historical.native_lat_index.values, dtype=np.int64)
        cols = np.asarray(historical.native_lon_index.values, dtype=np.int64)
        xi = np.asarray(historical.glo_location_xi_mm.values, dtype=np.float64)
        alpha = np.asarray(historical.glo_scale_alpha_mm.values, dtype=np.float64)
        kappa = np.asarray(historical.glo_shape_kappa.values, dtype=np.float64)
        require(np.all(historical.fit_status_code.values == 0), "historical frozen fit status changed")
    require(len(latitudes) == 11, "exactly 11 historical bridge cells required")
    started = time.perf_counter()
    precipitation, et0, counts, daily_audit = stream_monthly(paths, latitudes, rows, cols)
    balance = precipitation - et0
    accumulated = np.stack([_strict_rolling_sum(balance, scale) for scale in SCALES])
    future_spei = np.full(accumulated.shape, np.nan, dtype=np.float64)
    clips = np.full(accumulated.shape, -9, dtype=np.int8)
    for scale_index, _scale in enumerate(SCALES):
        for month_number in range(1, 13):
            positions = np.flatnonzero(EXPECTED_MONTHS.month == month_number)
            values, codes = standardize_vectorized(accumulated[scale_index, positions],
                                                    xi[scale_index, month_number-1],
                                                    alpha[scale_index, month_number-1],
                                                    kappa[scale_index, month_number-1])
            future_spei[scale_index, positions] = values
            clips[scale_index, positions] = codes
    dataset = xr.Dataset({
        "precipitation_mm": (("month", "cell"), precipitation),
        "et0_hargreaves_mm": (("month", "cell"), et0),
        "water_balance_mm": (("month", "cell"), balance),
        "accumulated_water_balance_mm": (("scale", "month", "cell"), accumulated),
        "spei": (("scale", "month", "cell"), future_spei),
        "cdf_clip_code": (("scale", "month", "cell"), clips),
        "latitude": (("cell",), latitudes), "longitude": (("cell",), longitudes),
        "native_lat_index": (("cell",), rows.astype(np.int16)),
        "native_lon_index": (("cell",), cols.astype(np.int16)),
    }, coords={"month": EXPECTED_MONTHS, "cell": np.arange(11), "scale": list(SCALES)},
       attrs={"schema": "us_spei_bridge_future_case_v1", "esm": args.esm, "scenario": args.scenario,
              "scientific_role": "climate_only_exact_support_extension_no_county_panel_or_outcome_fit",
              "calibration": "historical GSWP3-W5E5 1982-2011 frozen without future refit",
              **{f"gate_{name}": "false" for name in FALSE_GATES}})
    output_dir.mkdir(parents=True)
    output_path = output_dir / "future_spei_11_cells.nc"
    engine.write_netcdf_atomic(output_path, dataset)
    result = {
        "schema": "us_spei_bridge_future_case_result_v1", "status": "completed_pending_independent_validation",
        "role": "climate_only_exact_support_extension_no_county_panel_or_outcome_fit",
        "esm": args.esm, "scenario": args.scenario, "period": "2091-2100", "cells": 11,
        "months": 120, "scales": list(SCALES), "daily_audit": daily_audit,
        "historical_fit": {"result_path": str(historical_result_path.relative_to(ROOT)),
                           "result_sha256": digest(historical_result_path),
                           "validation_path": str(historical_validation_path.relative_to(ROOT)),
                           "validation_sha256": digest(historical_validation_path),
                           "output_sha256": digest(historical_path)},
        "sources": [{"variable": name, "path": str(paths[name].relative_to(ROOT)),
                     "bytes": records[name]["bytes"], "sha512": records[name]["sha512"],
                     "file_url": records[name]["file_url"]} for name in sorted(records)],
        "output": {"path": str(output_path.relative_to(ROOT)), "bytes": output_path.stat().st_size,
                   "sha256": digest(output_path)},
        "wall_seconds": time.perf_counter()-started,
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                           "sha256": digest(Path(__file__).resolve())},
        "gates": {name: False for name in FALSE_GATES},
    }
    engine.write_json_atomic(output_dir / "result.json", result)
    print(json.dumps({"status": result["status"], "esm": args.esm, "scenario": args.scenario,
                      "daily_audit": daily_audit, "output": result["output"]}))


if __name__ == "__main__":
    main()
