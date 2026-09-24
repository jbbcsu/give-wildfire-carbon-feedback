#!/usr/bin/env python3
"""Build Hultgren maize weather bases from global daily files under bounded RAM.

The output is an alternative-product grid transport input, not a reproduction
of the paper's GMFD/SAGE administrative-unit weather.  Nonlinear transforms
are completed at grid-cell/regime level before any later spatial aggregation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
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

import sys
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import season_months, source_month_from_day
from src.hultgren_maize_weather import single_sine_degree_days_above_array


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def recorded_path(path: Path) -> str:
    """Prefer project-relative provenance paths without hiding external inputs."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_support(calendar_path: Path, area_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    with xr.open_dataset(calendar_path, engine="h5netcdf", decode_timedelta=False, cache=False) as dataset:
        require(set(("planting_day", "maturity_day")) <= set(dataset.data_vars), "calendar variables absent")
        latitude = np.asarray(dataset.lat.values, dtype=np.float64)
        longitude = np.asarray(dataset.lon.values, dtype=np.float64)
        require(np.array_equal(latitude, 89.75 - 0.5 * np.arange(360)), "calendar latitude grid changed")
        require(np.array_equal(longitude, -179.75 + 0.5 * np.arange(720)), "calendar longitude grid changed")
        planting = np.asarray(dataset.planting_day.values, dtype=np.float64)
        maturity = np.asarray(dataset.maturity_day.values, dtype=np.float64)
    with rasterio.open(area_path) as area_source:
        require(area_source.shape == (360, 720), "MIRCA area grid shape changed")
        require(area_source.crs == rasterio.crs.CRS.from_epsg(4326), "MIRCA CRS changed")
        area = np.asarray(area_source.read(1), dtype=np.float64)
    base = (area > 0) & np.isfinite(area) & np.isfinite(planting) & np.isfinite(maturity)
    rows, cols = np.nonzero(base)
    plant_month = np.fromiter((source_month_from_day(planting[i, j]) for i, j in zip(rows, cols, strict=True)), dtype=np.int16)
    harvest_month = np.fromiter((source_month_from_day(maturity[i, j]) for i, j in zip(rows, cols, strict=True)), dtype=np.int16)
    month_count = np.fromiter((len(season_months(p, h)) for p, h in zip(plant_month, harvest_month, strict=True)), dtype=np.int16)
    eligible = (month_count >= 4) & (month_count <= 10)
    frame = pd.DataFrame({
        "native_lat_index": rows[eligible].astype(np.int16),
        "native_lon_index": cols[eligible].astype(np.int16),
        "latitude": latitude[rows[eligible]],
        "longitude": longitude[cols[eligible]],
        "planting_day": planting[rows[eligible], cols[eligible]],
        "maturity_day": maturity[rows[eligible], cols[eligible]],
        "plant_month": plant_month[eligible],
        "harvest_month": harvest_month[eligible],
        "season_months": month_count[eligible],
        "mirca_area_ha": area[rows[eligible], cols[eligible]],
    })
    audit = {
        "positive_area_calendar_cells": int(len(rows)),
        "eligible_four_to_ten_month_cells": int(eligible.sum()),
        "excluded_short_or_long_calendar_cells": int((~eligible).sum()),
        "positive_area_ha": float(area[base].sum()),
        "eligible_area_ha": float(area[rows[eligible], cols[eligible]].sum()),
        "eligible_area_fraction": float(area[rows[eligible], cols[eligible]].sum() / area[base].sum()),
        "season_month_count_distribution": {
            str(value): int(np.count_nonzero(month_count[eligible] == value))
            for value in sorted(set(month_count[eligible]))
        },
        "all_support_season_month_count_distribution": {
            str(value): int(np.count_nonzero(month_count == value))
            for value in sorted(set(month_count))
        },
        "all_support_area_ha_by_season_month_count": {
            str(value): float(area[rows[month_count == value], cols[month_count == value]].sum())
            for value in sorted(set(month_count))
        },
    }
    require(len(frame) > 0 and audit["eligible_area_fraction"] > 0.95, "insufficient eligible crop support")
    return frame, audit


def validate_sources(
    pr: xr.Dataset, tmin: xr.Dataset, tmax: xr.Dataset, start_year: int, end_year: int
) -> pd.DatetimeIndex:
    for dataset, variable, units in (
        (pr, "pr", "kg m-2 s-1"), (tmin, "tasmin", "K"), (tmax, "tasmax", "K")
    ):
        require(variable in dataset and dataset[variable].dims == ("time", "lat", "lon"), f"{variable} schema changed")
        require(dataset[variable].attrs.get("units") == units, f"{variable} units changed")
        require(np.array_equal(dataset.lat.values, 89.75 - 0.5 * np.arange(360)), f"{variable} latitude changed")
        require(np.array_equal(dataset.lon.values, -179.75 + 0.5 * np.arange(720)), f"{variable} longitude changed")
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
) -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    rows = support.native_lat_index.to_numpy(dtype=np.int64)
    cols = support.native_lon_index.to_numpy(dtype=np.int64)
    flat = rows * 720 + cols
    months = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-01", freq="MS")
    shape = (len(months), len(support))
    rain = np.zeros(shape, dtype=np.float64)
    dd8 = np.zeros(shape, dtype=np.float64)
    dd31 = np.zeros(shape, dtype=np.float64)
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
            require(not np.any(daily_rain[complete] < -1e-10), "negative precipitation on crop support")
            margin = daily_max[complete] - daily_min[complete]
            if margin.size:
                minimum_margin = min(minimum_margin, float(margin.min()))
            require(not np.any(margin < -5e-5), "Tmax below Tmin on crop support")
            month_index = (day.year - start_year) * 12 + day.month - 1
            if np.any(complete):
                lo = daily_min[complete]
                hi = daily_max[complete]
                rain[month_index, complete] += np.maximum(daily_rain[complete], 0.0)
                dd8[month_index, complete] += single_sine_degree_days_above_array(lo, hi, 8.0)
                dd31[month_index, complete] += single_sine_degree_days_above_array(lo, hi, 31.0)
                counts[month_index, complete] += 1
    expected_counts = months.days_in_month.to_numpy(dtype=np.int16)[:, None]
    complete_months = counts == expected_counts
    rain[~complete_months] = np.nan
    dd8[~complete_months] = np.nan
    dd31[~complete_months] = np.nan
    audit = {
        "daily_steps": len(dates),
        "support_cells": len(support),
        "support_missing_daily_triplets": missing_triplets,
        "incomplete_cell_months": int(np.count_nonzero(~complete_months)),
        "minimum_tmax_minus_tmin_c": minimum_margin,
    }
    return months, rain, dd8, dd31, audit


def crop_month_keys(harvest_year: int, plant_month: int, harvest_month: int) -> tuple[tuple[int, int], ...]:
    months = season_months(plant_month, harvest_month)
    cross_year = plant_month >= harvest_month
    return tuple(
        (harvest_year - 1 if cross_year and month >= plant_month else harvest_year, month)
        for month in months
    )


def assemble(
    months: pd.DatetimeIndex,
    rain: np.ndarray,
    dd8: np.ndarray,
    dd31: np.ndarray,
    support: pd.DataFrame,
    harvest_years: range,
) -> pd.DataFrame:
    month_lookup = {(value.year, value.month): index for index, value in enumerate(months)}
    rows: list[dict[str, object]] = []
    for cell, record in support.iterrows():
        for harvest_year in harvest_years:
            keys = crop_month_keys(harvest_year, int(record.plant_month), int(record.harvest_month))
            if not all(key in month_lookup for key in keys):
                raise ValueError(f"source period does not contain season {keys}")
            indices = [month_lookup[key] for key in keys]
            monthly_rain = rain[indices, cell]
            monthly_dd8 = dd8[indices, cell]
            monthly_dd31 = dd31[indices, cell]
            complete = bool(
                np.isfinite(monthly_rain).all()
                and np.isfinite(monthly_dd8).all()
                and np.isfinite(monthly_dd31).all()
            )
            phase_slices = (slice(0, 1), slice(1, 4), slice(4, None))
            values: dict[str, object] = {
                "harvest_year": harvest_year,
                "native_lat_index": int(record.native_lat_index),
                "native_lon_index": int(record.native_lon_index),
                "latitude": float(record.latitude),
                "longitude": float(record.longitude),
                "plant_month": int(record.plant_month),
                "harvest_month": int(record.harvest_month),
                "season_months": len(keys),
                "cross_year": int(record.plant_month) >= int(record.harvest_month),
                "mirca_area_ha": float(record.mirca_area_ha),
                "complete": complete,
                "gdd": float(np.sum(monthly_dd8 - monthly_dd31)) if complete else np.nan,
                "kdd": float(np.sum(monthly_dd31)) if complete else np.nan,
            }
            for phase, selected in enumerate(phase_slices, start=1):
                part = monthly_rain[selected]
                values[f"prcp_poly_1_bin{phase}"] = float(np.sum(part)) if complete else np.nan
                values[f"prcp_poly_2_bin{phase}"] = float(np.sum(part * part)) if complete else np.nan
            rows.append(values)
    return pd.DataFrame(rows)


def write_year_batches(
    output_path: Path,
    months: pd.DatetimeIndex,
    rain: np.ndarray,
    dd8: np.ndarray,
    dd31: np.ndarray,
    support: pd.DataFrame,
    harvest_years: range,
) -> tuple[int, list[str]]:
    """Write one harvest year at a time to bound Python object memory."""
    partial_path = output_path.with_suffix(output_path.suffix + ".partial")
    require(not partial_path.exists(), "stale partial output must be reviewed or removed")
    writer: pq.ParquetWriter | None = None
    rows_written = 0
    columns: list[str] = []
    try:
        for harvest_year in harvest_years:
            batch = assemble(months, rain, dd8, dd31, support, range(harvest_year, harvest_year + 1))
            require(len(batch) == len(support), "annual output row count differs")
            require(batch.complete.all(), f"one or more crop seasons are incomplete for {harvest_year}")
            numeric = ["gdd", "kdd", *[f"prcp_poly_{p}_bin{b}" for p in (1, 2) for b in (1, 2, 3)]]
            require(np.isfinite(batch[numeric].to_numpy()).all(), f"nonfinite basis for {harvest_year}")
            table = pa.Table.from_pandas(batch, preserve_index=False)
            if writer is None:
                columns = list(batch.columns)
                writer = pq.ParquetWriter(partial_path, table.schema, compression="zstd")
            writer.write_table(table)
            rows_written += len(batch)
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
    parser.add_argument("--area", type=Path, required=True)
    parser.add_argument("--regime", choices=("rainfed", "irrigated"), required=True)
    parser.add_argument("--source-start-year", type=int, required=True)
    parser.add_argument("--source-end-year", type=int, required=True)
    parser.add_argument("--harvest-year-start", type=int, required=True)
    parser.add_argument("--harvest-year-end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    result_path = args.output.with_suffix(args.output.suffix + ".result.json")
    require(not result_path.exists(), "fresh result receipt required")
    require(args.source_start_year <= args.harvest_year_start <= args.harvest_year_end <= args.source_end_year, "year range invalid")

    started = time.perf_counter()
    support, support_audit = load_support(args.calendar, args.area)
    months, rain, dd8, dd31, stream_audit = stream_monthly(
        args.pr, args.tasmin, args.tasmax, support, args.source_start_year, args.source_end_year
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_rows, output_columns = write_year_batches(
        args.output,
        months,
        rain,
        dd8,
        dd31,
        support,
        range(args.harvest_year_start, args.harvest_year_end + 1),
    )
    expected_rows = len(support) * (args.harvest_year_end - args.harvest_year_start + 1)
    require(output_rows == expected_rows, "output row count differs")
    result = {
        "schema": "hultgren_grid_weather_basis/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_alternative_product_grid_basis_not_administrative_response_damage_or_scc",
        "regime": args.regime,
        "source_period": [args.source_start_year, args.source_end_year],
        "harvest_years": [args.harvest_year_start, args.harvest_year_end],
        "sources": {
            name: {"path": recorded_path(path), "bytes": path.stat().st_size, "sha512": digest(path, "sha512")}
            for name, path in (("pr", args.pr), ("tasmin", args.tasmin), ("tasmax", args.tasmax))
        },
        "support_sources": {
            "calendar": {"path": recorded_path(args.calendar), "bytes": args.calendar.stat().st_size, "sha256": digest(args.calendar)},
            "area": {"path": recorded_path(args.area), "bytes": args.area.stat().st_size, "sha256": digest(args.area)},
        },
        "support_audit": support_audit,
        "stream_audit": stream_audit,
        "output": {
            "path": recorded_path(args.output),
            "rows": output_rows,
            "columns": output_columns,
            "bytes": args.output.stat().st_size,
            "sha256": digest(args.output),
        },
        "transformation": {
            "calendar": "whole calendar months from GGCMI day-of-year planting/maturity",
            "temperature": "Snyder single-sine daily Tmin/Tmax; GDD 8-31 C and KDD above 31 C",
            "precipitation": "daily-to-monthly totals; phase linear sums and sums of monthly squares",
            "phases": ["month 1", "months 2-4", "month 5 through harvest"],
            "order": "nonlinear basis at grid-cell/regime level before spatial or irrigation aggregation",
        },
        "claim_gates": {
            "grid_basis_complete": True,
            "source_gmfd_sage_replication": False,
            "administrative_aggregation_validated": False,
            "future_yield_response_validated": False,
            "damage_validated": False,
            "scc_validated": False,
        },
        "wall_seconds": time.perf_counter() - started,
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": result["output"], "support_audit": support_audit}, indent=2))


if __name__ == "__main__":
    main()
