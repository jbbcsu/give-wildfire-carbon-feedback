#!/usr/bin/env python3
"""Validate the fixed five-month nClimGrid estimator expansion before acquisition."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


COUNTIES = ["01001", "05001", "06019", "16019", "18113", "19003", "20111", "21001", "31039"]
MONTHS = [1, 4, 6, 9, 12]
VARIABLES = ["PRCP", "TAVG", "TMIN", "TMAX"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(path: Path) -> dict[str, object]:
    contract = tomllib.loads(path.read_text(encoding="utf-8"))
    require(contract.get("schema") == "us_nclimgrid_estimator_spatiotemporal_expansion_contract_v2", "schema changed")
    require(contract.get("year") == 2019 and contract.get("months") == MONTHS, "fixed months changed")
    require(contract.get("new_months") == [4, 9], "new months changed")
    require(contract.get("county_geoids") == COUNTIES, "county sample changed")
    require(contract.get("variables") == VARIABLES, "variable set changed")
    require(len({county[:2] for county in COUNTIES}) == contract.get("minimum_unique_state_fips") == 9, "state dispersion changed")
    inputs = contract.get("inputs", {})
    require(str(inputs.get("county_average_url_template", "")).startswith("https://www.ncei.noaa.gov/data/nclimgrid-daily/"), "official series URL changed")
    require(str(inputs.get("version_url_template", "")).startswith("https://www.ncei.noaa.gov/data/nclimgrid-daily/"), "official version URL changed")
    validation = contract.get("validation", {})
    for gate in ("exact_county_order_required", "complete_official_support_required", "complete_daily_month_required", "registered_polygon_weights_required", "exact_month_order_required"):
        require(validation.get(gate) is True, f"required gate changed: {gate}")
    for gate in ("outcomes_read", "estimator_equivalence_threshold_defined", "registered_polygon_route_replaced", "relationship_estimation_authorized", "damage_or_scc_authorized"):
        require(validation.get(gate) is False, f"closed gate changed: {gate}")
    planned = []
    for month in contract["new_months"]:
        for variable in VARIABLES:
            planned.append(inputs["county_average_url_template"].format(year=2019, month=month, variable_lower=variable.lower()))
        planned.append(inputs["version_url_template"].format(year=2019, month=month))
    return {
        "schema": "us_nclimgrid_estimator_spatiotemporal_expansion_preregistration_v2",
        "status": "preregistered_before_official_series_acquisition_or_comparison",
        "contract_sha256": sha256(path),
        "implementation_sha256": sha256(Path(__file__)),
        "months": MONTHS,
        "new_months": [4, 9],
        "counties": COUNTIES,
        "planned_official_urls": planned,
        "outcomes_read": False,
        "estimators_declared_equivalent": False,
        "response_damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.contract)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("nClimGrid fixed five-month estimator expansion preregistration passed")


if __name__ == "__main__":
    main()
