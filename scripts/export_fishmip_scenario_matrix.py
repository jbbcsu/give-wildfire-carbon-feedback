#!/usr/bin/env python3
"""Export a compact, tracked summary of validated FishMIP scenario diagnostics."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    "data/raw/fishmip/gfdl-esm4/scenario_benchmark_v1.json",
    "data/raw/fishmip/gfdl-esm4/scenario_benchmark_ssp585_v1.json",
    "data/raw/fishmip/ipsl-cm6a-lr/scenario_benchmark_ssp126_v1.json",
    "data/raw/fishmip/ipsl-cm6a-lr/scenario_benchmark_ssp585_v1.json",
)
OUT = ROOT / "data/provenance/fishmip_scenario_benchmark_matrix_20260826.json"
FORCINGS = {"gfdl-esm4", "ipsl-cm6a-lr"}
SCENARIOS = {"ssp126", "ssp585"}
MODELS = {"boats", "ecoocean"}
PERIODS = {"near", "mid", "late"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def robustness_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    """Validate the frozen factorial and summarize signs without averaging levels."""
    indexed: dict[tuple[str, str, str], dict[str, object]] = {}
    support: dict[tuple[str, str], int] = {}
    for row in rows:
        forcing = str(row["climate_forcing"])
        scenario = str(row["climate_scenario"])
        support[(forcing, scenario)] = int(row["common_finite_grid_cells"])
        for model_row in row["models"]:
            model = str(model_row["model"])
            key = (forcing, scenario, model)
            if key in indexed:
                raise ValueError("scenario matrix duplicates a forcing/scenario/model row")
            changes = model_row["relative_change_from_reference"]
            if set(changes) != PERIODS or not all(math.isfinite(float(value)) for value in changes.values()):
                raise ValueError("scenario matrix has invalid reporting-period changes")
            reference = float(model_row["reference_mean_density_g_m2"])
            if not math.isfinite(reference) or reference <= 0:
                raise ValueError("scenario matrix reference density must be finite and positive")
            indexed[key] = model_row

    expected = {
        (forcing, scenario, model)
        for forcing in FORCINGS for scenario in SCENARIOS for model in MODELS
    }
    if set(indexed) != expected:
        raise ValueError("scenario matrix forcing/scenario/model factorial is incomplete")

    for forcing in FORCINGS:
        if support[(forcing, "ssp126")] != support[(forcing, "ssp585")]:
            raise ValueError("common support differs across scenarios within a forcing")
        for model in MODELS:
            low = float(indexed[(forcing, "ssp126", model)]["reference_mean_density_g_m2"])
            high = float(indexed[(forcing, "ssp585", model)]["reference_mean_density_g_m2"])
            if low != high:
                raise ValueError("historical reference differs across scenarios within a forcing/model")

    negative_counts: dict[str, int] = {}
    stronger_high_counts: dict[str, int] = {}
    for period in sorted(PERIODS):
        negative_counts[period] = sum(
            float(row["relative_change_from_reference"][period]) < 0
            for row in indexed.values()
        )
        stronger_high_counts[period] = sum(
            float(indexed[(forcing, "ssp585", model)]["relative_change_from_reference"][period])
            < float(indexed[(forcing, "ssp126", model)]["relative_change_from_reference"][period])
            for forcing in FORCINGS for model in MODELS
        )
    return {
        "comparison_unit": "within_climate_forcing_and_ecosystem_model_relative_change_only",
        "trajectory_count": len(indexed),
        "negative_change_counts_out_of_8": negative_counts,
        "ssp585_more_negative_than_ssp126_counts_out_of_4": stronger_high_counts,
        "absolute_model_levels_averaged": False,
        "inference_boundary": (
            "Sign agreement is a structural biophysical scenario diagnostic, not an "
            "observed-catch calibration, matched pulse, welfare effect, damage, or SCC input."
        ),
    }


def main() -> None:
    rows = []
    seen = set()
    for relative in INPUTS:
        path = ROOT / relative
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("result") != "passed" or result.get("matched_co2_pulse") is not False:
            raise ValueError("scenario result is not a passed non-pulse diagnostic")
        if result.get("welfare_output") is not False or result.get("scc_authorized") is not False:
            raise ValueError("scenario result opens welfare or SCC use")
        key = (result["climate_forcing"], result["climate_scenario"])
        if key in seen:
            raise ValueError("scenario matrix duplicates a forcing/scenario pair")
        seen.add(key)
        models = []
        for model in result["models"]:
            periods = {
                row["id"]: float(row["relative_change_from_reference"])
                for row in model["reporting_periods"]
            }
            if set(periods) != PERIODS:
                raise ValueError("scenario result reporting periods changed")
            models.append({
                "model": model["model"],
                "reference_mean_density_g_m2": float(model["reference_mean_density_g_m2"]),
                "relative_change_from_reference": periods,
            })
        if {row["model"] for row in models} != MODELS:
            raise ValueError("scenario result ecosystem-model set changed")
        rows.append({
            "climate_forcing": key[0],
            "climate_scenario": key[1],
            "common_finite_grid_cells": int(result["common_finite_grid_cells"]),
            "models": models,
            "source_result": {"path": relative, "sha256": sha256(path)},
        })
    if seen != {(forcing, scenario) for forcing in FORCINGS for scenario in SCENARIOS}:
        raise ValueError("scenario matrix is incomplete")
    summary = robustness_summary(rows)
    output = {
        "schema": "fishmip_scenario_benchmark_matrix_v1",
        "status": "validated_biophysical_scenario_diagnostic_only",
        "benchmarks": sorted(rows, key=lambda row: (row["climate_forcing"], row["climate_scenario"])),
        "robustness_summary": summary,
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256(Path(__file__)),
        },
        "observed_catch": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Within-model scenario catch-density changes are not observed catch, welfare, "
            "marginal CO2-pulse damages, or SCC. Absolute model levels are not averaged."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(OUT.suffix + ".partial")
    temporary.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(OUT)
    print(f"wrote compact {len(rows)}-benchmark FishMIP matrix to {OUT}")


if __name__ == "__main__":
    main()
