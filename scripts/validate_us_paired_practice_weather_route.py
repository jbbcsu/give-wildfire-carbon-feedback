#!/usr/bin/env python3
"""Independent Arrow/QR/cluster-sandwich audit of paired weather-route fit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from validate_us_direct_practice_precipitation_association_independent import (
    design, qr_cluster_fit, residualize,
)

OLD = ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
NEW = ROOT / "data/interim/us_county/noaa_county_average_crop_year_features_20260916"
RESULT = ROOT / "data/interim/us_county/noaa_county_paired_practice_weather_route_20260916/result.json"
SOURCE_SCRIPT = ROOT / "scripts/evaluate_us_paired_practice_weather_route.py"
KEY = ["outcome_crop", "county_geoid", "harvest_year"]
WEATHER = ["precip_mm", "stage1_precip_share", "stage2_precip_share",
           "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconstruct_pairs() -> pd.DataFrame:
    cols = KEY + ["state", "irrigation_practice", "yield_bu_acre",
                  "season_start", "season_end"]
    old = pq.read_table(OLD, columns=cols).to_pandas()
    old = old.loc[old.harvest_year.between(1981, 2018)].copy()
    if old.duplicated(KEY + ["irrigation_practice"]).any():
        raise ValueError("independent paired NASS outcome keys duplicate")
    weather_parts = []
    for year in range(1981, 2019):
        path = NEW / str(year) / "features.parquet"
        weather_parts.append(pq.read_table(path, columns=KEY + ["season_start", "season_end"] +
                                           WEATHER).to_pandas())
    weather = pd.concat(weather_parts, ignore_index=True)
    if weather.duplicated(KEY).any():
        raise ValueError("independent replacement weather keys duplicate")
    combined = old.merge(weather, on=KEY, how="left", validate="many_to_one",
                         indicator=True, suffixes=("_old", "_new"))
    if (not combined._merge.eq("both").all() or
        not combined.season_start_old.eq(combined.season_start_new).all() or
        not combined.season_end_old.eq(combined.season_end_new).all()):
        raise ValueError("independent paired outcome/new weather calendar mismatch")
    if combined.groupby(KEY).size().ne(2).any():
        raise ValueError("independent source lacks exact practice pairs")
    unique = combined.loc[combined.irrigation_practice.eq("non_irrigated"),
                          KEY + ["state"] + WEATHER].copy()
    yields = combined.pivot(index=KEY, columns="irrigation_practice", values="yield_bu_acre")
    if (set(yields.columns) != {"irrigated", "non_irrigated"} or
        yields.isna().any().any() or not yields.gt(0).all().all()):
        raise ValueError("independent practice-specific yields incomplete/nonpositive")
    gap = np.log(yields.irrigated) - np.log(yields.non_irrigated)
    paired = unique.merge(gap.rename("log_yield_gap").reset_index(), on=KEY,
                          how="inner", validate="one_to_one")
    return paired.sort_values(KEY).reset_index(drop=True)


def check(value: float, target: float, label: str, tolerance: float = 1e-9) -> float:
    difference = abs(float(value) - float(target))
    if not np.isfinite(difference) or difference > tolerance:
        raise ValueError(f"independent paired weather-route disagreement: {label} ({difference})")
    return difference


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored validator output required")
    reported = json.loads(RESULT.read_text())
    if (reported["status"] != "post_result_us_paired_practice_weather_route_association_sensitivity_not_causal" or
        reported["old_source_sha256"] != sha(OLD) or
        reported["code_sha256"] != sha(SOURCE_SCRIPT) or
        reported["causal_claim_authorized"] is not False or
        reported["scc_claim_authorized"] is not False):
        raise ValueError("reported paired weather-route source/gates changed")
    paired = reconstruct_pairs()
    if len(paired) != reported["paired_rows"]:
        raise ValueError("independent paired weather-route sample count differs")
    checks = 1
    largest = 0.0
    for fit_record in reported["estimates"]:
        crop, form = fit_record["crop"], fit_record["form"]
        sample = paired.loc[paired.outcome_crop.eq(crop)].copy()
        if (len(sample) != fit_record["rows"] or
            sample.county_geoid.nunique() != fit_record["counties"] or
            sample.state.nunique() != fit_record["states"]):
            raise ValueError("independent crop support differs")
        checks += 3
        county, _ = pd.factorize(sample.county_geoid.astype(str), sort=True)
        state_year, _ = pd.factorize(sample.state.astype(str) + "_" +
                                     sample.harvest_year.astype(str), sort=True)
        design_x, names = design(sample, form)
        residualized = residualize(np.column_stack([sample.log_yield_gap.to_numpy(float),
                                                      design_x]), [county, state_year])
        fitted = qr_cluster_fit(residualized[:, 0], residualized[:, 1:],
                                sample.county_geoid.to_numpy())
        beta = np.asarray(fitted["beta"])
        se = np.asarray(fitted["se"])
        covariance = np.asarray(fitted["covariance"])
        for name, actual, target in (("within_r_squared", fitted["r2"], fit_record["within_r_squared"]),
                                     ("residual_rmse", fitted["rmse"], fit_record["residual_rmse_log_yield_gap"]),
                                     ("cluster_count", fitted["clusters"], fit_record["cluster_count"])):
            largest = max(largest, check(actual, target, f"{crop}/{form}/{name}"))
            checks += 1
        for index, coefficient in enumerate(fit_record["coefficients"]):
            if coefficient["term"] != names[index]:
                raise ValueError("independent paired weather-route terms differ")
            for label, value, target in (
                ("beta", beta[index], coefficient["estimate"]),
                ("county_se", se[index], coefficient["standard_error_cluster_county"]),
                ("normal_p", math.erfc(abs(beta[index]/se[index])/math.sqrt(2)),
                 coefficient["normal_approx_p_value"]),
            ):
                largest = max(largest, check(value, target, f"{crop}/{form}/{names[index]}/{label}"))
                checks += 1
        rain = names.index("precipitation_per_100mm")
        rain2 = names.index("precipitation_per_100mm_squared")
        quantity = fit_record["contrasts"]["quantity_increment_at_median"]
        reference = quantity["reference_precipitation_mm"] / 100
        gradient = np.zeros(len(names))
        gradient[rain], gradient[rain2] = 1, (reference + 1)**2 - reference**2
        delta = float(gradient @ beta)
        delta_se = float(np.sqrt(max(gradient @ covariance @ gradient, 0)))
        for label, value, target in (
            ("rain_delta", delta, quantity["fitted_log_yield_gap_difference"]),
            ("rain_se", delta_se, quantity["standard_error_cluster_county"]),
            ("rain_percent", 100*math.expm1(delta),
             quantity["fitted_irrigated_to_non_irrigated_yield_ratio_percent_difference"]),
        ):
            largest = max(largest, check(value, target, f"{crop}/{form}/{label}"))
            checks += 1
        if form == "quantity_timing":
            timing = fit_record["contrasts"]["stage3_to_stage2_shift"]
            gradient = np.zeros(len(names))
            gradient[names.index("stage2_precip_share")] = 0.1
            delta = float(gradient @ beta)
            delta_se = float(np.sqrt(max(gradient @ covariance @ gradient, 0)))
            for label, value, target in (
                ("timing_delta", delta, timing["fitted_log_yield_gap_difference"]),
                ("timing_se", delta_se, timing["standard_error_cluster_county"]),
                ("timing_percent", 100*math.expm1(delta),
                 timing["fitted_irrigated_to_non_irrigated_yield_ratio_percent_difference"]),
            ):
                largest = max(largest, check(value, target, f"{crop}/{form}/{label}"))
                checks += 1
    audit = {"status": "independent_paired_weather_route_qr_cluster_validation_passed",
             "numeric_and_support_checks": checks, "maximum_absolute_disagreement": largest,
             "sensitivity_result_sha256": sha(RESULT), "code_sha256": sha(Path(__file__)),
             "causal_claim_authorized": False, "damage_claim_authorized": False,
             "scc_claim_authorized": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": audit["status"], "checks": checks,
                      "max_difference": largest}))


if __name__ == "__main__":
    main()
