#!/usr/bin/env python3
"""Validate the assembled sorghum/cotton direct-weather panel."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    frame = pd.read_parquet(args.panel)
    require(digest(args.panel) == receipt["output"]["sha256"], "panel hash differs")
    require(len(frame) == receipt["output"]["rows"], "row count differs")
    keys = ["crop", "county_geoid", "harvest_year"]
    groups = frame.groupby(keys, observed=True)
    require(groups.size().eq(2).all(), "practice pair count differs")
    require(groups.practice.agg(set).map(lambda x: x == {"irrigated", "non_irrigated"}).all(), "practice labels differ")
    columns = receipt["direct_weather_feature_columns_checked"]
    require(not frame[columns].isna().any().any() and np.isfinite(frame[columns]).all().all(), "weather values missing/nonfinite")
    require((frame.precip_mm >= 0).all() and (frame.wet_days_ge_1mm >= 0).all() and (frame.cdd_max_days >= 0).all(), "physical bounds differ")
    require(np.allclose(frame.stage1_precip_mm + frame.stage2_precip_mm + frame.stage3_precip_mm, frame.precip_mm, rtol=0, atol=1e-6), "stage totals differ")
    require(all(not groups[column].nunique(dropna=False).gt(1).any() for column in columns), "weather differs by practice")
    require(frame.pdsi_spei_scpdsi_coincluded.eq(False).all(), "drought-index co-inclusion gate opened")
    require(frame.response_estimation_authorized.eq(False).all() and frame.scc_authorized.eq(False).all(), "downstream gate opened")
    result = {
        "status": "validated_complete_direct_weather_join",
        "rows": len(frame), "paired_crop_county_years": int(groups.ngroups),
        "direct_weather_feature_columns_checked": len(columns), "missing_feature_cells": int(frame[columns].isna().sum().sum()),
        "stage_rainfall_reconciles": True, "features_shared_across_practices": True,
        "drought_index_coincluded": False, "response_estimation_authorized": False, "scc_authorized": False,
    }
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
