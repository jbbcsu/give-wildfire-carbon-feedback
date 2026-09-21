#!/usr/bin/env python3
"""Post-result 2017/2022 irrigation-share sample sensitivity; not causal."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assemble_us_county_average_nass_panel import (
    GEO, HIST, KEY, FEATURES, VALIDATION, feature_partitions,
    geo_selector, historic_outcomes, sha, terminal_outcomes,
)
from estimate_us_county_average_terminal_prediction import one_crop

PROTOCOL = ROOT / "US_COUNTY_AVERAGE_IRRIGATION_SCREEN_SENSITIVITY_20260916.md"
PREANALYSIS = ROOT / "US_COUNTY_AVERAGE_RESPONSE_PREANALYSIS_20260916.md"
PRIMARY = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916/panel.parquet"
PRIMARY_RESULT = ROOT / "data/interim/us_county/noaa_county_average_prediction_20260916/result.json"
SHARES = {year: ROOT / f"data/interim/us_county/nass_{year}_crop_irrigation_shares.csv"
          for year in (2017, 2022)}
KEEP_WEATHER = ["state", "precip_mm", "tmean_c", "tmax_exceedance_29c_c_days",
                "wet_days_ge_1mm", "cdd_max_days", "rx5day_mm",
                "stage1_precip_share", "stage2_precip_share"]


def selector(year: int) -> pd.DataFrame:
    frame = pd.read_csv(SHARES[year], dtype={"county_geoid": str})
    if (frame.duplicated(["crop", "county_geoid"]).any() or
        set(frame.census_year) != {year} or
        not frame.irrigation_share.dropna().between(0, 1).all()):
        raise ValueError("Census irrigation-share identity or range invalid")
    frame["outcome_crop"] = frame.crop.map({"corn": "corn_grain", "soybeans": "soybeans"})
    # The Census source also contains crops outside this corn/soy test.
    frame = frame.loc[frame.outcome_crop.notna()].copy()
    if frame.empty:
        raise ValueError("corn/soy missing from fixed irrigation-share selector")
    frame["share_eligible"] = frame.share_eligible.astype(str).str.lower().eq("true")
    return frame[["outcome_crop", "county_geoid", "irrigation_share", "share_eligible"]]


def key_digest(frame: pd.DataFrame) -> str:
    keys = frame[KEY].sort_values(KEY).astype(str)
    data = "\n".join("|".join(row) for row in keys.itertuples(index=False, name=None))
    return hashlib.sha256((data + "\n").encode()).hexdigest()


def primary_parity(frame: pd.DataFrame) -> None:
    original = pd.read_parquet(PRIMARY)
    columns = KEY + ["yield_bu_acre", "irrigation_share"] + KEEP_WEATHER
    left = frame[columns].sort_values(KEY).reset_index(drop=True)
    right = original[columns].sort_values(KEY).reset_index(drop=True)
    if not left.equals(right):
        raise ValueError("2017 <=10% sensitivity does not exactly reproduce primary panel")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored output directory required")
    primary = json.loads(PRIMARY_RESULT.read_text())
    if (primary["status"] != "us_county_average_predictive_benchmark_not_causal" or
        primary["panel_sha256"] != sha(PRIMARY)):
        raise ValueError("validated primary prediction or panel changed")
    historical = historic_outcomes()
    terminal, terminal_audit = terminal_outcomes()
    raw_rows = len(historical) + len(terminal)
    outcomes = pd.concat([historical, terminal], ignore_index=True)
    if outcomes.duplicated(KEY).any():
        raise ValueError("source NASS panel duplicates crop/county/year")
    outcomes = outcomes.loc[outcomes.outcome_value_eligible & outcomes.yield_bu_acre.gt(0)].copy()
    positive_rows = len(outcomes)
    geo = geo_selector()
    outcomes = outcomes.merge(geo, on="county_geoid", how="left", validate="many_to_one")
    outcomes = outcomes.loc[
        outcomes.selected_geography.astype("boolean").fillna(False).astype(bool),
                            KEY + ["yield_bu_acre", "period"]].copy()
    geography_rows = len(outcomes)
    weather, feature_hash = feature_partitions()
    weather = weather[KEY + KEEP_WEATHER]
    matched = outcomes.merge(weather, on=KEY, how="inner", validate="one_to_one")
    weather_rows = len(matched)
    del outcomes, weather
    gc.collect()

    screens = {}
    for year in (2017, 2022):
        shares = selector(year)
        for threshold in (10, 20, 30):
            key = f"{year}_le_{threshold}pct"
            selected = shares.loc[shares.share_eligible & shares.irrigation_share.notna() &
                                  shares.irrigation_share.le(threshold / 100),
                                  ["outcome_crop", "county_geoid", "irrigation_share"]]
            panel = matched.merge(selected, on=["outcome_crop", "county_geoid"],
                                  how="inner", validate="many_to_one")
            if panel.empty or panel.duplicated(KEY).any():
                raise ValueError(f"{key}: empty/duplicate selected panel")
            if (year, threshold) == (2017, 10):
                primary_parity(panel)
            record = {"census_year": year, "maximum_irrigated_acreage_share": threshold / 100,
                      "historical_rows": int(panel.period.eq("historical").sum()),
                      "terminal_rows_before_seen_county_filter": int(panel.period.eq("terminal").sum()),
                      "sample_key_sha256": key_digest(panel),
                      "all_practice_proxy_not_direct_nonirrigated": True,
                      "uses_terminal_period_selection_information": year == 2022,
                      "crops": {crop: one_crop(panel, crop)
                                for crop in ("corn_grain", "soybeans")}}
            screens[key] = record
            del panel
            gc.collect()
    result = {"status": "post_result_irrigation_screen_predictive_sensitivity_not_causal",
              "protocol_sha256": sha(PROTOCOL), "preanalysis_sha256": sha(PREANALYSIS),
              "script_sha256": sha(Path(__file__)), "primary_panel_sha256": sha(PRIMARY),
              "primary_prediction_sha256": sha(PRIMARY_RESULT),
              "historical_source_sha256": sha(HIST), "geography_gate_sha256": sha(GEO),
              "feature_summary_sha256": feature_hash, "feature_validation_sha256": sha(VALIDATION),
              "share_source_sha256": {str(year): sha(path) for year, path in SHARES.items()},
              "terminal_source": terminal_audit, "raw_outcome_rows": raw_rows,
              "positive_outcome_rows": positive_rows, "geography_rows": geography_rows,
              "weather_rows_before_irrigation_screen": weather_rows,
              "primary_2017_10pct_parity_passed": True, "screens": screens,
              "climate_change_attribution_performed": False,
              "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: {crop: {model: round(score["rmse_log_yield"], 5)
                                   for model, score in rec["terminal_scores"].items()}
                            for crop, rec in screen["crops"].items()}
                      for key, screen in screens.items()}))


if __name__ == "__main__":
    main()
