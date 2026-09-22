#!/usr/bin/env python3
"""Independent numerical validation of the Tuninetti spatial comparison."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/tuninetti_2026_zenodo_18937255"
ESMS = ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")
SCENARIOS = ("ssp370", "ssp585")
FILES = {
    ("mai", "noirr"): "FINAL_percentage_yield_variation_dueto_climate_RF_56_maize.txt",
    ("mai", "firr"): "FINAL_percentage_yield_variation_dueto_climate_IR_56_maize.txt",
    ("soy", "noirr"): "FINAL_percentage_yield_variation_dueto_climate_RF_236_soybean.txt",
    ("soy", "firr"): "FINAL_percentage_yield_variation_dueto_climate_IR_236_soybean.txt",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def weighted_corr(x: np.ndarray, y: np.ndarray, weight: np.ndarray) -> float:
    total = weight.sum()
    dx = x - np.dot(weight, x) / total
    dy = y - np.dot(weight, y) / total
    return float(np.dot(weight, dx * dy) / np.sqrt(np.dot(weight, dx * dx) * np.dot(weight, dy * dy)))


def midrank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    position = 0
    while position < len(values):
        end = position + 1
        while end < len(values) and values[order[end]] == values[order[position]]:
            end += 1
        ranks[order[position:end]] = (position + 1 + end) / 2
        position = end
    return ranks


def interval(rank_x: np.ndarray, rank_y: np.ndarray, weight: np.ndarray,
             latitude: np.ndarray, seed: int) -> list[float]:
    band = np.digitize(latitude, (-30.0, 0.0, 30.0))
    groups = [np.flatnonzero(band == value) for value in range(4)]
    rng = np.random.default_rng(seed)
    values = np.empty(2000)
    for draw in range(2000):
        selected = np.concatenate([rng.choice(group, len(group), replace=True) for group in groups])
        values[draw] = weighted_corr(rank_x[selected], rank_y[selected], weight[selected])
    return [float(value) for value in np.quantile(values, (0.025, 0.5, 0.975))]


def ascii_spots(path: Path, locations: list[tuple[int, int]]) -> dict[tuple[int, int], float]:
    targets = set(locations)
    pieces: dict[tuple[int, int], list[np.ndarray]] = {key: [] for key in targets}
    with path.open("r", encoding="utf-8") as stream:
        for _ in range(6):
            stream.readline()
        for source_row in range(2160):
            half_row = source_row // 6
            needed = [column for row, column in targets if row == half_row]
            line = stream.readline()
            if not needed:
                continue
            values = np.fromstring(line, sep=" ", dtype=np.float64)
            for column in needed:
                part = values[column * 6:(column + 1) * 6]
                pieces[(half_row, column)].append(part[part != -9999])
    answer = {}
    for key, arrays in pieces.items():
        finite = np.concatenate(arrays)
        answer[key] = float(finite.mean()) if finite.size else math.nan
    return answer


def close(actual: float, expected: float, tolerance: float = 2e-12) -> None:
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise ValueError(f"numeric validation failed: {actual} != {expected}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data/interim/tuninetti_2026_spatial_validation_20260922")
    args = parser.parse_args()
    directory = args.input_dir if args.input_dir.is_absolute() else ROOT / args.input_dir
    result_path = directory / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    table_path = ROOT / result["joined_table"]["path"]
    if digest(table_path) != result["joined_table"]["sha256"]:
        raise ValueError("joined-table hash changed")
    frame = pq.read_table(table_path).to_pandas()
    if len(frame) != result["joined_table"]["rows"] or frame.duplicated(["crop", "irrigation", "cell_id"]).any():
        raise ValueError("joined-table structure changed")

    numerical_checks = 0
    summary_lookup = {(item["crop"], item["irrigation"], item["contrast"]): item for item in result["summaries"]}
    for crop in ("mai", "soy"):
        for regime in ("noirr", "firr"):
            group = frame[(frame.crop == crop) & (frame.irrigation == regime)]
            for scenario_index, scenario in enumerate(SCENARIOS):
                columns = [f"spei3_{scenario}_minus_ssp126_{esm}" for esm in ESMS]
                matrix = group[columns].to_numpy(dtype=np.float64)
                mean = np.nanmean(matrix, axis=1)
                finite_models = np.isfinite(matrix).sum(axis=1)
                negative_models = (matrix < 0).sum(axis=1)
                np.testing.assert_allclose(mean, group[f"spei3_{scenario}_minus_ssp126_mean"], rtol=0, atol=1e-15)
                np.testing.assert_array_equal(finite_models, group[f"spei3_{scenario}_finite_models"])
                np.testing.assert_array_equal(negative_models, group[f"spei3_{scenario}_negative_models"])
                valid = np.isfinite(group.published_yield_change_pct) & np.isfinite(mean) & (finite_models >= 4) & (group.area_ha > 0)
                analysis = group.loc[valid]
                sensitivity = -analysis.published_yield_change_pct.to_numpy(dtype=np.float64)
                drying = -analysis[f"spei3_{scenario}_minus_ssp126_mean"].to_numpy(dtype=np.float64)
                weight = analysis.area_ha.to_numpy(dtype=np.float64)
                rank_x, rank_y = midrank(sensitivity), midrank(drying)
                item = summary_lookup[(crop, regime, f"{scenario}_minus_ssp126")]
                if item["common_cells"] != len(analysis):
                    raise ValueError("common-cell count changed")
                close(item["common_area_ha"], float(weight.sum()))
                close(item["area_weighted_mean_spei3_contrast"], float(np.dot(weight, -drying) / weight.sum()))
                close(item["area_weighted_mean_published_yield_change_pct"], float(np.dot(weight, -sensitivity) / weight.sum()))
                close(item["unweighted_spearman"], weighted_corr(rank_x, rank_y, np.ones(len(analysis))))
                close(item["area_weighted_spearman"], weighted_corr(rank_x, rank_y, weight))
                expected_interval = interval(
                    rank_x, rank_y, weight, analysis.lat.to_numpy(dtype=np.float64),
                    20260922 + 1000 * scenario_index + 100 * (crop == "soy") + 10 * (regime == "firr"),
                )
                for actual, expected in zip(item["area_weighted_spearman_fixed_rank_stratified_bootstrap_95pct"], expected_interval):
                    close(actual, expected)
                close(item["all_five_models_drying_cell_fraction"], float((negative_models[valid] == 5).mean()))
                close(item["at_least_four_models_drying_cell_fraction"], float((negative_models[valid] >= 4).mean()))
                numerical_checks += 15 + len(mean) * 3

    spot_checks = 0
    for key, name in FILES.items():
        subset = frame[(frame.crop == key[0]) & (frame.irrigation == key[1]) & np.isfinite(frame.published_yield_change_pct)]
        chosen = subset.iloc[[0, len(subset) // 2, len(subset) - 1]]
        locations = list(zip(chosen.native_lat_index.astype(int), chosen.native_lon_index.astype(int)))
        observed = ascii_spots(RAW / name, locations)
        for row in chosen.itertuples(index=False):
            close(observed[(int(row.native_lat_index), int(row.native_lon_index))], float(row.published_yield_change_pct), 2e-10)
            spot_checks += 1

    validation = {
        "schema": "tuninetti_2026_future_drought_spatial_validation_audit_v1",
        "status": "passed",
        "result_sha256": digest(result_path),
        "joined_table_sha256": digest(table_path),
        "numerical_checks": numerical_checks,
        "independent_raw_ascii_block_checks": spot_checks,
        "gates": {"external_spatial_validation": True, "yield_response": False, "damage": False, "scc": False},
    }
    output = directory / "validation.json"
    output.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(validation))


if __name__ == "__main__":
    main()
