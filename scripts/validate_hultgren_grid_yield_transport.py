#!/usr/bin/env python3
"""Independently validate yield-transport summary and decomposition arithmetic."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = [
    "joint_climate", "precipitation_all_income_support", "temperature_all_income_support",
    "precipitation_common_positive_support", "precipitation_quantity_reference_scaling",
    "precipitation_distribution_residual",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(left: float, right: float, tolerance: float = 1e-10) -> None:
    require(abs(left - right) <= tolerance * max(1.0, abs(left), abs(right)), f"values differ: {left}, {right}")


def validate(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    require(result["status"] == "preliminary_published_coefficient_transport_not_causal_damage_or_scc", "status differs")
    annual = result["annual"]
    require([row["harvest_year"] for row in annual] == list(range(2092, 2101)), "year support differs")
    for row in annual:
        fixed = row["adaptation"]["fixed"]["components"]
        close(fixed["joint_climate"]["area_weighted_mean_delta_log_yield"],
              fixed["precipitation_all_income_support"]["area_weighted_mean_delta_log_yield"]
              + fixed["temperature_all_income_support"]["area_weighted_mean_delta_log_yield"])
        close(fixed["precipitation_common_positive_support"]["area_weighted_mean_delta_log_yield"],
              fixed["precipitation_quantity_reference_scaling"]["area_weighted_mean_delta_log_yield"]
              + fixed["precipitation_distribution_residual"]["area_weighted_mean_delta_log_yield"])
        for scenario, scenario_record in row["adaptation"].items():
            factor = scenario_record["remaining_effect_factor"]
            for component in COMPONENTS:
                summary = scenario_record["components"][component]
                close(summary["area_weighted_mean_delta_log_yield"],
                      fixed[component]["area_weighted_mean_delta_log_yield"] * factor)
                close(summary["percent_change_from_mean_log"],
                      100.0 * math.expm1(summary["area_weighted_mean_delta_log_yield"]))

    for scenario, pooled in result["pooled_area_year_weighted"].items():
        for component in COMPONENTS:
            summaries = [row["adaptation"][scenario]["components"][component] for row in annual]
            total_weight = sum(item["area_or_area_year_weight_ha"] for item in summaries)
            expected_log = sum(item["area_or_area_year_weight_ha"] * item["area_weighted_mean_delta_log_yield"] for item in summaries) / total_weight
            expected_exact = sum(item["area_or_area_year_weight_ha"] * item["area_weighted_mean_cell_exact_percent_change"] for item in summaries) / total_weight
            close(pooled[component]["area_or_area_year_weight_ha"], total_weight)
            close(pooled[component]["area_weighted_mean_delta_log_yield"], expected_log)
            close(pooled[component]["area_weighted_mean_cell_exact_percent_change"], expected_exact)
            close(pooled[component]["percent_change_from_mean_log"], 100.0 * math.expm1(expected_log))
        close(pooled["joint_climate"]["area_weighted_mean_delta_log_yield"],
              pooled["precipitation_all_income_support"]["area_weighted_mean_delta_log_yield"]
              + pooled["temperature_all_income_support"]["area_weighted_mean_delta_log_yield"])
        close(pooled["precipitation_common_positive_support"]["area_weighted_mean_delta_log_yield"],
              pooled["precipitation_quantity_reference_scaling"]["area_weighted_mean_delta_log_yield"]
              + pooled["precipitation_distribution_residual"]["area_weighted_mean_delta_log_yield"])
    return {
        "path": str(path), "sha256": digest(path),
        "moderator_support_selection": result["support"]["moderator_support_selection"],
        "analysis_area_fraction_of_total": result["support"]["analysis_area_fraction_of_total"],
        "years": len(annual), "adaptation_scenarios": sorted(result["pooled_area_year_weighted"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.receipt.exists(), "fresh receipt required")
    records = [validate(path) for path in args.input]
    require({record["moderator_support_selection"] for record in records} == {"full", "author_minmax", "author_p01_p99"}, "support sensitivity set differs")
    result = {
        "schema": "hultgren_grid_yield_transport_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "independent_summary_arithmetic_validation_passed",
        "inputs": records,
        "checks": {
            "annual_to_pooled_weighting": True, "log_to_percent_transformation": True,
            "adaptation_scaling": True, "joint_precipitation_temperature_additivity": True,
            "precipitation_quantity_distribution_additivity": True,
        },
        "interpretation": "validates stored aggregation and decomposition arithmetic, not causal identification, transport assumptions, monetization, or SCC",
        "claim_gates": {"summary_arithmetic_validated": True, "causal_damage_or_scc_validated": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
