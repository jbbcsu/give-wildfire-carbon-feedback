#!/usr/bin/env python3
"""Build season-specific rice irrigation weights from MIRCA-OS monthly grids.

Rice1 and Rice2 are mapped to the locked GDHY/ISIMIP rice-season outcomes.
Rice3 is retained for annual-area reconciliation and disclosed as uncovered;
it is never folded into either outcome. Passing this input gate estimates no
weather response, damage, or SCC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import Affine
import xarray as xr


VALID_YEARS = (2000, 2005, 2010, 2015, 2020)
SEASONS = (1, 2, 3)
SYSTEMS = ("ir", "rf")
SYSTEM_LABEL = {"ir": "irrigated", "rf": "rainfed"}
OUTCOME_MAP = {1: "ri1", 2: "ri2"}
SOURCE_ROLE = "independent_fixed_baseline_crop_area_share"
FINE_SHAPE = (2160, 4320)
COARSE_SHAPE = (360, 720)
FINE_RESOLUTION = 1.0 / 12.0
EXPECTED_COARSE_TRANSFORM = Affine(0.5, 0.0, -180.0, 0.0, -0.5, 90.0)


class RiceInputGateError(ValueError):
    """Carry a complete fail-closed audit without promoting an output table."""

    def __init__(self, audit: dict[str, object]):
        self.audit = audit
        if audit["status"] == "blocked_failed_annual_reconciliation":
            failed = [
                str(record["system"])
                for record in audit["annual_reconciliation"]  # type: ignore[index]
                if not record["passed"]
            ]
            message = (
                "Rice1+Rice2+Rice3 does not reconcile to annual Rice for "
                + ", ".join(failed)
            )
        else:
            message = "Rice annual reconciliation passed but the outcome crosswalk gate is incomplete"
        super().__init__(message)


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def aggregate_six_by_six(area: np.ndarray) -> np.ndarray:
    if area.ndim != 2 or area.shape[0] % 6 or area.shape[1] % 6:
        raise ValueError("Fine harvested-area array must be two-dimensional and divisible by six")
    if not np.isfinite(area).all() or (area < 0).any():
        raise ValueError("Harvested area must be finite and nonnegative before aggregation")
    return area.reshape(area.shape[0] // 6, 6, area.shape[1] // 6, 6).sum(axis=(1, 3))


def locate_monthly(root: Path, year: int, season: int, system: str) -> Path:
    name = f"MIRCA-OS_Rice{season}_{year}_{system}.nc"
    matches = sorted(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} below {root}; found {len(matches)}")
    return matches[0]


def locate_annual(root: Path, year: int, system: str) -> Path:
    name = f"MIRCA-OS_Rice_{year}_{system}_30arcmin_v2.tif"
    matches = sorted(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} below {root}; found {len(matches)}")
    return matches[0]


def read_monthly_maximum(
    path: Path, year: int, season: int, system: str
) -> tuple[np.ndarray, dict[str, object]]:
    expected_lat = 90.0 - FINE_RESOLUTION / 2 - FINE_RESOLUTION * np.arange(FINE_SHAPE[0])
    expected_lon = -180.0 + FINE_RESOLUTION / 2 + FINE_RESOLUTION * np.arange(FINE_SHAPE[1])
    with xr.open_dataset(path, engine="h5netcdf") as dataset:
        required_dims = {"month": 12, "latitude": FINE_SHAPE[0], "longitude": FINE_SHAPE[1]}
        if any(dataset.sizes.get(name) != size for name, size in required_dims.items()):
            raise ValueError(f"Unexpected monthly rice dimensions in {path}")
        if "harvested_area" not in dataset:
            raise ValueError(f"Missing harvested_area in {path}")
        variable = dataset["harvested_area"]
        if variable.dims != ("month", "latitude", "longitude"):
            raise ValueError(f"Unexpected harvested_area dimension order in {path}")
        if not np.array_equal(dataset.month.values, np.arange(1, 13)):
            raise ValueError(f"Months are not exactly 1..12 in {path}")
        if not np.allclose(dataset.latitude.values, expected_lat, rtol=0.0, atol=2e-10):
            raise ValueError(f"Unexpected 5-arcminute latitude grid in {path}")
        if not np.allclose(dataset.longitude.values, expected_lon, rtol=0.0, atol=2e-10):
            raise ValueError(f"Unexpected 5-arcminute longitude grid in {path}")
        if str(dataset.attrs.get("crop_name")) != f"Rice{season}":
            raise ValueError(f"Crop-name metadata differs in {path}")
        if int(dataset.attrs.get("year")) != year:
            raise ValueError(f"Year metadata differs in {path}")
        if str(dataset.attrs.get("irrigation_type")).strip().lower() != SYSTEM_LABEL[system].lower():
            raise ValueError(f"Irrigation metadata differs in {path}")
        maximum = np.zeros(FINE_SHAPE, dtype=np.float64)
        finite_values = 0
        missing_values = 0
        for month_index in range(12):
            values = np.asarray(variable.isel(month=month_index).values, dtype=np.float64)
            if np.isinf(values).any() or (values[np.isfinite(values)] < 0).any():
                raise ValueError(f"Monthly harvested area is infinite or negative in {path}")
            finite = np.isfinite(values)
            finite_values += int(finite.sum())
            missing_values += int((~finite).sum())
            np.maximum(maximum, np.where(finite, values, 0.0), out=maximum)
    coarse = aggregate_six_by_six(maximum)
    if coarse.shape != COARSE_SHAPE:
        raise AssertionError("5-arcminute aggregation did not produce a 0.5-degree grid")
    return coarse, {
        "file_name": path.name,
        "size_bytes": path.stat().st_size,
        "sha512": sha512(path),
        "finite_month_grid_values": finite_values,
        "missing_month_grid_values": missing_values,
        "annual_maximum_area_ha": float(maximum.sum()),
        "aggregated_area_ha": float(coarse.sum()),
        "variable_units": "ha from the source README; the NetCDF variable omits a units attribute",
    }


def read_annual(path: Path) -> np.ndarray:
    with rasterio.open(path) as dataset:
        if (dataset.height, dataset.width, dataset.count) != (*COARSE_SHAPE, 1):
            raise ValueError(f"Unexpected annual Rice grid in {path}")
        if dataset.crs is None or dataset.crs.to_epsg() != 4326:
            raise ValueError(f"Annual Rice grid is not EPSG:4326 in {path}")
        if not np.allclose(
            tuple(dataset.transform)[:6],
            tuple(EXPECTED_COARSE_TRANSFORM)[:6],
            rtol=0.0,
            atol=1e-9,
        ):
            raise ValueError(f"Unexpected annual Rice grid transform in {path}")
        if dataset.nodata is None or not np.isclose(float(dataset.nodata), 0.0):
            raise ValueError(f"Expected annual Rice zero-area/nodata encoding of 0 in {path}")
        values = dataset.read(1, masked=False).astype(np.float64)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(f"Annual Rice harvested area is invalid in {path}")
    return values


def build_weights(
    monthly_root: Path,
    annual_root: Path,
    year: int,
    *,
    reconciliation_rtol: float = 1e-5,
    reconciliation_atol_ha: float = 0.1,
    outcome_crosswalk_verified: bool = False,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if year not in VALID_YEARS:
        raise ValueError(f"Year must be one of {VALID_YEARS}")
    if reconciliation_rtol < 0 or reconciliation_atol_ha < 0:
        raise ValueError("Reconciliation tolerances must be nonnegative")
    areas: dict[tuple[int, str], np.ndarray] = {}
    input_records: list[dict[str, object]] = []
    for season in SEASONS:
        for system in SYSTEMS:
            path = locate_monthly(monthly_root, year, season, system)
            areas[(season, system)], record = read_monthly_maximum(path, year, season, system)
            record.update({"rice_season": season, "system": system})
            input_records.append(record)

    reconciliation: list[dict[str, object]] = []
    for system in SYSTEMS:
        reconstructed = sum((areas[(season, system)] for season in SEASONS), np.zeros(COARSE_SHAPE))
        annual_path = locate_annual(annual_root, year, system)
        published = read_annual(annual_path)
        difference = np.abs(reconstructed - published)
        passed = bool(
            np.allclose(
                reconstructed,
                published,
                rtol=reconciliation_rtol,
                atol=reconciliation_atol_ha,
            )
        )
        record = {
            "system": system,
            "published_file": annual_path.name,
            "published_sha512": sha512(annual_path),
            "published_area_ha": float(published.sum()),
            "reconstructed_area_ha": float(reconstructed.sum()),
            "absolute_global_difference_ha": float(abs(reconstructed.sum() - published.sum())),
            "maximum_cell_difference_ha": float(difference.max()),
            "cells_above_absolute_tolerance": int((difference > reconciliation_atol_ha).sum()),
            "rtol": reconciliation_rtol,
            "atol_ha": reconciliation_atol_ha,
            "passed": passed,
        }
        reconciliation.append(record)

    source_id = f"MIRCA-OS_v2_MHAG_RiceSeasons_5to30arcmin_{year}"
    rice3_total = areas[(3, "ir")].sum() + areas[(3, "rf")].sum()
    audit_base: dict[str, object] = {
        "schema_version": 1,
        "role": "season_specific_fixed_rice_irrigation_weights_not_response_or_scc",
        "share_year": year,
        "source_id": source_id,
        "fixed_across_outcome_years": True,
        "fine_grid": "global 5 arcminutes EPSG:4326",
        "output_grid": "global 0.5 degrees EPSG:4326; hectares summed in aligned 6x6 blocks",
        "annualization": "maximum monthly area within each rice season, then sum Rice1+Rice2+Rice3 for annual reconciliation",
        "input_files": input_records,
        "annual_reconciliation": reconciliation,
        "reconciliation_all_passed": bool(all(record["passed"] for record in reconciliation)),
        "uncovered_rice3_area_ha": float(rice3_total),
        "uncovered_rice3_rule": "disclose; never fold into ri1 or ri2 or renormalize represented rice",
        "outcome_crosswalk_gate": (
            "passed_by_separate_verified_audit"
            if outcome_crosswalk_verified
            else "not_run_pending_Rice1_Rice2_timing_and_spatial_support_audit"
        ),
        "scc_authorized": False,
    }
    if not audit_base["reconciliation_all_passed"]:
        audit_base.update(
            {
                "status": "blocked_failed_annual_reconciliation",
                "production_eligible_outcome_crops": [],
                "output_rows": 0,
                "production_gate": (
                    "No season-specific weight table is returned or written until every "
                    "irrigation-system reconciliation passes the predeclared tolerance."
                ),
            }
        )
        raise RiceInputGateError(audit_base)
    if not outcome_crosswalk_verified:
        audit_base.update(
            {
                "status": "blocked_pending_outcome_crosswalk",
                "production_eligible_outcome_crops": [],
                "output_rows": 0,
                "production_gate": (
                    "Annual reconciliation alone is insufficient. Rice1/Rice2 timing and "
                    "spatial support must be compared with the locked GGCMI/GDHY crosswalk."
                ),
            }
        )
        raise RiceInputGateError(audit_base)

    latitude = 89.75 - 0.5 * np.arange(COARSE_SHAPE[0], dtype=np.float64)
    longitude = -179.75 + 0.5 * np.arange(COARSE_SHAPE[1], dtype=np.float64)
    lon_grid, lat_grid = np.meshgrid(longitude, latitude)
    frames: list[pd.DataFrame] = []
    season_summaries: list[dict[str, object]] = []
    for season, crop in OUTCOME_MAP.items():
        irrigated = areas[(season, "ir")]
        rainfed = areas[(season, "rf")]
        total = irrigated + rainfed
        supported = total > 0
        irrigated_share = irrigated[supported] / total[supported]
        rainfed_share = rainfed[supported] / total[supported]
        common = {
            "lat": lat_grid[supported],
            "lon": lon_grid[supported],
            "lon_360": np.mod(lon_grid[supported], 360.0),
            "crop": crop,
            "mirca_crop": f"Rice{season}",
            "share_year": year,
            "irrigated_area_ha": irrigated[supported],
            "rainfed_area_ha": rainfed[supported],
            "total_area_ha": total[supported],
            "weight_source_id": source_id,
            "weight_vintage": f"fixed_{year}",
            "source_role": SOURCE_ROLE,
            "season_specific_share": True,
            "production_eligible": True,
            "mapping_note": f"MIRCA Rice{season} to locked GGCMI/GDHY {crop} season",
        }
        for irrigation, shares in (("firr", irrigated_share), ("noirr", rainfed_share)):
            frame = pd.DataFrame(common)
            frame["irrigation"] = irrigation
            frame["area_share"] = shares
            frames.append(frame)
        season_summaries.append(
            {
                "crop": crop,
                "mirca_crop": f"Rice{season}",
                "supported_cells": int(supported.sum()),
                "irrigated_area_ha": float(irrigated.sum()),
                "rainfed_area_ha": float(rainfed.sum()),
                "global_area_weighted_irrigated_share": float(irrigated.sum() / total.sum()),
            }
        )
    output = pd.concat(frames, ignore_index=True)
    output = output[
        [
            "lat", "lon", "lon_360", "crop", "irrigation", "area_share",
            "weight_source_id", "weight_vintage", "source_role", "mirca_crop",
            "share_year", "irrigated_area_ha", "rainfed_area_ha", "total_area_ha",
            "season_specific_share", "production_eligible", "mapping_note",
        ]
    ].sort_values(["crop", "lat", "lon_360", "irrigation"], ascending=[True, False, True, True])
    output = output.reset_index(drop=True)
    keys = ["lat", "lon_360", "crop", "irrigation"]
    if output.duplicated(keys).any():
        raise AssertionError("Built duplicate rice-season crop-grid-irrigation weights")
    sums = output.groupby(["lat", "lon_360", "crop"], observed=True).area_share.sum()
    if not np.allclose(sums.to_numpy(), 1.0, rtol=0.0, atol=1e-12):
        raise AssertionError("Rice-season irrigation shares do not sum to one")
    audit: dict[str, object] = {
        **audit_base,
        "status": "passed_annual_reconciliation_input_gate_only",
        "season_summaries": season_summaries,
        "output_rows": int(len(output)),
        "production_eligible_outcome_crops": ["ri1", "ri2"],
    }
    return output, audit


def write_table(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        frame.to_csv(path, index=False)
    elif path.suffix.lower() in {".parquet", ".pq"}:
        frame.to_parquet(path, index=False)
    else:
        raise ValueError(f"Unsupported output format for {path}; use CSV or Parquet")


def clear_failed_output(path: Path) -> dict[str, bool]:
    """Remove a stale promotable table when the current input gate fails."""
    existed = path.exists()
    path.unlink(missing_ok=True)
    return {
        "stale_output_removed": existed,
        "output_path_absent_after_failure": not path.exists(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--monthly-root", required=True)
    parser.add_argument("--annual-root", required=True)
    parser.add_argument("--year", required=True, type=int, choices=VALID_YEARS)
    parser.add_argument("--reconciliation-rtol", type=float, default=1e-5)
    parser.add_argument("--reconciliation-atol-ha", type=float, default=0.1)
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    try:
        output, audit = build_weights(
            Path(args.monthly_root),
            Path(args.annual_root),
            args.year,
            reconciliation_rtol=args.reconciliation_rtol,
            reconciliation_atol_ha=args.reconciliation_atol_ha,
        )
    except RiceInputGateError as error:
        output_path = Path(args.out)
        error.audit.update(clear_failed_output(output_path))
        audit_path = Path(args.audit_out)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps(error.audit, indent=2) + "\n")
        print(json.dumps(error.audit, indent=2))
        raise SystemExit(str(error)) from None
    output_path = Path(args.out)
    partial_path = output_path.with_name(output_path.stem + ".partial" + output_path.suffix)
    partial_path.unlink(missing_ok=True)
    try:
        write_table(output, partial_path)
        partial_path.replace(output_path)
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
