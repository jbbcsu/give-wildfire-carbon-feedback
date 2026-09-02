#!/usr/bin/env python3
"""Aggregate checksum-bound county-estimator comparisons across fixed months."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


COUNTIES = ["06019", "31039"]
VARIABLES = ["PRCP", "TAVG", "TMIN", "TMAX"]
MONTHS = [(1990, 4), (2000, 2), (2000, 7), (2012, 7), (2019, 1), (2019, 6), (2019, 12)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def audit(paths: list[Path]) -> dict[str, object]:
    require(len(paths) == len(MONTHS), "comparison receipt count changed")
    inputs = []
    rows = []
    seen_months = set()
    for path in paths:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        require(receipt.get("schema") == "us_nclimgrid_county_average_estimator_comparison_v1", "comparison schema changed")
        require(receipt.get("status") == "validated_measurement_comparison_not_estimator_equivalence", "comparison status changed")
        require(receipt.get("counties") == COUNTIES, "county set or order changed")
        require(receipt.get("variables") == VARIABLES, "variable set or order changed")
        require(receipt.get("official_counties_per_variable") == 3107, "official county support changed")
        require(receipt.get("estimators_declared_equivalent") is False, "an input declared estimator equivalence")
        require(receipt.get("registered_polygon_route_replaced") is False, "an input replaced the registered polygon route")
        month = (int(receipt["year"]), int(receipt["month"]))
        require(month not in seen_months, "comparison month is duplicated")
        seen_months.add(month)
        product = {(str(row["county_geoid"]), str(row["variable"])) for row in receipt["results"]}
        require(product == {(county, variable) for county in COUNTIES for variable in VARIABLES}, "county-variable product is incomplete")
        for row in receipt["results"]:
            require(int(row["days"]) in (28, 29, 30, 31), "day count is invalid")
            require(float(row["maximum_absolute_difference"]) >= 0, "absolute difference is negative")
            require(float(row["root_mean_squared_difference"]) >= 0, "RMSE is negative")
            correlation = row["pearson_correlation"]
            if correlation is None:
                require(float(row["maximum_absolute_difference"]) == 0 and float(row["root_mean_squared_difference"]) == 0, "undefined correlation is not an exact constant match")
            else:
                require(-1 <= float(correlation) <= 1, "correlation is invalid")
            copy = dict(row)
            copy["year"], copy["month"] = month
            rows.append(copy)
        inputs.append({"path": path.as_posix(), "sha256": sha256(path), "year": month[0], "month": month[1]})
    require(seen_months == set(MONTHS), "fixed comparison-month set changed")

    summaries = []
    for county in COUNTIES:
        for variable in VARIABLES:
            subset = [row for row in rows if row["county_geoid"] == county and row["variable"] == variable]
            correlations = [float(row["pearson_correlation"]) for row in subset if row["pearson_correlation"] is not None]
            maximums = [float(row["maximum_absolute_difference"]) for row in subset]
            rmses = [float(row["root_mean_squared_difference"]) for row in subset]
            signs = {0 if abs(float(row["mean_difference"])) <= 1e-15 else 1 if float(row["mean_difference"]) > 0 else -1 for row in subset}
            summary = {
                "county_geoid": county,
                "variable": variable,
                "months": len(subset),
                "minimum_pearson_correlation": min(correlations),
                "undefined_correlation_exact_constant_matches": sum(row["pearson_correlation"] is None for row in subset),
                "maximum_absolute_daily_difference": max(maximums),
                "maximum_daily_rmse": max(rmses),
                "mean_difference_signs": sorted(signs),
                "mean_difference_sign_stable": len(signs) == 1,
            }
            if variable == "PRCP":
                summary["maximum_absolute_monthly_total_difference"] = max(abs(float(row["monthly_total_difference"])) for row in subset)
            summaries.append(summary)

    return {
        "schema": "us_nclimgrid_county_average_estimator_comparison_series_v1",
        "status": "validated_bounded_temporal_measurement_sensitivity_not_estimator_equivalence",
        "inputs": inputs,
        "fixed_months": [{"year": year, "month": month} for year, month in MONTHS],
        "counties": COUNTIES,
        "variables": VARIABLES,
        "comparisons": len(rows),
        "summaries": summaries,
        "minimum_correlation_all_defined_comparisons": min(float(row["pearson_correlation"]) for row in rows if row["pearson_correlation"] is not None),
        "undefined_correlation_exact_constant_matches": sum(row["pearson_correlation"] is None for row in rows),
        "nonzero_difference_comparisons": sum(float(row["maximum_absolute_difference"]) > 0 for row in rows),
        "estimators_declared_equivalent": False,
        "registered_polygon_route_replaced": False,
        "relationship_estimated": False,
        "response_damage_or_scc_authorized": False,
        "disclaimer": "Seven selected months in two counties diagnose temporal measurement sensitivity only; they do not establish national estimator equivalence or a climate-yield response.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipts", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.receipts)
    result["implementation"] = {"path": Path(__file__).as_posix(), "sha256": sha256(Path(__file__))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"nClimGrid estimator series: {result['comparisons']} comparisons, minimum defined r={result['minimum_correlation_all_defined_comparisons']:.6f}")


if __name__ == "__main__":
    main()
