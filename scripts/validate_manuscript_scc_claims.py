#!/usr/bin/env python3
"""Fail closed if the manuscript's headline SCC claims drift from receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def dollars(value: float, signed_positive: bool = False) -> str:
    if value < 0:
        return f"-${abs(value):.5f}"
    prefix = "+" if signed_positive else ""
    return f"{prefix}${value:.5f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--structural", type=Path, required=True)
    parser.add_argument("--coefficient-grid", type=Path, required=True)
    parser.add_argument("--by-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")

    text = args.manuscript.read_text()
    normalized_text = " ".join(text.split())
    structural = json.loads(args.structural.read_text())
    coefficient = json.loads(args.coefficient_grid.read_text())
    by_model = json.loads(args.by_model.read_text())
    require(structural["schema"] == "quantity_structural_sensitivity_envelope/v1", "structural schema differs")
    require(coefficient["schema"] == "quantity_coefficient_delta_uncertainty_grid/v1", "coefficient schema differs")
    require(by_model["schema"] == "quantity_coefficient_delta_by_model/v1", "by-model schema differs")

    overall = structural["overall"]["2.0%"]
    central = next(row for row in coefficient["results"] if row["discount_rate_label"] == "2.0%")
    model_summary = next(row for row in by_model["summaries"] if row["discount_rate_label"] == "2.0%")
    required_fragments = {
        "central_mean": dollars(central["central_mean_usd2020_per_tco2"]),
        "design_mean": dollars(overall["mean_usd2020_per_tco2"]),
        "design_p025": dollars(overall["p02_5_usd2020_per_tco2"]),
        "design_p975": dollars(overall["p97_5_usd2020_per_tco2"], signed_positive=True),
        "coefficient_se": dollars(central["coefficient_only_delta_standard_error_usd2020_per_tco2"]),
        "coefficient_lower": dollars(central["normal_approximation_95_interval_usd2020_per_tco2"][0]),
        "coefficient_upper": dollars(central["normal_approximation_95_interval_usd2020_per_tco2"][1]),
        "model_sd": dollars(model_summary["descriptive_across_model_standard_deviation_usd2020_per_tco2"]),
        "paired_paths": "936 paired paths",
        "negative_design_cells": f"{overall['negative_cells']} paths are negative",
        "model_interval_count": "23 model-specific coefficient-only intervals",
    }
    missing = {name: fragment for name, fragment in required_fragments.items() if fragment not in normalized_text}
    require(not missing, f"manuscript required claim fragments missing: {missing}")
    prohibited = [
        "no global damage or SCC estimate is reported",
        "empirical coefficient uncertainty is not yet included",
        "SCC results and scenario definitions (after estimation)",
    ]
    present = [fragment for fragment in prohibited if fragment in normalized_text]
    require(not present, f"stale manuscript claims remain: {present}")
    safeguards = [
        "not the total precipitation effect on agriculture",
        "design summaries, not probabilities",
        "climate-model spread, not sampling uncertainty",
        "not as an additive precipitation sector",
    ]
    missing_safeguards = [fragment for fragment in safeguards if fragment not in normalized_text]
    require(not missing_safeguards, f"claim safeguards missing: {missing_safeguards}")

    output = {
        "schema": "manuscript_scc_claim_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "sources": {
            "manuscript": {"path": str(args.manuscript), "sha256": digest(args.manuscript)},
            "structural": {"path": str(args.structural), "sha256": digest(args.structural)},
            "coefficient_grid": {"path": str(args.coefficient_grid), "sha256": digest(args.coefficient_grid)},
            "by_model": {"path": str(args.by_model), "sha256": digest(args.by_model)},
        },
        "required_claim_fragments": required_fragments,
        "prohibited_stale_fragments_absent": prohibited,
        "required_safeguards_present": safeguards,
        "implementation": {"path": str(Path(__file__).relative_to(Path(__file__).parents[1])), "sha256": digest(Path(__file__))},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "required_claims": len(required_fragments), "safeguards": len(safeguards)}, indent=2))


if __name__ == "__main__":
    main()
