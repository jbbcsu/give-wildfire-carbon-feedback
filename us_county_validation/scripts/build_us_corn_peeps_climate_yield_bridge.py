#!/usr/bin/env python3
"""Combine published PEEPS monthly slopes with the frozen U.S. corn response."""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import shapefile
import xarray as xr

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = SCRIPT_DIR.parents[1]
ROOT_SCRIPTS = PROJECT / "scripts"
for path in (SCRIPT_DIR, ROOT_SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from probe_peeps_december_crop_support import nearest_circular, nearest_linear  # noqa: E402
from run_us_corn_quantity_pdsi_spatial_synthetic_executor import design, residualize  # noqa: E402
from us_corn_spatial_inference_primitives import contrast_standard_error, county_cr1_meat, county_plus_spatial_covariance  # noqa: E402

MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
KEYS = ["county_geoid", "state", "harvest_year", "irrigation_practice"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_coordinates(path: Path) -> pd.DataFrame:
    reader = shapefile.Reader(dbf=str(path))
    fields = [field[0] for field in reader.fields[1:]]
    indices = [fields.index(name) for name in ("GEOID", "INTPTLAT", "INTPTLON")]
    rows = [(str(record[indices[0]]).zfill(5), float(record[indices[1]]), float(record[indices[2]])) for record in reader.iterRecords()]
    result = pd.DataFrame(rows, columns=["county_geoid", "latitude", "longitude"])
    require(len(result) == 3233 and not result.county_geoid.duplicated().any(), "coordinate support differs")
    return result


def month_overlap_days(start: pd.Timestamp, end: pd.Timestamp) -> np.ndarray:
    require(end >= start, "crop season ends before it begins")
    days = np.zeros(12, dtype=np.float64)
    cursor = pd.Timestamp(start.year, start.month, 1)
    while cursor <= end:
        last = pd.Timestamp(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
        left, right = max(start, cursor), min(end, last)
        if right >= left:
            days[cursor.month - 1] += float((right - left).days + 1)
        cursor = last + pd.Timedelta(days=1)
    require(days.sum() == float((end - start).days + 1), "monthly crop-season days do not reconcile")
    return days


def peeps_slopes(source_receipt: Path, latitudes: np.ndarray, longitudes: np.ndarray) -> tuple[np.ndarray, list[dict[str, object]]]:
    receipt = json.loads(source_receipt.read_text())
    require(receipt["status"] == "whole_author_archive_md5_verified_selected_members_acquired", "PEEPS receipt status differs")
    require(receipt["model"] == "MPI-ESM1-2-HR" and receipt["scenario"] == "ssp585", "PEEPS model/scenario differs")
    require(receipt["selected_months"] == list(MONTHS), "PEEPS month order differs")
    values, sources = [], []
    mapped_i = mapped_j = grid_lat = grid_lon = None
    for month, item in zip(MONTHS, receipt["selected_members"], strict=True):
        path = source_receipt.parent / item["name"]
        require(path.is_file() and path.stat().st_size == item["bytes"] and digest(path) == item["sha256"], f"PEEPS source differs: {month}")
        with xr.open_dataset(path, cache=False) as dataset:
            this_lat, this_lon = np.asarray(dataset.lat.values, dtype=float), np.asarray(dataset.lon.values, dtype=float)
            if grid_lat is None:
                grid_lat, grid_lon = this_lat, this_lon
                mapped_i, mapped_j = nearest_linear(latitudes, grid_lat), nearest_circular(longitudes, grid_lon)
            else:
                require(np.array_equal(grid_lat, this_lat) and np.array_equal(grid_lon, this_lon), "PEEPS grids differ")
            slope = np.asarray(dataset.slope.values[0], dtype=float)
            require(np.isfinite(slope).all(), f"nonfinite PEEPS slope: {month}")
            values.append(slope[mapped_i, mapped_j])
        sources.append({"month": month, "path": str(path), "bytes": path.stat().st_size, "sha256": item["sha256"]})
    return np.column_stack(values), sources


def fit_quantity(frame: pd.DataFrame) -> tuple[np.ndarray, dict[str, np.ndarray], float]:
    raw_x, names = design(frame, "quantity")
    county, _ = pd.factorize(frame.county_geoid.astype(str), sort=True)
    state_year, _ = pd.factorize(frame.state.astype(str) + "_" + frame.harvest_year.astype(str), sort=True)
    transformed = residualize(np.column_stack([np.log(frame.yield_bu_acre.to_numpy(float)), raw_x]), [county, state_year])
    y, x = transformed[:, 0], transformed[:, 1:]
    gram = x.T @ x
    beta = np.linalg.solve(gram, x.T @ y)
    error = y - x @ beta
    bread = np.linalg.inv(gram)
    covariance = {"county_cr1": bread @ county_cr1_meat(x, error, frame.county_geoid.to_numpy()) @ bread}
    for cutoff in (250.0, 500.0):
        covariance[f"spatial_{int(cutoff)}km"] = county_plus_spatial_covariance(x, error, frame.county_geoid.to_numpy(), frame.harvest_year.to_numpy(), frame.latitude.to_numpy(float), frame.longitude.to_numpy(float), cutoff)
    median = float(frame.precip_mm.quantile(0.5))
    target = np.zeros(len(names), dtype=float)
    scaled = median / 100.0
    target[names.index("precipitation_per_100mm")] = 1.0
    target[names.index("precipitation_per_100mm_squared")] = (scaled + 1.0) ** 2 - scaled**2
    return beta, covariance, float(target @ beta)


def summarize(vector: np.ndarray, beta: np.ndarray, covariance: dict[str, np.ndarray]) -> dict[str, object]:
    estimate = float(vector @ beta)
    ses = {name: contrast_standard_error(value, vector) for name, value in covariance.items()}
    intervals = {name: [estimate - 1.96 * se, estimate + 1.96 * se] for name, se in ses.items()}
    return {"estimate_log_yield_per_k": estimate, "estimate_percent_yield_per_k": 100.0 * np.expm1(estimate), "standard_errors_log_yield": ses, "normal_95_intervals_percent_yield": {name: [100.0 * np.expm1(bounds[0]), 100.0 * np.expm1(bounds[1])] for name, bounds in intervals.items()}, "spatially_robust_excludes_zero": all(bounds[0] * bounds[1] > 0 for bounds in intervals.values())}


def equal_county_vector(frame: pd.DataFrame) -> np.ndarray:
    columns = [f"contrast_{index}" for index in range(8)]
    county = frame.groupby("county_geoid", as_index=False)[columns].mean()
    return county[columns].mean().to_numpy(float)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-sha256", required=True)
    parser.add_argument("--coordinate-dbf", type=Path, required=True)
    parser.add_argument("--peeps-receipt", type=Path, required=True)
    parser.add_argument("--us-result-receipt", type=Path, required=True)
    parser.add_argument("--state-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.state_output.exists() and not args.receipt.exists(), "fresh outputs required")
    require(digest(args.panel) == args.panel_sha256, "NASS/nClimGrid panel hash differs")
    us_receipt = json.loads(args.us_result_receipt.read_text())
    require(us_receipt["schema"] == "us_corn_quantity_pdsi_spatial_real_receipt/v1", "U.S. response receipt differs")
    require(us_receipt["claim_gates"]["historical_association"] and not us_receipt["claim_gates"]["climate_attribution"], "U.S. response claim gates differ")
    columns = KEYS + ["outcome_crop", "yield_bu_acre", "precip_mm", "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c", "season_start", "season_end"]
    panel = pd.read_parquet(args.panel, columns=columns)
    panel = panel.loc[panel.outcome_crop.eq("corn_grain") & panel.harvest_year.between(1981, 2018)].copy()
    panel["county_geoid"] = panel.county_geoid.astype(str).str.zfill(5)
    panel = panel.merge(load_coordinates(args.coordinate_dbf), on="county_geoid", validate="many_to_one")
    require(len(panel) == 14026 and panel.county_geoid.nunique() == 361, "response support differs")
    unique = panel.drop_duplicates(["county_geoid", "harvest_year"])[["county_geoid", "harvest_year", "season_start", "season_end", "latitude", "longitude"]].sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
    require(len(unique) == 7013, "paired exposure support differs")
    unique["season_start"] = pd.to_datetime(unique.season_start)
    unique["season_end"] = pd.to_datetime(unique.season_end)
    monthly, sources = peeps_slopes(args.peeps_receipt, unique.latitude.to_numpy(float), unique.longitude.to_numpy(float))
    overlaps = np.vstack([month_overlap_days(row.season_start, row.season_end) for row in unique.itertuples(index=False)])
    unique["peeps_crop_season_precip_slope_mm_per_k"] = np.sum(monthly * overlaps * 86_400.0, axis=1)
    panel = panel.merge(unique[["county_geoid", "harvest_year", "peeps_crop_season_precip_slope_mm_per_k"]], on=["county_geoid", "harvest_year"], validate="many_to_one")

    state_records, national = [], {}
    for practice in ("non_irrigated", "irrigated"):
        frame = panel.loc[panel.irrigation_practice.eq(practice)].copy().sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
        beta, covariance, median_contrast = fit_quantity(frame)
        frozen = next(item for item in us_receipt["central_full_sample_contrasts"] if item["practice"] == practice and item["family"] == "quantity")
        require(abs(median_contrast - frozen["estimate_log_yield"]) <= 1e-13, "frozen U.S. response not reproduced")
        vectors = np.zeros((len(frame), 8), dtype=float)
        slope = frame.peeps_crop_season_precip_slope_mm_per_k.to_numpy(float)
        precip = frame.precip_mm.to_numpy(float)
        vectors[:, 6] = slope / 100.0
        vectors[:, 7] = np.square((precip + slope) / 100.0) - np.square(precip / 100.0)
        for index in range(8):
            frame[f"contrast_{index}"] = vectors[:, index]
        national[practice] = {"equal_county": summarize(equal_county_vector(frame), beta, covariance), "equal_row": summarize(vectors.mean(axis=0), beta, covariance)}
        for state, state_frame in frame.groupby("state"):
            summary = summarize(equal_county_vector(state_frame), beta, covariance)
            state_records.append({"state": state, "practice": practice, "counties": int(state_frame.county_geoid.nunique()), "county_years": len(state_frame), "mean_peeps_crop_season_precip_slope_mm_per_k": float(state_frame.groupby("county_geoid").peeps_crop_season_precip_slope_mm_per_k.mean().mean()), **summary})
    states = pd.DataFrame(state_records).sort_values(["practice", "state"]).reset_index(drop=True)
    args.state_output.parent.mkdir(parents=True, exist_ok=True)
    states.to_csv(args.state_output, index=False)
    climate = unique.groupby("county_geoid").peeps_crop_season_precip_slope_mm_per_k.mean()
    result = {"schema": "us_corn_peeps_climate_yield_bridge/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "one_esm_published_monthly_slope_to_selected_sample_historical_yield_association_not_damage_or_scc", "definition": "published PEEPS MPI-ESM1-2-HR SSP5-8.5 monthly precipitation slopes integrated over NASS corn seasons and evaluated through the frozen U.S. quantity response separately by practice", "sources": {"panel": {"path": str(args.panel), "sha256": digest(args.panel)}, "coordinates": {"path": str(args.coordinate_dbf), "sha256": digest(args.coordinate_dbf)}, "peeps": {"receipt": str(args.peeps_receipt), "receipt_sha256": digest(args.peeps_receipt), "members": sources}, "us_response": {"receipt": str(args.us_result_receipt), "receipt_sha256": digest(args.us_result_receipt)}}, "support": {"paired_county_years": len(unique), "counties": int(unique.county_geoid.nunique()), "states": int(panel.state.nunique()), "years": [1981, 2018]}, "climate_slope_mm_per_k_equal_county": {"minimum": float(climate.min()), "median": float(climate.median()), "mean": float(climate.mean()), "maximum": float(climate.max()), "negative_counties": int(climate.lt(0).sum()), "positive_counties": int(climate.gt(0).sum())}, "national_selected_sample": national, "state_output": {"path": str(args.state_output), "bytes": args.state_output.stat().st_size, "sha256": digest(args.state_output)}, "validation": {"monthly_day_reconciliation": True, "frozen_us_quantity_response_reproduced_tolerance": 1e-13, "finite_outputs": bool(np.isfinite(states.select_dtypes(include=[np.number]).to_numpy()).all())}, "claim_gates": {"published_climate_to_crop_season_rainfall_slope": True, "selected_sample_historical_response_transport_diagnostic": True, "multi_model_climate_attribution": False, "national_yield_effect": False, "damage": False, "scc": False}, "limitations": ["One ESM and SSP5-8.5 pattern; no climate-model uncertainty.", "PEEPS monthly means omit daily dry spells, extremes, and PDSI.", "County internal points are mapped to the nearest coarse native PEEPS grid center.", "The historical quantity response fails strict geographic and temporal stability gates and the ten-state reported-practice sample is not nationally representative.", "Equal-county and equal-row summaries have no acreage, production, or welfare weights."], "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())}}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "climate_slope": result["climate_slope_mm_per_k_equal_county"], "national": national, "state_output": result["state_output"]}, indent=2))


if __name__ == "__main__":
    main()
