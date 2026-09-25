#!/usr/bin/env python3
"""Independently validate the compact country timing/quantity summary."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


COMPONENTS = ("net", "quantity", "timing_distribution")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def close(left: float, right: float, tolerance: float = 2e-12) -> bool:
    return abs(left - right) <= tolerance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country-input", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.receipt.read_text())
    rows = list(csv.DictReader(args.country_input.open(newline="")))
    by_country: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_country[row["country_code"]].append(row)
    checks = {
        "source_status": source["status"] == "scenario_heterogeneity_diagnostic_not_damage_or_scc",
        "country_csv_hash": digest(args.country_input) == source["output"]["sha256"],
        "row_count": len(rows) == source["output"]["rows"],
        "country_count": len(by_country) == source["country_count"],
        "balanced_five_model_support": all(len(values) == 5 for values in by_country.values()),
    }
    country_means = {}
    for country, values in by_country.items():
        country_means[country] = {
            component: sum(float(row[f"global_{component}_contribution"]) for row in values) / 5.0
            for component in COMPONENTS
        }
    checks["country_decomposition"] = all(
        close(values["net"], values["quantity"] + values["timing_distribution"])
        for values in country_means.values()
    )
    reconstructed = {
        component: sum(values[component] for values in country_means.values())
        for component in COMPONENTS
    }
    checks["global_components"] = all(
        close(reconstructed[component], source["equal_model_global_log_yield_components"][component])
        for component in COMPONENTS
    )
    negative = sum(values["net"] < 0.0 for values in country_means.values())
    positive = sum(values["net"] > 0.0 for values in country_means.values())
    checks["winner_loser_counts"] = (
        negative == source["countries"]["mean_net_negative"]
        and positive == source["countries"]["mean_net_positive"]
    )
    checks["claim_gates_closed"] = (
        source["claim_gates"]["country_scenario_heterogeneity"] is True
        and source["claim_gates"]["causal_country_damage"] is False
        and source["claim_gates"]["timing_marginal_scc"] is False
        and source["claim_gates"]["total_precipitation_scc"] is False
    )
    result = {
        "schema": "hultgren_timing_country_heterogeneity_validation/v1",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "passed_checks": sum(checks.values()),
        "total_checks": len(checks),
        "reconstructed_equal_model_global_log_yield_components": reconstructed,
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "country_input": {"path": str(args.country_input), "sha256": digest(args.country_input)},
        "validator_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if result["status"] != "passed":
        raise SystemExit("country heterogeneity validation failed")


if __name__ == "__main__":
    main()
