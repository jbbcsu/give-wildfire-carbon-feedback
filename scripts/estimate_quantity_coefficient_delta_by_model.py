#!/usr/bin/env python3
"""Resolve coefficient-only delta uncertainty by climate model and discount schedule."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from estimate_quantity_coefficient_delta_uncertainty import (
    PULSE,
    PublishedEstimate,
    digest,
    evaluate_model,
    require,
)


def delta_variance(gradient: np.ndarray, covariance: np.ndarray) -> float:
    return float(np.sum(np.multiply.outer(gradient, gradient) * covariance, dtype=np.float64))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-receipt", type=Path, required=True)
    parser.add_argument("--slopes", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--cpc", type=Path, required=True)
    parser.add_argument("--diagnostic-receipt", type=Path, required=True)
    parser.add_argument("--grid-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")

    panel_receipt = json.loads(args.panel_receipt.read_text())
    diagnostic = json.loads(args.diagnostic_receipt.read_text())
    grid = json.loads(args.grid_receipt.read_text())
    panel_path = Path(panel_receipt["output"]["path"])
    market_receipt = json.loads(Path(diagnostic["sources"]["market_paths"]["receipt"]).read_text())
    coefficient_path = Path(panel_receipt["published_response"]["coefficients"]["path"])
    covariance_path = Path(panel_receipt["published_response"]["covariance"]["path"])
    expected_hashes = (
        (panel_path, panel_receipt["output"]["sha256"]),
        (args.slopes, market_receipt["sources"]["slopes"]["sha256"]),
        (args.fair, market_receipt["sources"]["fair"]["sha256"]),
        (args.cpc, diagnostic["sources"]["give_cpc"]["sha256"]),
        (coefficient_path, panel_receipt["published_response"]["coefficients"]["sha256"]),
        (covariance_path, panel_receipt["published_response"]["covariance"]["sha256"]),
    )
    for path, expected_hash in expected_hashes:
        require(digest(path) == expected_hash, f"source hash differs: {path}")
    require(grid["schema"] == "quantity_coefficient_delta_uncertainty_grid/v1", "grid receipt schema differs")

    estimate = PublishedEstimate.from_exports(coefficient_path, covariance_path)
    coefficients = np.asarray(estimate.coefficients, dtype=float)
    covariance = np.asarray(estimate.covariance, dtype=float)
    covariance = (covariance + covariance.T) / 2.0
    panel = pd.read_parquet(panel_path)
    slopes = pd.read_csv(args.slopes)
    fair = pd.read_csv(args.fair)
    years = np.arange(2020, 2301)
    temperature = fair.loc[
        fair.pulse_size_gtc.eq(PULSE) & fair.year.isin(years)
    ].sort_values("year").difference_k.to_numpy(float)
    cpc = pd.read_csv(args.cpc).set_index("year").loc[years, "net_cpc_2005usd_per_person"].to_numpy(float)
    models = sorted(slopes.source.unique())
    require(len(models) == 26, "climate-model support differs")
    expected = pd.read_csv(Path(diagnostic["output"]["path"]))
    expected = expected.loc[
        expected.pulse_size_gtc.eq(PULSE)
        & expected.adaptation.eq("fixed")
        & expected.tail_rule.eq("uncapped")
        & expected.elasticity_id.eq("hultgren_pair_010_004")
        & expected.yield_to_supply_mapping.eq("horizontal_output")
    ].set_index(["discount_rate_label", "climate_model"])
    currency_scalar = float(market_receipt["currency"]["central_scalar"])
    terms = tuple(estimate.terms)

    rows = []
    summaries = []
    max_value_error = 0.0
    max_mean_se_error = 0.0
    grid_by_rate = {row["discount_rate_label"]: row for row in grid["results"]}
    for schedule in diagnostic["discounting"]["rates"]:
        label = schedule["label"]
        discount = np.power(cpc[0] / cpc, float(schedule["eta"])) / np.power(
            1.0 + float(schedule["prtp"]), years - 2020
        )
        values = []
        gradients = []
        for model in models:
            value, gradient, _ = evaluate_model(
                panel, slopes, model, temperature, discount, coefficients, terms,
                currency_scalar, True,
            )
            assert gradient is not None
            variance = delta_variance(gradient, covariance)
            require(variance >= -1e-18, f"negative delta variance: {label}/{model}")
            se = math.sqrt(max(variance, 0.0))
            lower = value - 1.96 * se
            upper = value + 1.96 * se
            max_value_error = max(
                max_value_error,
                abs(value - float(expected.loc[(label, model), "partial_scc_diagnostic_usd2020_per_tco2"])),
            )
            rows.append({
                "discount_rate_label": label,
                "climate_model": model,
                "central_scc_usd2020_per_tco2": value,
                "coefficient_only_delta_standard_error_usd2020_per_tco2": se,
                "normal_approximation_95_lower_usd2020_per_tco2": lower,
                "normal_approximation_95_upper_usd2020_per_tco2": upper,
                "interval_includes_zero": lower <= 0.0 <= upper,
            })
            values.append(value)
            gradients.append(gradient)
        mean_gradient = np.mean(np.vstack(gradients), axis=0)
        shared_mean_se = math.sqrt(max(delta_variance(mean_gradient, covariance), 0.0))
        grid_row = grid_by_rate[label]
        max_mean_se_error = max(
            max_mean_se_error,
            abs(shared_mean_se - grid_row["coefficient_only_delta_standard_error_usd2020_per_tco2"]),
        )
        rate_rows = rows[-len(models):]
        summaries.append({
            "discount_rate_label": label,
            "central_equal_model_mean_usd2020_per_tco2": float(np.mean(values)),
            "descriptive_across_model_standard_deviation_usd2020_per_tco2": float(np.std(values, ddof=1)),
            "shared_coefficient_delta_se_of_equal_model_mean_usd2020_per_tco2": shared_mean_se,
            "models_with_negative_central_scc": sum(row["central_scc_usd2020_per_tco2"] < 0 for row in rate_rows),
            "model_specific_coefficient_intervals_including_zero": sum(row["interval_includes_zero"] for row in rate_rows),
            "climate_models": len(models),
        })

    require(max_value_error <= 2e-14, "central values differ from diagnostic")
    require(max_mean_se_error <= 5e-15, "shared-mean SE differs from grid receipt")
    output = {
        "schema": "quantity_coefficient_delta_by_model/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "coefficient_only_delta_by_climate_model_complete",
        "estimand": "central fixed-adaptation uncapped annual-maize rainfall-quantity SCC by climate model and GIVE discount schedule",
        "summaries": summaries,
        "rows": rows,
        "validation": {
            "maximum_central_value_error_usd2020_per_tco2": max_value_error,
            "maximum_shared_mean_se_error_usd2020_per_tco2": max_mean_se_error,
            "all_rows": len(rows),
            "all_values_finite": all(math.isfinite(value) for row in rows for key, value in row.items() if key not in {"discount_rate_label", "climate_model", "interval_includes_zero"}),
        },
        "interpretation": {
            "climate_model_standard_deviation": "descriptive spread across 26 models, not sampling uncertainty",
            "coefficient_intervals": "first-order normal intervals conditional on each model and the narrow quantity channel",
            "shared_mean_se": "uses one common empirical coefficient draw across all climate models",
        },
        "claim_gates": {
            "probabilistic_climate_model_weights": False,
            "joint_climate_coefficient_distribution": False,
            "probabilistic_total_scc_interval": False,
            "full_precipitation_agriculture_scc": False,
        },
        "sources": {
            "grid_receipt": {"path": str(args.grid_receipt), "sha256": digest(args.grid_receipt)},
            "diagnostic_receipt": {"path": str(args.diagnostic_receipt), "sha256": digest(args.diagnostic_receipt)},
            "panel_receipt": {"path": str(args.panel_receipt), "sha256": digest(args.panel_receipt)},
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    require(output["validation"]["all_values_finite"], "nonfinite output")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "summaries": summaries, "validation": output["validation"]}, indent=2))


if __name__ == "__main__":
    main()
