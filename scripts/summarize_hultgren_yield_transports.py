#!/usr/bin/env python3
"""Summarize named-ESM published-response transports without probability weights."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = [
    "joint_climate", "precipitation_all_income_support", "temperature_all_income_support",
    "precipitation_quantity_reference_scaling", "precipitation_distribution_residual",
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


def summarize(records: list[dict]) -> dict:
    def mean(record: dict) -> float:
        return record.get("weighted_mean_delta_log_yield", record.get("area_weighted_mean_delta_log_yield"))

    values = np.asarray([mean(record) for record in records], dtype=np.float64)
    models = [record["climate_model"] for record in records]
    require(len(models) == len(set(models)), "duplicate climate model")
    mean_log = float(values.mean())
    return {
        "named_model_results": [
            {
                "climate_model": record["climate_model"],
                "weighted_mean_delta_log_yield": mean(record),
                "percent_change_from_mean_log": 100.0 * math.expm1(mean(record)),
                "coefficient_only_standard_error_log_points": record["coefficient_only_standard_error_log_points"],
            }
            for record in records
        ],
        "equal_model_mean_delta_log_yield": mean_log,
        "percent_change_from_equal_model_mean_log": 100.0 * math.expm1(mean_log),
        "named_model_minimum_delta_log_yield": float(values.min()),
        "named_model_maximum_delta_log_yield": float(values.max()),
        "models_negative": int(np.count_nonzero(values < 0.0)),
        "models_positive": int(np.count_nonzero(values > 0.0)),
        "models_zero": int(np.count_nonzero(values == 0.0)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    loaded = []
    for path in args.input:
        value = json.loads(path.read_text(encoding="utf-8"))
        require(value["status"] == "preliminary_published_coefficient_transport_not_causal_damage_or_scc", "input status failed")
        require(value["climate_contrast"]["direction"] == "comparison_minus_reference", "contrast direction differs")
        loaded.append((path, value))
    reference = {(value["climate_contrast"]["reference"], value["climate_contrast"]["comparison"]) for _, value in loaded}
    require(len(reference) == 1, "scenario labels differ")
    models = sorted({value["climate_contrast"]["climate_model"] for _, value in loaded})
    support_labels = sorted({value["support"]["moderator_support_selection"] for _, value in loaded})
    weight_labels = {value["support"].get("analysis_weight_label", "fixed MIRCA harvested area") for _, value in loaded}
    weight_units = {value["support"].get("analysis_weight_unit", "ha") for _, value in loaded}
    require(len(weight_labels) == 1 and len(weight_units) == 1, "analysis weighting differs")
    require(len(loaded) == len(models) * len(support_labels), "incomplete model-by-support matrix")
    output_support = {}
    for support in support_labels:
        subset = [value for _, value in loaded if value["support"]["moderator_support_selection"] == support]
        require(sorted(value["climate_contrast"]["climate_model"] for value in subset) == models, "model support differs")
        output_support[support] = {}
        for scenario in ("fixed", "trend", "upper"):
            output_support[support][scenario] = {}
            for component in COMPONENTS:
                records = []
                for value in subset:
                    pooled = value.get("pooled_weighted", value.get("pooled_area_year_weighted"))
                    record = dict(pooled[scenario][component])
                    record["climate_model"] = value["climate_contrast"]["climate_model"]
                    records.append(record)
                output_support[support][scenario][component] = summarize(records)
    result = {
        "schema": "hultgren_named_esm_yield_transport_summary/v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "named_model_transport_summary_not_probability_damage_or_scc",
        "climate_models": models,
        "scenario_contrast": {"reference": next(iter(reference))[0], "comparison": next(iter(reference))[1]},
        "analysis_weighting": {"label": next(iter(weight_labels)), "unit": next(iter(weight_units))},
        "sources": [{"path": str(path), "sha256": digest(path)} for path, _ in loaded],
        "support_sensitivities": output_support,
        "aggregation": "simple unweighted mean of named-model mean log-yield responses; min--max and sign counts are descriptive, not uncertainty intervals or probabilities",
        "uncertainty": "model-specific standard errors propagate the common published coefficient covariance only and are not pooled across climate models",
        "claim_gates": {"named_model_summary_complete": True, "climate_probability_distribution": False, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "models": models, "fixed_full": output_support.get("full", {}).get("fixed")}, indent=2))


if __name__ == "__main__":
    main()
