#!/usr/bin/env python3
"""Build an unweighted, season-specific historical rice weather basis.

This is a transport preflight for one GGCMI rice calendar branch.  The broad
annual MIRCA rice rasters are used only as a positive-support mask: their
values are never emitted or used as weights, and the two calendar branches
must be built and interpreted separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import season_months, source_month_from_day
from src.hultgren_maize_weather import single_sine_degree_days_above_array

WEATHER = [
    "gdd", "kdd", "tmin",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]
MEMORY_CEILING_BYTES = 512 * 1024 * 1024


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def recorded_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def peak_rss_bytes() -> int:
    maximum = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return maximum if sys.platform == "darwin" else maximum * 1024


def load_support(
    calendar_path: Path, annual_rice_irrigated_path: Path, annual_rice_rainfed_path: Path
) -> tuple[pd.DataFrame, dict[str, object]]:
    with xr.open_dataset(
        calendar_path, engine="h5netcdf", decode_timedelta=False, cache=False
    ) as dataset:
        require(
            {"planting_day", "maturity_day"} <= set(dataset.data_vars),
            "calendar variables absent",
        )
        latitude = np.asarray(dataset.lat.values, dtype=np.float64)
        longitude = np.asarray(dataset.lon.values, dtype=np.float64)
        require(
            np.array_equal(latitude, 89.75 - 0.5 * np.arange(360)),
            "calendar latitude grid changed",
        )
        require(
            np.array_equal(longitude, -179.75 + 0.5 * np.arange(720)),
            "calendar longitude grid changed",
        )
        planting = np.asarray(dataset.planting_day.values, dtype=np.float64)
        maturity = np.asarray(dataset.maturity_day.values, dtype=np.float64)

    masks = []
    for path in (annual_rice_irrigated_path, annual_rice_rainfed_path):
        with rasterio.open(path) as source:
            require(source.shape == (360, 720), "annual MIRCA rice grid shape changed")
            require(
                source.crs == rasterio.crs.CRS.from_epsg(4326),
                "annual MIRCA rice CRS changed",
            )
            values = np.asarray(source.read(1), dtype=np.float64)
            masks.append(np.isfinite(values) & (values > 0.0))
    annual_support = masks[0] | masks[1]
    calendar_support = annual_support & np.isfinite(planting) & np.isfinite(maturity)
    rows, cols = np.nonzero(calendar_support)
    plant_month = np.fromiter(
        (source_month_from_day(planting[i, j]) for i, j in zip(rows, cols, strict=True)),
        dtype=np.int16,
    )
    harvest_month = np.fromiter(
        (source_month_from_day(maturity[i, j]) for i, j in zip(rows, cols, strict=True)),
        dtype=np.int16,
    )
    month_count = np.fromiter(
        (len(season_months(p, h)) for p, h in zip(plant_month, harvest_month, strict=True)),
        dtype=np.int16,
    )
    eligible = (month_count >= 6) & (month_count <= 12)
    frame = pd.DataFrame(
        {
            "native_lat_index": rows[eligible].astype(np.int16),
            "native_lon_index": cols[eligible].astype(np.int16),
            "latitude": latitude[rows[eligible]],
            "longitude": longitude[cols[eligible]],
            "planting_day": planting[rows[eligible], cols[eligible]],
            "maturity_day": maturity[rows[eligible], cols[eligible]],
            "plant_month": plant_month[eligible],
            "harvest_month": harvest_month[eligible],
            "season_months": month_count[eligible],
        }
    )
    distribution = {
        str(int(value)): int(np.count_nonzero(month_count == value))
        for value in sorted(set(month_count.tolist()))
    }
    audit = {
        "annual_positive_rice_cells": int(np.count_nonzero(annual_support)),
        "annual_positive_rice_cells_with_finite_calendar": int(len(rows)),
        "eligible_six_to_twelve_month_cells": int(np.count_nonzero(eligible)),
        "excluded_three_to_five_month_cells": int(np.count_nonzero(~eligible)),
        "eligible_cell_fraction_of_finite_calendar_support": float(np.mean(eligible)),
        "calendar_month_count_distribution": distribution,
        "annual_mirca_values_used_as_weights": False,
        "annual_mirca_values_emitted": False,
    }
    require(not frame.empty, "no eligible positive-rice calendar support")
    return frame, audit


def validate_sources(
    pr: xr.Dataset, tmin: xr.Dataset, tmax: xr.Dataset, start_year: int, end_year: int
) -> pd.DatetimeIndex:
    for dataset, variable, units in (
        (pr, "pr", "kg m-2 s-1"),
        (tmin, "tasmin", "K"),
        (tmax, "tasmax", "K"),
    ):
        require(
            variable in dataset and dataset[variable].dims == ("time", "lat", "lon"),
            f"{variable} schema changed",
        )
        require(dataset[variable].attrs.get("units") == units, f"{variable} units changed")
        require(
            np.array_equal(dataset.lat.values, 89.75 - 0.5 * np.arange(360)),
            f"{variable} latitude changed",
        )
        require(
            np.array_equal(dataset.lon.values, -179.75 + 0.5 * np.arange(720)),
            f"{variable} longitude changed",
        )
    dates = pd.DatetimeIndex(pr.time.values).normalize()
    require(dates.equals(pd.DatetimeIndex(tmin.time.values).normalize()), "pr/tasmin dates differ")
    require(dates.equals(pd.DatetimeIndex(tmax.time.values).normalize()), "pr/tasmax dates differ")
    expected = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="D")
    require(dates.equals(expected), "daily chronology differs from declared full-year period")
    return dates


def stream_monthly(
    pr_path: Path,
    tmin_path: Path,
    tmax_path: Path,
    support: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> tuple[pd.DatetimeIndex, dict[str, np.ndarray], dict[str, object]]:
    flat = (
        support.native_lat_index.to_numpy(dtype=np.int64) * 720
        + support.native_lon_index.to_numpy(dtype=np.int64)
    )
    months = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-01", freq="MS")
    shape = (len(months), len(support))
    arrays = {
        "rain": np.zeros(shape, dtype=np.float64),
        "dd14": np.zeros(shape, dtype=np.float64),
        "dd30": np.zeros(shape, dtype=np.float64),
        "tmin_sum": np.zeros(shape, dtype=np.float64),
    }
    counts = np.zeros(shape, dtype=np.int16)
    minimum_margin = math.inf
    missing_triplets = 0
    with xr.open_dataset(pr_path, engine="h5netcdf", decode_times=True, cache=False) as pr, xr.open_dataset(
        tmin_path, engine="h5netcdf", decode_times=True, cache=False
    ) as tmin, xr.open_dataset(tmax_path, engine="h5netcdf", decode_times=True, cache=False) as tmax:
        dates = validate_sources(pr, tmin, tmax, start_year, end_year)
        for position, day in enumerate(dates):
            daily_rain = np.asarray(pr.pr.isel(time=position).values, dtype=np.float64).reshape(-1)[flat] * 86_400.0
            daily_min = np.asarray(tmin.tasmin.isel(time=position).values, dtype=np.float64).reshape(-1)[flat] - 273.15
            daily_max = np.asarray(tmax.tasmax.isel(time=position).values, dtype=np.float64).reshape(-1)[flat] - 273.15
            complete = np.isfinite(daily_rain) & np.isfinite(daily_min) & np.isfinite(daily_max)
            missing_triplets += int(np.count_nonzero(~complete))
            require(not np.any(daily_rain[complete] < -1e-10), "negative precipitation on rice support")
            margin = daily_max[complete] - daily_min[complete]
            if margin.size:
                minimum_margin = min(minimum_margin, float(margin.min()))
            require(not np.any(margin < -5e-5), "Tmax below Tmin on rice support")
            month_index = (day.year - start_year) * 12 + day.month - 1
            if np.any(complete):
                lo, hi = daily_min[complete], daily_max[complete]
                arrays["rain"][month_index, complete] += np.maximum(daily_rain[complete], 0.0)
                arrays["dd14"][month_index, complete] += single_sine_degree_days_above_array(lo, hi, 14.0)
                arrays["dd30"][month_index, complete] += single_sine_degree_days_above_array(lo, hi, 30.0)
                arrays["tmin_sum"][month_index, complete] += lo
                counts[month_index, complete] += 1
    expected_counts = months.days_in_month.to_numpy(dtype=np.int16)[:, None]
    complete_months = counts == expected_counts
    for name in ("rain", "dd14", "dd30"):
        arrays[name][~complete_months] = np.nan
    monthly_tmin = np.full(shape, np.nan, dtype=np.float64)
    monthly_tmin[complete_months] = (
        arrays["tmin_sum"][complete_months] / counts[complete_months]
    )
    arrays["monthly_tmin"] = monthly_tmin
    del arrays["tmin_sum"]
    audit = {
        "daily_steps": len(dates),
        "support_cells": len(support),
        "support_missing_daily_triplets": missing_triplets,
        "incomplete_cell_months": int(np.count_nonzero(~complete_months)),
        "minimum_tmax_minus_tmin_c": minimum_margin,
    }
    return months, arrays, audit


def crop_month_keys(
    harvest_year: int, plant_month: int, harvest_month: int
) -> tuple[tuple[int, int], ...]:
    months = season_months(plant_month, harvest_month)
    cross_year = plant_month >= harvest_month
    return tuple(
        (harvest_year - 1 if cross_year and month >= plant_month else harvest_year, month)
        for month in months
    )


def assemble_year(
    year: int,
    months: pd.DatetimeIndex,
    arrays: dict[str, np.ndarray],
    support: pd.DataFrame,
    branch: str,
) -> pd.DataFrame:
    lookup = {(value.year, value.month): index for index, value in enumerate(months)}
    records: list[dict[str, object]] = []
    for cell, row in support.iterrows():
        keys = crop_month_keys(year, int(row.plant_month), int(row.harvest_month))
        require(all(key in lookup for key in keys), f"source period lacks crop season {keys}")
        indices = [lookup[key] for key in keys]
        rain = arrays["rain"][indices, cell]
        dd14 = arrays["dd14"][indices, cell]
        dd30 = arrays["dd30"][indices, cell]
        monthly_tmin = arrays["monthly_tmin"][indices, cell]
        complete = bool(
            np.isfinite(rain).all()
            and np.isfinite(dd14).all()
            and np.isfinite(dd30).all()
            and np.isfinite(monthly_tmin).all()
        )
        values: dict[str, object] = {
            "calendar_branch": branch,
            "harvest_year": year,
            "native_lat_index": int(row.native_lat_index),
            "native_lon_index": int(row.native_lon_index),
            "latitude": float(row.latitude),
            "longitude": float(row.longitude),
            "plant_month": int(row.plant_month),
            "harvest_month": int(row.harvest_month),
            "season_months": len(keys),
            "cross_year": int(row.plant_month) >= int(row.harvest_month),
            "complete": complete,
            "gdd": float(np.sum(dd14 - dd30)) if complete else np.nan,
            "kdd": float(np.sum(dd30)) if complete else np.nan,
            "tmin": float(np.sum(monthly_tmin)) if complete else np.nan,
        }
        for phase, selected in enumerate((slice(0, 2), slice(2, 5), slice(5, None)), start=1):
            part = rain[selected]
            values[f"prcp_poly_1_bin{phase}"] = float(np.sum(part)) if complete else np.nan
            values[f"prcp_poly_2_bin{phase}"] = float(np.sum(part * part)) if complete else np.nan
        records.append(values)
    return pd.DataFrame(records)


def write_year_batches(
    output_path: Path,
    months: pd.DatetimeIndex,
    arrays: dict[str, np.ndarray],
    support: pd.DataFrame,
    harvest_years: range,
    branch: str,
) -> tuple[int, list[str]]:
    partial_path = output_path.with_suffix(output_path.suffix + ".partial")
    require(not partial_path.exists(), "stale partial output must be reviewed or removed")
    writer: pq.ParquetWriter | None = None
    rows_written = 0
    columns: list[str] = []
    try:
        for year in harvest_years:
            frame = assemble_year(year, months, arrays, support, branch)
            require(len(frame) == len(support), "annual output row count differs")
            require(frame.complete.all(), f"one or more rice seasons are incomplete for {year}")
            require(np.isfinite(frame[WEATHER].to_numpy()).all(), f"nonfinite rice basis for {year}")
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                columns = list(frame.columns)
                writer = pq.ParquetWriter(partial_path, table.schema, compression="zstd")
            writer.write_table(table)
            rows_written += len(frame)
    except Exception:
        if writer is not None:
            writer.close()
        if partial_path.exists():
            partial_path.unlink()
        raise
    require(writer is not None, "no harvest years requested")
    writer.close()
    os.replace(partial_path, output_path)
    return rows_written, columns


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=Path, required=True)
    parser.add_argument("--tasmin", type=Path, required=True)
    parser.add_argument("--tasmax", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--annual-rice-irrigated", type=Path, required=True)
    parser.add_argument("--annual-rice-rainfed", type=Path, required=True)
    parser.add_argument("--calendar-branch", choices=("ri1_noirr", "ri1_firr"), required=True)
    parser.add_argument("--source-start-year", type=int, required=True)
    parser.add_argument("--source-end-year", type=int, required=True)
    parser.add_argument("--harvest-year-start", type=int, required=True)
    parser.add_argument("--harvest-year-end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.output.with_suffix(args.output.suffix + ".result.json")
    require(not args.output.exists() and not result_path.exists(), "fresh outputs required")
    require(
        args.source_start_year <= args.harvest_year_start <= args.harvest_year_end <= args.source_end_year,
        "year range invalid",
    )
    require(args.calendar_branch in args.calendar.name, "calendar path and declared branch differ")

    started = time.perf_counter()
    support, support_audit = load_support(
        args.calendar, args.annual_rice_irrigated, args.annual_rice_rainfed
    )
    months, arrays, stream_audit = stream_monthly(
        args.pr, args.tasmin, args.tasmax, support, args.source_start_year, args.source_end_year
    )
    rows, columns = write_year_batches(
        args.output,
        months,
        arrays,
        support,
        range(args.harvest_year_start, args.harvest_year_end + 1),
        args.calendar_branch,
    )
    expected = len(support) * (args.harvest_year_end - args.harvest_year_start + 1)
    require(rows == expected, "output row count differs")
    observed_peak_rss = peak_rss_bytes()
    require(observed_peak_rss < MEMORY_CEILING_BYTES, "rice basis build exceeded 512 MiB RSS ceiling")
    result = {
        "schema": "hultgren_rice_grid_weather_basis/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_unweighted_rice_calendar_branch_basis_not_response_damage_or_scc",
        "calendar_branch": args.calendar_branch,
        "source_period": [args.source_start_year, args.source_end_year],
        "harvest_years": [args.harvest_year_start, args.harvest_year_end],
        "sources": {
            name: {
                "path": recorded_path(path),
                "bytes": path.stat().st_size,
                "sha512": digest(path, "sha512"),
            }
            for name, path in (("pr", args.pr), ("tasmin", args.tasmin), ("tasmax", args.tasmax))
        },
        "support_sources": {
            name: {"path": recorded_path(path), "bytes": path.stat().st_size, "sha256": digest(path)}
            for name, path in (
                ("calendar", args.calendar),
                ("annual_rice_irrigated", args.annual_rice_irrigated),
                ("annual_rice_rainfed", args.annual_rice_rainfed),
            )
        },
        "support_audit": support_audit,
        "stream_audit": stream_audit,
        "output": {
            "path": recorded_path(args.output),
            "rows": rows,
            "columns": columns,
            "bytes": args.output.stat().st_size,
            "sha256": digest(args.output),
        },
        "transformation": {
            "calendar": "whole months from the declared GGCMI ri1 branch, retained separately",
            "temperature": "Snyder single-sine daily Tmin/Tmax; GDD 14-30 C, KDD above 30 C; Tmin is sum of monthly mean daily minima",
            "precipitation": "daily-to-monthly totals; 2/3/remainder phase sums and sums of monthly squares",
            "support": "boolean union of positive annual MIRCA Rice irrigated/rainfed cells; no MIRCA magnitude retained",
            "aggregation": "none across cells or calendar branches",
        },
        "claim_gates": {
            "calendar_branch_grid_basis_complete": True,
            "annual_rice_used_only_as_boolean_support": True,
            "ri1_ri2_or_calendar_branch_aggregation": False,
            "published_response_evaluated": False,
            "author_application_domain_available": False,
            "damage_validated": False,
            "scc_validated": False,
        },
        "wall_seconds": time.perf_counter() - started,
        "resources": {
            "peak_rss_bytes": observed_peak_rss,
            "memory_ceiling_bytes": MEMORY_CEILING_BYTES,
            "memory_gate_passed": True,
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": result["output"], "support_audit": support_audit}, indent=2))


if __name__ == "__main__":
    main()
