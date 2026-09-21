#!/usr/bin/env python3
"""Independent Arrow-source reconstruction of county weather comparison."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
NEW = ROOT / "data/interim/us_county/noaa_county_average_crop_year_features_20260916"
RESULT = ROOT / "data/interim/us_county/noaa_county_weather_estimator_comparison_20260916/result.json"
SOURCE_SCRIPT = ROOT / "scripts/compare_us_county_weather_estimators.py"
KEY = ["outcome_crop", "county_geoid", "harvest_year"]
FIELDS = ["precip_mm", "tmean_c", "wet_days", "cdd_max_days", "rx5day_mm",
          "stage1_precip_share", "stage2_precip_share"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_number(actual: float, reported: float, label: str) -> None:
    if not np.isfinite(actual) or not np.isfinite(reported) or abs(actual - reported) > 1e-10:
        raise ValueError(f"independent weather statistic differs: {label}")


def read_sources() -> pd.DataFrame:
    old_fields = ["wet_days_n" if field == "wet_days" else field for field in FIELDS]
    old = pq.read_table(OLD, columns=KEY + ["irrigation_practice", "season_start",
                                             "season_end"] + old_fields).to_pandas()
    old = old.loc[old.irrigation_practice.eq("non_irrigated")].copy()
    old = old.drop(columns="irrigation_practice").rename(columns={"wet_days_n": "wet_days"})
    new_fields = ["wet_days_ge_1mm" if field == "wet_days" else field for field in FIELDS]
    parts = []
    for year in range(1981, 2020):
        path = NEW / str(year) / "features.parquet"
        parts.append(pq.read_table(path, columns=KEY + ["season_start", "season_end"] +
                                    new_fields).to_pandas())
    fresh = pd.concat(parts, ignore_index=True).rename(columns={"wet_days_ge_1mm": "wet_days"})
    if old.duplicated(KEY).any() or fresh.duplicated(KEY).any():
        raise ValueError("independent weather keys not unique")
    joined = old.merge(fresh, on=KEY, how="left", validate="one_to_one",
                       indicator=True, suffixes=("_old", "_new"))
    if (not joined._merge.eq("both").all() or
        not joined.season_start_old.eq(joined.season_start_new).all() or
        not joined.season_end_old.eq(joined.season_end_new).all()):
        raise ValueError("independent exact-calendar weather support differs")
    return joined.sort_values(KEY).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored validation output required")
    reported = json.loads(RESULT.read_text())
    if (reported["status"] != "source_only_exact_calendar_weather_estimator_comparison" or
        reported["old_source_sha256"] != sha(OLD) or
        reported["code_sha256"] != sha(SOURCE_SCRIPT) or
        reported["yield_values_read"] is not False):
        raise ValueError("reported source-only comparison identity changed")
    joined = read_sources()
    if len(joined) != reported["exact_calendar_matches"]:
        raise ValueError("independent weather comparison support count changed")
    checks = 1
    for crop, group in joined.groupby("outcome_crop", sort=True):
        if len(group) != reported["crops"][crop]["matched_calendar_rows"]:
            raise ValueError("independent crop sample differs")
        checks += 1
        anchors = reported["fixed_anchors"][crop]
        rows = group.iloc[sorted({0, len(group)//2, len(group)-1})]
        for anchor, (_, row) in zip(anchors, rows.iterrows()):
            if {name: str(row[name]) for name in KEY} != anchor["key"]:
                raise ValueError("independent anchor key differs")
            checks += 1
            for field in FIELDS:
                for side in ("old", "new"):
                    validate_number(float(row[f"{field}_{side}"]),
                                    anchor["values"][field][side], f"anchor/{crop}/{field}/{side}")
                    checks += 1
        for field in FIELDS:
            left = group[f"{field}_old"].to_numpy(dtype=float)
            right = group[f"{field}_new"].to_numpy(dtype=float)
            valid = np.isfinite(left) & np.isfinite(right)
            rec = reported["crops"][crop]["fields"][field]
            if int(valid.sum()) != rec["n"] or int((~valid).sum()) != rec["missing_or_nonfinite_pairs"]:
                raise ValueError("independent field support differs")
            checks += 2
            delta = right[valid] - left[valid]
            absolute = np.abs(delta)
            values = {"mean_new_minus_old": np.mean(delta),
                      "median_absolute_difference": np.median(absolute),
                      "p95_absolute_difference": np.percentile(absolute, 95),
                      "rmse_difference": np.linalg.norm(delta) / np.sqrt(len(delta)),
                      "pearson_correlation": np.corrcoef(left[valid], right[valid])[0, 1]}
            for name, value in values.items():
                validate_number(float(value), rec[name], f"{crop}/{field}/{name}")
                checks += 1
    audit = {"status": "independent_source_only_weather_estimator_comparison_validated",
             "numeric_and_support_checks": checks, "comparison_sha256": sha(RESULT),
             "code_sha256": sha(Path(__file__)), "yield_values_read": False,
             "climate_change_attribution_performed": False,
             "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": audit["status"], "checks": checks}))


if __name__ == "__main__":
    main()
