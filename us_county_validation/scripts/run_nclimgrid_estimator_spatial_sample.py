#!/usr/bin/env python3
"""Run the preregistered nine-county nClimGrid estimator comparison."""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

from compare_nclimgrid_county_average_estimators import compare, sha256


COUNTIES = ["01001", "05001", "06019", "16019", "18113", "19003", "20111", "21001", "31039"]
VARIABLES = ["PRCP", "TAVG", "TMIN", "TMAX"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def run(contract_path: Path, root: Path) -> dict[str, object]:
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    require(contract.get("schema") == "us_nclimgrid_estimator_spatial_sample_contract_v1", "contract schema changed")
    require(contract.get("year") == 2019 and contract.get("month") == 6, "registered month changed")
    require(contract.get("county_geoids") == COUNTIES, "registered county sample changed")
    require(len({county[:2] for county in COUNTIES}) == contract.get("minimum_unique_state_fips") == 9, "state dispersion gate changed")
    require(contract.get("variables") == VARIABLES, "variable set changed")
    validation = contract.get("validation", {})
    for gate in ("exact_county_order_required", "complete_official_support_required", "complete_daily_month_required", "registered_polygon_weights_required"):
        require(validation.get(gate) is True, f"required gate changed: {gate}")
    for gate in ("outcomes_read", "estimator_equivalence_threshold_defined", "registered_polygon_route_replaced", "relationship_estimation_authorized", "damage_or_scc_authorized"):
        require(validation.get(gate) is False, f"closed gate changed: {gate}")
    inputs = contract.get("inputs", {})
    paths = {name: root / str(inputs[name]) for name in ("grid", "prcp", "tavg", "tmin", "tmax", "version", "state_crosswalk")}
    weights = [root / str(inputs["weight_root"]) / f"county_geoid={county}" / "weights.parquet" for county in COUNTIES]
    for path in [*paths.values(), *weights]:
        require(path.is_file(), f"registered input is missing: {path}")
    result = compare(
        paths["grid"],
        {variable: paths[variable.lower()] for variable in VARIABLES},
        paths["version"],
        paths["state_crosswalk"],
        weights,
    )
    require(result["counties"] == sorted(COUNTIES), "comparison county output changed")
    require(len(result["results"]) == len(COUNTIES) * len(VARIABLES), "comparison product is incomplete")
    result["schema"] = "us_nclimgrid_estimator_spatial_sample_audit_v1"
    result["status"] = "validated_nine_county_measurement_sensitivity_not_estimator_equivalence"
    result["contract"] = {
        "path": contract_path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": sha256(contract_path),
        "selection_rule": contract["selection_rule"],
    }
    result["implementation"] = {
        "path": Path(__file__).resolve().relative_to(root.resolve()).as_posix(),
        "sha256": sha256(Path(__file__).resolve()),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.contract.resolve(), args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("nClimGrid nine-county estimator spatial sample passed")


if __name__ == "__main__":
    main()
