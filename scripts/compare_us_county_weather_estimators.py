#!/usr/bin/env python3
"""Compare exact-calendar regional NOAA county weather estimators, no yields."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
NEW = ROOT / "data/interim/us_county/noaa_county_average_crop_year_features_20260916"
SUMMARY = NEW / "feature_summary.json"
PROTOCOL = ROOT / "US_COUNTY_WEATHER_ESTIMATOR_COMPARISON_PROTOCOL_20260916.md"
KEY = ["outcome_crop", "county_geoid", "harvest_year"]
META = ["season_start", "season_end", "calendar_source_id", "calendar_vintage", "stage_definition"]
FIELDS = {"precip_mm": "mm/season", "tmean_c": "degC/season",
          "wet_days": "days/season", "cdd_max_days": "days/season",
          "rx5day_mm": "mm", "stage1_precip_share": "fraction",
          "stage2_precip_share": "fraction"}
OLD_MAP = {"wet_days": "wet_days_n"}
NEW_MAP = {"wet_days": "wet_days_ge_1mm"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def load_old() -> pd.DataFrame:
    columns = (KEY + ["irrigation_practice", "wet_day_threshold_mm"] + META +
               [OLD_MAP.get(name, name) for name in FIELDS])
    frame = pd.read_parquet(OLD, columns=columns)
    if (set(frame.irrigation_practice) != {"irrigated", "non_irrigated"} or
        set(frame.wet_day_threshold_mm) != {1.0} or
        set(frame.harvest_year) != set(range(1981, 2020)) or
        frame.duplicated(KEY + ["irrigation_practice"]).any()):
        raise ValueError("old weather/practice support or wet-day threshold differs")
    counts = frame.groupby(KEY, sort=False).size()
    if not counts.eq(2).all():
        raise ValueError("old practice pairs do not share every weather key")
    compare = [name for name in frame.columns if name not in KEY + ["irrigation_practice"]]
    if frame.groupby(KEY, sort=False)[compare].nunique(dropna=False).gt(1).any().any():
        raise ValueError("old irrigation-practice rows have different weather/calendar")
    frame = frame.loc[frame.irrigation_practice.eq("non_irrigated")].copy()
    return frame.drop(columns="irrigation_practice").rename(
        columns={"wet_days_n": "wet_days"})


def load_new() -> tuple[pd.DataFrame, str]:
    summary = json.loads(SUMMARY.read_text())
    if summary["status"] != "complete" or summary["completed_years"] != 45:
        raise ValueError("new weather feature source incomplete")
    years = {int(item["year"]): item for item in summary["years"]}
    frames = []
    for year in range(1981, 2020):
        path = NEW / str(year) / "features.parquet"
        if sha(path) != years[year]["features_sha256"]:
            raise ValueError(f"new weather year {year} hash changed")
        cols = KEY + META + [NEW_MAP.get(name, name) for name in FIELDS]
        part = pd.read_parquet(path, columns=cols)
        if not part.harvest_year.eq(year).all():
            raise ValueError("new weather year partition key differs")
        frames.append(part)
    frame = pd.concat(frames, ignore_index=True).rename(
        columns={"wet_days_ge_1mm": "wet_days"})
    if frame.duplicated(KEY).any():
        raise ValueError("new weather features duplicate key")
    return frame, sha(SUMMARY)


def moments(left: np.ndarray, right: np.ndarray) -> dict:
    valid = np.isfinite(left) & np.isfinite(right)
    if not valid.any():
        return {"n": 0, "missing_or_nonfinite_pairs": len(left), "statistics": None}
    a, b = left[valid], right[valid]
    diff = b - a
    correlation = (float(np.corrcoef(a, b)[0, 1])
                   if np.std(a) > 0 and np.std(b) > 0 and len(a) > 1 else None)
    return {"n": int(len(a)), "missing_or_nonfinite_pairs": int(len(left) - len(a)),
            "mean_new_minus_old": float(np.mean(diff)),
            "median_absolute_difference": float(np.median(np.abs(diff))),
            "p95_absolute_difference": float(np.quantile(np.abs(diff), 0.95)),
            "rmse_difference": float(np.sqrt(np.mean(diff**2))),
            "pearson_correlation": correlation}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored output required")
    old = load_old()
    newer, new_hash = load_new()
    merged = old.merge(newer, on=KEY, how="left", validate="one_to_one",
                       indicator=True, suffixes=("_old", "_new"))
    key_match = merged._merge.eq("both")
    calendar_match = key_match.copy()
    for name in META:
        left = merged[f"{name}_old"].astype(str)
        right = merged[f"{name}_new"].astype(str)
        calendar_match &= left.eq(right)
    comparison = merged.loc[calendar_match].copy().sort_values(KEY)
    if comparison.empty:
        raise ValueError("no exact-calendar comparable NOAA weather keys")
    crops = {}
    anchors = {}
    for crop, group in comparison.groupby("outcome_crop", sort=True):
        measurements = {}
        for field, unit in FIELDS.items():
            measurements[field] = {"unit": unit, **moments(
                group[f"{field}_old"].to_numpy(dtype=float),
                group[f"{field}_new"].to_numpy(dtype=float))}
        crops[crop] = {"matched_calendar_rows": len(group), "fields": measurements}
        indexes = sorted({0, len(group)//2, len(group)-1})
        anchors[crop] = [
            {"key": {name: str(row[name]) for name in KEY},
             "values": {field: {"old": float(row[f"{field}_old"]),
                                "new": float(row[f"{field}_new"])} for field in FIELDS}}
            for _, row in group.iloc[indexes].iterrows()]
    result = {"status": "source_only_exact_calendar_weather_estimator_comparison",
              "old_source_sha256": sha(OLD), "new_feature_summary_sha256": new_hash,
              "protocol_sha256": sha(PROTOCOL), "code_sha256": sha(Path(__file__)),
              "old_unique_weather_keys": len(old),
              "new_exact_key_matches": int(key_match.sum()),
              "old_keys_without_new_weather": int((~key_match).sum()),
              "exact_calendar_matches": int(calendar_match.sum()),
              "matched_keys_with_calendar_mismatch": int((key_match & ~calendar_match).sum()),
              "crops": crops, "fixed_anchors": anchors,
              "yield_values_read": False, "climate_change_attribution_performed": False,
              "economic_damage_or_scc_estimated": False}
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"old_keys": len(old), "exact_calendar_matches": int(calendar_match.sum()),
                      "crops": {crop: {name: round(value["rmse_difference"], 4)
                                           for name, value in data["fields"].items()}
                                for crop, data in crops.items()}}))


if __name__ == "__main__":
    main()
