#!/usr/bin/env python3
"""Plan LOCA2 historical sentinel chunks without reading climate values."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import s3fs
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def chunk_ids(indices: np.ndarray, width: int) -> list[int]:
    require(width > 0 and indices.ndim == 1 and len(indices) > 0, "invalid chunk inputs")
    return sorted({int(index // width) for index in indices})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    output = args.output if args.output.is_absolute() else ROOT / args.output
    require(not output.exists(), "fresh output required")
    config = tomllib.loads(config_path.read_text())
    require(config["sample"]["outcome_columns_read"] is False, "outcome gate opened")
    require(config["sample"]["paired_year_scoring"] is False, "paired-year gate opened")

    weights_path = ROOT / config["inputs"]["weights"]
    weights_receipt_path = ROOT / config["inputs"]["weights_receipt"]
    weights_receipt = json.loads(weights_receipt_path.read_text())
    require(weights_receipt["status"] == "pass", "weights receipt failed")
    require(digest(weights_path) == weights_receipt["output"]["sha256"], "weights changed")
    weights = pd.read_parquet(weights_path, columns=["grid_lat_index", "grid_lon_index"])

    fs = s3fs.S3FileSystem(anon=True, client_kwargs={"endpoint_url": config["source"]["endpoint_url"]})
    store = config["source"]["store"]
    dataset = xr.open_zarr(fs.get_mapper(store), consolidated=True, chunks=None)
    require(dataset.pr.attrs.get("LOCA2_version") == config["source"]["precipitation_version"], "precipitation version differs")
    mask = (
        (dataset.source_id.values == config["source"]["source_id"])
        & (dataset.experiment_id.values == config["source"]["experiment_id"])
        & (dataset.variant_label.values == config["source"]["variant_label"])
    )
    matches = np.flatnonzero(mask)
    require(len(matches) == 1, "ensemble identity is not unique")
    ensemble_index = int(matches[0])
    chunk_shape = tuple(int(value) for value in dataset.pr.encoding["chunks"])

    time_indices = []
    for year in range(int(config["sample"]["year_min"]), int(config["sample"]["year_max"]) + 1):
        start = np.datetime64(f"{year}-{config['sample']['season_start_month_day']}")
        end = np.datetime64(f"{year}-{config['sample']['season_end_month_day']}")
        selected = np.flatnonzero((dataset.time.values >= start) & (dataset.time.values <= end))
        require(len(selected) == int((end - start).astype(int)) + 1, f"daily support differs: {year}")
        time_indices.extend(selected.tolist())
    time_chunks = chunk_ids(np.asarray(time_indices, dtype=int), chunk_shape[1])
    spatial_chunks = sorted({
        (int(y) // chunk_shape[2], int(x) // chunk_shape[3])
        for y, x in zip(weights.grid_lat_index, weights.grid_lon_index, strict=True)
    })
    records = []
    for variable in config["source"]["variables"]:
        require(tuple(dataset[variable].encoding["chunks"]) == chunk_shape, "variable chunk shape differs")
        for time_chunk in time_chunks:
            for lat_chunk, lon_chunk in spatial_chunks:
                key = f"{variable}/{ensemble_index}.{time_chunk}.{lat_chunk}.{lon_chunk}"
                records.append({
                    "variable": variable,
                    "key": key,
                    "compressed_bytes": int(fs.info(f"{store}/{key}")["size"]),
                })
    total = sum(record["compressed_bytes"] for record in records)
    cap = int(config["resources"]["maximum_remote_chunk_mib"]) * 1024**2
    status = "pass_metadata_only_plan_within_cap" if total <= cap else "blocked_remote_chunk_plan_exceeds_cap"
    result = {
        "schema": "loca2_us_historical_climate_sentinel_preflight/v1",
        "status": status,
        "role": "metadata_only_remote_chunk_plan_no_climate_values_or_outcomes",
        "config": {"path": str(config_path.relative_to(ROOT)), "sha256": digest(config_path)},
        "weights": {"path": str(weights_path.relative_to(ROOT)), "sha256": digest(weights_path), "grid_cells": int(len(weights))},
        "source": {
            "store": store,
            "source_id": config["source"]["source_id"],
            "experiment_id": config["source"]["experiment_id"],
            "variant_label": config["source"]["variant_label"],
            "ensemble_index": ensemble_index,
            "precipitation_version": dataset.pr.attrs["LOCA2_version"],
            "chunk_shape": chunk_shape,
        },
        "plan": {
            "time_chunks": time_chunks,
            "spatial_chunks": [list(value) for value in spatial_chunks],
            "remote_objects": len(records),
            "remote_chunks": records,
            "compressed_bytes": total,
            "compressed_mib": total / 1024**2,
            "maximum_remote_chunk_mib": int(config["resources"]["maximum_remote_chunk_mib"]),
        },
        "inspection": {"climate_values_read": False, "outcome_columns_read": False},
        "next_step_if_blocked": "Freeze two chronological six-year partitions, require each partition plan below the unchanged cap, build each serially under the 512 MiB monitor, then concatenate only after exact key, calendar, feature, source, and nonoverlap checks; compare the combined 2001-2012 distribution without paired-year scoring.",
        "claim_gates": {
            "county_geometry_weights": True,
            "second_county_climate_sentinel": False,
            "multi_county_validation": False,
            "outcome_response": False,
            "causal_damage": False,
            "SCC": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "compressed_mib": result["plan"]["compressed_mib"], "remote_objects": len(records)}, sort_keys=True))


if __name__ == "__main__":
    main()
