#!/usr/bin/env python3
"""Validate bounded multi-crop ISIMIP3b feature support without promoting a response."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

import compare_climate_feature_cells
import reconcile_stage_season_features
from compare_climate_feature_cells import KEYS, SEASON_METRICS, compare, paired_summary
from reconcile_stage_season_features import validate_row_invariants


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def implementation_record(path: Path, root: Path) -> dict[str, str]:
    resolved = path.resolve()
    try:
        display = resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        display = resolved.as_posix()
    return {"path": display, "sha256": sha256(resolved)}


def require_hash(root: Path, record: dict[str, object], path_key: str, hash_key: str) -> dict[str, object]:
    path = resolve(root, str(record[path_key]))
    observed = sha256(path)
    expected = str(record[hash_key])
    if observed != expected:
        raise ValueError(f"{path_key} hash mismatch for {path}: {observed} != {expected}")
    return {"path": str(record[path_key]), "sha256": observed}


def validate_reconciliation(season: pd.DataFrame, stages: pd.DataFrame) -> dict[str, float]:
    validate_row_invariants(season, "season_days", "season")
    validate_row_invariants(stages, "stage_days", "stage")
    grouped = stages.groupby(KEYS, observed=True).agg(
        stage_days=("stage_days", "sum"),
        precip_mm=("precip_mm", "sum"),
        wet_days_n=("wet_days_n", "sum"),
        rx1day_mm=("rx1day_mm", "max"),
    ).reset_index()
    merged = season.merge(grouped, on=KEYS, suffixes=("_season", "_stages"), validate="one_to_one")
    if len(merged) != len(season):
        raise ValueError("stages do not cover every season row")
    differences = {
        "stage_days": float((merged.stage_days - merged.season_days).abs().max()),
        "precip_mm": float((merged.precip_mm_stages - merged.precip_mm_season).abs().max()),
        "wet_days_n": float((merged.wet_days_n_stages - merged.wet_days_n_season).abs().max()),
        "rx1day_mm": float((merged.rx1day_mm_stages - merged.rx1day_mm_season).abs().max()),
    }
    tolerances = {"stage_days": 0.0, "precip_mm": 1e-3, "wet_days_n": 0.0, "rx1day_mm": 1e-6}
    failures = {name: value for name, value in differences.items() if value > tolerances[name]}
    if failures:
        raise ValueError(f"stage/season reconciliation failed: {failures}")
    return differences


def check_cell(root: Path, config: dict[str, object], cell: dict[str, object]) -> dict[str, object]:
    expected_rows = int(cell.get("expected_season_rows", config["expected_season_rows_per_cell"]))
    expected_stage_rows = int(cell.get("expected_stage_rows", config["expected_stage_rows_per_cell"]))
    expected_stages = int(config["expected_stages"])
    paths = {name: resolve(root, str(cell[name])) for name in (
        "reference_season", "reference_stages", "candidate_season", "candidate_stages"
    )}
    frames = {name: pd.read_parquet(path) for name, path in paths.items()}
    for name in ("reference_season", "candidate_season"):
        frame = frames[name]
        if len(frame) != expected_rows:
            raise ValueError(f"{cell['id']} {name} has {len(frame)} rows, expected {expected_rows}")
    for name in ("reference_stages", "candidate_stages"):
        frame = frames[name]
        if len(frame) != expected_stage_rows:
            raise ValueError(f"{cell['id']} {name} has {len(frame)} rows, expected {expected_stage_rows}")
        if set(frame.stage_id.unique()) != set(range(1, expected_stages + 1)):
            raise ValueError(f"{cell['id']} {name} has incorrect stage IDs")
    for name, frame in frames.items():
        if set(frame.crop.unique()) != {cell["crop"]} or set(frame.irrigation.unique()) != {cell["irrigation"]}:
            raise ValueError(f"{cell['id']} {name} crop/irrigation identity mismatch")
        years = set(frame.harvest_year.unique())
        if years != set(range(int(config["year_start"]), int(config["year_end"]) + 1)):
            raise ValueError(f"{cell['id']} {name} year coverage mismatch")
    reconciliations = {
        scenario: validate_reconciliation(frames[f"{scenario}_season"], frames[f"{scenario}_stages"])
        for scenario in ("reference", "candidate")
    }
    summary = compare(
        paths["reference_season"], paths["reference_stages"],
        paths["candidate_season"], paths["candidate_stages"],
        reference_label=str(config["reference_scenario"]),
        candidate_label=str(config["candidate_scenario"]),
        year_start=int(config["year_start"]), year_end=int(config["year_end"]),
        expected_stages=expected_stages,
    )
    return {
        "id": cell["id"], "crop": cell["crop"], "irrigation": cell["irrigation"],
        "calendar": require_hash(root, cell, "calendar", "calendar_sha256"),
        "inputs": {name: {"path": str(cell[name]), "sha256": sha256(path)} for name, path in paths.items()},
        "reconciliation_max_absolute_differences": reconciliations,
        "candidate_minus_reference": {
            metric: summary["metrics"][metric] for metric in SEASON_METRICS + [
                "stage1_precip_share", "stage2_precip_share", "stage3_precip_share",
                "precipitation_timing_centroid", "precipitation_concentration_hhi",
            ]
        },
    }


def calendar_sensitivity(cells: dict[str, dict[str, object]], scenario: str) -> dict[str, object]:
    left = cells["soy_noirr"][f"_{scenario}_season"].sort_values(["harvest_year", "lat", "lon_360"])
    right = cells["soy_firr"][f"_{scenario}_season"].sort_values(["harvest_year", "lat", "lon_360"])
    keys = ["harvest_year", "lat", "lon_360", "crop"]
    if not left[keys].reset_index(drop=True).equals(right[keys].reset_index(drop=True)):
        raise ValueError(f"soy calendar sensitivity lacks exact paired {scenario} support")
    return {
        "scenario": scenario,
        "rows": len(left),
        "firr_minus_noirr": {metric: paired_summary(left[metric], right[metric]) for metric in SEASON_METRICS},
    }


def audit(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    cells = config["cells"]
    required = list(config["required_cells"])
    observed = [str(cell["id"]) for cell in cells]
    if observed != required or len(observed) != len(set(observed)):
        raise ValueError("cell list must exactly equal the ordered required_cells declaration")
    sources = [require_hash(root, source, "path", "sha256") | {"scenario": source["scenario"]}
               for source in config["source_provenance"]]
    if [source["scenario"] for source in config["source_provenance"]] != [
        config["reference_scenario"], config["candidate_scenario"]
    ]:
        raise ValueError("source provenance must bind reference then candidate scenario")
    internal: dict[str, dict[str, object]] = {}
    summaries = []
    for cell in cells:
        checked = check_cell(root, config, cell)
        summaries.append(checked)
        internal[str(cell["id"])] = dict(cell)
        for scenario in ("reference", "candidate"):
            internal[str(cell["id"])][f"_{scenario}_season"] = pd.read_parquet(
                resolve(root, str(cell[f"{scenario}_season"]))
            )
    result = {
        "schema": "isimip3b_bounded_multicrop_support_audit_v1",
        "role": config["role"],
        "config": {"path": str(config_path.relative_to(root)), "sha256": sha256(config_path)},
        "implementation": {
            "audit": implementation_record(Path(__file__), root),
            "comparison": implementation_record(Path(compare_climate_feature_cells.__file__), root),
            "reconciliation": implementation_record(Path(reconcile_stage_season_features.__file__), root),
        },
        "esm": config["esm"], "member": config["member"],
        "reference_scenario": config["reference_scenario"],
        "candidate_scenario": config["candidate_scenario"],
        "year_start": config["year_start"], "year_end": config["year_end"],
        "source_provenance": sources,
        "cells": summaries,
        "soybean_calendar_sensitivity": [
            calendar_sensitivity(internal, "reference"), calendar_sensitivity(internal, "candidate")
        ],
        "gates": {
            "bounded_multicrop_feature_support": True,
            "whole_scenario_emulator_promoted": False,
            "whole_esm_emulator_promoted": False,
            "causal_yield_response": False,
            "irrigation_treatment_effect": False,
            "damage_or_scc_input": False,
        },
        "result": "passed",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.config, args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"multicrop support audit passed: {len(result['cells'])} cells")


if __name__ == "__main__":
    main()
