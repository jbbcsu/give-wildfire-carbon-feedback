#!/usr/bin/env python3
"""Compare three monthly precipitation-pattern transports on U.S. corn support."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_us_corn_peeps_climate_yield_bridge import (
    digest,
    equal_county_vector,
    fit_quantity,
    load_coordinates,
    month_overlap_days,
    peeps_slopes,
    require,
    summarize,
)
from probe_peeps_december_crop_support import nearest_circular, nearest_linear

KEYS = ["county_geoid", "state", "harvest_year", "irrigation_practice"]


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fitted_pattern(path: Path, expected_sha256: str, latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
    require(file_digest(path) == expected_sha256, f"pattern coefficient hash differs: {path}")
    with np.load(path) as values:
        require(set(["monthly_slope_flux_per_k", "latitude", "longitude"]).issubset(values.files), "pattern fields differ")
        latitude, longitude = np.asarray(values["latitude"], dtype=float), np.asarray(values["longitude"], dtype=float)
        slope = np.asarray(values["monthly_slope_flux_per_k"], dtype=float)
    require(slope.shape == (12, len(latitude), len(longitude)) and np.isfinite(slope).all(), "pattern array differs")
    i, j = nearest_linear(latitudes, latitude), nearest_circular(longitudes, longitude)
    return np.column_stack([slope[month, i, j] for month in range(12)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-sha256", required=True)
    parser.add_argument("--coordinate-dbf", type=Path, required=True)
    parser.add_argument("--peeps-receipt", type=Path, required=True)
    parser.add_argument("--gfdl", type=Path, required=True)
    parser.add_argument("--gfdl-sha256", required=True)
    parser.add_argument("--ipsl", type=Path, required=True)
    parser.add_argument("--ipsl-sha256", required=True)
    parser.add_argument("--fit-audit", type=Path, required=True)
    parser.add_argument("--us-result-receipt", type=Path, required=True)
    parser.add_argument("--state-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.state_output.exists() and not args.receipt.exists(), "fresh outputs required")
    require(digest(args.panel) == args.panel_sha256, "panel hash differs")
    audit = json.loads(args.fit_audit.read_text())
    require(audit["status"] == "two_monthly_climate_fits_independently_audited_not_holdout_validated", "fit audit status differs")
    expected = {item["model"]: item["coefficient_sha256"] for item in audit["records"]}
    require(expected == {"GFDL-ESM4": args.gfdl_sha256, "IPSL-CM6A-LR": args.ipsl_sha256}, "fit audit coefficient hashes differ")
    us_receipt = json.loads(args.us_result_receipt.read_text())
    require(us_receipt["schema"] == "us_corn_quantity_pdsi_spatial_real_receipt/v1", "U.S. response receipt differs")

    columns = KEYS + ["outcome_crop", "yield_bu_acre", "precip_mm", "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c", "season_start", "season_end"]
    panel = pd.read_parquet(args.panel, columns=columns)
    panel = panel.loc[panel.outcome_crop.eq("corn_grain") & panel.harvest_year.between(1981, 2018)].copy()
    panel["county_geoid"] = panel.county_geoid.astype(str).str.zfill(5)
    panel = panel.merge(load_coordinates(args.coordinate_dbf), on="county_geoid", validate="many_to_one")
    unique = panel.drop_duplicates(["county_geoid", "harvest_year"])[["county_geoid", "harvest_year", "season_start", "season_end", "latitude", "longitude"]].sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
    require(len(panel) == 14026 and len(unique) == 7013, "U.S. support differs")
    unique["season_start"], unique["season_end"] = pd.to_datetime(unique.season_start), pd.to_datetime(unique.season_end)
    overlaps = np.vstack([month_overlap_days(row.season_start, row.season_end) for row in unique.itertuples(index=False)])
    peeps, peeps_sources = peeps_slopes(args.peeps_receipt, unique.latitude.to_numpy(float), unique.longitude.to_numpy(float))
    patterns = {
        "PEEPS_MPI-ESM1-2-HR_published": peeps,
        "project_fit_GFDL-ESM4": fitted_pattern(args.gfdl, args.gfdl_sha256, unique.latitude.to_numpy(float), unique.longitude.to_numpy(float)),
        "project_fit_IPSL-CM6A-LR": fitted_pattern(args.ipsl, args.ipsl_sha256, unique.latitude.to_numpy(float), unique.longitude.to_numpy(float)),
    }
    slope_by_model = {model: np.sum(values * overlaps * 86_400.0, axis=1) for model, values in patterns.items()}
    county_model = pd.DataFrame({"county_geoid": unique.county_geoid})
    for model, slope in slope_by_model.items():
        county_model[model] = slope
    county_mean = county_model.groupby("county_geoid").mean()
    model_names = list(patterns)
    signs = np.sign(county_mean[model_names])
    sign_agreement = signs.nunique(axis=1).eq(1) & signs.iloc[:, 0].ne(0)

    response = {}
    for practice in ("non_irrigated", "irrigated"):
        frame = panel.loc[panel.irrigation_practice.eq(practice)].copy().sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
        beta, covariance, median_contrast = fit_quantity(frame)
        frozen = next(item for item in us_receipt["central_full_sample_contrasts"] if item["practice"] == practice and item["family"] == "quantity")
        require(abs(median_contrast - frozen["estimate_log_yield"]) <= 1e-13, "frozen response not reproduced")
        response[practice] = (beta, covariance)

    records, national, climate = [], {}, {}
    for model, slope in slope_by_model.items():
        slope_frame = unique[["county_geoid", "harvest_year"]].copy()
        slope_frame["slope"] = slope
        climate_values = slope_frame.groupby("county_geoid").slope.mean()
        climate[model] = {"minimum": float(climate_values.min()), "median": float(climate_values.median()), "mean": float(climate_values.mean()), "maximum": float(climate_values.max()), "negative_counties": int(climate_values.lt(0).sum()), "positive_counties": int(climate_values.gt(0).sum())}
        national[model] = {}
        for practice in ("non_irrigated", "irrigated"):
            frame = panel.loc[panel.irrigation_practice.eq(practice)].copy().sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
            frame = frame.merge(slope_frame, on=["county_geoid", "harvest_year"], validate="one_to_one")
            beta, covariance = response[practice]
            vectors = np.zeros((len(frame), 8), dtype=float)
            precip, local_slope = frame.precip_mm.to_numpy(float), frame.slope.to_numpy(float)
            require(np.all(precip + local_slope >= 0), f"one-K seasonal rainfall becomes negative: {model}")
            vectors[:, 6] = local_slope / 100.0
            vectors[:, 7] = np.square((precip + local_slope) / 100.0) - np.square(precip / 100.0)
            for index in range(8):
                frame[f"contrast_{index}"] = vectors[:, index]
            national[model][practice] = summarize(equal_county_vector(frame), beta, covariance)
            for state, state_frame in frame.groupby("state"):
                records.append({"model": model, "practice": practice, "state": state, "counties": int(state_frame.county_geoid.nunique()), "mean_crop_season_precip_slope_mm_per_k": float(state_frame.groupby("county_geoid").slope.mean().mean()), **summarize(equal_county_vector(state_frame), beta, covariance)})
    state = pd.DataFrame(records).sort_values(["model", "practice", "state"]).reset_index(drop=True)
    args.state_output.parent.mkdir(parents=True, exist_ok=True)
    state.to_csv(args.state_output, index=False)
    nonirrigated = [national[model]["non_irrigated"]["estimate_percent_yield_per_k"] for model in model_names]
    result = {"schema": "us_corn_three_pattern_sensitivity/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "three_monthly_pattern_structural_sensitivity_not_validated_climate_ensemble_damage_or_scc", "definition": "U.S. selected-sample corn rainfall-response transport under one published PEEPS pattern and two independently audited project-fitted PEEPS-style monthly patterns", "sources": {"panel": {"path": str(args.panel), "sha256": digest(args.panel)}, "coordinates": {"path": str(args.coordinate_dbf), "sha256": digest(args.coordinate_dbf)}, "published_peeps": {"receipt": str(args.peeps_receipt), "receipt_sha256": digest(args.peeps_receipt), "members": peeps_sources}, "project_patterns": {"GFDL-ESM4": {"path": str(args.gfdl), "sha256": digest(args.gfdl)}, "IPSL-CM6A-LR": {"path": str(args.ipsl), "sha256": digest(args.ipsl)}, "audit": {"path": str(args.fit_audit), "sha256": digest(args.fit_audit)}}, "us_response": {"receipt": str(args.us_result_receipt), "receipt_sha256": digest(args.us_result_receipt)}}, "support": {"paired_county_years": len(unique), "counties": int(unique.county_geoid.nunique()), "states": int(panel.state.nunique()), "patterns": model_names, "counties_with_same_nonzero_slope_sign_all_patterns": int(sign_agreement.sum())}, "climate_slope_mm_per_k_equal_county": climate, "national_selected_sample_equal_county": national, "descriptive_nonirrigated_response_across_patterns_percent_per_k": {"minimum": float(min(nonirrigated)), "maximum": float(max(nonirrigated)), "equal_pattern_mean": float(np.mean(nonirrigated))}, "state_output": {"path": str(args.state_output), "bytes": args.state_output.stat().st_size, "sha256": digest(args.state_output)}, "validation": {"monthly_day_reconciliation": True, "frozen_us_quantity_response_reproduced_tolerance": 1e-13, "one_k_total_season_rainfall_nonnegative": True, "finite_outputs": bool(np.isfinite(state.select_dtypes(include=[np.number]).to_numpy()).all())}, "claim_gates": {"published_peeps_transport": True, "project_pattern_structural_sensitivity": True, "validated_multi_model_climate_ensemble": False, "national_yield_effect": False, "damage": False, "scc": False}, "limitations": ["The three patterns are not a homogeneous probability-weighted ensemble.", "GFDL and IPSL slopes are project-fitted SSP5-8.5 patterns whose source algebra was independently audited but whose holdout gains were small and whose raw fitted levels can be negative; only slopes are used here.", "Monthly mean patterns omit daily drought and extremes.", "The U.S. historical response and ten-state support retain the limitations documented upstream.", "No acreage, production, welfare, or adaptation weighting is applied."], "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())}}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "climate": climate, "national": national, "descriptive_nonirrigated": result["descriptive_nonirrigated_response_across_patterns_percent_per_k"], "state_output": result["state_output"]}, indent=2))


if __name__ == "__main__":
    main()
