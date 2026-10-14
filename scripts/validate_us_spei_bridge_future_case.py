#!/usr/bin/env python3
"""Independently validate one future 11-cell U.S. SPEI bridge reduction."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from spei_distribution import standardize_glo  # noqa: E402
from spei_monthly_engine import _strict_rolling_sum  # noqa: E402


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
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    case_dir = args.case_dir if args.case_dir.is_absolute() else ROOT / args.case_dir
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output_path.exists(), "fresh validation output required")
    result_path = case_dir / "result.json"
    result = json.loads(result_path.read_text())
    require(result["schema"] == "us_spei_bridge_future_case_result_v1", "result schema changed")
    require(result["status"] == "completed_pending_independent_validation", "result status changed")
    require(result["cells"] == 11 and result["months"] == 120 and result["scales"] == [1, 3, 6],
            "result dimensions changed")
    require(not any(result["gates"].values()), "a future bridge gate is open")
    for source in result["sources"]:
        path = ROOT / source["path"]
        require(path.stat().st_size == source["bytes"] and digest(path, "sha512") == source["sha512"],
                f"source identity changed: {source['variable']}")
    derived = ROOT / result["output"]["path"]
    require(derived.stat().st_size == result["output"]["bytes"] and digest(derived) == result["output"]["sha256"],
            "derived output changed")
    historical_result_path = ROOT / result["historical_fit"]["result_path"]
    historical_validation_path = ROOT / result["historical_fit"]["validation_path"]
    require(digest(historical_result_path) == result["historical_fit"]["result_sha256"], "historical result changed")
    require(digest(historical_validation_path) == result["historical_fit"]["validation_sha256"], "historical validation changed")
    historical_result = json.loads(historical_result_path.read_text())
    historical_path = ROOT / historical_result["output"]["path"]
    require(digest(historical_path) == result["historical_fit"]["output_sha256"], "historical fit output changed")
    maximum_difference = 0.0
    checks = 14 + len(result["sources"])
    with xr.open_dataset(historical_path, engine="h5netcdf", cache=False) as historical, \
         xr.open_dataset(derived, engine="h5netcdf", cache=False) as future:
        require(dict(future.sizes) == {"month": 120, "cell": 11, "scale": 3}, "future dimensions changed")
        months = pd.DatetimeIndex(future.month.values)
        require(months.equals(pd.date_range("2091-01-01", "2100-12-01", freq="MS")), "future chronology changed")
        require(np.array_equal(future.native_lat_index.values, historical.native_lat_index.values)
                and np.array_equal(future.native_lon_index.values, historical.native_lon_index.values),
                "historical/future cell order changed")
        balance = future.precipitation_mm.values - future.et0_hargreaves_mm.values
        require(np.array_equal(balance, future.water_balance_mm.values), "water balance arithmetic changed")
        for scale_index, scale in enumerate((1, 3, 6)):
            accumulated = _strict_rolling_sum(balance, scale)
            require(np.array_equal(accumulated, future.accumulated_water_balance_mm.values[scale_index], equal_nan=True),
                    f"scale-{scale} accumulation changed")
            for month_number in range(1, 13):
                positions = np.flatnonzero(months.month == month_number)
                for cell in range(11):
                    parameters = SimpleNamespace(
                        xi=float(historical.glo_location_xi_mm.values[scale_index, month_number-1, cell]),
                        alpha=float(historical.glo_scale_alpha_mm.values[scale_index, month_number-1, cell]),
                        kappa=float(historical.glo_shape_kappa.values[scale_index, month_number-1, cell]),
                    )
                    expected = standardize_glo(accumulated[positions, cell], parameters)
                    observed = future.spei.values[scale_index, positions, cell]
                    require(np.array_equal(np.isfinite(observed), np.isfinite(expected.spei)), "future SPEI missingness changed")
                    finite = np.isfinite(expected.spei)
                    difference = float(np.max(np.abs(observed[finite]-expected.spei[finite]), initial=0))
                    require(difference <= 3e-7, "future SPEI independent reconstruction differs")
                    require(np.array_equal(future.cdf_clip_code.values[scale_index, positions, cell], expected.clip_code),
                            "future clip codes changed")
                    maximum_difference = max(maximum_difference, difference)
                    checks += 3
    validation = {
        "schema": "us_spei_bridge_future_case_validation_v1", "status": "passed",
        "role": "independent_climate_only_validation_no_county_panel_or_outcome_fit",
        "esm": result["esm"], "scenario": result["scenario"], "cells": 11, "months": 120,
        "checks": checks, "maximum_spei_absolute_difference": maximum_difference,
        "pair_result_sha256": digest(result_path), "output_sha256": digest(derived),
        "gates": {name: False for name in result["gates"]},
    }
    output_path.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    print(json.dumps(validation, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
