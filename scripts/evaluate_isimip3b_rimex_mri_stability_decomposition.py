#!/usr/bin/env python3
"""Decompose the locked MRI wet-frequency/extreme-intensity instability.

The evaluator reads only checksum-bound derived centered Parquet pairs, one
crop/regime pair at a time. It does not read global daily inputs or fit any
climate, yield, damage, or welfare model.
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

from evaluate_isimip3b_rimex_dependence_stability import prepare_file_pair
from validate_isimip3b_rimex_mri_stability_decomposition_contract import validate as validate_contract


PAIR_COLUMN = "rho|wet_logit|rx1_given_rx5_logit"


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


def reported_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def compare(frame: pd.DataFrame, focal_mask: pd.Series, comparison_mask: pd.Series) -> dict[str, object]:
    focal = frame.loc[focal_mask, PAIR_COLUMN]
    comparison = frame.loc[comparison_mask, PAIR_COLUMN]
    require(len(focal) > 0 and len(comparison) > 0, "comparison group is empty")
    require(np.isfinite(focal).all() and np.isfinite(comparison).all(), "comparison contains nonfinite correlation")
    focal_median = float(focal.median())
    comparison_median = float(comparison.median())
    return {
        "focal_templates": int(len(focal)),
        "comparison_templates": int(len(comparison)),
        "focal_median_spearman": focal_median,
        "comparison_median_spearman": comparison_median,
        "absolute_difference": abs(focal_median - comparison_median),
    }


def summarize(template_values: pd.DataFrame, cell_values: pd.DataFrame, config: dict[str, object]) -> dict[str, object]:
    sample = config["sample"]
    method = config["method"]
    outputs = config["outputs"]
    focal_esm = str(sample["focal_esm"])
    shared = list(sample["shared_scenarios"])
    years = list(sample["center_years"])
    require(len(template_values) == int(sample["completed_templates_required"]), "template value count changed")
    require(template_values[["esm", "scenario", "center_year"]].duplicated().sum() == 0, "duplicate aggregate template keys")
    require(PAIR_COLUMN in template_values, "locked focal pair is absent")
    require(len(cell_values) == int(outputs["cell_template_rows_required"]), "cell-template value count changed")
    require(cell_values[["esm", "scenario", "center_year", "crop", "irrigation"]].duplicated().sum() == 0, "duplicate cell-template keys")

    focal = template_values.esm == focal_esm
    nonfocal = ~focal
    require(int(focal.sum()) == int(sample["focal_esm_templates_required"]), "focal template count changed")
    require(int(nonfocal.sum()) == int(sample["nonfocal_templates_required"]), "nonfocal template count changed")
    full = compare(template_values, focal, nonfocal)
    locked_failure = float(method["locked_original_failure_difference"])
    require(abs(float(full["absolute_difference"]) - locked_failure) <= 1e-12, "locked full-sample MRI failure did not reproduce")

    shared_mask = template_values.scenario.isin(shared)
    matched = compare(template_values, focal & shared_mask, nonfocal & shared_mask)
    require(matched["focal_templates"] == len(shared) * int(sample["focal_templates_per_shared_scenario"]), "matched focal support changed")
    require(matched["comparison_templates"] == len(shared) * int(sample["nonfocal_templates_per_shared_scenario"]), "matched comparison support changed")

    scenario_rows = []
    for scenario in shared:
        scenario_mask = template_values.scenario == scenario
        row = compare(template_values, focal & scenario_mask, nonfocal & scenario_mask)
        require(row["focal_templates"] == int(sample["focal_templates_per_shared_scenario"]), "scenario focal support changed")
        require(row["comparison_templates"] == int(sample["nonfocal_templates_per_shared_scenario"]), "scenario comparison support changed")
        scenario_rows.append({"scenario": scenario, **row})

    center_year_rows = []
    for year in years:
        year_mask = (template_values.center_year == year) & shared_mask
        center_year_rows.append({"center_year": year, **compare(template_values, focal & year_mask, nonfocal & year_mask)})
    require(len(center_year_rows) == int(outputs["center_year_rows_required"]), "center-year result count changed")

    cell_rows = []
    expected_cells = {
        (crop, irrigation)
        for crop in sample["crops_required"]
        for irrigation in sample["irrigation_regimes_required"]
    }
    observed_cells = set(zip(cell_values.crop, cell_values.irrigation))
    require(observed_cells == expected_cells, "crop/regime cells changed")
    cell_focal = cell_values.esm == focal_esm
    cell_nonfocal = ~cell_focal
    cell_shared = cell_values.scenario.isin(shared)
    for crop, irrigation in sorted(expected_cells):
        selected = (cell_values.crop == crop) & (cell_values.irrigation == irrigation)
        aggregate = compare(cell_values, selected & cell_focal & cell_shared, selected & cell_nonfocal & cell_shared)
        scenario_differences = {}
        for scenario in shared:
            scenario_selected = selected & (cell_values.scenario == scenario)
            scenario_differences[scenario] = compare(
                cell_values,
                scenario_selected & cell_focal,
                scenario_selected & cell_nonfocal,
            )["absolute_difference"]
        cell_rows.append({
            "crop": crop,
            "irrigation": irrigation,
            **aggregate,
            "ssp126_absolute_difference": float(scenario_differences["ssp126"]),
            "ssp370_absolute_difference": float(scenario_differences["ssp370"]),
        })
    require(len(cell_rows) == int(outputs["crop_regime_rows_required"]), "crop/regime result count changed")

    gate = float(method["locked_original_maximum_difference_gate"])
    matched_difference = float(matched["absolute_difference"])
    scenario_imbalance_sufficient = matched_difference <= gate
    center_differences = [float(row["absolute_difference"]) for row in center_year_rows]
    cell_differences = [float(row["absolute_difference"]) for row in cell_rows]
    return {
        "full_sample_reproduction": full,
        "scenario_matched_primary": matched,
        "shared_scenario_diagnostics": scenario_rows,
        "center_year_diagnostics": center_year_rows,
        "crop_regime_diagnostics": cell_rows,
        "locked_gate": gate,
        "scenario_imbalance_sufficient_to_explain_locked_failure": scenario_imbalance_sufficient,
        "scenario_matching_reduction_in_absolute_difference": float(full["absolute_difference"]) - matched_difference,
        "center_year_absolute_difference_minimum": min(center_differences),
        "center_year_absolute_difference_maximum": max(center_differences),
        "center_years_above_locked_gate": sum(value > gate for value in center_differences),
        "crop_regime_absolute_difference_minimum": min(cell_differences),
        "crop_regime_absolute_difference_maximum": max(cell_differences),
        "crop_regime_cells_above_locked_gate": sum(value > gate for value in cell_differences),
    }


def evaluate(config_path: Path, root: Path, cell_csv_path: Path) -> dict[str, object]:
    preregistration = validate_contract(config_path, root)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    inventory = json.loads((root / config["source_receipts"][0]["path"]).read_text(encoding="utf-8"))
    template_values = pd.read_csv(root / config["source_receipts"][2]["path"])
    expected_years = set(config["sample"]["center_years"])
    epsilon = 1e-6
    cell_records: list[dict[str, object]] = []
    source_files = 0

    for inventory_cell in inventory["cells"]:
        audit_path = root / inventory_cell["audit"]
        require(sha256(audit_path) == inventory_cell["audit_sha256"], f"cell audit hash changed: {audit_path}")
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        realization = audit["realization"]
        for crop_cell in sorted(audit["cells"], key=lambda item: item["id"]):
            crop, irrigation = crop_cell["id"].split("_", 1)
            season_info = crop_cell["inputs"]["center_season"]
            stage_info = crop_cell["inputs"]["center_stages"]
            season_path = root / season_info["path"]
            stage_path = root / stage_info["path"]
            require(sha256(season_path) == season_info["sha256"], f"centered season hash changed: {season_path}")
            require(sha256(stage_path) == stage_info["sha256"], f"centered stage hash changed: {stage_path}")
            prepared = prepare_file_pair(season_path, stage_path, epsilon)
            require(set(prepared) == expected_years, f"center years changed in {season_path}")
            source_files += 2
            for year in sorted(expected_years):
                frame = prepared[year][["wet_logit", "rx1_given_rx5_logit"]]
                correlation = float(frame.corr(method="spearman").iloc[0, 1])
                require(np.isfinite(correlation), f"nonfinite focal correlation in {season_path}, {year}")
                cell_records.append({
                    "esm": realization["esm"],
                    "scenario": realization["scenario"],
                    "center_year": year,
                    "crop": crop,
                    "irrigation": irrigation,
                    "rows": len(frame),
                    PAIR_COLUMN: correlation,
                })
            del prepared
            require(observed_rss_bytes() < int(config["resources"]["maximum_peak_resident_memory_bytes"]), "peak RSS exceeded 2 GiB")

    cell_values = pd.DataFrame(cell_records).sort_values(["esm", "scenario", "center_year", "crop", "irrigation"]).reset_index(drop=True)
    summary = summarize(template_values, cell_values, config)
    cell_csv_path.parent.mkdir(parents=True, exist_ok=True)
    cell_values.to_csv(cell_csv_path, index=False, float_format="%.15g", lineterminator="\n")
    maximum_rss = observed_rss_bytes()
    require(maximum_rss < int(config["resources"]["maximum_peak_resident_memory_bytes"]), "peak RSS exceeded 2 GiB")
    sufficient = bool(summary["scenario_imbalance_sufficient_to_explain_locked_failure"])
    return {
        "schema": "isimip3b_rimex_mri_stability_decomposition_audit_v1",
        "status": "scenario_imbalance_sufficient_under_locked_gate" if sufficient else "mri_instability_persists_after_scenario_matching",
        "preregistration": {
            "path": "data/provenance/isimip3b_rimex_mri_stability_decomposition_preregistration_20260904.json",
            "sha256": sha256(root / "data/provenance/isimip3b_rimex_mri_stability_decomposition_preregistration_20260904.json"),
            "config_sha256": preregistration["config_sha256"],
        },
        "implementation_sha256": sha256(Path(__file__)),
        "cell_template_values": {"path": reported_path(cell_csv_path, root), "sha256": sha256(cell_csv_path), "rows": len(cell_values)},
        "derived_parquet_files_read_sequentially": source_files,
        "minimum_rows_in_cell_template": int(cell_values.rows.min()),
        "peak_rss_gate_bytes": int(config["resources"]["maximum_peak_resident_memory_bytes"]),
        "peak_rss_gate_passed": True,
        **summary,
        "balanced_five_esm_three_scenario_matrix_complete": False,
        "dependence_fit_authorized": False,
        "fair_feature_response_authorized": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "interpretation": "Diagnostic decomposition of a locked adverse dependence-stability result; no tolerance retuning, model fit, causal response, damage, welfare, or SCC use.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--cell-template-csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.config, args.root, args.cell_template_csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"MRI stability decomposition: {result['status']}; peak_rss_bytes={observed_rss_bytes()}")


if __name__ == "__main__":
    main()
