#!/usr/bin/env python3
"""Audit structural FishMIP contrasts in the frozen scenario matrix.

The audit compares exact within-cell relative changes. It does not average
absolute catch-density levels, assign probabilities to models, or create a
matched pulse, welfare estimate, damage, or SCC input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


FORCINGS = ("gfdl-esm4", "ipsl-cm6a-lr")
SCENARIOS = ("ssp126", "ssp585")
MODELS = ("boats", "ecoocean")
PERIODS = ("near", "mid", "late")
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def index_matrix(payload: dict[str, object]) -> dict[tuple[str, str, str, str], float]:
    require(payload.get("schema") == "fishmip_scenario_benchmark_matrix_v1", "matrix schema changed")
    require(payload.get("status") == "validated_biophysical_scenario_diagnostic_only", "matrix status changed")
    for gate in ("observed_catch", "matched_co2_pulse", "welfare_estimated", "damage_estimated", "scc_authorized"):
        require(payload.get(gate) is False, f"matrix improperly opens {gate}")
    rows = payload.get("benchmarks")
    require(isinstance(rows, list), "matrix benchmarks are missing")
    indexed: dict[tuple[str, str, str, str], float] = {}
    for row in rows:
        forcing = str(row["climate_forcing"])
        scenario = str(row["climate_scenario"])
        for model_row in row["models"]:
            model = str(model_row["model"])
            changes = model_row["relative_change_from_reference"]
            require(set(changes) == set(PERIODS), "matrix reporting periods changed")
            for period in PERIODS:
                key = (forcing, scenario, model, period)
                require(key not in indexed, "matrix duplicates a factorial cell")
                value = float(changes[period])
                require(math.isfinite(value), "matrix contains a nonfinite relative change")
                indexed[key] = value
    expected = {
        (forcing, scenario, model, period)
        for forcing in FORCINGS
        for scenario in SCENARIOS
        for model in MODELS
        for period in PERIODS
    }
    require(set(indexed) == expected, "matrix lacks the exact forcing/scenario/model/period factorial")
    return indexed


def evaluate(payload: dict[str, object]) -> dict[str, object]:
    values = index_matrix(payload)
    rows: list[dict[str, object]] = []
    dominance_count = 0
    for scenario in SCENARIOS:
        for period in PERIODS:
            ecosystem = {
                forcing: values[(forcing, scenario, "ecoocean", period)]
                - values[(forcing, scenario, "boats", period)]
                for forcing in FORCINGS
            }
            forcing = {
                model: values[("ipsl-cm6a-lr", scenario, model, period)]
                - values[("gfdl-esm4", scenario, model, period)]
                for model in MODELS
            }
            ecosystem_abs = [abs(value) for value in ecosystem.values()]
            forcing_abs = [abs(value) for value in forcing.values()]
            ecosystem_dominates = min(ecosystem_abs) > max(forcing_abs)
            dominance_count += int(ecosystem_dominates)
            rows.append({
                "scenario": scenario,
                "period": period,
                "ecoocean_minus_boats_by_forcing": ecosystem,
                "ipsl_minus_gfdl_by_ecosystem_model": forcing,
                "difference_in_differences": forcing["ecoocean"] - forcing["boats"],
                "absolute_ecosystem_model_contrast_range": [min(ecosystem_abs), max(ecosystem_abs)],
                "absolute_climate_forcing_contrast_range": [min(forcing_abs), max(forcing_abs)],
                "both_ecosystem_model_contrasts_exceed_both_climate_forcing_contrasts": ecosystem_dominates,
            })
    require(len(rows) == len(SCENARIOS) * len(PERIODS), "factorial summary is incomplete")
    return {
        "schema": "fishmip_factorial_relative_change_sensitivity_v1",
        "status": "validated_biophysical_structural_sensitivity_only",
        "comparison_unit": "relative_change_from_each_model_and_forcing_specific_historical_reference",
        "rows": rows,
        "ecosystem_contrast_dominance_cells": dominance_count,
        "scenario_period_cells": len(rows),
        "absolute_model_levels_averaged": False,
        "model_probabilities_assigned": False,
        "observed_catch": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Exact structural contrasts in modelled scenario catch-density changes are not uncertainty "
            "probabilities, observed catch, a marginal carbon-pulse response, welfare, damages, or SCC evidence."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.matrix.read_text(encoding="utf-8"))
    result = evaluate(payload)
    matrix_path = args.matrix.resolve()
    implementation_path = Path(__file__).resolve()
    result["source_matrix"] = {"path": str(matrix_path.relative_to(ROOT)), "sha256": sha256(matrix_path)}
    result["implementation"] = {
        "path": str(implementation_path.relative_to(ROOT)),
        "sha256": sha256(implementation_path),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(
        "FishMIP factorial sensitivity passed: "
        f"ecosystem contrasts dominate in {result['ecosystem_contrast_dominance_cells']}/"
        f"{result['scenario_period_cells']} scenario-period cells"
    )


if __name__ == "__main__":
    main()
