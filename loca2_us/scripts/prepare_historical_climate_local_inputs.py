#!/usr/bin/env python3
"""Prepare an outcome-blind local slice so the climate worker avoids PyArrow."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
FEATURES = [
    "precip_mm", "tmean_c", "tmin_mean_c", "tmax_mean_c", "wet_days_n",
    "cdd_max_days", "rx1day_mm", "rx5day_mm", "stage1_precip_mm",
    "stage2_precip_mm", "stage3_precip_mm", "stage1_precip_share",
    "stage2_precip_share", "stage3_precip_share",
    "precipitation_concentration_hhi", "precipitation_timing_centroid",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    config = tomllib.loads(config_path.read_text())
    output = ROOT / config["inputs"]["prepared_local_inputs"]
    receipt_path = ROOT / config["inputs"]["prepared_local_inputs_receipt"]
    require(not output.exists() and not receipt_path.exists(), "fresh prepared outputs required")
    require(config["sample"]["outcome_columns_read"] is False, "outcome gate opened")
    require(config["sample"]["paired_year_scoring"] is False, "paired scoring gate opened")

    weights_path = ROOT / config["inputs"]["weights"]
    weights_receipt_path = ROOT / config["inputs"]["weights_receipt"]
    weights_receipt = json.loads(weights_receipt_path.read_text())
    require(weights_receipt["status"] == "pass", "weights receipt failed")
    require(weights_receipt["output"]["sha256"] == sha256(weights_path), "weights changed")
    weights = pd.read_parquet(
        weights_path,
        columns=["grid_lat_index", "grid_lon_index", "spatial_weight"],
    ).sort_values(["grid_lat_index", "grid_lon_index"]).reset_index(drop=True)
    require(np.isclose(weights.spatial_weight.sum(), 1.0, rtol=0, atol=1e-12), "weights do not sum to one")

    columns = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice", "season_start", "season_end", *FEATURES]
    rows = []
    sources = []
    for year in range(config["sample"]["year_min"], config["sample"]["year_max"] + 1):
        path = ROOT / config["inputs"]["nclimgrid_feature_pattern"].format(year=year)
        frame = pd.read_parquet(path, columns=columns)
        selected = frame.loc[
            frame.county_geoid.astype(str).str.zfill(5).eq(config["sample"]["county_geoid"])
            & frame.outcome_crop.eq(config["sample"]["crop"])
        ].copy()
        require(not selected.empty, f"nClimGrid sentinel missing in {year}")
        for column in ["season_start", "season_end", *FEATURES]:
            require(selected[column].nunique(dropna=False) == 1, f"nClimGrid practices differ on {column}/{year}")
        rows.append(selected.iloc[0][["harvest_year", "season_start", "season_end", *FEATURES]])
        sources.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path)})
    observed = pd.DataFrame(rows).sort_values("harvest_year").reset_index(drop=True)
    expected_years = list(range(config["sample"]["year_min"], config["sample"]["year_max"] + 1))
    require(observed.harvest_year.astype(int).tolist() == expected_years, "prepared years differ")

    arrays = {
        "grid_lat_index": weights.grid_lat_index.to_numpy(dtype=np.int64),
        "grid_lon_index": weights.grid_lon_index.to_numpy(dtype=np.int64),
        "spatial_weight": weights.spatial_weight.to_numpy(dtype=np.float64),
        "harvest_year": observed.harvest_year.to_numpy(dtype=np.int64),
        "season_start": pd.to_datetime(observed.season_start).dt.strftime("%Y-%m-%d").to_numpy(dtype="U10"),
        "season_end": pd.to_datetime(observed.season_end).dt.strftime("%Y-%m-%d").to_numpy(dtype="U10"),
        **{feature: observed[feature].to_numpy(dtype=np.float64) for feature in FEATURES},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output, **arrays)
    receipt = {
        "schema": "loca2_us_prepared_historical_local_inputs/v1",
        "status": "pass",
        "role": "outcome_blind_local_climate_reference_slice_no_yield_or_paired_scoring",
        "config": {"path": str(config_path.relative_to(ROOT)), "sha256": sha256(config_path)},
        "inputs": {
            "weights": {"path": str(weights_path.relative_to(ROOT)), "sha256": sha256(weights_path)},
            "weights_receipt": {"path": str(weights_receipt_path.relative_to(ROOT)), "sha256": sha256(weights_receipt_path)},
            "nclimgrid": sources,
            "columns_read": columns,
        },
        "support": {"county_geoid": config["sample"]["county_geoid"], "years": expected_years, "grid_cells": int(len(weights))},
        "inspection": {"outcome_columns_read": False, "paired_year_scoring": False},
        "output": {"path": str(output.relative_to(ROOT)), "bytes": output.stat().st_size, "sha256": sha256(output)},
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "grid_cells": len(weights), "years": expected_years, "bytes": output.stat().st_size}))


if __name__ == "__main__":
    main()
