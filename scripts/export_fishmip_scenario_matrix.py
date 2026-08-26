#!/usr/bin/env python3
"""Export a compact, tracked summary of validated FishMIP scenario diagnostics."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    "data/raw/fishmip/gfdl-esm4/scenario_benchmark_v1.json",
    "data/raw/fishmip/gfdl-esm4/scenario_benchmark_ssp585_v1.json",
    "data/raw/fishmip/ipsl-cm6a-lr/scenario_benchmark_ssp126_v1.json",
    "data/raw/fishmip/ipsl-cm6a-lr/scenario_benchmark_ssp585_v1.json",
)
OUT = ROOT / "data/provenance/fishmip_scenario_benchmark_matrix_20260826.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
            if set(periods) != {"near", "mid", "late"}:
                raise ValueError("scenario result reporting periods changed")
            models.append({
                "model": model["model"],
                "reference_mean_density_g_m2": float(model["reference_mean_density_g_m2"]),
                "relative_change_from_reference": periods,
            })
        if {row["model"] for row in models} != {"boats", "ecoocean"}:
            raise ValueError("scenario result ecosystem-model set changed")
        rows.append({
            "climate_forcing": key[0],
            "climate_scenario": key[1],
            "common_finite_grid_cells": int(result["common_finite_grid_cells"]),
            "models": models,
            "source_result": {"path": relative, "sha256": sha256(path)},
        })
    if seen != {
        ("gfdl-esm4", "ssp126"), ("gfdl-esm4", "ssp585"),
        ("ipsl-cm6a-lr", "ssp126"), ("ipsl-cm6a-lr", "ssp585"),
    }:
        raise ValueError("scenario matrix is incomplete")
    output = {
        "schema": "fishmip_scenario_benchmark_matrix_v1",
        "status": "validated_biophysical_scenario_diagnostic_only",
        "benchmarks": sorted(rows, key=lambda row: (row["climate_forcing"], row["climate_scenario"])),
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
