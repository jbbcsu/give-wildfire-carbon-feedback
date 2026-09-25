#!/usr/bin/env python3
"""Propagate published coefficient covariance across all GIVE discount schedules."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from estimate_quantity_coefficient_delta_uncertainty import (
    DEMAND,
    PULSE,
    SUPPLY,
    PublishedEstimate,
    digest,
    evaluate_model,
    require,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-receipt", type=Path, required=True)
    parser.add_argument("--slopes", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--cpc", type=Path, required=True)
    parser.add_argument("--diagnostic-receipt", type=Path, required=True)
    parser.add_argument("--two-percent-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")

    panel_receipt = json.loads(args.panel_receipt.read_text())
    diagnostic = json.loads(args.diagnostic_receipt.read_text())
    two_percent = json.loads(args.two_percent_receipt.read_text())
    panel_path = Path(panel_receipt["output"]["path"])
    market_receipt = json.loads(Path(diagnostic["sources"]["market_paths"]["receipt"]).read_text())
    coefficients_path = Path(panel_receipt["published_response"]["coefficients"]["path"])
    covariance_path = Path(panel_receipt["published_response"]["covariance"]["path"])
    for path, expected in (
        (panel_path, panel_receipt["output"]["sha256"]),
        (args.slopes, market_receipt["sources"]["slopes"]["sha256"]),
        (args.fair, market_receipt["sources"]["fair"]["sha256"]),
        (args.cpc, diagnostic["sources"]["give_cpc"]["sha256"]),
        (coefficients_path, panel_receipt["published_response"]["coefficients"]["sha256"]),
        (covariance_path, panel_receipt["published_response"]["covariance"]["sha256"]),
    ):
        require(digest(path) == expected, f"source hash differs: {path}")
    require(two_percent["schema"] == "quantity_coefficient_delta_uncertainty/v1", "2% receipt schema differs")

    estimate = PublishedEstimate.from_exports(coefficients_path, covariance_path)
    coefficients = np.asarray(estimate.coefficients, dtype=float)
    covariance = np.asarray(estimate.covariance, dtype=float)
    covariance = (covariance + covariance.T) / 2.0
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    require(eigenvalues.min() >= -1e-10, "covariance materially indefinite")
    direction = math.sqrt(max(float(eigenvalues[-1]), 0.0)) * eigenvectors[:, -1]
    epsilon = 1e-4

    panel = pd.read_parquet(panel_path)
    slopes = pd.read_csv(args.slopes)
    fair = pd.read_csv(args.fair)
    years = np.arange(2020, 2301)
    temperature = fair.loc[
        fair.pulse_size_gtc.eq(PULSE) & fair.year.isin(years)
    ].sort_values("year").difference_k.to_numpy(float)
    cpc = pd.read_csv(args.cpc).set_index("year").loc[years, "net_cpc_2005usd_per_person"].to_numpy(float)
    expected = pd.read_csv(Path(diagnostic["output"]["path"]))
    expected = expected.loc[
        expected.pulse_size_gtc.eq(PULSE)
        & expected.adaptation.eq("fixed")
        & expected.tail_rule.eq("uncapped")
        & expected.elasticity_id.eq("hultgren_pair_010_004")
        & expected.yield_to_supply_mapping.eq("horizontal_output")
    ]
    models = sorted(slopes.source.unique())
    require(len(models) == 26, "climate-model support differs")
    terms = tuple(estimate.terms)
    currency_scalar = float(market_receipt["currency"]["central_scalar"])

    results = []
    validation = []
    for schedule in diagnostic["discounting"]["rates"]:
        label = schedule["label"]
        discount = np.power(cpc[0] / cpc, float(schedule["eta"])) / np.power(
            1.0 + float(schedule["prtp"]), years - 2020
        )
        values = []
        gradients = []
        max_central_error = 0.0
        expected_rate = expected.loc[expected.discount_rate_label.eq(label)].set_index("climate_model")
        require(len(expected_rate) == 26, f"expected support differs for {label}")
        for model in models:
            value, gradient, _ = evaluate_model(
                panel, slopes, model, temperature, discount, coefficients, terms,
                currency_scalar, True,
            )
            assert gradient is not None
            values.append(value)
            gradients.append(gradient)
            max_central_error = max(
                max_central_error,
                abs(value - float(expected_rate.loc[model, "partial_scc_diagnostic_usd2020_per_tco2"])),
            )
        require(max_central_error <= 2e-14, f"central reconstruction differs for {label}")
        mean_value = float(np.mean(values))
        gradient = np.mean(np.vstack(gradients), axis=0)
        # Avoid the macOS Accelerate matmul warning observed for this small,
        # ill-scaled covariance; explicit elementwise summation is stable and
        # matches the independently validated 2% implementation.
        variance = float(np.sum(np.multiply.outer(gradient, gradient) * covariance, dtype=np.float64))
        require(variance >= -1e-18, f"negative delta variance for {label}")
        standard_error = math.sqrt(max(variance, 0.0))

        directional_values = []
        for sign in (-1.0, 1.0):
            beta = coefficients + sign * epsilon * direction
            perturbed = [
                evaluate_model(
                    panel, slopes, model, temperature, discount, beta, terms,
                    currency_scalar, False,
                )[0]
                for model in models
            ]
            directional_values.append(float(np.mean(perturbed)))
        finite = (directional_values[1] - directional_values[0]) / (2.0 * epsilon)
        analytic = float(gradient @ direction)
        relative_error = abs(finite - analytic) / max(abs(analytic), 1e-30)
        require(relative_error <= 5e-4, f"directional derivative differs for {label}")
        results.append({
            "discount_rate_label": label,
            "central_mean_usd2020_per_tco2": mean_value,
            "coefficient_only_delta_standard_error_usd2020_per_tco2": standard_error,
            "normal_approximation_95_interval_usd2020_per_tco2": [
                mean_value - 1.96 * standard_error,
                mean_value + 1.96 * standard_error,
            ],
        })
        validation.append({
            "discount_rate_label": label,
            "maximum_central_reconstruction_error_usd2020_per_tco2": max_central_error,
            "analytic_directional_derivative": analytic,
            "finite_difference_directional_derivative": finite,
            "directional_derivative_relative_error": relative_error,
        })

    two = next(row for row in results if row["discount_rate_label"] == "2.0%")
    prior = two_percent["result"]
    two_percent_error = max(
        abs(two["central_mean_usd2020_per_tco2"] - prior["central_mean_usd2020_per_tco2"]),
        abs(two["coefficient_only_delta_standard_error_usd2020_per_tco2"] - prior["coefficient_only_delta_standard_error_usd2020_per_tco2"]),
        *(abs(a - b) for a, b in zip(two["normal_approximation_95_interval_usd2020_per_tco2"], prior["normal_approximation_95_interval_usd2020_per_tco2"])),
    )
    require(two_percent_error <= 5e-15, "2% result differs from prior receipt")

    output = {
        "schema": "quantity_coefficient_delta_uncertainty_grid/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "published_coefficient_covariance_delta_grid_complete",
        "estimand": "equal-26-model central fixed-adaptation uncapped annual-maize rainfall-quantity SCC by GIVE discount schedule",
        "results": results,
        "validation": {
            "by_discount_schedule": validation,
            "maximum_two_percent_prior_receipt_error_usd2020_per_tco2": two_percent_error,
            "directional_derivative_relative_tolerance": 5e-4,
            "finite_difference_epsilon_in_standard_deviation_units": epsilon,
            "minimum_covariance_eigenvalue": float(eigenvalues.min()),
        },
        "sources": {
            "two_percent_receipt": {"path": str(args.two_percent_receipt), "sha256": digest(args.two_percent_receipt)},
            "diagnostic_receipt": {"path": str(args.diagnostic_receipt), "sha256": digest(args.diagnostic_receipt)},
            "panel_receipt": {"path": str(args.panel_receipt), "sha256": digest(args.panel_receipt)},
        },
        "claim_gates": {
            "published_coefficient_covariance_delta_method": True,
            "joint_climate_structural_or_adaptation_uncertainty": False,
            "probabilistic_total_scc_interval": False,
            "full_precipitation_agriculture_scc": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "results": results, "validation": output["validation"]}, indent=2))


if __name__ == "__main__":
    main()
