#!/usr/bin/env python3
"""Compare published water-stress maps with five-ESM future SPEI drying.

External validation only: this script does not estimate yield, damage, or SCC.
It streams four 5-arc-minute ASCII rasters into 0.5-degree summaries and reads
one validated SPEI cube at a time.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import sys

import h5py
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from summarize_isimip3b_late_drought_crop_windows import frozen_support, sources  # noqa: E402
from build_spei_tile_crop_features import spans  # noqa: E402
from spei_crop_window_metrics import window_metrics  # noqa: E402


RAW = ROOT / "data/raw/tuninetti_2026_zenodo_18937255"
ACQUISITION = ROOT / "data/interim/tuninetti_2026_crop_raster_acquisition_20260922/result.json"
PAIR_ROOT = ROOT / "data/interim/five_esm_late_drought_20260921"
PROTOCOL = ROOT / "TUNINETTI_2026_SPATIAL_VALIDATION_PROTOCOL_20260922.md"
ESMS = ("gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll")
SCENARIOS = ("ssp370", "ssp585")
YEARS = tuple(range(2092, 2100))
FILES = {
    ("mai", "noirr"): "FINAL_percentage_yield_variation_dueto_climate_RF_56_maize.txt",
    ("mai", "firr"): "FINAL_percentage_yield_variation_dueto_climate_IR_56_maize.txt",
    ("soy", "noirr"): "FINAL_percentage_yield_variation_dueto_climate_RF_236_soybean.txt",
    ("soy", "firr"): "FINAL_percentage_yield_variation_dueto_climate_IR_236_soybean.txt",
}


def digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_ascii_half_degree(path: Path) -> tuple[np.ndarray, dict]:
    """Stream a 4320x2160 ESRI ASCII grid and mean each 6x6 block."""
    header = {}
    output = np.full((360, 720), np.nan, dtype=np.float64)
    valid_source = 0
    minimum = math.inf
    maximum = -math.inf
    with path.open("r", encoding="utf-8") as stream:
        for _ in range(6):
            key, value = stream.readline().strip().split()
            header[key.lower()] = float(value)
        require(
            header == {
                "ncols": 4320.0,
                "nrows": 2160.0,
                "xllcorner": -180.0,
                "yllcorner": -90.0,
                "cellsize": 0.0833333,
                "nodata_value": -9999.0,
            },
            f"ASCII header changed: {path.name}",
        )
        rows = []
        for source_row in range(2160):
            values = np.fromstring(stream.readline(), sep=" ", dtype=np.float64)
            require(values.size == 4320, f"ASCII row width changed: {path.name} row {source_row}")
            values[values == -9999] = np.nan
            finite = np.isfinite(values)
            if finite.any():
                valid_source += int(finite.sum())
                minimum = min(minimum, float(values[finite].min()))
                maximum = max(maximum, float(values[finite].max()))
            rows.append(values)
            if len(rows) == 6:
                block = np.stack(rows).reshape(6, 720, 6)
                count = np.isfinite(block).sum(axis=(0, 2))
                total = np.nansum(block, axis=(0, 2))
                output[source_row // 6] = np.divide(total, count, out=np.full(720, np.nan), where=count > 0)
                rows.clear()
        require(not rows and stream.readline() == "", f"ASCII row count changed: {path.name}")
    finite_output = np.isfinite(output)
    require(valid_source > 0 and finite_output.any(), f"no finite published values: {path.name}")
    require(minimum >= -100.000001 and maximum <= 0.000001, f"published loss range changed: {path.name}")
    audit = {
        "source_valid_cells": valid_source,
        "half_degree_valid_cells": int(finite_output.sum()),
        "minimum_percent_change": minimum,
        "maximum_percent_change": maximum,
    }
    return output, audit


def validated_cube(esm: str, scenario: str) -> tuple[Path, dict]:
    directory = PAIR_ROOT / f"{esm}_{scenario}"
    result_path = directory / "result.json"
    validation_path = directory / "validation.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    require(result["esm"] == esm and result["scenario"] == scenario, "pair identity changed")
    require(validation["status"] == "passed", "pair validation no longer passed")
    require(validation["pair_result_sha256"] == digest(result_path), "pair result binding changed")
    path = ROOT / result["output"]["path"]
    require(result["output"]["sha256"] == validation["output_sha256"] == digest(path), "pair cube hash changed")
    return path, {"result_sha256": digest(result_path), "validation_sha256": digest(validation_path), "cube_sha256": digest(path)}


def load_cube(path: Path) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex, np.ndarray, np.ndarray]:
    with h5py.File(path, "r") as handle:
        require(tuple(handle["scale"][:]) == (1, 3, 6), "SPEI scale axis changed")
        months = pd.DatetimeIndex(handle["month"][:].astype("datetime64[ns]"))
        values = np.asarray(handle["spei"][1], dtype=np.float64)
        clips = np.asarray(handle["cdf_clip_code"][1], dtype=np.int8)
        native_rows = np.asarray(handle["native_lat_index"][:], dtype=np.int16)
        native_cols = np.asarray(handle["native_lon_index"][:], dtype=np.int16)
    require(values.shape == clips.shape == (120, 31208), "SPEI3 cube shape changed")
    return values, clips, months, native_rows, native_cols


def crop_season_average(values: np.ndarray, clips: np.ndarray, months: pd.DatetimeIndex, frame: pd.DataFrame) -> np.ndarray:
    lookup = {(month.year, month.month): index for index, month in enumerate(months)}
    answer = np.full(len(frame), np.nan, dtype=np.float64)
    for position, row in enumerate(frame.itertuples(index=False)):
        annual = []
        for year in YEARS:
            season = spans(year, row.planting_day, row.maturity_day)["season"]
            metric = window_metrics(values[:, row.cell_id], clips[:, row.cell_id], lookup, *season)
            if metric["status"] != "complete":
                annual = []
                break
            annual.append(metric["spei_mean"])
        if annual:
            answer[position] = math.fsum(annual) / len(annual)
    return answer


def weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    total = float(weights.sum())
    if total <= 0:
        return math.nan
    mx = float(np.dot(weights, x) / total)
    my = float(np.dot(weights, y) / total)
    dx, dy = x - mx, y - my
    denominator = math.sqrt(float(np.dot(weights, dx * dx) * np.dot(weights, dy * dy)))
    return float(np.dot(weights, dx * dy) / denominator) if denominator > 0 else math.nan


def rank_scores(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).rank(method="average").to_numpy(dtype=np.float64)


def stratified_bootstrap(ranked_x: np.ndarray, ranked_y: np.ndarray, weights: np.ndarray,
                         latitudes: np.ndarray, seed: int, draws: int = 2000) -> list[float]:
    bands = np.digitize(latitudes, (-30.0, 0.0, 30.0))
    groups = [np.flatnonzero(bands == band) for band in range(4)]
    require(all(len(group) > 1 for group in groups), "latitude bootstrap band has insufficient support")
    rng = np.random.default_rng(seed)
    estimates = np.empty(draws, dtype=np.float64)
    for draw in range(draws):
        selected = np.concatenate([rng.choice(group, size=len(group), replace=True) for group in groups])
        estimates[draw] = weighted_corr(ranked_x[selected], ranked_y[selected], weights[selected])
    finite = estimates[np.isfinite(estimates)]
    require(len(finite) == draws, "nonfinite bootstrap correlation")
    return [float(v) for v in np.quantile(finite, (0.025, 0.5, 0.975))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/interim/tuninetti_2026_spatial_validation_20260922")
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    require(not output_dir.exists(), "fresh output directory required")
    require(PROTOCOL.is_file(), "frozen protocol missing")

    acquisition = json.loads(ACQUISITION.read_text(encoding="utf-8"))
    require(acquisition["status"] == "passed" and acquisition["total_bytes"] == 333400387, "raster acquisition not validated")
    receipts = {item["file"]: item for item in acquisition["files"]}
    rasters, raster_audits = {}, {}
    for key, name in FILES.items():
        path = RAW / name
        require(path.stat().st_size == receipts[name]["bytes"] and digest(path) == receipts[name]["sha256"], "raster binding changed")
        rasters[key], raster_audits[name] = read_ascii_half_degree(path)

    support = frozen_support()
    calendars, weights, calendar_bindings = sources()
    weight_lookup = weights.set_index(["crop", "lat", "lon_360", "irrigation"]).to_dict("index")
    first_cube_path, first_binding = validated_cube(ESMS[0], "ssp126")
    _, _, _, native_rows, native_cols = load_cube(first_cube_path)

    rows = []
    for item in support.itertuples(index=False):
        for regime in ("noirr", "firr"):
            if not bool(getattr(item, regime + "_calendar_valid")):
                continue
            weight = weight_lookup[(item.crop, item.lat, item.lon_360, regime)]
            area = float(weight["rainfed_area_ha"] if regime == "noirr" else weight["irrigated_area_ha"])
            if area <= 0:
                continue
            calendar = calendars[(item.crop, regime)]
            i, j = calendar["lat"][item.lat], calendar["lon"][item.lon_360]
            grid_row, grid_col = int(native_rows[item.cell_id]), int(native_cols[item.cell_id])
            published = float(rasters[(item.crop, regime)][grid_row, grid_col])
            rows.append(
                {
                    "crop": item.crop,
                    "irrigation": regime,
                    "cell_id": int(item.cell_id),
                    "lat": float(item.lat),
                    "lon_360": float(item.lon_360),
                    "native_lat_index": grid_row,
                    "native_lon_index": grid_col,
                    "area_ha": area,
                    "planting_day": int(calendar["plant"][i, j]),
                    "maturity_day": int(calendar["maturity"][i, j]),
                    "published_yield_change_pct": published if math.isfinite(published) else math.nan,
                }
            )
    frame = pd.DataFrame(rows).sort_values(["crop", "irrigation", "cell_id"]).reset_index(drop=True)
    require(not frame.duplicated(["crop", "irrigation", "cell_id"]).any(), "analysis keys duplicated")
    del calendars, weights, rasters, support
    gc.collect()

    cube_bindings = {f"{ESMS[0]}_ssp126": first_binding}
    for esm_index, esm in enumerate(ESMS):
        base_path, base_binding = validated_cube(esm, "ssp126")
        cube_bindings[f"{esm}_ssp126"] = base_binding
        base_values, base_clips, base_months, check_rows, check_cols = load_cube(base_path)
        require(np.array_equal(check_rows, native_rows) and np.array_equal(check_cols, native_cols), "cube cell axes differ")
        base = crop_season_average(base_values, base_clips, base_months, frame)
        del base_values, base_clips
        for scenario in SCENARIOS:
            target_path, target_binding = validated_cube(esm, scenario)
            cube_bindings[f"{esm}_{scenario}"] = target_binding
            values, clips, months, check_rows, check_cols = load_cube(target_path)
            require(months.equals(base_months) and np.array_equal(check_rows, native_rows) and np.array_equal(check_cols, native_cols), "cube axes differ")
            target = crop_season_average(values, clips, months, frame)
            frame[f"spei3_{scenario}_minus_ssp126_{esm}"] = target - base
            del values, clips, target
            gc.collect()
        del base
        gc.collect()
        print(json.dumps({"esm": esm, "status": "crop-season contrasts completed"}), flush=True)

    summaries = []
    for crop in ("mai", "soy"):
        for regime in ("noirr", "firr"):
            group = frame[(frame.crop == crop) & (frame.irrigation == regime)].copy()
            for scenario_index, scenario in enumerate(SCENARIOS):
                columns = [f"spei3_{scenario}_minus_ssp126_{esm}" for esm in ESMS]
                contrasts = group[columns].to_numpy(dtype=np.float64)
                group[f"spei3_{scenario}_minus_ssp126_mean"] = np.nanmean(contrasts, axis=1)
                group[f"spei3_{scenario}_finite_models"] = np.isfinite(contrasts).sum(axis=1)
                group[f"spei3_{scenario}_negative_models"] = (contrasts < 0).sum(axis=1)
                frame.loc[group.index, f"spei3_{scenario}_minus_ssp126_mean"] = group[f"spei3_{scenario}_minus_ssp126_mean"]
                frame.loc[group.index, f"spei3_{scenario}_finite_models"] = group[f"spei3_{scenario}_finite_models"]
                frame.loc[group.index, f"spei3_{scenario}_negative_models"] = group[f"spei3_{scenario}_negative_models"]
                valid = (
                    np.isfinite(group.published_yield_change_pct)
                    & np.isfinite(group[f"spei3_{scenario}_minus_ssp126_mean"])
                    & (group[f"spei3_{scenario}_finite_models"] >= 4)
                    & (group.area_ha > 0)
                )
                analysis = group.loc[valid]
                require(len(analysis) >= 100, "external common support unexpectedly small")
                sensitivity = -analysis.published_yield_change_pct.to_numpy(dtype=np.float64)
                drying = -analysis[f"spei3_{scenario}_minus_ssp126_mean"].to_numpy(dtype=np.float64)
                area = analysis.area_ha.to_numpy(dtype=np.float64)
                rank_x, rank_y = rank_scores(sensitivity), rank_scores(drying)
                unweighted = weighted_corr(rank_x, rank_y, np.ones(len(analysis)))
                weighted = weighted_corr(rank_x, rank_y, area)
                interval = stratified_bootstrap(
                    rank_x, rank_y, area, analysis.lat.to_numpy(dtype=np.float64),
                    seed=20260922 + 1000 * scenario_index + 100 * (crop == "soy") + 10 * (regime == "firr"),
                )
                total_area = float(area.sum())
                summaries.append(
                    {
                        "crop": crop,
                        "irrigation": regime,
                        "contrast": f"{scenario}_minus_ssp126",
                        "common_cells": len(analysis),
                        "common_area_ha": total_area,
                        "area_weighted_mean_spei3_contrast": float(np.dot(area, -drying) / total_area),
                        "area_weighted_mean_published_yield_change_pct": float(np.dot(area, -sensitivity) / total_area),
                        "unweighted_spearman": unweighted,
                        "area_weighted_spearman": weighted,
                        "area_weighted_spearman_fixed_rank_stratified_bootstrap_95pct": interval,
                        "all_five_models_drying_cell_fraction": float((analysis[f"spei3_{scenario}_negative_models"] == 5).mean()),
                        "at_least_four_models_drying_cell_fraction": float((analysis[f"spei3_{scenario}_negative_models"] >= 4).mean()),
                        "published_sensitivity_pct_range": [float(sensitivity.min()), float(sensitivity.max())],
                        "projected_drying_severity_range_spei": [float(drying.min()), float(drying.max())],
                    }
                )

    output_dir.mkdir(parents=True)
    table_path = output_dir / "joined_cell_diagnostics.parquet"
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), table_path, compression="zstd")
    result = {
        "schema": "tuninetti_2026_future_drought_spatial_validation_v1",
        "status": "completed_pending_independent_validation",
        "role": "external_spatial_process_validation_not_yield_damage_or_scc",
        "protocol_sha256": digest(PROTOCOL),
        "acquisition_sha256": digest(ACQUISITION),
        "calendar_bindings": calendar_bindings,
        "cube_bindings": cube_bindings,
        "raster_audits": raster_audits,
        "summaries": summaries,
        "joined_table": {"path": str(table_path.relative_to(ROOT)), "bytes": table_path.stat().st_size, "sha256": digest(table_path), "rows": len(frame)},
        "gates": {"external_spatial_validation": False, "yield_response": False, "damage": False, "scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    result_path = output_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "summaries": len(summaries), "rows": len(frame)}))


if __name__ == "__main__":
    main()
