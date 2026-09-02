#!/usr/bin/env python3
"""Run a preregistered nine-county nClimGrid estimator comparison."""
from __future__ import annotations

import argparse
import json
import math
import tomllib
from pathlib import Path

from compare_nclimgrid_county_average_estimators import compare, sha256


COUNTIES = ["01001", "05001", "06019", "16019", "18113", "19003", "20111", "21001", "31039"]
MONTH_SETS = {
    "us_nclimgrid_estimator_spatiotemporal_sample_contract_v1": [1, 6, 12],
    "us_nclimgrid_estimator_spatiotemporal_expansion_contract_v2": [1, 4, 6, 9, 12],
}
VARIABLES = ["PRCP", "TAVG", "TMIN", "TMAX"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def render(template: str, year: int, month: int, variable: str = "") -> str:
    return template.format(year=year, month=month, variable_lower=variable.lower())


def run(contract_path: Path, root: Path) -> dict[str, object]:
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    schema = str(contract.get("schema"))
    require(schema in MONTH_SETS, "contract schema changed")
    months = MONTH_SETS[schema]
    require(contract.get("year") == 2019 and contract.get("months") == months, "registered months changed")
    if schema.endswith("_v2"):
        require(contract.get("new_months") == [4, 9], "registered new months changed")
    require(contract.get("county_geoids") == COUNTIES, "registered county sample changed")
    require(len({county[:2] for county in COUNTIES}) == contract.get("minimum_unique_state_fips") == 9, "state dispersion gate changed")
    require(contract.get("variables") == VARIABLES, "variable set changed")
    validation = contract.get("validation", {})
    for gate in ("exact_county_order_required", "complete_official_support_required", "complete_daily_month_required", "registered_polygon_weights_required", "exact_month_order_required"):
        require(validation.get(gate) is True, f"required gate changed: {gate}")
    for gate in ("outcomes_read", "estimator_equivalence_threshold_defined", "registered_polygon_route_replaced", "relationship_estimation_authorized", "damage_or_scc_authorized"):
        require(validation.get(gate) is False, f"closed gate changed: {gate}")

    inputs = contract.get("inputs", {})
    crosswalk = root / str(inputs["state_crosswalk"])
    weights = [root / str(inputs["weight_root"]) / f"county_geoid={county}" / "weights.parquet" for county in COUNTIES]
    for path in [crosswalk, *weights]:
        require(path.is_file(), f"registered input is missing: {path}")

    monthly: list[dict] = []
    flat_results: list[dict] = []
    for month in months:
        grid = root / render(str(inputs["grid_template"]), 2019, month)
        version = root / render(str(inputs["version_template"]), 2019, month)
        sources = {variable: root / render(str(inputs["county_average_template"]), 2019, month, variable) for variable in VARIABLES}
        for path in [grid, version, *sources.values()]:
            require(path.is_file(), f"registered input is missing: {path}")
        result = compare(grid, sources, version, crosswalk, weights)
        require(result["counties"] == sorted(COUNTIES), "comparison county output changed")
        require(result["month"] == month and result["year"] == 2019, "comparison month identity changed")
        require(len(result["results"]) == len(COUNTIES) * len(VARIABLES), "comparison product is incomplete")
        monthly.append(result)
        flat_results.extend({"month": month, **row} for row in result["results"])

    correlations = [float(row["pearson_correlation"]) for row in flat_results if row["pearson_correlation"] is not None and math.isfinite(float(row["pearson_correlation"]))]
    rain = [row for row in flat_results if row["variable"] == "PRCP"]
    return {
        "schema": "us_nclimgrid_estimator_spatiotemporal_sample_audit_v1",
        "status": f"validated_fixed_nine_county_{len(months)}_month_measurement_sensitivity_not_estimator_equivalence",
        "year": 2019,
        "months": months,
        "counties": COUNTIES,
        "variables": VARIABLES,
        "result_cells": len(flat_results),
        "minimum_defined_daily_correlation": min(correlations),
        "maximum_absolute_daily_difference": max(float(row["maximum_absolute_difference"]) for row in flat_results),
        "rainfall_monthly_total_difference_minimum": min(float(row["monthly_total_difference"]) for row in rain),
        "rainfall_monthly_total_difference_maximum": max(float(row["monthly_total_difference"]) for row in rain),
        "nonzero_maximum_difference_cells": sum(float(row["maximum_absolute_difference"]) > 0 for row in flat_results),
        "monthly_audits": monthly,
        "contract": {"path": contract_path.resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(contract_path), "selection_rule": contract["selection_rule"]},
        "implementation": {"path": Path(__file__).resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(Path(__file__))},
        "estimators_declared_equivalent": False,
        "registered_polygon_route_replaced": False,
        "relationship_estimated": False,
        "response_damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.contract.resolve(), args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("nClimGrid fixed spatiotemporal estimator sample passed")


if __name__ == "__main__":
    main()
