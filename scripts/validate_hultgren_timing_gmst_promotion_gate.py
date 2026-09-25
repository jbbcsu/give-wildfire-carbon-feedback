#!/usr/bin/env python3
"""Independent arithmetic audit of the five-ESM timing promotion gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


LABELS = {
    "net_precipitation": "precipitation_all_income_support",
    "quantity_reference": "precipitation_quantity_reference_scaling",
    "timing_distribution_increment": "precipitation_distribution_residual",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_close(actual: float, expected: float, label: str, checks: list[float]) -> None:
    error = abs(float(actual) - float(expected))
    checks.append(error)
    if not math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-15):
        raise ValueError(f"{label} differs: {actual} versus {expected}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--transport-summary", type=Path, required=True)
    parser.add_argument("--gmst-link", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")

    result = json.loads(args.result.read_text(encoding="utf-8"))
    transport = json.loads(args.transport_summary.read_text(encoding="utf-8"))
    gmst = json.loads(args.gmst_link.read_text(encoding="utf-8"))
    if result["schema"] != "hultgren_timing_gmst_promotion_gate/v1":
        raise ValueError("result schema differs")
    if result["sources"]["transport_summary"]["sha256"] != sha256(args.transport_summary):
        raise ValueError("transport hash differs")
    if result["sources"]["gmst_link"]["sha256"] != sha256(args.gmst_link):
        raise ValueError("GMST hash differs")

    target = next(row for row in gmst["primary_records"] if row["crop"] == "mai" and row["irrigation"] == "noirr" and row["scale_months"] == 3 and row["window"] == "season")
    temperatures = {
        row["esm"].upper(): float(row["gmst_difference_k"])
        for row in target["full_fit"]["points"] if row["contrast"] == "ssp585_minus_ssp126"
    }
    fixed = transport["support_sensitivities"]["full"]["fixed"]
    errors: list[float] = []
    reconstructed = {}
    for public_label, source_label in LABELS.items():
        effects = {row["climate_model"]: float(row["weighted_mean_delta_log_yield"]) for row in fixed[source_label]["named_model_results"]}
        models = list(effects)
        x = [temperatures[model.upper()] for model in models]
        y = [effects[model] for model in models]
        slope = sum(a * b for a, b in zip(x, y)) / sum(a * a for a in x)
        rmse = math.sqrt(sum((b - slope * a) ** 2 for a, b in zip(x, y)) / len(x))
        zero = math.sqrt(sum(b * b for b in y) / len(y))
        reported = result["components"][public_label]
        check_close(reported["origin_constrained_slope_delta_log_yield_per_k"], slope, f"{public_label} slope", errors)
        check_close(reported["rmse"], rmse, f"{public_label} RMSE", errors)
        check_close(reported["zero_change_rmse"], zero, f"{public_label} zero RMSE", errors)
        holdout_flags = []
        for index, model in enumerate(models):
            train_x = x[:index] + x[index + 1:]
            train_y = y[:index] + y[index + 1:]
            train_slope = sum(a * b for a, b in zip(train_x, train_y)) / sum(a * a for a in train_x)
            prediction = train_slope * x[index]
            improves = abs(y[index] - prediction) < abs(y[index])
            reported_row = next(row for row in reported["whole_esm_holdouts"] if row["held_out_climate_model"] == model)
            check_close(reported_row["training_slope_delta_log_yield_per_k"], train_slope, f"{public_label}/{model} holdout slope", errors)
            check_close(reported_row["predicted_delta_log_yield"], prediction, f"{public_label}/{model} prediction", errors)
            if bool(reported_row["improves_on_zero_change"]) != improves:
                raise ValueError(f"{public_label}/{model} holdout flag differs")
            holdout_flags.append(improves)
        sign_stable = all(value < 0.0 for value in y) or all(value > 0.0 for value in y) or all(value == 0.0 for value in y)
        if bool(reported["sign_stable"]) != sign_stable:
            raise ValueError(f"{public_label} sign flag differs")
        if bool(reported["all_whole_esm_holdouts_improve_on_zero"]) != all(holdout_flags):
            raise ValueError(f"{public_label} holdout aggregate differs")
        reconstructed[public_label] = {"slope": slope, "sign_stable": sign_stable, "holdouts_improving": sum(holdout_flags)}

    timing = reconstructed["timing_distribution_increment"]
    quantity = reconstructed["quantity_reference"]
    share = abs(timing["slope"]) / abs(quantity["slope"])
    check_close(result["timing_increment_absolute_slope_share_of_quantity_reference"], share, "timing share", errors)
    promoted = timing["sign_stable"] and timing["holdouts_improving"] == 5
    if bool(result["gates"]["timing_increment_promoted_to_marginal_scc"]) != promoted:
        raise ValueError("promotion gate differs")

    audit = {
        "schema": "hultgren_timing_gmst_promotion_gate_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_timing_promotion_gate_not_damage_or_scc",
        "result": {"path": str(args.result), "sha256": sha256(args.result)},
        "sources": {"transport_summary_sha256": sha256(args.transport_summary), "gmst_link_sha256": sha256(args.gmst_link)},
        "numeric_checks": len(errors),
        "maximum_absolute_numeric_difference": max(errors, default=0.0),
        "reconstructed": reconstructed,
        "timing_share": share,
        "promotion_gate": promoted,
        "claim_gates": {"arithmetic_validated": True, "damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
