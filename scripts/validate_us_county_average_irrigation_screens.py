#!/usr/bin/env python3
"""Independent selector and pandas within-OLS check of irrigation sensitivities."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assemble_us_county_average_nass_panel import (
    GEO, HIST, KEY, FEATURES, feature_partitions, terminal_outcomes, sha,
)
from validate_us_county_average_terminal_prediction import fit_score, reconcile

PREDICTION = ROOT / "data/interim/us_county/noaa_county_average_irrigation_screen_sensitivity_20260916/result.json"
SOURCE_SCRIPT = ROOT / "scripts/evaluate_us_county_average_irrigation_screens.py"
SHARES = {year: ROOT / f"data/interim/us_county/nass_{year}_crop_irrigation_shares.csv"
          for year in (2017, 2022)}
MODEL_NAMES = ("no_weather", "quantity_temperature", "quantity_temperature_pattern")
WEATHER_COLUMNS = ["state", "precip_mm", "tmean_c", "tmax_exceedance_29c_c_days",
                   "wet_days_ge_1mm", "cdd_max_days", "rx5day_mm",
                   "stage1_precip_share", "stage2_precip_share"]


def sample_digest(frame: pd.DataFrame) -> str:
    ordered = frame[KEY].sort_values(KEY)
    text = "\n".join("|".join(map(str, row))
                     for row in ordered.itertuples(index=False, name=None)) + "\n"
    return hashlib.sha256(text.encode()).hexdigest()


def source_outcomes() -> tuple[pd.DataFrame, dict]:
    hist = pd.read_parquet(HIST, columns=KEY + ["yield_bu_acre", "outcome_value_eligible"])
    hist["period"] = "historical"
    terminal, source = terminal_outcomes()
    combined = pd.concat([hist, terminal], ignore_index=True)
    if combined.duplicated(KEY).any():
        raise ValueError("independent source outcomes duplicate keys")
    combined = combined.loc[combined.outcome_value_eligible &
                            combined.yield_bu_acre.gt(0)].copy()
    geo = pd.read_csv(GEO, dtype={"county_geoid": str})
    geo = set(geo.loc[geo.feature_construction_eligible.astype(str).str.lower().eq("true"),
                      "county_geoid"])
    combined = combined.loc[combined.county_geoid.isin(geo)].copy()
    features, _ = feature_partitions()
    features = features[KEY + WEATHER_COLUMNS]
    panel = combined[KEY + ["yield_bu_acre", "period"]].merge(
        features, on=KEY, how="inner", validate="one_to_one")
    return panel, source


def source_selector(year: int, threshold: int) -> pd.DataFrame:
    source = pd.read_csv(SHARES[year], dtype={"county_geoid": str})
    source = source.loc[source.crop.isin(["corn", "soybeans"])].copy()
    if source.duplicated(["crop", "county_geoid"]).any() or set(source.census_year) != {year}:
        raise ValueError("independent Census source identity invalid")
    source = source.loc[source.share_eligible.astype(str).str.lower().eq("true") &
                        source.irrigation_share.notna() &
                        source.irrigation_share.ge(0) &
                        source.irrigation_share.le(threshold / 100)].copy()
    source["outcome_crop"] = source.crop.replace({"corn": "corn_grain", "soybeans": "soybeans"})
    return source[["outcome_crop", "county_geoid"]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored validator output required")
    result = json.loads(PREDICTION.read_text())
    if (result["status"] != "post_result_irrigation_screen_predictive_sensitivity_not_causal" or
        result["script_sha256"] != sha(SOURCE_SCRIPT) or
        result["historical_source_sha256"] != sha(HIST) or
        result["geography_gate_sha256"] != sha(GEO) or
        result["share_source_sha256"] != {str(y): sha(p) for y, p in SHARES.items()}):
        raise ValueError("reported sample source/script identities invalid")
    base, terminal_source = source_outcomes()
    if terminal_source != result["terminal_source"]:
        raise ValueError("independent terminal source identity changed")
    checks = 0
    for year in (2017, 2022):
        for threshold in (10, 20, 30):
            key = f"{year}_le_{threshold}pct"
            selected = source_selector(year, threshold)
            panel = base.merge(selected, on=["outcome_crop", "county_geoid"],
                               how="inner", validate="many_to_one")
            reported = result["screens"][key]
            if (sample_digest(panel) != reported["sample_key_sha256"] or
                int(panel.period.eq("historical").sum()) != reported["historical_rows"] or
                int(panel.period.eq("terminal").sum()) !=
                reported["terminal_rows_before_seen_county_filter"]):
                raise ValueError(f"{key}: independent sample support differs")
            checks += 3
            for crop in ("corn_grain", "soybeans"):
                crop_panel = panel.loc[panel.outcome_crop.eq(crop)]
                train = crop_panel.loc[crop_panel.harvest_year.between(1981, 2019)]
                test = crop_panel.loc[crop_panel.harvest_year.between(2020, 2025)]
                test = test.loc[test.county_geoid.isin(set(train.county_geoid))]
                early = crop_panel.loc[crop_panel.harvest_year.between(1981, 2010)]
                blocked = crop_panel.loc[crop_panel.harvest_year.between(2012, 2019)]
                blocked = blocked.loc[blocked.county_geoid.isin(set(early.county_geoid))]
                target = reported["crops"][crop]
                if (len(train) != target["historical_rows"] or
                    len(test) != target["terminal_rows_scored"] or
                    len(blocked) != target["historical_blocked_scores"]["no_weather"]["n"]):
                    raise ValueError(f"{key}/{crop}: crop-specific support differs")
                checks += 3
                for model in MODEL_NAMES:
                    terminal_score, counties = fit_score(train, test, model)
                    blocked_score, _ = fit_score(early, blocked, model)
                    if counties != target["historical_counties"]:
                        raise ValueError("independent county-intercept count differs")
                    checks += 1
                    for term, value in zip(terminal_score["names"], terminal_score["beta"]):
                        index = target["fits"][model]["terms"].index(term)
                        reconcile(value, target["fits"][model]["beta"][index],
                                  f"{key}/{crop}/{model}/{term}")
                        checks += 1
                    for field in ("rmse_log_yield", "mae_log_yield", "mean_error_log_yield"):
                        reconcile(terminal_score[field], target["terminal_scores"][model][field],
                                  f"{key}/{crop}/{model}/terminal/{field}")
                        reconcile(blocked_score[field], target["historical_blocked_scores"][model][field],
                                  f"{key}/{crop}/{model}/blocked/{field}")
                        checks += 2
            del panel
            gc.collect()
    audit = {"status": "independent_irrigation_screen_support_and_scores_validated",
             "numeric_and_support_checks": checks, "screens": sorted(result["screens"]),
             "prediction_sha256": sha(PREDICTION), "code_sha256": sha(Path(__file__)),
             "climate_change_attribution_performed": False,
             "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": audit["status"], "checks": checks}))


if __name__ == "__main__":
    main()
