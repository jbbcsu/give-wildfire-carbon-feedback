#!/usr/bin/env python3
"""Audit stability of fixed county irrigation-share selectors across Census vintages."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


YEARS = (2012, 2017, 2022)
THRESHOLDS = (10, 20, 30)
REQUIRED = {"crop", "census_year", "county_geoid", "irrigation_share", "share_eligible"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path, expected_year: int) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"county_geoid": "string"})
    missing = REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    years = set(pd.to_numeric(frame.census_year, errors="raise").astype(int))
    if years != {expected_year}:
        raise ValueError(f"{path}: expected only Census year {expected_year}, got {sorted(years)}")
    frame["county_geoid"] = frame.county_geoid.str.strip().str.zfill(5)
    eligible = frame.loc[frame.share_eligible.eq(True), ["crop", "county_geoid", "irrigation_share"]].copy()
    eligible["irrigation_share"] = pd.to_numeric(eligible.irrigation_share, errors="raise")
    if eligible.irrigation_share.isna().any() or not eligible.irrigation_share.between(0.0, 1.0).all():
        raise ValueError(f"{path}: eligible shares must be finite and within [0,1]")
    if eligible.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError(f"{path}: invalid county GEOID")
    if eligible.duplicated(["crop", "county_geoid"]).any():
        raise ValueError(f"{path}: duplicate crop-county keys")
    return eligible


def summarize(paths: dict[int, Path]) -> dict:
    frames = {year: load(paths[year], year) for year in YEARS}
    common_crops = sorted(set.intersection(*(set(frame.crop) for frame in frames.values())))
    if common_crops != ["corn", "soybeans", "wheat"]:
        raise ValueError(f"expected corn, soybeans, and wheat in every vintage, got {common_crops}")

    results = []
    for crop in common_crops:
        merged = None
        for year in YEARS:
            part = frames[year].loc[frames[year].crop.eq(crop), ["county_geoid", "irrigation_share"]]
            part = part.rename(columns={"irrigation_share": f"share_{year}"})
            merged = part if merged is None else merged.merge(part, on="county_geoid", how="inner", validate="one_to_one")
        if merged is None or merged.empty:
            raise ValueError(f"{crop}: no common eligible counties")
        crop_result = {"crop": crop, "common_numeric_counties": int(len(merged)), "pairs": []}
        for left, right in ((2012, 2017), (2017, 2022), (2012, 2022)):
            x = merged[f"share_{left}"].to_numpy(dtype=float)
            y = merged[f"share_{right}"].to_numpy(dtype=float)
            if np.std(x) == 0 or np.std(y) == 0:
                raise ValueError(f"{crop} {left}-{right}: correlation undefined")
            pair = {
                "left_year": left,
                "right_year": right,
                "pearson_correlation": float(np.corrcoef(x, y)[0, 1]),
                "mean_absolute_share_difference": float(np.mean(np.abs(x - y))),
                "thresholds": [],
            }
            for threshold in THRESHOLDS:
                left_flag = x <= threshold / 100.0
                right_flag = y <= threshold / 100.0
                switches = int(np.count_nonzero(left_flag != right_flag))
                pair["thresholds"].append({
                    "irrigation_share_at_most_percent": threshold,
                    "agreement_fraction": float(np.mean(left_flag == right_flag)),
                    "switching_counties": switches,
                })
            crop_result["pairs"].append(pair)
        results.append(crop_result)

    return {
        "schema": "us_irrigation_share_vintage_stability_v1",
        "status": "validated_descriptive_selector_stability_not_irrigation_effect_response_damage_or_scc",
        "inputs": [{"census_year": year, "path": str(paths[year]), "sha256": sha256(paths[year])} for year in YEARS],
        "results": results,
        "interpretation": "Common-county agreement quantifies sensitivity of fixed share selectors to Census vintage; it does not identify irrigation effects.",
        "primary_2017_selector_changed": False,
        "response_damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for year in YEARS:
        parser.add_argument(f"--shares-{year}", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    paths = {year: getattr(args, f"shares_{year}") for year in YEARS}
    result = summarize(paths)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("validated irrigation-share vintage stability for " + ", ".join(r["crop"] for r in result["results"]))


if __name__ == "__main__":
    main()
