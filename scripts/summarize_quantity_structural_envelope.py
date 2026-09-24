#!/usr/bin/env python3
"""Summarize the registered quantity-channel design without probabilistic claims."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PULSE = 0.000025
RATES = ["1.5%", "2.0%", "2.5%", "3.0%"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def statistics(values: pd.Series) -> dict[str, float | int]:
    return {
        "cells": int(len(values)),
        "mean_usd2020_per_tco2": float(values.mean()),
        "median_usd2020_per_tco2": float(values.median()),
        "p02_5_usd2020_per_tco2": float(values.quantile(0.025)),
        "p97_5_usd2020_per_tco2": float(values.quantile(0.975)),
        "minimum_usd2020_per_tco2": float(values.min()),
        "maximum_usd2020_per_tco2": float(values.max()),
        "negative_cells": int((values < 0).sum()),
        "positive_cells": int((values > 0).sum()),
        "zero_cells": int((values == 0).sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic-receipt", type=Path, required=True)
    parser.add_argument("--validation-receipt", type=Path, required=True)
    parser.add_argument("--paired-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    diagnostic = json.loads(args.diagnostic_receipt.read_text(encoding="utf-8"))
    validation = json.loads(args.validation_receipt.read_text(encoding="utf-8"))
    paired = json.loads(args.paired_receipt.read_text(encoding="utf-8"))
    require(diagnostic["schema"] == "epa_fair_hultgren_quantity_partial_scc_diagnostic/v1", "diagnostic receipt differs")
    require(validation["schema"] == "epa_fair_hultgren_quantity_partial_scc_diagnostic_validation/v1" and validation["status"] == "pass", "independent validation absent")
    require(paired["schema"] == "quantity_anchored_replacement_ensemble/v1" and paired["status"] == "paired_26_model_central_marginal_response_replacement_pass", "paired central ensemble absent")
    source = Path(diagnostic["output"]["path"])
    require(digest(source) == diagnostic["output"]["sha256"], "diagnostic hash differs")
    frame = pd.read_csv(source)
    require(len(frame) == 11_232, "full diagnostic support differs")
    keys = ["climate_model", "pulse_size_gtc", "adaptation", "tail_rule", "elasticity_id", "yield_to_supply_mapping", "discount_rate_label"]
    require(not frame.duplicated(keys).any(), "diagnostic keys are not unique")
    smallest = frame.loc[frame.pulse_size_gtc.eq(PULSE)].copy()
    require(len(smallest) == 26 * 3 * 2 * 3 * 2 * 4 == 3_744, "smallest-pulse design differs")
    require(sorted(smallest.discount_rate_label.unique(), key=RATES.index) == RATES, "discount schedules differ")

    value = "partial_scc_diagnostic_usd2020_per_tco2"
    overall = {label: statistics(smallest.loc[smallest.discount_rate_label.eq(label), value]) for label in RATES}
    dimension_means = {}
    for dimension in ["adaptation", "tail_rule", "elasticity_id", "yield_to_supply_mapping"]:
        dimension_means[dimension] = {}
        for (label, level), group in smallest.groupby(["discount_rate_label", dimension], sort=True):
            dimension_means[dimension].setdefault(label, {})[str(level)] = statistics(group[value])

    central = smallest.loc[
        smallest.adaptation.eq("fixed")
        & smallest.tail_rule.eq("uncapped")
        & smallest.elasticity_id.eq("hultgren_pair_010_004")
        & smallest.yield_to_supply_mapping.eq("horizontal_output")
    ]
    require(len(central) == 104, "central support differs")
    central_summary = {label: statistics(central.loc[central.discount_rate_label.eq(label), value]) for label in RATES}
    for label in RATES:
        require(abs(central_summary[label]["mean_usd2020_per_tco2"] - paired["summary"][label]["mean_usd2020_per_tco2"]) <= 1e-15, f"paired central mean differs for {label}")

    result = {
        "schema": "quantity_structural_sensitivity_envelope/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "registered_balanced_structural_design_summarized",
        "definition": "unweighted balanced design envelope across climate models and registered modeling choices; percentiles are design-cell quantiles, not probability intervals",
        "support": {"smallest_pulse_gtc": PULSE, "design_cells": len(smallest), "climate_models": 26, "adaptation_cases": 3, "tail_rules": 2, "elasticity_pairs": 3, "supply_mappings": 2, "discount_schedules": 4},
        "overall": overall,
        "central_paired_case": central_summary,
        "dimension_conditionals": dimension_means,
        "validation": {
            "unique_balanced_keys": True,
            "independent_source_rows_reconstructed": validation["validation"]["diagnostic_rows_reconstructed"],
            "independent_maximum_absolute_usd2020_per_tco2_error": validation["validation"]["maximum_absolute_usd2020_per_tco2_error"],
            "central_104_values_match_paired_ensemble_summary": True,
            "source_maximum_relative_small_pulse_disagreement": diagnostic["validation"]["maximum_relative_small_pulse_scc_disagreement"],
        },
        "sources": {
            "diagnostic": {"path": str(source), "sha256": digest(source), "receipt": str(args.diagnostic_receipt), "receipt_sha256": digest(args.diagnostic_receipt)},
            "independent_validation": {"path": str(args.validation_receipt), "sha256": digest(args.validation_receipt)},
            "paired_central_ensemble": {"path": str(args.paired_receipt), "sha256": digest(args.paired_receipt)},
        },
        "claim_gates": {"registered_structural_sensitivity": True, "probabilistic_uncertainty": False, "empirical_coefficient_uncertainty": False, "full_precipitation_agriculture_scc": False},
        "limitations": [
            "Design cells are equally summarized for transparency but are not assigned probabilities.",
            "Only the central 104 values have been executed through paired GIVE; other cells are paired-equivalent diagnostics under the validated anchored-linear accounting identity.",
            "Timing, drought, temperature, other crops, irrigation adaptation, trade, storage, and adaptation costs remain omitted.",
        ],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support": result["support"], "overall": overall}, indent=2))


if __name__ == "__main__":
    main()
