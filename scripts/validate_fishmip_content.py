#!/usr/bin/env python3
"""Validate complete pinned FishMIP total-catch files without SCC inference."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import xarray as xr


EXPECTED_LAT = np.arange(89.5, -90.0, -1.0)
EXPECTED_LON = np.arange(-179.5, 180.0, 1.0)
MODEL_TIME = {
    "boats": {
        "units": "months since 1601-01-01 00:00:00",
        "calendar": "360_day",
    },
    "ecoocean": {
        "units": "days since 1601-1-1 00:00:00",
        "calendar": "365_day",
    },
}
NOLEAP_MONTH_START = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334], dtype=float)


def expected_time(row: dict[str, str]) -> tuple[np.ndarray, str, str]:
    model = row["model"]
    if model not in MODEL_TIME:
        raise ValueError(f"unsupported FishMIP model time encoding: {model}")
    start_year = int(row["start_year"])
    end_year = int(row["end_year"])
    if model == "boats":
        values = np.arange((start_year - 1601) * 12, (end_year - 1601 + 1) * 12, dtype=float)
    else:
        values = np.concatenate(
            [(year - 1601) * 365 + NOLEAP_MONTH_START for year in range(start_year, end_year + 1)]
        )
    time = MODEL_TIME[model]
    return values, time["units"], time["calendar"]


def checksum(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plan_row(plan: Path, file_name: str) -> dict[str, str]:
    with plan.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if Path(urlparse(row["file_url"]).path).name == file_name]
    if len(rows) != 1:
        raise ValueError(f"expected one acquisition-plan row for {file_name}, got {len(rows)}")
    if rows[0]["acquisition_stage"] != "content_smoke":
        raise ValueError("file is not authorized in the frozen content-smoke stage")
    return rows[0]


def validate(path: Path, row: dict[str, str], *, block_months: int = 24) -> dict[str, object]:
    if block_months < 1:
        raise ValueError("block_months must be positive")
    expected_bytes = int(row["bytes"])
    if path.stat().st_size != expected_bytes:
        raise ValueError("local FishMIP byte size differs from the acquisition plan")
    actual_checksum = checksum(path)
    if actual_checksum != row["sha512"]:
        raise ValueError("local FishMIP SHA-512 differs from the acquisition plan")
    start_year = int(row["start_year"])
    end_year = int(row["end_year"])
    expected_time_values, time_units, time_calendar = expected_time(row)
    totals = {"finite": 0, "missing": 0, "zero": 0, "negative": 0}
    minimum = np.inf
    maximum = -np.inf
    yearly: list[dict[str, object]] = []
    always_finite: np.ndarray | None = None
    always_missing: np.ndarray | None = None
    with xr.open_dataset(path, engine="h5netcdf", decode_times=False) as dataset:
        if set(dataset.data_vars) != {"tc"}:
            raise ValueError(f"expected only tc data variable, got {sorted(dataset.data_vars)}")
        tc = dataset["tc"]
        if tc.dims != ("time", "lat", "lon"):
            raise ValueError(f"unexpected tc dimension order: {tc.dims}")
        if dataset.sizes != {"time": len(expected_time_values), "lat": 180, "lon": 360}:
            raise ValueError(f"unexpected FishMIP dimensions: {dict(dataset.sizes)}")
        if tc.attrs.get("units") != "g m-2":
            raise ValueError("tc units must be g m-2")
        if dataset["time"].attrs.get("units") != time_units:
            raise ValueError("FishMIP time units changed")
        if dataset["time"].attrs.get("calendar") != time_calendar:
            raise ValueError(f"FishMIP calendar must be explicit {time_calendar}")
        if not np.array_equal(dataset["time"].values, expected_time_values):
            raise ValueError("FishMIP time coordinate is not the exact contiguous monthly sequence")
        if not np.array_equal(dataset["lat"].values, EXPECTED_LAT):
            raise ValueError("FishMIP latitude grid changed")
        if not np.array_equal(dataset["lon"].values, EXPECTED_LON):
            raise ValueError("FishMIP longitude grid changed")
        fill = tc.encoding.get("_FillValue")
        missing = tc.encoding.get("missing_value")
        if fill is None or missing is None or not np.isclose(float(fill), float(missing), rtol=1e-6, atol=0):
            raise ValueError("tc fill and missing-value encodings must be explicit and equal")
        if tc.encoding.get("chunksizes") != (1, 180, 360):
            raise ValueError(f"unexpected tc chunking: {tc.encoding.get('chunksizes')}")
        for year_index, year in enumerate(range(start_year, end_year + 1)):
            values = tc.isel(time=slice(year_index * 12, (year_index + 1) * 12)).values
            finite = np.isfinite(values)
            valid = values[finite]
            stats = {
                "year": year,
                "finite": int(finite.sum()),
                "missing": int((~finite).sum()),
                "zero": int((valid == 0).sum()),
                "negative": int((valid < 0).sum()),
                "minimum": float(valid.min()) if valid.size else None,
                "maximum": float(valid.max()) if valid.size else None,
            }
            yearly.append(stats)
            for name in totals:
                totals[name] += int(stats[name])
            if valid.size:
                minimum = min(minimum, float(valid.min()))
                maximum = max(maximum, float(valid.max()))
            finite_cell = finite.all(axis=0)
            missing_cell = (~finite).all(axis=0)
            always_finite = finite_cell if always_finite is None else (always_finite & finite_cell)
            always_missing = missing_cell if always_missing is None else (always_missing & missing_cell)
    if totals["finite"] == 0 or totals["negative"] != 0:
        raise ValueError(f"FishMIP tc contains no finite values or negative catch: {totals}")
    mixed_cells = 180 * 360 - int(always_finite.sum()) - int(always_missing.sum())
    if mixed_cells:
        raise ValueError(f"FishMIP tc has {mixed_cells} grid cells with time-varying missingness")
    return {
        "role": "biophysical_scenario_content_smoke_not_pulse_welfare_or_scc",
        "dataset_id": row["dataset_id"],
        "file_id": row["file_id"],
        "file_name": path.name,
        "model": row["model"],
        "climate_forcing": row["climate_forcing"],
        "climate_scenario": row["climate_scenario"],
        "version": row["version"],
        "bytes": expected_bytes,
        "sha512": actual_checksum,
        "dimensions": {"time": len(expected_time_values), "lat": 180, "lon": 360},
        "calendar": time_calendar,
        "time_units": time_units,
        "units": "g m-2",
        "finite_values": totals["finite"],
        "missing_values": totals["missing"],
        "zero_values": totals["zero"],
        "negative_values": totals["negative"],
        "minimum": minimum,
        "maximum": maximum,
        "always_finite_grid_cells": int(always_finite.sum()),
        "always_missing_grid_cells": int(always_missing.sum()),
        "mixed_validity_grid_cells": mixed_cells,
        "yearly": yearly,
        "result": "passed",
    }


def validate_pair(
    historical_path: Path,
    historical_row: dict[str, str],
    future_path: Path,
    future_row: dict[str, str],
) -> dict[str, object]:
    """Fail closed on a model-specific historical/future content join."""
    if historical_row["climate_scenario"] != "historical":
        raise ValueError("first FishMIP pair file must be historical")
    if future_row["climate_scenario"] in {"historical", "picontrol"}:
        raise ValueError("second FishMIP pair file must be a forced future scenario")
    for field in ("model", "climate_forcing"):
        if historical_row[field] != future_row[field]:
            raise ValueError(f"FishMIP pair differs in {field}")
    if int(future_row["start_year"]) != int(historical_row["end_year"]) + 1:
        raise ValueError("FishMIP pair years are not contiguous")

    historical_audit = validate(historical_path, historical_row)
    future_audit = validate(future_path, future_row)
    expected_combined, units, calendar = expected_time(
        {
            **historical_row,
            "end_year": future_row["end_year"],
        }
    )
    with xr.open_dataset(historical_path, engine="h5netcdf", decode_times=False) as historical, xr.open_dataset(
        future_path, engine="h5netcdf", decode_times=False
    ) as future:
        combined_time = np.concatenate([historical["time"].values, future["time"].values])
        if not np.array_equal(combined_time, expected_combined):
            raise ValueError("FishMIP historical/future time join is not an exact monthly sequence")
        if not np.array_equal(historical["lat"].values, future["lat"].values) or not np.array_equal(
            historical["lon"].values, future["lon"].values
        ):
            raise ValueError("FishMIP historical/future grids differ")
        historical_mask = np.isfinite(historical["tc"].isel(time=0).values)
        future_mask = np.isfinite(future["tc"].isel(time=0).values)
        if not np.array_equal(historical_mask, future_mask):
            raise ValueError("FishMIP historical/future finite/missing masks differ")
    return {
        "role": "biophysical_scenario_join_not_pulse_welfare_or_scc",
        "model": historical_row["model"],
        "climate_forcing": historical_row["climate_forcing"],
        "historical_file": historical_path.name,
        "future_file": future_path.name,
        "future_scenario": future_row["climate_scenario"],
        "calendar": calendar,
        "time_units": units,
        "historical_last_time": float(expected_time(historical_row)[0][-1]),
        "future_first_time": float(expected_time(future_row)[0][0]),
        "grid_cells_with_finite_values": historical_audit["always_finite_grid_cells"],
        "grid_cells_with_missing_values": historical_audit["always_missing_grid_cells"],
        "historical_content_result": historical_audit["result"],
        "future_content_result": future_audit["result"],
        "result": "passed",
    }


def validate_cross_model_support(
    first_path: Path,
    first_row: dict[str, str],
    second_path: Path,
    second_row: dict[str, str],
) -> dict[str, object]:
    """Record explicit common support without coercing model masks."""
    if first_row["model"] == second_row["model"]:
        raise ValueError("cross-model support audit requires two different ecosystem models")
    for field in ("climate_forcing", "climate_scenario", "start_year", "end_year"):
        if first_row[field] != second_row[field]:
            raise ValueError(f"cross-model support files differ in {field}")
    validate(first_path, first_row)
    validate(second_path, second_row)
    with xr.open_dataset(first_path, engine="h5netcdf", decode_times=False) as first, xr.open_dataset(
        second_path, engine="h5netcdf", decode_times=False
    ) as second:
        if not np.array_equal(first["lat"].values, second["lat"].values) or not np.array_equal(
            first["lon"].values, second["lon"].values
        ):
            raise ValueError("cross-model FishMIP grids differ")
        first_mask = np.isfinite(first["tc"].isel(time=0).values)
        second_mask = np.isfinite(second["tc"].isel(time=0).values)
    common = first_mask & second_mask
    union = first_mask | second_mask
    return {
        "role": "biophysical_common_support_audit_not_pulse_welfare_or_scc",
        "first_model": first_row["model"],
        "second_model": second_row["model"],
        "climate_forcing": first_row["climate_forcing"],
        "climate_scenario": first_row["climate_scenario"],
        "first_finite_grid_cells": int(first_mask.sum()),
        "second_finite_grid_cells": int(second_mask.sum()),
        "common_finite_grid_cells": int(common.sum()),
        "union_finite_grid_cells": int(union.sum()),
        "first_only_grid_cells": int((first_mask & ~second_mask).sum()),
        "second_only_grid_cells": int((~first_mask & second_mask).sum()),
        "support_rule": "Retain model-specific flags; use the intersection for direct cross-model comparisons; never fill unsupported cells with zero.",
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    parser.add_argument("--pair-file", type=Path)
    parser.add_argument("--pair-audit-out", type=Path)
    parser.add_argument("--compare-file", type=Path)
    parser.add_argument("--compare-audit-out", type=Path)
    args = parser.parse_args()
    row = plan_row(args.plan, args.file.name)
    audit = validate(args.file, row)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"FishMIP content file passed: finite={audit['finite_values']}, missing={audit['missing_values']}, "
        f"zero={audit['zero_values']}, range={audit['minimum']}..{audit['maximum']}"
    )
    if (args.pair_file is None) != (args.pair_audit_out is None):
        raise ValueError("--pair-file and --pair-audit-out must be supplied together")
    if args.pair_file is not None:
        pair_row = plan_row(args.plan, args.pair_file.name)
        pair_audit = validate_pair(args.file, row, args.pair_file, pair_row)
        args.pair_audit_out.parent.mkdir(parents=True, exist_ok=True)
        args.pair_audit_out.write_text(json.dumps(pair_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(
            f"FishMIP pair passed: {pair_audit['model']} {pair_audit['historical_last_time']} -> "
            f"{pair_audit['future_first_time']} ({pair_audit['calendar']})"
        )
    if (args.compare_file is None) != (args.compare_audit_out is None):
        raise ValueError("--compare-file and --compare-audit-out must be supplied together")
    if args.compare_file is not None:
        compare_row = plan_row(args.plan, args.compare_file.name)
        compare_audit = validate_cross_model_support(args.file, row, args.compare_file, compare_row)
        args.compare_audit_out.parent.mkdir(parents=True, exist_ok=True)
        args.compare_audit_out.write_text(
            json.dumps(compare_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            f"FishMIP common support passed: common={compare_audit['common_finite_grid_cells']}, "
            f"first-only={compare_audit['first_only_grid_cells']}, "
            f"second-only={compare_audit['second_only_grid_cells']}"
        )


if __name__ == "__main__":
    main()
