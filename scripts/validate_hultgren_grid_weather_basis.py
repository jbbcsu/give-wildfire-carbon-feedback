#!/usr/bin/env python3
"""Independently validate a bounded Hultgren grid-weather basis output."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_maize_weather import build_maize_weather_basis_from_daily


FEATURES = (
    "gdd", "kdd",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def select_checks(frame: pd.DataFrame) -> pd.DataFrame:
    """Select deterministic geography, calendar, and year checks."""
    years = sorted(frame.harvest_year.unique())
    selected_years = sorted(set((years[0], years[len(years) // 2], years[-1])))
    cells = frame.drop_duplicates(["native_lat_index", "native_lon_index"]).sort_values(
        ["native_lat_index", "native_lon_index"]
    )
    positions = np.linspace(0, len(cells) - 1, 4, dtype=int)
    keys = cells.iloc[positions][["native_lat_index", "native_lon_index"]]
    checks = frame.merge(keys, on=["native_lat_index", "native_lon_index"], how="inner")
    checks = checks[checks.harvest_year.isin(selected_years)]
    # Ensure at least one cross-year season is audited if one exists.
    cross = frame[frame.cross_year].sort_values(
        ["harvest_year", "native_lat_index", "native_lon_index"]
    ).head(1)
    return pd.concat([checks, cross]).drop_duplicates()


def scalar_recompute(
    row: pd.Series,
    dates: pd.DatetimeIndex,
    rain: np.ndarray,
    minimum: np.ndarray,
    maximum: np.ndarray,
) -> dict[str, float]:
    records = (
        (stamp.date(), float(r), float(lo), float(hi))
        for stamp, r, lo, hi in zip(dates, rain, minimum, maximum, strict=True)
    )
    basis = build_maize_weather_basis_from_daily(
        records,
        report_year=int(row.harvest_year),
        plant_month=int(row.plant_month),
        harvest_month=int(row.harvest_month),
        iso="USA",  # generic physical-harvest-year rule; no India reporting-year relabeling
    )
    return {
        "gdd": basis.gdd,
        "kdd": basis.kdd,
        "prcp_poly_1_bin1": basis.prcp_poly_1_bins[0],
        "prcp_poly_1_bin2": basis.prcp_poly_1_bins[1],
        "prcp_poly_1_bin3": basis.prcp_poly_1_bins[2],
        "prcp_poly_2_bin1": basis.prcp_poly_2_bins[0],
        "prcp_poly_2_bin2": basis.prcp_poly_2_bins[1],
        "prcp_poly_2_bin3": basis.prcp_poly_2_bins[2],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", type=Path, required=True)
    parser.add_argument("--builder-receipt", type=Path, required=True)
    parser.add_argument("--pr", type=Path, required=True)
    parser.add_argument("--tasmin", type=Path, required=True)
    parser.add_argument("--tasmax", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation receipt required")

    builder = json.loads(args.builder_receipt.read_text(encoding="utf-8"))
    require(builder["status"].startswith("complete_alternative_product_grid_basis"), "builder status failed")
    require(digest(args.basis) == builder["output"]["sha256"], "basis hash differs from builder receipt")
    metadata = pq.read_metadata(args.basis)
    require(metadata.num_rows == builder["output"]["rows"], "Parquet row count differs")
    requested_years = builder["harvest_years"][1] - builder["harvest_years"][0] + 1
    require(metadata.num_row_groups == requested_years, "expected one Parquet row group per harvest year")

    frame = pd.read_parquet(args.basis)
    require(len(frame) == len(frame.drop_duplicates(["harvest_year", "native_lat_index", "native_lon_index"])), "duplicate cell-year")
    require(frame.complete.all(), "incomplete rows present")
    require(np.isfinite(frame[list(FEATURES)].to_numpy()).all(), "nonfinite features present")
    require((frame.gdd >= 0).all() and (frame.kdd >= 0).all(), "negative temperature exposure")
    require((frame[[name for name in FEATURES if name.startswith("prcp")]] >= 0).all().all(), "negative precipitation basis")

    checks = select_checks(frame)
    differences = []
    with xr.open_dataset(args.pr, engine="h5netcdf", cache=False) as pr, xr.open_dataset(
        args.tasmin, engine="h5netcdf", cache=False
    ) as tmin, xr.open_dataset(args.tasmax, engine="h5netcdf", cache=False) as tmax:
        dates = pd.DatetimeIndex(pr.time.values).normalize()
        require(dates.equals(pd.DatetimeIndex(tmin.time.values).normalize()), "raw dates differ")
        require(dates.equals(pd.DatetimeIndex(tmax.time.values).normalize()), "raw dates differ")
        cell_cache: dict[tuple[int, int], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        for _, row in checks.iterrows():
            key = (int(row.native_lat_index), int(row.native_lon_index))
            if key not in cell_cache:
                i, j = key
                cell_cache[key] = (
                    np.asarray(pr.pr[:, i, j].values, dtype=np.float64) * 86_400.0,
                    np.asarray(tmin.tasmin[:, i, j].values, dtype=np.float64) - 273.15,
                    np.asarray(tmax.tasmax[:, i, j].values, dtype=np.float64) - 273.15,
                )
            expected = scalar_recompute(row, dates, *cell_cache[key])
            record = {
                "harvest_year": int(row.harvest_year),
                "native_lat_index": int(row.native_lat_index),
                "native_lon_index": int(row.native_lon_index),
                "cross_year": bool(row.cross_year),
            }
            for feature, value in expected.items():
                record[f"abs_diff_{feature}"] = abs(float(row[feature]) - value)
            differences.append(record)
    maximum_difference = max(value for record in differences for key, value in record.items() if key.startswith("abs_diff_"))
    require(maximum_difference <= 1e-6, "scalar raw-daily recomputation differs")

    grouped = frame.groupby("harvest_year", sort=True).apply(
        lambda group: pd.Series({
            "cells": len(group),
            "area_ha": group.mirca_area_ha.sum(),
            **{
                f"area_weighted_{feature}": np.average(group[feature], weights=group.mirca_area_ha)
                for feature in FEATURES
            },
        }),
        include_groups=False,
    ).reset_index()
    result = {
        "schema": "hultgren_grid_weather_basis_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_grid_basis_not_response_damage_or_scc",
        "basis": {
            "path": str(args.basis.resolve().relative_to(ROOT)),
            "bytes": args.basis.stat().st_size,
            "sha256": digest(args.basis),
            "rows": len(frame),
            "row_groups": metadata.num_row_groups,
        },
        "source_identity_from_builder_receipt": {
            "daily_climate": builder["sources"],
            "support": builder["support_sources"],
            "transformation": builder["transformation"],
            "builder_implementation": builder["implementation"],
        },
        "checks": {
            "unique_cell_years": True,
            "complete_finite_nonnegative": True,
            "raw_daily_scalar_recomputations": len(differences),
            "maximum_absolute_feature_difference": maximum_difference,
            "raw_daily_details": differences,
        },
        "annual_area_weighted_summary": grouped.to_dict(orient="records"),
        "claim_gates": builder["claim_gates"],
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, indent=2))


if __name__ == "__main__":
    main()
