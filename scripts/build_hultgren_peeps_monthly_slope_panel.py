#!/usr/bin/env python3
"""Map published PEEPS monthly precipitation slopes to crop-calendar cells."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_hultgren_monthly_precip_climatology import CALENDAR_COLUMNS, MAX_MONTHS, RAIN_COLUMNS, RAIN_SQUARED_COLUMNS
from build_hultgren_precip_basis_climatology import require
from extract_peeps_full_month_mpi import MODEL, MONTHS, OUTER_MD5, SCENARIO
from probe_peeps_december_crop_support import nearest_circular, nearest_linear

ROOT = Path(__file__).resolve().parents[1]
SLOPE_COLUMNS = [f"crop_month_offset_{index:02d}_peeps_slope_kg_m2_s_K" for index in range(1, MAX_MONTHS + 1)]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monthly", type=Path, required=True)
    parser.add_argument("--monthly-receipt", type=Path, required=True)
    parser.add_argument("--peeps-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    monthly_receipt = json.loads(args.monthly_receipt.read_text())
    peeps_receipt = json.loads(args.peeps_receipt.read_text())
    require(monthly_receipt["schema"] == "hultgren_monthly_precip_climatology/v1", "monthly receipt differs")
    require(monthly_receipt["output"]["sha256"] == digest(args.monthly), "monthly hash differs")
    require(peeps_receipt["status"] == "whole_author_archive_md5_verified_selected_members_acquired", "PEEPS source status differs")
    require(peeps_receipt["outer_archive_md5"] == OUTER_MD5, "PEEPS archive MD5 differs")
    require(peeps_receipt["model"] == MODEL and peeps_receipt["scenario"] == SCENARIO, "PEEPS model/scenario differs")
    require(peeps_receipt["selected_months"] == list(MONTHS), "PEEPS month order differs")

    frame = pd.read_parquet(args.monthly)
    keys = ["regime", "native_lat_index", "native_lon_index"]
    require(not frame.duplicated(keys).any(), "duplicate monthly support")
    require(frame.season_months.between(4, MAX_MONTHS).all(), "season length differs")
    latitude = frame.latitude.to_numpy(dtype=np.float64)
    longitude = frame.longitude.to_numpy(dtype=np.float64)
    mapped_i = mapped_j = grid_lat = grid_lon = None
    slope_by_month = []
    sentinels = np.linspace(0, len(frame) - 1, 100, dtype=int)
    source_records = []
    for month_number, (month, item) in enumerate(zip(MONTHS, peeps_receipt["selected_members"], strict=True), 1):
        expected_name = f"{MODEL}_{SCENARIO}_pr_monthly_patterns_{month}.nc"
        path = args.peeps_receipt.parent / expected_name
        require(item["name"] == expected_name and path.is_file(), f"PEEPS month missing: {month}")
        require(path.stat().st_size == item["bytes"] and digest(path) == item["sha256"], f"PEEPS month hash differs: {month}")
        with xr.open_dataset(path, cache=False) as dataset:
            require(dict(dataset.sizes) == {"param": 1, "lat": 192, "lon": 384}, f"PEEPS dimensions differ: {month}")
            require(dataset.attrs.get("source_id") == MODEL and dataset.attrs.get("experiment_id") == SCENARIO, f"PEEPS metadata differs: {month}")
            require(dataset.attrs.get("variable_id") == "pr" and dataset.attrs.get("variable_units") == "kg m-2 s-1", f"PEEPS units differ: {month}")
            this_lat = np.asarray(dataset.lat.values, dtype=np.float64)
            this_lon = np.asarray(dataset.lon.values, dtype=np.float64)
            if grid_lat is None:
                grid_lat, grid_lon = this_lat, this_lon
                mapped_i = nearest_linear(latitude, grid_lat)
                mapped_j = nearest_circular(longitude, grid_lon)
                for index in sentinels:
                    require(mapped_i[index] == int(np.argmin(np.abs(grid_lat - latitude[index]))), "latitude mapping sentinel failed")
                    require(mapped_j[index] == int(np.argmin(np.abs(((grid_lon - longitude[index] + 180) % 360) - 180))), "longitude mapping sentinel failed")
            else:
                require(np.array_equal(this_lat, grid_lat) and np.array_equal(this_lon, grid_lon), "PEEPS monthly grids differ")
            slope = np.asarray(dataset.slope.values[0], dtype=np.float64)
            require(np.isfinite(slope).all(), f"nonfinite PEEPS slope: {month}")
            slope_by_month.append(slope[mapped_i, mapped_j])
        source_records.append({"month": month_number, "path": str(path), "bytes": path.stat().st_size, "sha256": item["sha256"]})

    slopes = np.stack(slope_by_month)
    calendar = frame[CALENDAR_COLUMNS].to_numpy(dtype=np.int16)
    output_slopes = np.zeros((len(frame), MAX_MONTHS), dtype=np.float64)
    row_index = np.arange(len(frame))
    for offset in range(MAX_MONTHS):
        active = calendar[:, offset] > 0
        output_slopes[active, offset] = slopes[calendar[active, offset] - 1, row_index[active]]
    require(np.isfinite(output_slopes).all(), "nonfinite mapped slopes")
    for offset, name in enumerate(SLOPE_COLUMNS):
        frame[name] = output_slopes[:, offset]
    keep = keys + ["latitude", "longitude", "plant_month", "harvest_month", "season_months", "mirca_area_ha", *CALENDAR_COLUMNS, *RAIN_COLUMNS, *RAIN_SQUARED_COLUMNS, *SLOPE_COLUMNS]
    output = frame[keep].copy()
    output.to_parquet(args.output, index=False, compression="zstd")
    require(args.output.stat().st_size < 64 * 2**20, "mapped slope output exceeds 64 MiB")

    native = mapped_i * len(grid_lon) + mapped_j
    total_area = float(output.mirca_area_ha.sum())
    mapped_area = float(np.bincount(native, weights=output.mirca_area_ha.to_numpy(), minlength=len(grid_lat) * len(grid_lon)).sum())
    require(np.isclose(total_area, mapped_area, rtol=1e-12, atol=0), "crop area not conserved")
    result = {
        "schema": "hultgren_peeps_monthly_slope_panel/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_published_monthly_slope_input_not_response_damage_or_scc",
        "definition": "PEEPS MPI-ESM1-2-HR SSP5-8.5 monthly precipitation slopes mapped by nearest native grid center to each rainfed and irrigated crop-calendar cell",
        "monthly_input": {"path": str(args.monthly), "sha256": digest(args.monthly), "receipt": str(args.monthly_receipt), "receipt_sha256": digest(args.monthly_receipt)},
        "peeps_input": {"receipt": str(args.peeps_receipt), "receipt_sha256": digest(args.peeps_receipt), "outer_archive_md5": OUTER_MD5, "license": peeps_receipt["source_license"], "sources": source_records},
        "mapping": {"method": "nearest native latitude and circular-longitude grid center", "rows": len(output), "mapped_native_cells": int(np.unique(native).size), "sentinel_rows": len(sentinels), "total_crop_area_ha": total_area, "area_conserved": True},
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output), "slope_columns": SLOPE_COLUMNS},
        "limitations": ["One ESM and one scenario; structural sensitivity only.", "Slopes describe monthly mean precipitation and not daily dry spells, extremes, or drought.", "No PEEPS intercept or absolute fitted precipitation level is used.", "No FAIR pulse, crop response, damage, or SCC is evaluated here."],
        "claim_gates": {"published_monthly_slope_input": True, "marginal_response": False, "damage": False, "scc": False},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "mapping": result["mapping"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
