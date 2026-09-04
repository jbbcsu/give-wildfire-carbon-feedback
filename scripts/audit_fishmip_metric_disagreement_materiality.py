#!/usr/bin/env python3
"""Cross-audit metric disagreement against the preregistered 1.25 RMS gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def key(cell: dict[str, object]) -> tuple[str, int, int, str]:
    period = cell["future_period"]
    return (str(cell["climate_scenario"]), int(period["start_year"]), int(period["end_year"]), str(cell["latitude_band"]))


def audit(metric_path: Path, dominance_path: Path) -> dict[str, object]:
    metric = json.loads(metric_path.read_text(encoding="utf-8"))
    dominance = json.loads(dominance_path.read_text(encoding="utf-8"))
    if metric.get("preferred_metric_selected") is not False:
        raise ValueError("source selected a preferred metric")
    if dominance.get("material_dominance_ratio_threshold") != 1.25:
        raise ValueError("fixed dominance threshold changed")
    if dominance.get("probability_or_variance_decomposition") is not False:
        raise ValueError("source claimed a probability or variance decomposition")
    if metric.get("scc_authorized") is not False or dominance.get("scc_authorized") is not False:
        raise ValueError("source opened the SCC gate")
    metric_cells = {key(cell): cell for cell in metric["cells"]}
    dominance_cells = {key(cell): cell for cell in dominance["cells"]}
    if len(metric_cells) != 30 or metric_cells.keys() != dominance_cells.keys():
        raise ValueError("source cell keys are incomplete or do not match")

    counts = {
        "metric_agreement_and_material_dominance": 0,
        "metric_agreement_and_near_tie": 0,
        "metric_disagreement_and_material_dominance": 0,
        "metric_disagreement_and_near_tie": 0,
    }
    disagreement_ratios = []
    agreement_ratios = []
    for cell_key in sorted(metric_cells):
        agrees = bool(metric_cells[cell_key]["larger_axis_agrees_across_metrics"])
        material = bool(dominance_cells[cell_key]["material_dominance_at_fixed_ratio"])
        label = f"metric_{'agreement' if agrees else 'disagreement'}_and_{'material_dominance' if material else 'near_tie'}"
        counts[label] += 1
        ratio = float(dominance_cells[cell_key]["larger_to_smaller_rms_ratio"])
        (agreement_ratios if agrees else disagreement_ratios).append(ratio)

    return {
        "schema": "fishmip_metric_disagreement_materiality_audit_v1",
        "status": "validated_structural_cross_audit_not_metric_selection_probability_welfare_damage_or_scc",
        "sources": [
            {"path": metric_path.as_posix(), "sha256": sha256(metric_path)},
            {"path": dominance_path.as_posix(), "sha256": sha256(dominance_path)},
        ],
        "cells": 30,
        "fixed_material_dominance_ratio": 1.25,
        "cross_tabulation": counts,
        "metric_disagreement_fraction_materially_dominant": counts["metric_disagreement_and_material_dominance"] / 10,
        "metric_agreement_fraction_materially_dominant": counts["metric_agreement_and_material_dominance"] / 20,
        "metric_disagreement_rms_ratio_range": [min(disagreement_ratios), max(disagreement_ratios)],
        "metric_agreement_rms_ratio_range": [min(agreement_ratios), max(agreement_ratios)],
        "preferred_metric_selected": False,
        "probability_or_variance_decomposition": False,
        "country_or_eez_allocation_performed": False,
        "welfare_estimated": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metric-audit", type=Path, required=True)
    parser.add_argument("--dominance-audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.metric_audit, args.dominance_audit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FishMIP metric-disagreement materiality cross-audit passed")


if __name__ == "__main__":
    main()
