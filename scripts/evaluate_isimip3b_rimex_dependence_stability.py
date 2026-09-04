#!/usr/bin/env python3
"""Evaluate represented-template dependence stability from derived Parquet files.

This diagnostic reads one centered season/stage file pair at a time and one
explicit center year at a time. It never opens a global daily climate file and
does not fit a marginal response, joint climate response, yield response, or
damage model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import tomllib

import numpy as np
import pandas as pd

from validate_isimip3b_rimex_dependence_stability_contract import (
    COORDINATES,
    validate as validate_contract,
)
from validate_isimip3b_rimex_joint_dependence_contract import encode_physical


SEASON_COLUMNS = [
    "lat", "lon", "crop", "irrigation", "center_year",
    "season_days_21yr_mean", "tmean_c_21yr_mean", "precip_mm_21yr_mean",
    "wet_days_n_21yr_mean", "cdd_max_days_21yr_mean",
    "rx1day_mm_21yr_mean", "rx5day_mm_21yr_mean",
]
STAGE_COLUMNS = [
    "lat", "lon", "crop", "irrigation", "stage_id", "center_year",
    "precip_mm_21yr_mean",
]
KEYS = ["lat", "lon", "crop", "irrigation", "center_year"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def observed_rss_bytes() -> int:
    raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return raw if platform.system() == "Darwin" else raw * 1024


def prepare_file_pair(season_path: Path, stage_path: Path, epsilon: float) -> dict[int, pd.DataFrame]:
    season = pd.read_parquet(season_path, columns=SEASON_COLUMNS)
    stages = pd.read_parquet(stage_path, columns=STAGE_COLUMNS)
    require(not season.duplicated(KEYS).any(), f"duplicate centered season keys in {season_path}")
    require(not stages.duplicated(KEYS + ["stage_id"]).any(), f"duplicate centered stage keys in {stage_path}")
    require(set(stages.stage_id.unique()) == {1, 2, 3}, f"stage identities changed in {stage_path}")
    pivot = stages.pivot(index=KEYS, columns="stage_id", values="precip_mm_21yr_mean").reset_index()
    pivot = pivot.rename(columns={1: "stage1_precip", 2: "stage2_precip", 3: "stage3_precip"})
    merged = season.merge(pivot, on=KEYS, how="left", validate="one_to_one", indicator=True)
    require((merged._merge == "both").all() and len(merged) == len(season), f"stage/season join incomplete in {season_path}")
    merged = merged.drop(columns="_merge")
    total = merged[["stage1_precip", "stage2_precip", "stage3_precip"]].sum(axis=1)
    require(np.allclose(total, merged.precip_mm_21yr_mean, rtol=0, atol=1e-9), f"stage precipitation does not reconcile in {season_path}")
    require((merged.precip_mm_21yr_mean > 0).all(), f"nonpositive centered precipitation in {season_path}")
    for number in (1, 2, 3):
        merged[f"stage{number}_precip_share"] = merged[f"stage{number}_precip"] / merged.precip_mm_21yr_mean
    physical = merged.rename(columns={
        "season_days_21yr_mean": "season_days",
        "tmean_c_21yr_mean": "tmean_c",
        "precip_mm_21yr_mean": "precip_mm",
        "wet_days_n_21yr_mean": "wet_days_n",
        "cdd_max_days_21yr_mean": "cdd_max_days",
        "rx1day_mm_21yr_mean": "rx1day_mm",
        "rx5day_mm_21yr_mean": "rx5day_mm",
    })
    output: dict[int, pd.DataFrame] = {}
    for year, block in physical.groupby("center_year", sort=True):
        output[int(year)] = encode_physical(block, epsilon).reset_index(drop=True)
    return output


def correlation_pairs(frame: pd.DataFrame) -> dict[tuple[str, str], float]:
    require(list(frame.columns) == COORDINATES, "linked-coordinate order changed")
    correlation = frame.corr(method="spearman")
    require(np.isfinite(correlation.to_numpy()).all(), "template Spearman matrix is not finite")
    return {
        (left, right): float(correlation.loc[left, right])
        for left_index, left in enumerate(COORDINATES)
        for right in COORDINATES[left_index + 1:]
    }


def summarize_holdout(
    templates: pd.DataFrame,
    field: str,
    value: str,
    mean_limit: float,
    maximum_limit: float,
    strong_threshold: float,
    sign_flips_allowed: int,
) -> dict[str, object]:
    train = templates.loc[templates[field] != value]
    test = templates.loc[templates[field] == value]
    require(len(train) >= 51 and len(test) > 0, f"{field}={value} lacks preregistered train/test support")
    pair_columns = [column for column in templates.columns if column.startswith("rho|")]
    train_median = train[pair_columns].median(axis=0)
    test_median = test[pair_columns].median(axis=0)
    differences = (test_median - train_median).abs()
    strong = train_median.abs() >= strong_threshold
    sign_flips = strong & (np.sign(train_median) != np.sign(test_median))
    worst = str(differences.idxmax()).split("|", 2)
    mean_difference = float(differences.mean())
    maximum_difference = float(differences.max())
    sign_flip_count = int(sign_flips.sum())
    passed = mean_difference <= mean_limit and maximum_difference <= maximum_limit and sign_flip_count <= sign_flips_allowed
    return {
        "holdout_type": field,
        "holdout": value,
        "training_templates": int(len(train)),
        "test_templates": int(len(test)),
        "pairwise_spearman_median_mean_absolute_difference": mean_difference,
        "pairwise_spearman_median_maximum_absolute_difference": maximum_difference,
        "worst_coordinate_pair": worst[1:],
        "strong_pair_sign_flips": sign_flip_count,
        "passed_preregistered_stability_tolerances": bool(passed),
    }


def summarize_holdouts(templates: pd.DataFrame, config: dict[str, object]) -> list[dict[str, object]]:
    diagnostic = config["diagnostic"]
    sample = config["sample"]
    arguments = (
        float(diagnostic["mean_absolute_difference_max"]),
        float(diagnostic["maximum_absolute_difference_max"]),
        float(diagnostic["strong_pair_absolute_training_median"]),
        int(diagnostic["strong_pair_sign_flips_allowed"]),
    )
    return [
        *[
            summarize_holdout(templates, "esm", esm, *arguments)
            for esm in sample["represented_whole_esm_holdouts"]
        ],
        *[
            summarize_holdout(templates, "scenario", scenario, *arguments)
            for scenario in sample["represented_whole_scenario_holdouts"]
        ],
    ]


def evaluate(config_path: Path, root: Path, template_csv_path: Path) -> dict[str, object]:
    preregistration = validate_contract(config_path, root)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    inventory_path = root / config["source_receipts"][0]["path"]
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    require(inventory.get("completed_templates") == 88, "completed template inventory changed")
    require(inventory.get("balanced_five_esm_three_scenario_matrix_complete") is False, "balanced-matrix boundary changed")
    epsilon = float(config["physical"]["boundary_epsilon"])
    expected_years = set(config["sample"]["center_years"])
    expected_ids = {
        f"{crop}_{irrigation}"
        for crop in config["sample"]["crops_required"]
        for irrigation in config["sample"]["irrigation_regimes_required"]
    }
    template_records: list[dict[str, object]] = []
    source_files = 0

    for inventory_cell in inventory["cells"]:
        audit_path = root / inventory_cell["audit"]
        require(sha256(audit_path) == inventory_cell["audit_sha256"], f"cell audit hash changed: {audit_path}")
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        realization = audit["realization"]
        require(realization["esm"] == inventory_cell["esm"] and realization["scenario"] == inventory_cell["scenario"], "cell realization identity changed")
        require({cell["id"] for cell in audit["cells"]} == expected_ids, "crop/regime cell set changed")
        year_blocks: dict[int, list[pd.DataFrame]] = {year: [] for year in sorted(expected_years)}
        for crop_cell in sorted(audit["cells"], key=lambda item: item["id"]):
            season_info = crop_cell["inputs"]["center_season"]
            stage_info = crop_cell["inputs"]["center_stages"]
            season_path = root / season_info["path"]
            stage_path = root / stage_info["path"]
            require(sha256(season_path) == season_info["sha256"], f"centered season hash changed: {season_path}")
            require(sha256(stage_path) == stage_info["sha256"], f"centered stage hash changed: {stage_path}")
            source_files += 2
            prepared = prepare_file_pair(season_path, stage_path, epsilon)
            require(set(prepared) == expected_years, f"center years changed in {season_path}")
            for year in sorted(expected_years):
                year_blocks[year].append(prepared[year])
            del prepared
            require(observed_rss_bytes() < int(config["resources"]["maximum_peak_resident_memory_bytes"]), "peak RSS exceeded 2 GiB while streaming derived files")

        for year in sorted(expected_years):
            linked = pd.concat(year_blocks[year], ignore_index=True)
            require(len(linked) == int(config["sample"]["expected_rows_per_template"]), "complete-template row count changed")
            pairs = correlation_pairs(linked)
            record: dict[str, object] = {
                "esm": realization["esm"],
                "scenario": realization["scenario"],
                "center_year": year,
                "rows": len(linked),
            }
            record.update({f"rho|{left}|{right}": value for (left, right), value in pairs.items()})
            template_records.append(record)
            del linked
        del year_blocks

    templates = pd.DataFrame(template_records).sort_values(["esm", "scenario", "center_year"]).reset_index(drop=True)
    require(len(templates) == 88, "real template count changed")
    require(len([column for column in templates if column.startswith("rho|")]) == 28, "pairwise correlation count changed")
    holdouts = summarize_holdouts(templates, config)
    passed = all(item["passed_preregistered_stability_tolerances"] for item in holdouts)
    require(observed_rss_bytes() < int(config["resources"]["maximum_peak_resident_memory_bytes"]), "peak RSS exceeded 2 GiB")

    template_csv_path.parent.mkdir(parents=True, exist_ok=True)
    templates.to_csv(template_csv_path, index=False, float_format="%.15g", lineterminator="\n")
    return {
        "schema": "isimip3b_rimex_dependence_stability_audit_v1",
        "status": "passed_represented_template_stability_balanced_matrix_incomplete" if passed else "failed_represented_template_stability_balanced_matrix_incomplete",
        "preregistration": {
            "path": "data/provenance/isimip3b_rimex_dependence_stability_preregistration_20260903.json",
            "sha256": sha256(root / "data/provenance/isimip3b_rimex_dependence_stability_preregistration_20260903.json"),
            "config_sha256": preregistration["config_sha256"],
        },
        "implementation_sha256": sha256(Path(__file__)),
        "completed_templates": len(templates),
        "rows_per_template": int(templates.rows.iloc[0]),
        "derived_parquet_files_read_sequentially": source_files,
        "template_spearman_csv": {
            "path": str(template_csv_path.relative_to(root)),
            "sha256": sha256(template_csv_path),
        },
        "holdouts": holdouts,
        "all_represented_holdouts_passed": passed,
        "peak_rss_gate_bytes": int(config["resources"]["maximum_peak_resident_memory_bytes"]),
        "peak_rss_gate_passed": True,
        "balanced_five_esm_three_scenario_matrix_complete": False,
        "missing_dataset_cells": inventory["missing_dataset_cells"],
        "real_joint_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "interpretation": "Outcome-blind dependence stability diagnostic over represented completed templates only; not a marginal fit, joint climate response, crop-yield response, damage, welfare, or SCC result.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--template-csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.config, args.root, args.template_csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"RIME-X dependence stability: {result['status']}; peak_rss_bytes={observed_rss_bytes()}")


if __name__ == "__main__":
    main()
