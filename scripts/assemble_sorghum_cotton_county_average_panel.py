#!/usr/bin/env python3
"""Assemble 38 yearly NOAA county-average features onto paired crop outcomes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

KEYS = ["crop", "county_geoid", "harvest_year"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--feature-root", type=Path, required=True)
    parser.add_argument("--feature-summary", type=Path, required=True)
    parser.add_argument("--source-summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    feature_summary = json.loads(args.feature_summary.read_text())
    source_summary = json.loads(args.source_summary.read_text())
    if feature_summary["status"] != "complete_38_sequential_year_jobs" or feature_summary["completed_years"] != 38:
        raise ValueError("feature-year summary is incomplete")
    if source_summary["status"] != "complete" or source_summary["completed_batches"] != 90:
        raise ValueError("NOAA source summary is incomplete")
    frames = []
    for record in feature_summary["year_receipts"]:
        year = int(record["year"])
        receipt_path = args.feature_root / str(year) / "result.json"
        feature_path = args.feature_root / str(year) / "features.parquet"
        if digest(receipt_path) != record["receipt_sha256"] or digest(feature_path) != record["features_sha256"]:
            raise ValueError(f"year {year} feature identity differs")
        frame = pd.read_parquet(feature_path)
        if not frame.harvest_year.eq(year).all() or len(frame) != record["rows"]:
            raise ValueError(f"year {year} feature content differs")
        frames.append(frame)
    features = pd.concat(frames, ignore_index=True)
    if len(features) != feature_summary["total_rows"] or features.duplicated(KEYS).any():
        raise ValueError("assembled feature keys differ")
    panel = pd.read_parquet(args.panel)
    joined = panel.merge(features, on=KEYS, how="left", validate="many_to_one")
    feature_columns = [
        "precip_mm", "wet_days_ge_1mm", "cdd_max_days", "rx5day_mm", "tmean_c",
        "tmax_exceedance_29c_c_days", "tmax_exceedance_30c_c_days",
        "stage1_precip_mm", "stage2_precip_mm", "stage3_precip_mm",
        "stage1_precip_share", "stage2_precip_share", "stage3_precip_share",
        "precipitation_concentration_hhi",
    ]
    if joined[feature_columns].isna().any().any():
        raise ValueError("eligible outcome panel has missing direct-weather features")
    for _, group in joined.groupby(KEYS, observed=True):
        if len(group) != 2 or group[feature_columns].nunique(dropna=False).gt(1).any():
            raise ValueError("paired practices do not share identical county weather")
    joined["moisture_family"] = "direct_precipitation_with_temperature_control_candidate"
    joined["pdsi_spei_scpdsi_coincluded"] = False
    joined["response_estimation_authorized"] = False
    joined["scc_authorized"] = False
    args.out.parent.mkdir(parents=True, exist_ok=True)
    joined.to_parquet(args.out, index=False)
    pairs = joined.drop_duplicates(KEYS)
    receipt = {
        "status": "complete_primary_calendar_direct_weather_join",
        "panel_sha256": digest(args.panel), "feature_summary_sha256": digest(args.feature_summary),
        "source_summary": {
            "path": str(args.source_summary), "sha256": digest(args.source_summary),
            "source_objects": source_summary["source_objects"], "source_bytes": source_summary["source_bytes"],
        },
        "output": {"path": str(args.out), "sha256": digest(args.out), "rows": len(joined)},
        "paired_crop_county_years": len(pairs),
        "pairs_by_crop": {k: int(v) for k, v in pairs.groupby("crop").size().items()},
        "counties_by_crop": {k: int(v) for k, v in pairs.groupby("crop").county_geoid.nunique().items()},
        "direct_weather_feature_columns_checked": feature_columns,
        "features_shared_across_practices": True,
        "moisture_family": "direct_precipitation_with_temperature_control_candidate",
        "pdsi_spei_scpdsi_coincluded": False,
        "response_estimation_authorized": False, "scc_authorized": False,
    }
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()

