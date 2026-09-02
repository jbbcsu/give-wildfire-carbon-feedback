#!/usr/bin/env python3
"""Audit the preregistered contiguous GFDL crop × calendar-regime expansion."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd

from compare_climate_feature_cells import SEASON_METRICS, paired_summary, timing_features
from reconcile_stage_season_features import validate_row_invariants


RAW_KEYS = ["harvest_year", "lat", "lon_360", "crop", "irrigation"]
CENTER_KEYS = ["center_year", "lat", "lon_360", "crop", "irrigation"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_group_years(frame: pd.DataFrame, keys: list[str], year: str, expected: list[int], label: str) -> None:
    require(not frame.duplicated(keys + [year]).any(), f"{label} has duplicate cell-years")
    counts = frame.groupby(keys, observed=True)[year].agg(lambda values: sorted(values.astype(int).tolist()))
    require(counts.map(lambda values: values == expected).all(), f"{label} does not have exact annual support in every cell")


def reconcile_raw(season: pd.DataFrame, stages: pd.DataFrame) -> dict[str, float]:
    validate_row_invariants(season, "season_days", "season")
    validate_row_invariants(stages, "stage_days", "stage")
    grouped = stages.groupby(RAW_KEYS, observed=True).agg(
        stage_days=("stage_days", "sum"), precip_mm=("precip_mm", "sum"),
        wet_days_n=("wet_days_n", "sum"), rx1day_mm=("rx1day_mm", "max"),
    ).reset_index()
    joined = season.merge(grouped, on=RAW_KEYS, suffixes=("_season", "_stages"), validate="one_to_one")
    require(len(joined) == len(season), "stage rows do not cover all season rows")
    differences = {
        "stage_days": float(np.abs(joined.stage_days - joined.season_days).max()),
        "precip_mm": float(np.abs(joined.precip_mm_stages - joined.precip_mm_season).max()),
        "wet_days_n": float(np.abs(joined.wet_days_n_stages - joined.wet_days_n_season).max()),
        "rx1day_mm": float(np.abs(joined.rx1day_mm_stages - joined.rx1day_mm_season).max()),
    }
    require(differences["stage_days"] == 0 and differences["wet_days_n"] == 0, "integer stage reconciliation failed")
    require(differences["precip_mm"] <= 1e-3 and differences["rx1day_mm"] <= 1e-6, "rainfall stage reconciliation failed")
    return differences


def physical_raw(frame: pd.DataFrame) -> None:
    numeric = frame[["season_days", *SEASON_METRICS]].to_numpy(dtype=float)
    require(np.isfinite(numeric).all(), "raw physical features are incomplete")
    require(((frame.precip_mm >= 0) & (frame.wet_days_n >= 0) & (frame.wet_days_n <= frame.season_days)).all(), "raw quantity/frequency bounds failed")
    require(((frame.cdd_max_days >= 0) & (frame.cdd_max_days <= frame.season_days)).all(), "raw dry-spell bounds failed")
    require(((frame.rx1day_mm >= 0) & (frame.rx1day_mm <= frame.rx5day_mm + 1e-9) & (frame.rx5day_mm <= frame.precip_mm + 1e-6)).all(), "raw extreme-rain ordering failed")


def centered_timing(season: pd.DataFrame, stages: pd.DataFrame, window: int) -> pd.DataFrame:
    rename = {"center_year": "harvest_year", f"precip_mm_{window}yr_mean": "precip_mm"}
    raw_season = season.rename(columns=rename)
    raw_stages = stages.rename(columns=rename)
    return timing_features(raw_season, raw_stages, 3).rename(columns={"harvest_year": "center_year"})


def centered_calendar_sensitivity(cells: dict[str, dict[str, pd.DataFrame]], crop: str, window: int) -> dict[str, object]:
    left = cells[f"{crop}_noirr"]
    right = cells[f"{crop}_firr"]
    keys = ["center_year", "lat", "lon_360", "crop"]
    left_season = left["center_season"].sort_values(keys).reset_index(drop=True)
    right_season = right["center_season"].sort_values(keys).reset_index(drop=True)
    require(left_season[keys].equals(right_season[keys]), f"{crop} calendar regimes lack exact paired centered support")
    metrics = {name: paired_summary(left_season[f"{name}_{window}yr_mean"], right_season[f"{name}_{window}yr_mean"]) for name in SEASON_METRICS}
    left_timing = centered_timing(left_season, left["center_stages"], window).sort_values(keys).reset_index(drop=True)
    right_timing = centered_timing(right_season, right["center_stages"], window).sort_values(keys).reset_index(drop=True)
    require(left_timing[keys].equals(right_timing[keys]), f"{crop} timing regimes lack exact paired support")
    for name in ["stage1_precip_share", "stage2_precip_share", "stage3_precip_share", "precipitation_timing_centroid", "precipitation_concentration_hhi"]:
        metrics[name] = paired_summary(left_timing[name], right_timing[name])
    return {"crop": crop, "interpretation": "firr_minus_noirr_calendar_sensitivity_not_irrigation_treatment", "rows": len(left_season), "metrics": metrics}


def audit(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == "isimip3b_rimex_contiguous_multicrop_regime_contract_v1", "contract schema changed")
    window = int(config["centered_window_years"])
    base = root / "data/interim/isimip3b_gfdl_ssp126_2031_2060_contiguous_multicrop"
    gmst_hashes: set[str] = set()
    internal: dict[str, dict[str, pd.DataFrame]] = {}
    results = []
    for cell in config["cells"]:
        cell_id = str(cell["id"])
        paths = {
            "season": base / cell_id / "season.parquet", "stages": base / cell_id / "stages.parquet",
            "center_season": base / cell_id / "centered_season_21yr.parquet",
            "center_stages": base / cell_id / "centered_stages_21yr.parquet",
            "center_gmst": base / cell_id / "centered_gmst_21yr.parquet",
            "center_audit": base / cell_id / "centered_audit_21yr.json",
        }
        require(all(path.is_file() for path in paths.values()), f"{cell_id} output set is incomplete")
        frames = {name: pd.read_parquet(path) for name, path in paths.items() if name != "center_audit"}
        expected_cells = int(cell["valid_calendar_cells"])
        require(len(frames["season"]) == expected_cells * 28 and len(frames["stages"]) == expected_cells * 28 * 3, f"{cell_id} raw row counts changed")
        require(len(frames["center_season"]) == expected_cells * 8 and len(frames["center_stages"]) == expected_cells * 8 * 3, f"{cell_id} centered row counts changed")
        require(len(frames["center_gmst"]) == 8, f"{cell_id} centered GMST count changed")
        for name in ("season", "stages"):
            require(set(frames[name].crop.unique()) == {cell["crop"]} and set(frames[name].irrigation.unique()) == {cell["irrigation"]}, f"{cell_id} identity changed")
        exact_group_years(frames["season"], ["lat", "lon_360", "crop", "irrigation"], "harvest_year", list(range(2032, 2060)), f"{cell_id} season")
        exact_group_years(frames["center_season"], ["lat", "lon_360", "crop", "irrigation"], "center_year", list(range(2042, 2050)), f"{cell_id} centered season")
        require(set(frames["stages"].stage_id.unique()) == {1, 2, 3} and set(frames["center_stages"].stage_id.unique()) == {1, 2, 3}, f"{cell_id} stage IDs changed")
        physical_raw(frames["season"])
        differences = reconcile_raw(frames["season"], frames["stages"])
        centered_receipt = json.loads(paths["center_audit"].read_text(encoding="utf-8"))
        require(centered_receipt.get("result") == "passed" and centered_receipt.get("center_years") == list(range(2042, 2050)), f"{cell_id} centered reconciliation failed")
        gmst_hashes.add(sha256(paths["center_gmst"]))
        internal[cell_id] = frames
        results.append({
            "id": cell_id, "valid_calendar_cells": expected_cells,
            "row_counts": {name: len(frame) for name, frame in frames.items()},
            "raw_reconciliation_max_absolute_differences": differences,
            "inputs": {name: {"path": path.relative_to(root).as_posix(), "sha256": sha256(path)} for name, path in paths.items()},
        })
    require(len(gmst_hashes) == 1, "crop/regime cells do not share identical same-realization centered GMST")
    sensitivities = [centered_calendar_sensitivity(internal, crop, window) for crop in ["mai", "soy", "ri1", "ri2", "swh", "wwh"]]
    return {
        "schema": "isimip3b_rimex_contiguous_multicrop_regime_audit_v1",
        "status": "validated_bounded_multicrop_calendar_support_not_response_damage_or_scc",
        "config": {"path": config_path.relative_to(root).as_posix(), "sha256": sha256(config_path)},
        "implementation": {
            name: {"path": path.relative_to(root).as_posix(), "sha256": sha256(path)}
            for name, path in {
                "audit": Path(__file__).resolve(),
                "season_builder": root / "scripts/build_crop_year_features.py",
                "stage_builder": root / "scripts/build_crop_stage_features.py",
                "centered_builder": root / "scripts/build_rimex_centered_feature_means.py",
            }.items()
        },
        "realization": {"esm": config["esm"], "member": config["member"], "scenario": config["scenario"]},
        "cells": results, "calendar_sensitivities": sensitivities,
        "common_centered_gmst_sha256": next(iter(gmst_hashes)),
        "gates": {"bounded_multicrop_calendar_support": True, "whole_esm_emulator_promoted": False, "whole_scenario_emulator_promoted": False, "irrigation_treatment_effect": False, "response_damage_or_scc_authorized": False},
        "result": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.config.resolve(), args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("contiguous GFDL 12-cell crop × calendar-regime audit passed")


if __name__ == "__main__":
    main()
