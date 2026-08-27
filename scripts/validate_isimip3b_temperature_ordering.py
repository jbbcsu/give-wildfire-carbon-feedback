#!/usr/bin/env python3
"""Check complete daily tasmin <= tas <= tasmax ordering on one climate cell."""
from __future__ import annotations

import argparse
import json
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import xarray as xr


VARIABLES = ("tasmin", "tas", "tasmax")


def validate(
    tasmin_path: Path,
    tas_path: Path,
    tasmax_path: Path,
    *,
    tolerance_k: float = 5e-5,
    block_days: int = 32,
) -> dict[str, object]:
    if block_days < 1:
        raise ValueError("block_days must be positive")
    if not np.isfinite(tolerance_k) or tolerance_k < 0:
        raise ValueError("tolerance_k must be finite and nonnegative")
    paths = dict(zip(VARIABLES, (tasmin_path, tas_path, tasmax_path)))
    with ExitStack() as stack:
        datasets = {
            name: stack.enter_context(xr.open_dataset(path, engine="h5netcdf"))
            for name, path in paths.items()
        }
        arrays: dict[str, xr.DataArray] = {}
        for name, dataset in datasets.items():
            if set(dataset.data_vars) != {name}:
                raise ValueError(f"{name} file must contain only data variable {name}")
            array = dataset[name]
            if array.dims != ("time", "lat", "lon"):
                raise ValueError(f"unexpected {name} dimension order: {array.dims}")
            if array.attrs.get("standard_name") != "air_temperature":
                raise ValueError(f"{name} standard_name must be air_temperature")
            if array.attrs.get("units") != "K":
                raise ValueError(f"{name} units must be K")
            arrays[name] = array
        reference = arrays["tas"]
        for name in ("tasmin", "tasmax"):
            candidate = arrays[name]
            if candidate.sizes != reference.sizes:
                raise ValueError(f"{name} dimensions differ from tas")
            for coordinate in ("time", "lat", "lon"):
                if not np.array_equal(candidate[coordinate].values, reference[coordinate].values):
                    raise ValueError(f"{name} {coordinate} coordinate differs from tas")

        counts = {
            "finite_triplets": 0,
            "raw_tasmin_above_tas": 0,
            "raw_tas_above_tasmax": 0,
            "tasmin_above_tas_beyond_tolerance": 0,
            "tas_above_tasmax_beyond_tolerance": 0,
        }
        maximum_tasmin_minus_tas_k = -np.inf
        maximum_tas_minus_tasmax_k = -np.inf
        minimum_tasmax_minus_tasmin_k = np.inf
        for start in range(0, reference.sizes["time"], block_days):
            values = {
                name: array.isel(time=slice(start, start + block_days)).values
                for name, array in arrays.items()
            }
            finite = np.isfinite(values["tasmin"]) & np.isfinite(values["tas"]) & np.isfinite(
                values["tasmax"]
            )
            if not finite.all():
                raise ValueError("temperature-order inputs must be completely finite")
            minimum_gap = values["tas"] - values["tasmin"]
            maximum_gap = values["tasmax"] - values["tas"]
            diurnal_range = values["tasmax"] - values["tasmin"]
            counts["finite_triplets"] += int(finite.sum())
            counts["raw_tasmin_above_tas"] += int((minimum_gap < 0).sum())
            counts["raw_tas_above_tasmax"] += int((maximum_gap < 0).sum())
            counts["tasmin_above_tas_beyond_tolerance"] += int(
                (minimum_gap < -tolerance_k).sum()
            )
            counts["tas_above_tasmax_beyond_tolerance"] += int(
                (maximum_gap < -tolerance_k).sum()
            )
            maximum_tasmin_minus_tas_k = max(
                maximum_tasmin_minus_tas_k, float((-minimum_gap).max())
            )
            maximum_tas_minus_tasmax_k = max(
                maximum_tas_minus_tasmax_k, float((-maximum_gap).max())
            )
            minimum_tasmax_minus_tasmin_k = min(
                minimum_tasmax_minus_tasmin_k, float(diurnal_range.min())
            )
    if (
        counts["tasmin_above_tas_beyond_tolerance"]
        or counts["tas_above_tasmax_beyond_tolerance"]
    ):
        raise ValueError(f"daily temperature ordering failed: {counts}")
    return {
        "role": "complete_file_temperature_ordering_engineering_gate_not_damage_or_scc",
        "files": {name: path.name for name, path in paths.items()},
        "dimensions": dict(reference.sizes),
        "tolerance_k": tolerance_k,
        **counts,
        "maximum_tasmin_minus_tas_k": maximum_tasmin_minus_tas_k,
        "maximum_tas_minus_tasmax_k": maximum_tas_minus_tasmax_k,
        "minimum_tasmax_minus_tasmin_k": minimum_tasmax_minus_tasmin_k,
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasmin", type=Path, required=True)
    parser.add_argument("--tas", type=Path, required=True)
    parser.add_argument("--tasmax", type=Path, required=True)
    parser.add_argument("--tolerance-k", type=float, default=5e-5)
    parser.add_argument("--block-days", type=int, default=32)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(
        args.tasmin,
        args.tas,
        args.tasmax,
        tolerance_k=args.tolerance_k,
        block_days=args.block_days,
    )
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"temperature ordering passed for {result['finite_triplets']} complete daily-grid triplets"
    )


if __name__ == "__main__":
    main()
