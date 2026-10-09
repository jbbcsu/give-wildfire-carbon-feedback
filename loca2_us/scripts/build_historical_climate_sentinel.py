#!/usr/bin/env python3
"""Build and compare an outcome-blind LOCA2 county climate sentinel."""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import s3fs
import xarray as xr


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURE_MODULE_PATH = PROJECT_ROOT / "us_county_validation/scripts/build_county_nclimgrid_feature_smoke.py"
FEATURE_SPEC = importlib.util.spec_from_file_location("nclimgrid_feature_basis", FEATURE_MODULE_PATH)
require_loader = FEATURE_SPEC is not None and FEATURE_SPEC.loader is not None
if not require_loader:
    raise ImportError(f"cannot load feature basis from {FEATURE_MODULE_PATH}")
FEATURE_MODULE = importlib.util.module_from_spec(FEATURE_SPEC)
FEATURE_SPEC.loader.exec_module(FEATURE_MODULE)
build_cell_basis = FEATURE_MODULE.build_cell_basis


FEATURES = [
    "precip_mm", "tmean_c", "tmin_mean_c", "tmax_mean_c", "wet_days_n",
    "cdd_max_days", "rx1day_mm", "rx5day_mm", "stage1_precip_mm",
    "stage2_precip_mm", "stage3_precip_mm", "stage1_precip_share",
    "stage2_precip_share", "stage3_precip_share",
    "precipitation_concentration_hhi", "precipitation_timing_centroid",
]
QUANTILES = [0.1, 0.25, 0.5, 0.75, 0.9]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compare_distributions(model: pd.DataFrame, observed: pd.DataFrame) -> dict[str, dict[str, object]]:
    require(model.harvest_year.tolist() == observed.harvest_year.tolist(), "comparison years differ")
    result = {}
    for feature in FEATURES:
        modeled = model[feature].to_numpy(dtype=float)
        reference = observed[feature].to_numpy(dtype=float)
        require(np.isfinite(modeled).all() and np.isfinite(reference).all(), f"nonfinite comparison: {feature}")
        model_quantiles = np.quantile(modeled, QUANTILES)
        observed_quantiles = np.quantile(reference, QUANTILES)
        observed_sd = float(np.std(reference, ddof=1))
        result[feature] = {
            "model_mean": float(np.mean(modeled)),
            "observed_mean": float(np.mean(reference)),
            "climatology_bias_model_minus_observed": float(np.mean(modeled) - np.mean(reference)),
            "model_standard_deviation": float(np.std(modeled, ddof=1)),
            "observed_standard_deviation": observed_sd,
            "standard_deviation_ratio": float(np.std(modeled, ddof=1) / observed_sd) if observed_sd > 0 else None,
            "quantile_probabilities": QUANTILES,
            "model_quantiles": model_quantiles.tolist(),
            "observed_quantiles": observed_quantiles.tolist(),
            "quantile_differences_model_minus_observed": (model_quantiles - observed_quantiles).tolist(),
            "quantile_rmse": float(np.sqrt(np.mean(np.square(model_quantiles - observed_quantiles)))),
        }
    return result


def build_basis_frame(
    rain: np.ndarray,
    tmin: np.ndarray,
    tmax: np.ndarray,
    cell_positions: np.ndarray,
    wet_day_threshold_mm: float,
) -> pd.DataFrame:
    """Construct nonlinear cell features while retaining global cell order."""
    cell_positions = np.asarray(cell_positions, dtype=int)
    require(rain.ndim == 2 and rain.shape == tmin.shape == tmax.shape, "cell arrays differ")
    require(rain.shape[1] == len(cell_positions), "cell positions differ from arrays")
    require(len(np.unique(cell_positions)) == len(cell_positions), "duplicate cell positions")
    rows = [
        build_cell_basis(
            rain[:, cell],
            (tmin[:, cell] + tmax[:, cell]) / 2,
            tmin[:, cell],
            tmax[:, cell],
            wet_day_threshold_mm,
        )
        for cell in range(len(cell_positions))
    ]
    return pd.DataFrame(rows, index=cell_positions)


def aggregate_basis_frames(frames: list[pd.DataFrame], weight_values: np.ndarray) -> dict[str, float]:
    """Reassemble partitions, then use the original full-vector dot order."""
    require(bool(frames), "no cell-basis partitions")
    weights = np.asarray(weight_values, dtype=float)
    cell_basis = pd.concat(frames).sort_index()
    require(cell_basis.index.tolist() == list(range(len(weights))), "cell partitions overlap or omit cells")
    return {column: float(np.dot(cell_basis[column].to_numpy(dtype=float), weights)) for column in cell_basis.columns}


def aggregate_all_cells(
    rain: np.ndarray,
    tmin: np.ndarray,
    tmax: np.ndarray,
    weight_values: np.ndarray,
    wet_day_threshold_mm: float,
) -> dict[str, float]:
    positions = np.arange(rain.shape[1], dtype=int)
    return aggregate_basis_frames(
        [build_basis_frame(rain, tmin, tmax, positions, wet_day_threshold_mm)],
        weight_values,
    )


def aggregate_spatial_partitions(
    rain: np.ndarray,
    tmin: np.ndarray,
    tmax: np.ndarray,
    weight_values: np.ndarray,
    partitions: list[np.ndarray],
    wet_day_threshold_mm: float,
) -> dict[str, float]:
    """Synthetic/reference entry point for exact partition equivalence."""
    frames = [
        build_basis_frame(rain[:, positions], tmin[:, positions], tmax[:, positions], positions, wet_day_threshold_mm)
        for positions in partitions
    ]
    return aggregate_basis_frames(frames, weight_values)


def spatial_cell_partitions(weights: pd.DataFrame, chunk_shape: tuple[int, ...]) -> list[np.ndarray]:
    require(len(chunk_shape) == 4, "unexpected source chunk rank")
    groups: dict[tuple[int, int], list[int]] = {}
    for position, row in enumerate(weights.itertuples(index=False)):
        key = (int(row.grid_lat_index) // chunk_shape[2], int(row.grid_lon_index) // chunk_shape[3])
        groups.setdefault(key, []).append(position)
    partitions = [np.asarray(groups[key], dtype=int) for key in sorted(groups)]
    require(sorted(np.concatenate(partitions).tolist()) == list(range(len(weights))), "spatial partitions differ from weights")
    return partitions


def read_observed(root: Path, config: dict) -> pd.DataFrame:
    columns = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice", "season_start", "season_end", *FEATURES]
    rows = []
    for year in range(config["sample"]["year_min"], config["sample"]["year_max"] + 1):
        path = root / config["inputs"]["nclimgrid_feature_pattern"].format(year=year)
        frame = pd.read_parquet(path, columns=columns)
        selected = frame.loc[
            frame.county_geoid.astype(str).str.zfill(5).eq(config["sample"]["county_geoid"])
            & frame.outcome_crop.eq(config["sample"]["crop"])
        ].copy()
        require(not selected.empty, f"nClimGrid sentinel missing in {year}")
        for feature in ["season_start", "season_end", *FEATURES]:
            require(selected[feature].nunique(dropna=False) == 1, f"nClimGrid practices differ on {feature}/{year}")
        rows.append(selected.iloc[0][["harvest_year", "season_start", "season_end", *FEATURES]])
    result = pd.DataFrame(rows).sort_values("harvest_year").reset_index(drop=True)
    result["season_start"] = pd.to_datetime(result.season_start)
    result["season_end"] = pd.to_datetime(result.season_end)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    root = Path(__file__).resolve().parents[2]
    output = root / config["outputs"]["features"]
    receipt_path = root / config["outputs"]["receipt"]
    require(not output.exists() and not receipt_path.exists(), "fresh outputs required")
    require(config["sample"]["outcome_columns_read"] is False, "sentinel must exclude outcomes")
    require(config["sample"]["paired_year_scoring"] is False, "free-running climate cannot use paired-year scores")

    weights_path = root / config["inputs"]["weights"]
    weights_receipt_path = root / config["inputs"]["weights_receipt"]
    weights_receipt = json.loads(weights_receipt_path.read_text())
    require(weights_receipt["status"] == "pass", "county weights receipt failed")
    require(sha256(weights_path) == weights_receipt["output"]["sha256"], "county weights changed")
    weights = pd.read_parquet(weights_path).sort_values(["grid_lat_index", "grid_lon_index"]).reset_index(drop=True)
    require(np.isclose(weights.spatial_weight.sum(), 1.0, rtol=0, atol=1e-12), "county weights do not sum to one")

    observed = read_observed(root, config)
    expected_start = [pd.Timestamp(f"{year}-{config['sample']['season_start_month_day']}") for year in observed.harvest_year]
    expected_end = [pd.Timestamp(f"{year}-{config['sample']['season_end_month_day']}") for year in observed.harvest_year]
    require(observed.season_start.tolist() == expected_start and observed.season_end.tolist() == expected_end, "observed calendars differ from frozen dates")

    fs = s3fs.S3FileSystem(anon=True, client_kwargs={"endpoint_url": config["source"]["endpoint_url"]})
    store = config["source"]["store"]
    ds = xr.open_zarr(fs.get_mapper(store), consolidated=True, chunks=None)
    require(ds.pr.attrs.get("LOCA2_version") == config["source"]["precipitation_version"], "LOCA2 precipitation version differs")
    mask = (
        (ds.source_id.values == config["source"]["source_id"])
        & (ds.experiment_id.values == config["source"]["experiment_id"])
        & (ds.variant_label.values == config["source"]["variant_label"])
    )
    matches = np.flatnonzero(mask)
    require(len(matches) == 1, "historical ensemble identity is not unique")
    ensemble_index = int(matches[0])
    lat_indices = weights.grid_lat_index.to_numpy(dtype=int)
    lon_indices = weights.grid_lon_index.to_numpy(dtype=int)
    weight_values = weights.spatial_weight.to_numpy(dtype=float)

    chunk_shape = ds.pr.encoding["chunks"]
    all_time_indices = []
    for row in observed.itertuples(index=False):
        indices = np.flatnonzero((ds.time.values >= np.datetime64(row.season_start)) & (ds.time.values <= np.datetime64(row.season_end)))
        require(len(indices) == (row.season_end - row.season_start).days + 1, "LOCA2 season has missing days")
        all_time_indices.extend(indices.tolist())
    time_chunks = sorted({int(index // chunk_shape[1]) for index in all_time_indices})
    spatial_chunks = sorted({(int(y // chunk_shape[2]), int(x // chunk_shape[3])) for y, x in zip(lat_indices, lon_indices, strict=True)})
    accumulator = config["resources"].get("spatial_accumulator", "all_cells_v1")
    require(accumulator in {"all_cells_v1", "one_source_spatial_chunk_at_a_time_v1"}, "unknown spatial accumulator")
    cell_partitions = spatial_cell_partitions(weights, tuple(int(value) for value in chunk_shape))
    if accumulator == "all_cells_v1":
        cell_partitions = [np.arange(len(weights), dtype=int)]
    chunk_records = []
    for variable in config["source"]["variables"]:
        require(tuple(ds[variable].encoding["chunks"]) == tuple(chunk_shape), "variable chunks differ")
        for time_chunk in time_chunks:
            for lat_chunk, lon_chunk in spatial_chunks:
                key = f"{variable}/{ensemble_index}.{time_chunk}.{lat_chunk}.{lon_chunk}"
                chunk_records.append({"variable": variable, "key": key, "compressed_bytes": int(fs.info(f"{store}/{key}")["size"])})
    remote_bytes = sum(item["compressed_bytes"] for item in chunk_records)
    require(remote_bytes <= int(config["resources"]["maximum_remote_chunk_mib"]) * 1024**2, "remote chunk plan exceeds cap")

    modeled_rows = []
    for row in observed.itertuples(index=False):
        dates = slice(str(row.season_start.date()), str(row.season_end.date()))
        basis_frames = []
        for positions in cell_partitions:
            partition_lat = xr.DataArray(lat_indices[positions], dims="cell")
            partition_lon = xr.DataArray(lon_indices[positions], dims="cell")
            indexers = {"ensemble": ensemble_index, "lat": partition_lat, "lon": partition_lon}
            # Exactly one source spatial chunk is decoded at a time under the
            # low-memory strategy. Only the small selected cell arrays survive
            # long enough to construct that partition's nonlinear basis.
            rain = ds.pr.isel(**indexers).sel(time=dates).values.astype(float)
            tmin = ds.tasmin.isel(**indexers).sel(time=dates).values.astype(float)
            tmax = ds.tasmax.isel(**indexers).sel(time=dates).values.astype(float)
            require(rain.shape == (170, len(positions)), "unexpected LOCA2 season shape")
            require(np.isfinite(rain).all() and np.isfinite(tmin).all() and np.isfinite(tmax).all(), "nonfinite LOCA2 values")
            require((rain >= 0).all() and (tmax >= tmin).all(), "LOCA2 physical checks failed")
            basis_frames.append(build_basis_frame(
                rain,
                tmin,
                tmax,
                positions,
                float(config["sample"]["wet_day_threshold_mm"]),
            ))
            del rain, tmin, tmax
            gc.collect()
        aggregated = aggregate_basis_frames(basis_frames, weight_values)
        modeled_rows.append({"harvest_year": int(row.harvest_year), **aggregated})
    modeled = pd.DataFrame(modeled_rows).sort_values("harvest_year").reset_index(drop=True)
    comparisons = compare_distributions(modeled, observed)
    output.parent.mkdir(parents=True, exist_ok=True)
    modeled.to_parquet(output, index=False)
    receipt = {
        "schema": "loca2_us_historical_climate_sentinel/v1",
        "status": "pass",
        "role": "free_running_climate_distribution_validation_not_paired_year_prediction",
        "config": {"path": str(args.config), "sha256": sha256(args.config)},
        "source": {
            "store": store,
            "source_id": config["source"]["source_id"],
            "experiment_id": config["source"]["experiment_id"],
            "variant_label": config["source"]["variant_label"],
            "ensemble_index": ensemble_index,
            "precipitation_version": ds.pr.attrs["LOCA2_version"],
            "remote_chunks": chunk_records,
            "remote_chunk_mib_upper_bound": remote_bytes / 1024**2,
            "spatial_accumulator": accumulator,
            "spatial_accumulator_partitions": len(cell_partitions),
        },
        "support": {
            "county_geoid": config["sample"]["county_geoid"],
            "crop": config["sample"]["crop"],
            "years": modeled.harvest_year.tolist(),
            "year_count": int(len(modeled)),
            "grid_cells": int(len(weights)),
            "season_days_each": 170,
            "outcome_columns_read": False,
            "paired_year_scoring": False,
        },
        "comparisons": comparisons,
        "inputs": {
            "weights": {"path": config["inputs"]["weights"], "sha256": sha256(weights_path)},
            "weights_receipt": {"path": config["inputs"]["weights_receipt"], "sha256": sha256(weights_receipt_path)},
            "nclimgrid_columns_read": ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice", "season_start", "season_end", *FEATURES],
        },
        "output": {"path": str(output.relative_to(root)), "bytes": output.stat().st_size, "sha256": sha256(output)},
        "claim_gates": {
            "historical_climate_sentinel": True,
            "multi_model_validation": False,
            "outcome_response": False,
            "causal_damage": False,
            "SCC": False,
        },
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    headline = {feature: {key: comparisons[feature][key] for key in ("model_mean", "observed_mean", "climatology_bias_model_minus_observed", "quantile_rmse")} for feature in ("precip_mm", "cdd_max_days", "rx5day_mm", "tmean_c")}
    print(json.dumps({"status": "pass", "remote_chunk_mib": receipt["source"]["remote_chunk_mib_upper_bound"], "headline": headline}, indent=2))


if __name__ == "__main__":
    main()
