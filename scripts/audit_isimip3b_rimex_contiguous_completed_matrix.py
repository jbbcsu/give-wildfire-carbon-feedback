#!/usr/bin/env python3
"""Audit completed contiguous RIME-X feature cells without fitting a model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


ESMS = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"]
SCENARIOS = ["ssp126", "ssp370", "ssp585"]
TEMPLATES_PER_CELL = 8
MINIMUM_TRAINING_TEMPLATES = 51


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(identities: list[tuple[str, str]]) -> dict[str, object]:
    require(len(identities) == len(set(identities)), "completed matrix has duplicate ESM/scenario cells")
    require(all(esm in ESMS and scenario in SCENARIOS for esm, scenario in identities), "unexpected matrix identity")
    completed = set(identities)
    expected = {(esm, scenario) for esm in ESMS for scenario in SCENARIOS}
    total = len(completed) * TEMPLATES_PER_CELL
    esm_holdouts = {
        esm: {
            "test_templates": sum(item_esm == esm for item_esm, _ in completed) * TEMPLATES_PER_CELL,
            "training_templates": sum(item_esm != esm for item_esm, _ in completed) * TEMPLATES_PER_CELL,
        }
        for esm in ESMS
    }
    scenario_holdouts = {
        scenario: {
            "test_templates": sum(item_scenario == scenario for _, item_scenario in completed) * TEMPLATES_PER_CELL,
            "training_templates": sum(item_scenario != scenario for _, item_scenario in completed) * TEMPLATES_PER_CELL,
        }
        for scenario in SCENARIOS
    }
    represented_training = [
        value["training_templates"]
        for value in [*esm_holdouts.values(), *scenario_holdouts.values()]
        if value["test_templates"] > 0
    ]
    matrix_complete = completed == expected
    return {
        "completed_dataset_cells": len(completed),
        "expected_dataset_cells": len(expected),
        "completed_templates": total,
        "templates_per_dataset_cell": TEMPLATES_PER_CELL,
        "minimum_training_templates": MINIMUM_TRAINING_TEMPLATES,
        "minimum_training_templates_across_represented_holdouts": min(represented_training),
        "all_represented_holdouts_clear_minimum": min(represented_training) >= MINIMUM_TRAINING_TEMPLATES,
        "whole_esm_holdouts": esm_holdouts,
        "whole_scenario_holdouts": scenario_holdouts,
        "missing_dataset_cells": [
            {"esm": esm, "scenario": scenario} for esm, scenario in sorted(expected - completed)
        ],
        "balanced_five_esm_three_scenario_matrix_complete": matrix_complete,
        "joint_dependence_authorized": False,
        "whole_esm_holdout_promotion_authorized": False,
        "whole_scenario_holdout_promotion_authorized": False,
        "response_damage_or_scc_authorized": False,
    }


def audit(root: Path) -> dict[str, object]:
    config_paths = sorted((root / "config").glob("isimip3b_rimex_contiguous_multicrop_regime*v1.toml"))
    audit_paths = sorted((root / "data/provenance").glob("isimip3b_rimex_contiguous_multicrop_regime*audit*.json"))
    audits_by_config: dict[str, tuple[Path, dict]] = {}
    for path in audit_paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("schema") != "isimip3b_rimex_contiguous_multicrop_regime_audit_v1":
            continue
        config_reference = record.get("config", {}).get("path")
        require(config_reference not in audits_by_config, f"duplicate aggregate audit for {config_reference}")
        audits_by_config[config_reference] = (path, record)

    identities: list[tuple[str, str]] = []
    cells = []
    for config_path in config_paths:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        if config.get("schema") != "isimip3b_rimex_contiguous_multicrop_regime_contract_v1":
            continue
        relative_config = config_path.relative_to(root).as_posix()
        require(relative_config in audits_by_config, f"missing aggregate audit for {relative_config}")
        audit_path, record = audits_by_config[relative_config]
        require(record.get("result") == "passed", f"aggregate audit did not pass for {relative_config}")
        require(record["config"].get("sha256") == sha256(config_path), f"config hash changed for {relative_config}")
        identity = (str(config["esm"]), str(config["scenario"]))
        require(record.get("realization", {}).get("esm") == identity[0], "audit ESM identity changed")
        require(record.get("realization", {}).get("scenario") == identity[1], "audit scenario identity changed")
        require(config["center_year_end"] - config["center_year_start"] + 1 == TEMPLATES_PER_CELL, "center-year count changed")
        require(len(config.get("required_cells", [])) == 12 and len(record.get("cells", [])) == 12, "crop/calendar matrix changed")
        require(all(config.get(gate) is False for gate in ("response_estimation_authorized", "whole_esm_emulator_promoted", "whole_scenario_emulator_promoted", "irrigation_treatment_effect_authorized", "damage_or_scc_authorized")), "closed contract gate changed")
        require(all(value is False for key, value in record.get("gates", {}).items() if key != "bounded_multicrop_calendar_support"), "closed audit gate changed")
        identities.append(identity)
        cells.append({
            "esm": identity[0], "scenario": identity[1],
            "config": relative_config, "config_sha256": sha256(config_path),
            "audit": audit_path.relative_to(root).as_posix(), "audit_sha256": sha256(audit_path),
        })

    summary = summarize(identities)
    return {
        "schema": "isimip3b_rimex_contiguous_completed_matrix_audit_v1",
        "status": "passed_inventory_only_not_model_validation",
        "cells": sorted(cells, key=lambda item: (item["esm"], item["scenario"])),
        **summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"audited {result['completed_templates']} completed templates; promotion gates remain closed")


if __name__ == "__main__":
    main()
