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
    pooled_key = "pooled_weighted" if "pooled_weighted" in result else "pooled_area_year_weighted"
    pooled_result = result[pooled_key]

    def fields(summary: dict) -> tuple[str, str, str]:
        if "weighted_mean_delta_log_yield" in summary:
            return "weight_sum", "weighted_mean_delta_log_yield", "weighted_mean_cell_exact_percent_change"
        return "area_or_area_year_weight_ha", "area_weighted_mean_delta_log_yield", "area_weighted_mean_cell_exact_percent_change"

    annual = result["annual"]
    require([row["harvest_year"] for row in annual] == list(range(2092, 2101)), "year support differs")
    for row in annual:
        fixed = row["adaptation"]["fixed"]["components"]
        _, mean_key, _ = fields(fixed["joint_climate"])
        close(fixed["joint_climate"][mean_key],
              fixed["precipitation_all_income_support"][mean_key]
              + fixed["temperature_all_income_support"][mean_key])
        close(fixed["precipitation_common_positive_support"][mean_key],
              fixed["precipitation_quantity_reference_scaling"][mean_key]
              + fixed["precipitation_distribution_residual"][mean_key])
        for scenario, scenario_record in row["adaptation"].items():
            require(0.0 < scenario_record["loss_remaining_effect_factor"] <= 1.0, "invalid loss factor")
            for component in COMPONENTS:
                summary = scenario_record["components"][component]
                _, mean_key, _ = fields(summary)
                close(summary["percent_change_from_mean_log"],
                      100.0 * math.expm1(summary[mean_key]))
        for component in COMPONENTS:
            _, mean_key, _ = fields(row["adaptation"]["fixed"]["components"][component])
            fixed_log = row["adaptation"]["fixed"]["components"][component][mean_key]
            trend_log = row["adaptation"]["trend"]["components"][component][mean_key]
            upper_log = row["adaptation"]["upper"]["components"][component][mean_key]
            require(fixed_log <= trend_log + 1e-12 <= upper_log + 2e-12, "loss-only adaptation is not monotone")

    for scenario, pooled in pooled_result.items():
        for component in COMPONENTS:
            summaries = [row["adaptation"][scenario]["components"][component] for row in annual]
            weight_key, mean_key, exact_key = fields(summaries[0])
            total_weight = sum(item[weight_key] for item in summaries)
            expected_log = sum(item[weight_key] * item[mean_key] for item in summaries) / total_weight
            expected_exact = sum(item[weight_key] * item[exact_key] for item in summaries) / total_weight
            close(pooled[component][weight_key], total_weight)
            close(pooled[component][mean_key], expected_log)
            close(pooled[component][exact_key], expected_exact)
            close(pooled[component]["percent_change_from_mean_log"], 100.0 * math.expm1(expected_log))
        if scenario == "fixed":
            _, mean_key, _ = fields(pooled["joint_climate"])
            close(pooled["joint_climate"][mean_key],
                  pooled["precipitation_all_income_support"][mean_key]
                  + pooled["temperature_all_income_support"][mean_key])
            close(pooled["precipitation_common_positive_support"][mean_key],
                  pooled["precipitation_quantity_reference_scaling"][mean_key]
                  + pooled["precipitation_distribution_residual"][mean_key])
    for component in COMPONENTS:
        _, mean_key, _ = fields(pooled_result["fixed"][component])
        fixed_log = pooled_result["fixed"][component][mean_key]
        trend_log = pooled_result["trend"][component][mean_key]
        upper_log = pooled_result["upper"][component][mean_key]
        require(fixed_log <= trend_log + 1e-12 <= upper_log + 2e-12, "pooled loss-only adaptation is not monotone")
    return {
        "path": str(path), "sha256": digest(path),
        "moderator_support_selection": result["support"]["moderator_support_selection"],
        "analysis_weight_label": result["support"].get("analysis_weight_label", "fixed MIRCA harvested area"),
        "analysis_weight_fraction": result["support"].get("analysis_weight_fraction_of_eligible", result["support"]["analysis_area_fraction_of_total"]),
        "years": len(annual), "adaptation_scenarios": sorted(pooled_result),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.receipt.exists(), "fresh receipt required")
    records = [validate(path) for path in args.input]
    support_set = {record["moderator_support_selection"] for record in records}
    require(support_set in ({"full"}, {"full", "author_minmax", "author_p01_p99"}), "support sensitivity set differs")
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
