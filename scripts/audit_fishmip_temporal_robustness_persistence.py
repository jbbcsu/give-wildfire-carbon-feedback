#!/usr/bin/env python3
"""Describe temporal persistence of already-robust FishMIP scenario pairs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SOURCE_SHA256 = "8a3aaca2bb3d20f81c795f7f0fc5e22c538404ddfe21997cc725793521199315"
WINDOWS = [(2021, 2030), (2041, 2050), (2081, 2090)]
BANDS = ["south_high", "south_mid", "tropics", "north_mid", "north_high"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(source_path: Path) -> dict[str, object]:
    observed_hash = sha256(source_path)
    require(observed_hash == SOURCE_SHA256, "scenario-pair source hash changed")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    require(
        source.get("status")
        == "validated_structural_robustness_intersection_not_selection_probability_welfare_damage_or_scc",
        "scenario-pair source status changed",
    )
    require(source.get("fixed_material_dominance_ratio") == 1.25, "materiality threshold changed")
    for gate in (
        "common_structural_axis_selected",
        "preferred_metric_selected",
        "probability_or_variance_decomposition",
        "country_or_eez_allocation_performed",
        "welfare_estimated",
        "damage_or_scc_authorized",
    ):
        require(source.get(gate) is False, f"source gate changed: {gate}")

    expected = {(window, band) for window in WINDOWS for band in BANDS}
    rows: dict[tuple[tuple[int, int], str], dict[str, object]] = {}
    for row in source.get("pairs", []):
        period = row["future_period"]
        row_key = ((int(period["start_year"]), int(period["end_year"])), str(row["latitude_band"]))
        require(row_key not in rows, f"duplicate pair: {row_key}")
        require(
            bool(row["robust_material_and_scenario_stable"])
            == bool(row["both_scenarios_robust_material"] and row["same_larger_axis_across_scenarios"]),
            f"robust/stable arithmetic changed: {row_key}",
        )
        rows[row_key] = row
    require(set(rows) == expected, "window/latitude pair coverage changed")

    by_band = []
    for band in BANDS:
        robust_windows = [
            {"start_year": window[0], "end_year": window[1]}
            for window in WINDOWS
            if rows[(window, band)]["robust_material_and_scenario_stable"]
        ]
        axes = {
            str(rows[(window, band)]["ssp126_larger_axis"])
            for window in WINDOWS
            if rows[(window, band)]["robust_material_and_scenario_stable"]
        }
        by_band.append({
            "latitude_band": band,
            "robust_scenario_stable_windows": robust_windows,
            "robust_scenario_stable_window_count": len(robust_windows),
            "all_three_windows_robust_and_scenario_stable": len(robust_windows) == len(WINDOWS),
            "robust_window_axes": sorted(axes),
        })

    by_window = []
    for window in WINDOWS:
        passing = [band for band in BANDS if rows[(window, band)]["robust_material_and_scenario_stable"]]
        by_window.append({
            "future_period": {"start_year": window[0], "end_year": window[1]},
            "robust_scenario_stable_latitude_bands": passing,
            "robust_scenario_stable_latitude_band_count": len(passing),
        })

    persistent_bands = [row["latitude_band"] for row in by_band if row["all_three_windows_robust_and_scenario_stable"]]
    return {
        "schema": "fishmip_temporal_robustness_persistence_audit_v1",
        "status": "descriptive_cross_audit_no_temporally_persistent_robust_latitude_band",
        "source": {"path": source_path.as_posix(), "sha256": observed_hash},
        "fixed_material_dominance_ratio": 1.25,
        "future_windows": [{"start_year": start, "end_year": end} for start, end in WINDOWS],
        "latitude_band_count": len(BANDS),
        "by_latitude_band": by_band,
        "by_future_window": by_window,
        "latitude_bands_robust_and_scenario_stable_in_all_windows": persistent_bands,
        "temporally_persistent_latitude_band_count": len(persistent_bands),
        "common_structural_axis_selected": False,
        "preferred_metric_selected": False,
        "probability_or_variance_decomposition": False,
        "country_or_eez_allocation_performed": False,
        "welfare_estimated": False,
        "damage_or_scc_authorized": False,
        "interpretation": (
            "None of the five latitude bands is metric-agreeing, materially dominant, and scenario-stable "
            "in all three future windows. The five previously robust scenario pairs occur only in 2021-2030 "
            "or 2041-2050; zero occur in 2081-2090. This descriptive intersection does not select a metric or "
            "structural axis and does not support probabilities, allocation, welfare, damage, or SCC use."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FishMIP temporal robustness persistence audit passed")


if __name__ == "__main__":
    main()
