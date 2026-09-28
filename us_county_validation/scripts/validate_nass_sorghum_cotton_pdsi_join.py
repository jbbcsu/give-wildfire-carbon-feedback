#!/usr/bin/env python3
"""Validate the crop-outcome/PDSI join without importing its builder."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

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
    parser.add_argument("--joined", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    frame = pd.read_parquet(args.joined)
    require(digest(args.joined) == receipt["output"]["sha256"], "output hash differs")
    require(len(frame) == receipt["output"]["rows"], "row count differs")
    keys = ["crop", "county_geoid", "harvest_year"]
    groups = frame.groupby(keys, observed=True)
    require(groups.size().eq(2).all(), "practice pairs are incomplete")
    require(groups.practice.agg(set).map(lambda x: x == {"irrigated", "non_irrigated"}).all(), "practice labels differ")
    pdsi_columns = [column for column in frame if column.startswith("pdsi_")]
    require(len(pdsi_columns) == 25 and not frame[pdsi_columns].isna().any().any(), "PDSI feature schema differs")
    require(all(not groups[column].nunique(dropna=False).gt(1).any() for column in pdsi_columns), "features differ by practice")
    require(frame.moisture_family.eq("pdsi_only_competing_representation").all(), "moisture family differs")
    require(frame.direct_precipitation_coincluded.eq(False).all() and frame.temperature_coincluded.eq(False).all(), "double-count gate opened")
    require(frame.response_estimation_authorized.eq(False).all() and frame.scc_authorized.eq(False).all(), "downstream gate opened")
    pairs = frame.drop_duplicates(keys)
    result = {
        "status": "validated_complete_mutually_exclusive_pdsi_join",
        "rows": len(frame), "paired_crop_county_years": len(pairs),
        "pairs_by_crop": {k: int(v) for k, v in pairs.groupby("crop").size().items()},
        "pdsi_feature_columns": len(pdsi_columns), "missing_pdsi_cells": int(frame[pdsi_columns].isna().sum().sum()),
        "features_shared_across_practices": True,
        "direct_precipitation_coincluded": False, "temperature_coincluded": False,
        "response_estimation_authorized": False, "scc_authorized": False,
    }
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
