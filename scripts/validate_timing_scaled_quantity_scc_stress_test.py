#!/usr/bin/env python3
"""Independent arithmetic and claim-gate check for the timing scale test."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    sources = result["sources"]
    quantity_path = Path(sources["quantity_scc"]["path"])
    country_path = Path(sources["country_timing"]["path"])
    gate_path = Path(sources["timing_gate"]["path"])
    quantity = json.loads(quantity_path.read_text())
    country = json.loads(country_path.read_text())
    gate = json.loads(gate_path.read_text())
    central = float(quantity["summary"]["2.0%"]["fixed"]["uncapped"]["mean_usd2020_per_tco2"])
    components = country["equal_model_global_log_yield_components"]
    ratio = float(components["timing_distribution"] / components["quantity"])
    qpoints = {row["climate_model"]: float(row["delta_log_yield"]) for row in gate["components"]["quantity_reference"]["points"]}
    tpoints = {row["climate_model"]: float(row["delta_log_yield"]) for row in gate["components"]["timing_distribution_increment"]["points"]}
    combined = [central * (1.0 + tpoints[model] / qpoints[model]) for model in sorted(qpoints)]
    tolerance = 1e-14
    checks = {
        "source_hashes": all(digest(Path(record["path"])) == record["sha256"] for record in sources.values()),
        "central_quantity": abs(central - result["validated_quantity_benchmark_usd2020_per_tco2"]) <= tolerance,
        "pooled_ratio": abs(ratio - result["pooled_production_weighted_endpoint_ratio"]) <= tolerance,
        "pooled_increment": abs(central * ratio - result["pooled_mechanical_timing_increment_usd2020_per_tco2"]) <= tolerance,
        "pooled_combined": abs(central * (1.0 + ratio) - result["pooled_mechanical_combined_usd2020_per_tco2"]) <= tolerance,
        "model_range": max(abs(actual - expected) for actual, expected in zip([min(combined), max(combined)], result["five_endpoint_mechanical_combined_range_usd2020_per_tco2"], strict=True)) <= tolerance,
        "claim_gates": result["claim_gates"] == {"validated_quantity_scc": True, "timing_scc": False, "full_precipitation_scc": False, "causal_timing_attribution": False},
    }
    validation = {
        "schema": "timing_scaled_quantity_scc_stress_test_validation/v1",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "passed_checks": sum(checks.values()),
        "total_checks": len(checks),
        "result": {"path": str(args.result), "sha256": digest(args.result)},
        "validator_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(validation, indent=2, allow_nan=False) + "\n")
    if validation["status"] != "passed":
        raise SystemExit("timing SCC scale sensitivity validation failed")


if __name__ == "__main__":
    main()
