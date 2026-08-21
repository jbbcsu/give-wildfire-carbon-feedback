#!/usr/bin/env python3
"""Combine compatible crop-season panels without erasing crop identity.

This is a data-contract step, not permission to estimate common crop slopes.
Each input must contain exactly one crop/irrigation label and retain its own
observed-yield coverage. The output includes a source-panel field for audits.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


REQUIRED = {
    "harvest_year", "lat", "lon_360", "crop", "irrigation", "tmean_c",
    "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm",
    "yield_observed", "yield_t_ha",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True, help="crop-season estimation parquet; repeatable")
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    if len(args.input) < 2:
        raise ValueError("At least two crop-season panels are required")

    frames: list[pd.DataFrame] = []
    audit_sources: list[dict[str, object]] = []
    labels: set[tuple[str, str]] = set()
    for filename in args.input:
        path = Path(filename)
        frame = pd.read_parquet(path)
        if missing := REQUIRED - set(frame.columns):
            raise ValueError(f"{path} missing required fields {sorted(missing)}")
        crops = frame.crop.dropna().astype(str).unique()
        irrigation = frame.irrigation.dropna().astype(str).unique()
        if len(crops) != 1 or len(irrigation) != 1:
            raise ValueError(f"{path} must contain exactly one crop and irrigation label")
        label = (crops[0], irrigation[0])
        if label in labels:
            raise ValueError(f"Duplicate crop/irrigation input label {label}")
        labels.add(label)
        frame = frame.copy()
        frame["source_panel"] = str(path)
        frames.append(frame)
        audit_sources.append({
            "file": str(path), "crop": crops[0], "irrigation": irrigation[0],
            "n_rows": int(len(frame)), "n_observed_yields": int(frame.yield_observed.sum()),
            "n_grids": int(frame.loc[frame.yield_observed, ["lat", "lon_360"]].drop_duplicates().shape[0]),
        })
    columns = set(frames[0].columns)
    if any(set(frame.columns) != columns for frame in frames[1:]):
        raise ValueError("Input panel schemas differ; harmonize explicitly before combining")
    combined = pd.concat(frames, ignore_index=True)
    keys = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
    if combined.duplicated(keys).any():
        raise ValueError("Duplicate crop-season-grid-year rows after combine")
    if not combined.yield_observed.eq(combined.yield_t_ha.notna()).all():
        raise ValueError("Yield-observed flag does not match yield missingness")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(args.out, index=False)
    audit = {
        "purpose": "Multi-crop data contract only; no common-slope response estimate is authorized.",
        "sources": audit_sources,
        "n_rows": int(len(combined)),
        "n_observed_yields": int(combined.yield_observed.sum()),
        "crops": sorted(label[0] for label in labels),
    }
    Path(args.audit_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.audit_out).write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
