#!/usr/bin/env python3
"""Mechanical timing-scaled sensitivity around the validated quantity SCC."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quantity-scc", type=Path, required=True)
    parser.add_argument("--country-timing", type=Path, required=True)
    parser.add_argument("--timing-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    quantity = json.loads(args.quantity_scc.read_text())
    country = json.loads(args.country_timing.read_text())
    gate = json.loads(args.timing_gate.read_text())
    central = float(quantity["summary"]["2.0%"]["fixed"]["uncapped"]["mean_usd2020_per_tco2"])
    components = country["equal_model_global_log_yield_components"]
    pooled_ratio = float(components["timing_distribution"] / components["quantity"])
    quantity_points = {
        row["climate_model"]: float(row["delta_log_yield"])
        for row in gate["components"]["quantity_reference"]["points"]
    }
    timing_points = {
        row["climate_model"]: float(row["delta_log_yield"])
        for row in gate["components"]["timing_distribution_increment"]["points"]
    }
    if set(quantity_points) != set(timing_points):
        raise ValueError("quantity/timing climate-model support differs")
    model_sensitivities = []
    for model in sorted(quantity_points):
        ratio = timing_points[model] / quantity_points[model]
        model_sensitivities.append(
            {
                "climate_model": model,
                "endpoint_timing_to_quantity_ratio": ratio,
                "mechanical_timing_increment_usd2020_per_tco2": central * ratio,
                "mechanical_combined_usd2020_per_tco2": central * (1.0 + ratio),
            }
        )
    combined_values = [row["mechanical_combined_usd2020_per_tco2"] for row in model_sensitivities]
    result = {
        "schema": "timing_scaled_quantity_scc_stress_test/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "mechanical_nonpromoted_sensitivity_not_scc_estimate",
        "validated_quantity_benchmark_usd2020_per_tco2": central,
        "pooled_production_weighted_endpoint_ratio": pooled_ratio,
        "pooled_mechanical_timing_increment_usd2020_per_tco2": central * pooled_ratio,
        "pooled_mechanical_combined_usd2020_per_tco2": central * (1.0 + pooled_ratio),
        "five_endpoint_ratio_sensitivities": model_sensitivities,
        "five_endpoint_mechanical_combined_range_usd2020_per_tco2": [
            min(combined_values),
            max(combined_values),
        ],
        "assumption": "The late-century scenario timing-to-quantity log-yield ratio is imposed unchanged on every country, year, EPA climate pattern, market response, and marginal FAIR pulse contribution.",
        "claim_gates": {
            "validated_quantity_scc": True,
            "timing_scc": False,
            "full_precipitation_scc": False,
            "causal_timing_attribution": False,
        },
        "interpretation": [
            "This is a scale stress test around the quantity SCC, not a timing SCC estimate.",
            "Endpoint ratios are multi-forcing scenario responses and do not identify a transient marginal timing response.",
            "The five model-specific ratios are structural cases, not probability draws or an uncertainty interval.",
            "Drought, other crops, irrigation adaptation, trade, storage, and adaptation costs remain excluded.",
        ],
        "sources": {
            "quantity_scc": {"path": str(args.quantity_scc), "sha256": digest(args.quantity_scc)},
            "country_timing": {"path": str(args.country_timing), "sha256": digest(args.country_timing)},
            "timing_gate": {"path": str(args.timing_gate), "sha256": digest(args.timing_gate)},
        },
        "implementation": {"path": str(Path(__file__)), "sha256": digest(Path(__file__))},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "validated_quantity_benchmark_usd2020_per_tco2", "pooled_production_weighted_endpoint_ratio", "pooled_mechanical_timing_increment_usd2020_per_tco2", "pooled_mechanical_combined_usd2020_per_tco2", "five_endpoint_mechanical_combined_range_usd2020_per_tco2")}, indent=2))


if __name__ == "__main__":
    main()
