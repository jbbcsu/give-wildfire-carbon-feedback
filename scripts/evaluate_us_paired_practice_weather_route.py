#!/usr/bin/env python3
"""Post-result paired-practice association using NOAA county-average weather."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "us_county_validation/scripts"))
from estimate_us_paired_practice_gap_association import (
    WEATHER, build_paired_frame, fit, load_config,
)

OLD = ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
OLD_CONFIG = ROOT / "us_county_validation/us_paired_practice_gap_association_v1.toml"
OLD_RESULT = ROOT / "data/provenance/us_paired_practice_gap_association_20260827.json"
WEATHER_AUDIT = ROOT / "data/interim/us_county/noaa_county_weather_estimator_comparison_20260916/result.json"
WEATHER_VALIDATION = ROOT / "data/interim/us_county/noaa_county_weather_estimator_validation_20260916/result.json"
NEW = ROOT / "data/interim/us_county/noaa_county_average_crop_year_features_20260916"
PROTOCOL = ROOT / "US_PAIRED_PRACTICE_WEATHER_ROUTE_SENSITIVITY_20260916.md"
KEY = ["outcome_crop", "county_geoid", "harvest_year"]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def replacement_weather() -> tuple[pd.DataFrame, str]:
    summary_path = NEW / "feature_summary.json"
    summary = json.loads(summary_path.read_text())
    if summary["status"] != "complete" or summary["completed_years"] != 45:
        raise ValueError("new NOAA crop-year weather incomplete")
    registered = {int(item["year"]): item["features_sha256"] for item in summary["years"]}
    frames = []
    for year in range(1981, 2019):
        path = NEW / str(year) / "features.parquet"
        if sha(path) != registered[year]:
            raise ValueError("new NOAA yearly source hash differs")
        part = pd.read_parquet(path, columns=KEY + ["season_start", "season_end"] + WEATHER)
        if not part.harvest_year.eq(year).all():
            raise ValueError("new NOAA weather harvest-year partition differs")
        frames.append(part)
    frame = pd.concat(frames, ignore_index=True)
    if frame.duplicated(KEY).any():
        raise ValueError("new NOAA weather crop/county/year keys duplicate")
    return frame, sha(summary_path)


def matched_practices(config: dict) -> tuple[pd.DataFrame, str]:
    required = ["state", "irrigation_practice", "yield_bu_acre", "season_start",
                "season_end", "outcome_source_id", "calendar_role"]
    source = pd.read_parquet(OLD, columns=KEY + required)
    source = source.loc[source.harvest_year.between(1981, 2018)].copy()
    if (set(source.outcome_source_id) != {"nass_quickstats_direct_practice_screen"} or
        set(source.calendar_role) != {"fixed_primary"} or
        source.duplicated(KEY + ["irrigation_practice"]).any()):
        raise ValueError("direct-practice NASS outcomes/calendar identity changed")
    new, summary_hash = replacement_weather()
    joined = source.merge(new, on=KEY, how="left", validate="many_to_one",
                          indicator=True, suffixes=("_old", ""))
    if (not joined._merge.eq("both").all() or
        not joined.season_start_old.eq(joined.season_start).all() or
        not joined.season_end_old.eq(joined.season_end).all()):
        raise ValueError("new weather does not match all old practice calendars")
    joined = joined.drop(columns=["_merge", "season_start_old", "season_end_old"])
    joined["weather_exposure_shared_across_practices"] = True
    paired = build_paired_frame(joined, config)
    return paired, summary_hash


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored sensitivity output required")
    config = load_config(OLD_CONFIG)
    old = json.loads(OLD_RESULT.read_text())
    weather_audit = json.loads(WEATHER_AUDIT.read_text())
    weather_validation = json.loads(WEATHER_VALIDATION.read_text())
    if (config["input"]["expected_panel_sha256"] != sha(OLD) or
        old["status"] != "completed_historical_paired_practice_yield_gap_association_only" or
        old["input"]["sha256"] != sha(OLD) or
        old["config"]["sha256"] != sha(OLD_CONFIG) or
        weather_audit["status"] != "source_only_exact_calendar_weather_estimator_comparison" or
        weather_audit["old_source_sha256"] != sha(OLD) or
        weather_validation["status"] != "independent_source_only_weather_estimator_comparison_validated" or
        weather_validation["comparison_sha256"] != sha(WEATHER_AUDIT)):
        raise ValueError("old association or independently audited new weather changed")
    paired, summary_hash = matched_practices(config)
    if len(paired) != old["input"]["paired_rows"] or summary_hash != weather_audit["new_feature_summary_sha256"]:
        raise ValueError("paired-practice/weather source support differs from registered baseline")
    estimates = []
    comparisons = []
    for old_fit in old["estimates"]:
        crop, form = old_fit["crop"], old_fit["form"]
        new_fit = fit(paired, crop, form, config)
        if (new_fit["rows"] != old_fit["rows"] or
            new_fit["counties"] != old_fit["counties"] or
            new_fit["states"] != old_fit["states"] or
            [record["term"] for record in new_fit["coefficients"]] !=
            [record["term"] for record in old_fit["coefficients"]]):
            raise ValueError("paired model support/design differs across weather route")
        estimates.append(new_fit)
        comparisons.append({"crop": crop, "form": form,
                            "old_median_quantity_ratio_percent": old_fit["contrasts"]["quantity_increment_at_median"]["fitted_irrigated_to_non_irrigated_yield_ratio_percent_difference"],
                            "new_median_quantity_ratio_percent": new_fit["contrasts"]["quantity_increment_at_median"]["fitted_irrigated_to_non_irrigated_yield_ratio_percent_difference"],
                            "old_middle_for_late_ratio_percent": old_fit["contrasts"].get("stage3_to_stage2_shift", {}).get("fitted_irrigated_to_non_irrigated_yield_ratio_percent_difference"),
                            "new_middle_for_late_ratio_percent": new_fit["contrasts"].get("stage3_to_stage2_shift", {}).get("fitted_irrigated_to_non_irrigated_yield_ratio_percent_difference")})
    result = {"status": "post_result_us_paired_practice_weather_route_association_sensitivity_not_causal",
              "paired_rows": len(paired), "old_source_sha256": sha(OLD),
              "old_config_sha256": sha(OLD_CONFIG), "old_result_sha256": sha(OLD_RESULT),
              "weather_comparison_sha256": sha(WEATHER_AUDIT),
              "weather_comparison_validation_sha256": sha(WEATHER_VALIDATION),
              "new_feature_summary_sha256": summary_hash,
              "protocol_sha256": sha(PROTOCOL), "code_sha256": sha(Path(__file__)),
              "estimates": estimates, "route_comparisons": comparisons,
              "primary_descriptors": {"corn_grain": "quantity", "soybeans": "quantity_timing"},
              "row_predictions_emitted": False, "causal_claim_authorized": False,
              "damage_claim_authorized": False, "scc_claim_authorized": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"paired_rows": len(paired), "route_comparisons": comparisons}))


if __name__ == "__main__":
    main()
