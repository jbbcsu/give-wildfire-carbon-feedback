#!/usr/bin/env python3
"""Bounded geographic validation and source-cluster uncertainty audit."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from validate_global_continuous_geographic_cluster_contract import validate as validate_contract


ROOT = Path(__file__).resolve().parents[1]
KEYS = ["crop", "lat", "lon_360", "harvest_year"]
MODELS = ["controls_only", "quantity", "quantity_distribution", "scpdsi_mean", "scpdsi_stages"]
CONTRAST_PAIRS = {
    "quantity_minus_controls_only": ("quantity", "controls_only"),
    "quantity_distribution_minus_quantity": ("quantity_distribution", "quantity"),
    "scpdsi_mean_minus_quantity": ("scpdsi_mean", "quantity"),
    "scpdsi_stages_minus_quantity": ("scpdsi_stages", "quantity"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def moments(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, int]:
    return (
        np.einsum("ni,nj->ij", x, x, optimize=False),
        np.einsum("ni,n->i", x, y, optimize=False),
        float(np.dot(y, y)),
        len(y),
    )


def add_moments(
    left: tuple[np.ndarray, np.ndarray, float, int] | None,
    right: tuple[np.ndarray, np.ndarray, float, int],
) -> tuple[np.ndarray, np.ndarray, float, int]:
    return right if left is None else tuple(a + b for a, b in zip(left, right))


def fit_beta(train: tuple[np.ndarray, np.ndarray, float, int]) -> tuple[np.ndarray, float]:
    gram, cross, _, count = train
    if count <= 0:
        raise ValueError("empty training support")
    scale = np.sqrt(np.diag(gram) / count)
    if np.any(~np.isfinite(scale)) or np.any(scale <= 0):
        raise ValueError("zero or nonfinite training scale")
    standardized = gram / np.outer(scale, scale)
    condition = float(np.linalg.cond(standardized))
    if not np.isfinite(condition) or condition > 1e10:
        raise ValueError("ill-conditioned Gram matrix")
    beta = np.linalg.solve(standardized, cross / scale) / scale
    return beta, condition


def fold_ids(lat: np.ndarray, lon_360: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    latitude_blocks = np.floor((lat + 90.0) / 10.0).astype(np.int64)
    longitude_blocks = np.floor(lon_360 / 10.0).astype(np.int64)
    folds = (37 * latitude_blocks + 17 * longitude_blocks + 20260907) % 5
    return latitude_blocks, longitude_blocks, folds.astype(np.int8)


def read_band_period(
    path: Path, columns: list[str], lower: int, year_min: int, year_max: int
) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=8192, columns=columns, use_threads=False):
        frame = batch.to_pandas()
        mask = (
            frame["lat"].ge(lower)
            & frame["lat"].lt(lower + 10)
            & frame["harvest_year"].between(year_min, year_max)
            & frame["yield_t_ha"].gt(0)
        )
        if mask.any():
            pieces.append(frame.loc[mask].copy())
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(columns=columns)


def prepare_differences(
    paths: dict[str, Path], direct: list[str], heat: list[str], drought: list[str],
    lower: int, year_min: int, year_max: int,
) -> dict[str, object] | None:
    tables: dict[str, pd.DataFrame] = {}
    for family, columns in (("direct", direct), ("heat", heat), ("scpdsi", drought)):
        tables[family] = read_band_period(
            paths[family], KEYS + ["yield_t_ha"] + columns, lower, year_min, year_max
        )
        if tables[family].duplicated(KEYS).any():
            raise ValueError("duplicate candidate keys")
    frame = tables["direct"].merge(
        tables["heat"], on=KEYS, validate="one_to_one", suffixes=("", "_heat")
    )
    frame = frame.merge(
        tables["scpdsi"], on=KEYS, validate="one_to_one", suffixes=("", "_scpdsi")
    )
    del tables
    if frame.empty:
        return None
    for column in ("yield_t_ha_heat", "yield_t_ha_scpdsi"):
        if not np.allclose(frame["yield_t_ha"], frame[column], equal_nan=True):
            raise ValueError("outcomes differ across families")
    features = direct + heat + drought
    frame = frame.loc[
        frame["yield_t_ha"].notna() & frame["yield_t_ha"].gt(0)
    ].sort_values(KEYS)
    if frame.empty:
        return None
    if not np.isfinite(frame[features].to_numpy()).all():
        raise ValueError("nonfinite features on observed support")
    groups = frame.groupby(["crop", "lat", "lon_360"], observed=True, sort=False)
    consecutive = groups["harvest_year"].diff().eq(1).to_numpy()
    differences = groups[features].diff()
    log_yield = np.log(frame["yield_t_ha"])
    dy = log_yield.groupby(
        [frame["crop"], frame["lat"], frame["lon_360"]], observed=True, sort=False
    ).diff().to_numpy()
    selected = consecutive & np.isfinite(dy)
    if not selected.any():
        return None
    years = frame["harvest_year"].to_numpy()[selected]
    lat = frame["lat"].to_numpy()[selected]
    lon = frame["lon_360"].to_numpy()[selected]
    latitude_blocks, longitude_blocks, folds = fold_ids(lat, lon)
    feature_differences = {
        column: differences[column].to_numpy()[selected] for column in features
    }
    return {
        "crop_codes": sorted(set(frame["crop"].astype(str))),
        "years": years,
        "lat": lat,
        "lon": lon,
        "latitude_blocks": latitude_blocks,
        "longitude_blocks": longitude_blocks,
        "folds": folds,
        "dy": dy[selected],
        "differences": feature_differences,
    }


def design(data: dict[str, object], columns: list[str]) -> np.ndarray:
    years = np.asarray(data["years"])
    differences = data["differences"]
    year = (years - 2000.0) / 10.0
    return np.column_stack(
        [np.ones(len(year)), year, year**2]
        + [np.asarray(differences[column]) for column in columns]
    )


def resolve_inputs(config: dict[str, object], crop: str) -> tuple[dict[str, Path], dict[str, dict[str, str]]]:
    paths: dict[str, Path] = {}
    hashes: dict[str, dict[str, str]] = {}
    for item in config["inputs"]:
        if item["crop"] != crop:
            continue
        receipt_path = ROOT / item["receipt_path"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        data_path = ROOT / receipt["output"]["path"]
        actual = sha256(data_path)
        if actual != receipt["output"]["sha256"]:
            raise ValueError("assembly data hash mismatch")
        family = item["family"]
        paths[family] = data_path
        hashes[family] = {
            "receipt_sha256": sha256(receipt_path),
            "data_sha256": actual,
        }
    if set(paths) != {"direct", "heat", "scpdsi"}:
        raise ValueError("incomplete input family matrix")
    return paths, hashes


def bootstrap_contrasts(
    cluster_stats: dict[tuple[int, int, int], dict[str, tuple[float, int]]],
    replicates: int = 5000, seed: int = 20260907,
) -> dict[str, dict[str, float]]:
    by_fold: dict[int, list[dict[str, tuple[float, int]]]] = {fold: [] for fold in range(5)}
    for (fold, _, _), stats in sorted(cluster_stats.items()):
        by_fold[fold].append(stats)
    if any(len(values) < 2 for values in by_fold.values()):
        raise ValueError("insufficient source blocks per fold")
    rng = np.random.Generator(np.random.PCG64(seed))
    draws = {name: np.empty(replicates, dtype=np.float64) for name in CONTRAST_PAIRS}
    for replicate in range(replicates):
        sums = {model: [0.0, 0] for model in MODELS}
        for fold in range(5):
            clusters = by_fold[fold]
            for index in rng.integers(0, len(clusters), size=len(clusters)):
                for model in MODELS:
                    sse, count = clusters[int(index)][model]
                    sums[model][0] += sse
                    sums[model][1] += count
        rmse = {
            model: math.sqrt(sums[model][0] / sums[model][1]) for model in MODELS
        }
        for name, (left, right) in CONTRAST_PAIRS.items():
            draws[name][replicate] = rmse[left] - rmse[right]
    return {
        name: {
            "p025": float(np.quantile(values, 0.025)),
            "median": float(np.quantile(values, 0.5)),
            "p975": float(np.quantile(values, 0.975)),
        }
        for name, values in draws.items()
    }


def audit_crop(
    crop: str, code: str, threshold: int, config: dict[str, object], parent: dict[str, object]
) -> dict[str, object]:
    paths, input_hashes = resolve_inputs(config, crop)
    direct = [
        "log1p_precip_mm", "stage1_precip_share", "stage2_precip_share",
        "cdd_max_days", "rx5day_mm", "precipitation_concentration_hhi",
    ]
    heat = [f"stage{i}_tmean_c" for i in (1, 2, 3)] + [
        f"stage{i}_tmax_{threshold}c_degree_days" for i in (1, 2, 3)
    ]
    drought = ["season_scpdsi_mean"] + [f"stage{i}_scpdsi_mean" for i in (1, 2, 3)]
    specs = {
        "controls_only": heat,
        "quantity": heat + direct[:1],
        "quantity_distribution": heat + direct,
        "scpdsi_mean": heat + drought[:1],
        "scpdsi_stages": heat + drought[1:],
    }
    train_totals: dict[tuple[int, str], tuple[np.ndarray, np.ndarray, float, int] | None] = {
        (fold, model): None for fold in range(5) for model in MODELS
    }
    training_cells: set[tuple[float, float]] = set()
    unique_training_pairs = 0
    training_blocks: set[tuple[int, int]] = set()
    for lower in range(-90, 90, 10):
        data = prepare_differences(paths, direct, heat, drought, lower, 1982, 2010)
        if data is None:
            continue
        if data["crop_codes"] != [code]:
            raise ValueError("wrong crop in training source")
        years = np.asarray(data["years"])
        if not np.all((years >= 1983) & (years <= 2010)):
            raise ValueError("training endpoint outside frozen range")
        cells = list(zip(np.asarray(data["lat"]), np.asarray(data["lon"])))
        training_cells.update(cells)
        unique_training_pairs += len(years)
        lat_blocks = np.asarray(data["latitude_blocks"])
        lon_blocks = np.asarray(data["longitude_blocks"])
        folds = np.asarray(data["folds"])
        training_blocks.update(zip(lat_blocks.tolist(), lon_blocks.tolist()))
        for model, columns in specs.items():
            x = design(data, columns)
            for held_out in range(5):
                mask = folds != held_out
                train_totals[held_out, model] = add_moments(
                    train_totals[held_out, model], moments(x[mask], np.asarray(data["dy"])[mask])
                )
        del data
        gc.collect()

    betas: dict[tuple[int, str], np.ndarray] = {}
    conditions: dict[tuple[int, str], float] = {}
    for key, total in train_totals.items():
        if total is None:
            raise ValueError("missing fold training moments")
        beta, condition = fit_beta(total)
        betas[key] = beta
        conditions[key] = condition

    fold_stats = {
        fold: {model: [0.0, 0] for model in MODELS} for fold in range(5)
    }
    cluster_stats: dict[tuple[int, int, int], dict[str, tuple[float, int]]] = {}
    unique_terminal_pairs = 0
    for lower in range(-90, 90, 10):
        data = prepare_differences(paths, direct, heat, drought, lower, 2011, 2016)
        if data is None:
            continue
        if data["crop_codes"] != [code]:
            raise ValueError("wrong crop in terminal source")
        years = np.asarray(data["years"])
        cells = list(zip(np.asarray(data["lat"]), np.asarray(data["lon"])))
        eligible = np.fromiter((cell in training_cells for cell in cells), dtype=bool, count=len(cells))
        eligible &= (years >= 2012) & (years <= 2016)
        if not eligible.any():
            continue
        unique_terminal_pairs += int(eligible.sum())
        folds = np.asarray(data["folds"])
        lat_blocks = np.asarray(data["latitude_blocks"])
        lon_blocks = np.asarray(data["longitude_blocks"])
        dy = np.asarray(data["dy"])
        designs = {model: design(data, columns) for model, columns in specs.items()}
        for held_out in range(5):
            fold_mask = eligible & (folds == held_out)
            if not fold_mask.any():
                continue
            blocks = sorted(set(zip(lat_blocks[fold_mask].tolist(), lon_blocks[fold_mask].tolist())))
            for model in MODELS:
                residual = dy[fold_mask] - np.einsum(
                    "ni,i->n", designs[model][fold_mask], betas[held_out, model], optimize=False
                )
                squared = residual**2
                fold_stats[held_out][model][0] += float(squared.sum())
                fold_stats[held_out][model][1] += len(squared)
                block_lat = lat_blocks[fold_mask]
                block_lon = lon_blocks[fold_mask]
                for lat_block, lon_block in blocks:
                    block_mask = (block_lat == lat_block) & (block_lon == lon_block)
                    key = (held_out, int(lat_block), int(lon_block))
                    if key not in cluster_stats:
                        cluster_stats[key] = {}
                    cluster_stats[key][model] = (
                        float(squared[block_mask].sum()), int(block_mask.sum())
                    )
        del data, designs
        gc.collect()

    for stats in cluster_stats.values():
        if set(stats) != set(MODELS):
            raise ValueError("incomplete model support within source block")
        counts = {value[1] for value in stats.values()}
        if len(counts) != 1:
            raise ValueError("model support differs within source block")
    blocks_per_fold = {
        fold: sum(key[0] == fold for key in cluster_stats) for fold in range(5)
    }
    if any(count < 2 for count in blocks_per_fold.values()) or len(cluster_stats) < 10:
        raise ValueError("insufficient held-out source-block support")

    fold_results: list[dict[str, object]] = []
    pooled = {model: [0.0, 0] for model in MODELS}
    for held_out in range(5):
        metrics: dict[str, dict[str, float | int]] = {}
        train_counts = {train_totals[held_out, model][3] for model in MODELS}
        test_counts = {fold_stats[held_out][model][1] for model in MODELS}
        if len(train_counts) != 1 or len(test_counts) != 1 or next(iter(test_counts)) <= 0:
            raise ValueError("fold model support differs or is empty")
        for model in MODELS:
            sse, count = fold_stats[held_out][model]
            pooled[model][0] += sse
            pooled[model][1] += count
            metrics[model] = {
                "rmse": math.sqrt(sse / count),
                "scaled_gram_condition": conditions[held_out, model],
            }
        fold_results.append({
            "fold": held_out,
            "train_pairs": next(iter(train_counts)),
            "test_pairs": next(iter(test_counts)),
            "held_out_source_blocks": blocks_per_fold[held_out],
            "metrics": metrics,
        })
    pooled_metrics = {
        model: {"test_pairs": pooled[model][1], "rmse": math.sqrt(pooled[model][0] / pooled[model][1])}
        for model in MODELS
    }
    parent_metrics = parent["crops"][crop]["metrics"]
    parent_train = {parent_metrics[model]["train_pairs"] for model in MODELS}
    parent_test = {parent_metrics[model]["test_pairs"] for model in MODELS}
    if parent_train != {unique_training_pairs} or parent_test != {unique_terminal_pairs}:
        raise ValueError("parent temporal support did not reproduce")

    intervals = bootstrap_contrasts(cluster_stats)
    contrasts = {}
    for name, (left, right) in CONTRAST_PAIRS.items():
        contrasts[name] = {
            "point_rmse_difference": pooled_metrics[left]["rmse"] - pooled_metrics[right]["rmse"],
            "cluster_bootstrap": intervals[name],
        }
    return {
        "input_hashes": input_hashes,
        "unique_training_pairs": unique_training_pairs,
        "unique_terminal_pairs": unique_terminal_pairs,
        "training_source_blocks": len(training_blocks),
        "held_out_source_blocks": len(cluster_stats),
        "held_out_source_blocks_by_fold": blocks_per_fold,
        "folds": fold_results,
        "pooled_metrics": pooled_metrics,
        "paired_rmse_contrasts": contrasts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.with_suffix(".partial").exists():
        raise ValueError("output or partial output exists")
    config_path = args.config.resolve()
    validate_contract(config_path, ROOT)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    parent_path = ROOT / config["parent_result_path"]
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    preregistration_path = ROOT / "data/provenance/global_continuous_geographic_cluster_preregistration_20260907.json"
    output = {
        "schema": "global_continuous_geographic_cluster_audit_v1",
        "role": config["role"],
        "status": "completed_exploratory_geographic_and_source_cluster_diagnostic",
        "config_sha256": sha256(config_path),
        "protocol_sha256": sha256(ROOT / config["protocol_path"]),
        "preregistration_sha256": sha256(preregistration_path),
        "parent_result_sha256": sha256(parent_path),
        "implementation_sha256": sha256(Path(__file__)),
        "coefficient_exported": False,
        "row_predictions_exported": False,
        "model_promotion_authorized": False,
        "causal_response_authorized": False,
        "damage_or_scc_authorized": False,
        "bootstrap": {
            "cluster": config["uncertainty"]["cluster"],
            "resampling": config["uncertainty"]["resampling"],
            "replicates": config["uncertainty"]["replicates"],
            "generator": config["uncertainty"]["generator"],
            "seed": config["uncertainty"]["seed"],
        },
        "crops": {},
    }
    for crop, code, threshold in (("maize", "mai", 29), ("soy", "soy", 30)):
        output["crops"][crop] = audit_crop(crop, code, threshold, config, parent)
        print(f"{crop} completed", flush=True)
    encoded = (json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    if len(encoded) > int(config["resources"]["result_bytes_maximum"]):
        raise ValueError("result exceeds frozen byte ceiling")
    temporary = args.out.with_suffix(".partial")
    temporary.write_bytes(encoded)
    temporary.replace(args.out)
    print(f"wrote {args.out} ({len(encoded)} bytes)")


if __name__ == "__main__":
    main()
