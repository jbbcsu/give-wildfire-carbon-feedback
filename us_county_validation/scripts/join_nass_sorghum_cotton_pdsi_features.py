#!/usr/bin/env python3
"""Join primary-calendar PDSI features to geography-eligible crop outcomes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

KEYS = ["crop", "county_geoid", "harvest_year"]
METRICS = {
    "index_day_weighted_mean": "mean",
    "index_monthly_minimum": "minimum",
    "index_day_equivalents_at_or_below_moderate": "moderate_days",
    "index_day_equivalents_at_or_below_severe": "severe_days",
    "window_days": "window_days",
}
WINDOWS = ["preplant90", "stage1", "stage2", "stage3", "season"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--monthly-index", type=Path, required=True)
    parser.add_argument("--source-provenance", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    panel = pd.read_parquet(args.panel)
    monthly = pd.read_parquet(args.monthly_index)
    features = pd.read_parquet(args.features).rename(columns={"calendar_crop": "crop"})
    features = features.loc[features.calendar_role.eq("fixed_primary")]
    support = panel[KEYS].drop_duplicates()
    selected = support.merge(features, on=KEYS, how="left", validate="one_to_many")
    counts = selected.groupby(KEYS).window_id.nunique()
    if len(counts) != len(support) or not counts.eq(len(WINDOWS)).all() or set(selected.window_id) != set(WINDOWS):
        raise ValueError("not every eligible crop/county/year receives all PDSI windows")
    pieces = []
    for metric, short in METRICS.items():
        wide = selected.pivot(index=KEYS, columns="window_id", values=metric)
        wide = wide[WINDOWS].rename(columns={window: f"pdsi_{window}_{short}" for window in WINDOWS})
        pieces.append(wide)
    wide = pd.concat(pieces, axis=1).reset_index()
    joined = panel.merge(wide, on=KEYS, how="left", validate="many_to_one")
    pdsi_columns = [column for column in joined if column.startswith("pdsi_")]
    if joined[pdsi_columns].isna().any().any():
        raise ValueError("joined PDSI panel contains missing features")
    for _, group in joined.groupby(KEYS, observed=True):
        if len(group) != 2 or group[pdsi_columns].nunique(dropna=False).gt(1).any():
            raise ValueError("PDSI features differ across paired practices")
    joined["moisture_family"] = "pdsi_only_competing_representation"
    joined["direct_precipitation_coincluded"] = False
    joined["temperature_coincluded"] = False
    joined["response_estimation_authorized"] = False
    joined["scc_authorized"] = False
    args.out.parent.mkdir(parents=True, exist_ok=True)
    joined.to_parquet(args.out, index=False)
    pairs = joined.drop_duplicates(KEYS)
    receipt = {
        "status": "complete_primary_calendar_pdsi_join",
        "panel_sha256": digest(args.panel), "feature_sha256": digest(args.features),
        "monthly_index": {
            "path": str(args.monthly_index), "sha256": digest(args.monthly_index),
            "rows": len(monthly), "counties": int(monthly.county_geoid.nunique()),
            "year_min": int(monthly.year.min()), "year_max": int(monthly.year.max()),
            "index_source_id": str(monthly.index_source_id.iloc[0]),
        },
        "source_provenance": {"path": str(args.source_provenance), "sha256": digest(args.source_provenance)},
        "output": {"path": str(args.out), "sha256": digest(args.out), "rows": len(joined)},
        "paired_crop_county_years": len(pairs),
        "pairs_by_crop": {k: int(v) for k, v in pairs.groupby("crop").size().items()},
        "counties_by_crop": {k: int(v) for k, v in pairs.groupby("crop").county_geoid.nunique().items()},
        "windows": WINDOWS, "pdsi_feature_columns": len(pdsi_columns),
        "features_shared_across_practices": True,
        "moisture_family": "pdsi_only_competing_representation",
        "direct_precipitation_coincluded": False, "temperature_coincluded": False,
        "response_estimation_authorized": False, "scc_authorized": False,
    }
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
