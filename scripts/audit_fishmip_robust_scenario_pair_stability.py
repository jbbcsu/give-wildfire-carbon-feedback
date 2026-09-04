#!/usr/bin/env python3
"""Audit scenario stability after both metric and materiality gates pass."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCENARIOS = ["ssp126", "ssp585"]
WINDOWS = [(2021, 2030), (2041, 2050), (2081, 2090)]
BANDS = ["south_high", "south_mid", "tropics", "north_mid", "north_high"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def key(cell: dict[str, object]) -> tuple[str, tuple[int, int], str]:
    period = cell["future_period"]
    return (
        str(cell["climate_scenario"]),
        (int(period["start_year"]), int(period["end_year"])),
        str(cell["latitude_band"]),
    )


def audit(metric_path: Path, dominance_path: Path) -> dict[str, object]:
    metric = json.loads(metric_path.read_text(encoding="utf-8"))
    dominance = json.loads(dominance_path.read_text(encoding="utf-8"))
    require(metric.get("preferred_metric_selected") is False, "metric source selected a preferred metric")
    require(dominance.get("material_dominance_ratio_threshold") == 1.25, "fixed materiality threshold changed")
    for source in (metric, dominance):
        require(source.get("probability_or_variance_decomposition") is False, "source claims probability or variance decomposition")
        require(source.get("scc_authorized") is False, "source opened the SCC gate")

    metric_cells = {key(cell): cell for cell in metric["cells"]}
    dominance_cells = {key(cell): cell for cell in dominance["cells"]}
    expected = {(scenario, window, band) for scenario in SCENARIOS for window in WINDOWS for band in BANDS}
    require(set(metric_cells) == set(dominance_cells) == expected, "source cell keys are incomplete or do not match")

    cells = {}
    for cell_key in sorted(expected):
        metric_cell = metric_cells[cell_key]
        dominance_cell = dominance_cells[cell_key]
        rms_axis = str(metric_cell["rms"]["larger_axis"])
        require(rms_axis == dominance_cell["larger_rms_structural_contrast"], "RMS winner differs across sources")
        metric_agreement = bool(metric_cell["larger_axis_agrees_across_metrics"])
        material = bool(dominance_cell["material_dominance_at_fixed_ratio"])
        cells[cell_key] = {
            "larger_axis": rms_axis,
            "metric_agreement": metric_agreement,
            "material_dominance": material,
            "robust_material_cell": metric_agreement and material,
        }

    pairs = []
    for window in WINDOWS:
        for band in BANDS:
            low = cells[("ssp126", window, band)]
            high = cells[("ssp585", window, band)]
            both_robust = bool(low["robust_material_cell"] and high["robust_material_cell"])
            same_axis = low["larger_axis"] == high["larger_axis"]
            pairs.append({
                "future_period": {"start_year": window[0], "end_year": window[1]},
                "latitude_band": band,
                "ssp126_larger_axis": low["larger_axis"],
                "ssp585_larger_axis": high["larger_axis"],
                "ssp126_robust_material_cell": low["robust_material_cell"],
                "ssp585_robust_material_cell": high["robust_material_cell"],
                "both_scenarios_robust_material": both_robust,
                "same_larger_axis_across_scenarios": same_axis,
                "robust_material_and_scenario_stable": both_robust and same_axis,
            })

    both_robust = sum(row["both_scenarios_robust_material"] for row in pairs)
    robust_stable = sum(row["robust_material_and_scenario_stable"] for row in pairs)
    robust_stable_axis_counts = {
        axis: sum(
            row["robust_material_and_scenario_stable"] and row["ssp126_larger_axis"] == axis
            for row in pairs
        )
        for axis in ("climate_forcing", "ecosystem_model")
    }
    return {
        "schema": "fishmip_robust_scenario_pair_stability_audit_v1",
        "status": "validated_structural_robustness_intersection_not_selection_probability_welfare_damage_or_scc",
        "sources": [
            {"path": metric_path.as_posix(), "sha256": sha256(metric_path)},
            {"path": dominance_path.as_posix(), "sha256": sha256(dominance_path)},
        ],
        "fixed_material_dominance_ratio": 1.25,
        "scenario_pairs": len(pairs),
        "pairs": pairs,
        "both_scenarios_metric_agreeing_and_materially_dominant": both_robust,
        "both_robust_and_same_axis_across_scenarios": robust_stable,
        "robust_scenario_stable_axis_counts": robust_stable_axis_counts,
        "pairs_not_robust_in_both_scenarios": len(pairs) - both_robust,
        "common_structural_axis_selected": False,
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
    print("FishMIP robust scenario-pair stability audit passed")


if __name__ == "__main__":
    main()
