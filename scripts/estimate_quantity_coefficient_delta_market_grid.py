#!/usr/bin/env python3
"""Propagate published coefficient covariance across six registered market cases."""

from __future__ import annotations

import argparse
import json
import math
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from estimate_quantity_coefficient_delta_uncertainty import (
    CHUNK, PULSE, USD2020, VALUE, PublishedEstimate, coefficient_design, digest,
    require,
)


def evaluate(
    panel: pd.DataFrame, slopes: pd.DataFrame, model: str, temperature: np.ndarray,
    discount: np.ndarray, coefficients: np.ndarray, terms: tuple[str, ...],
    currency_scalar: float, supply: float, demand: float, mapping: str,
    need_gradient: bool,
) -> tuple[float, np.ndarray | None]:
    selected = slopes.loc[slopes.source.eq(model) & slopes.slope_available, ["iso3", "patterns.area"]]
    work = panel.merge(selected, on="iso3", how="inner", validate="many_to_one").sort_values(
        ["iso3", "native_lat_index", "native_lon_index"]
    ).reset_index(drop=True)
    linear_design, squared_design, _ = coefficient_design(work, terms)
    linear = np.einsum("ij,j->i", linear_design, coefficients, optimize=False)
    squared = np.einsum("ij,j->i", squared_design, coefficients, optimize=False)
    values = work[VALUE].to_numpy(float)
    iso = work.iso3.to_numpy()
    starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
    counts = np.diff(np.r_[starts, len(work)])
    country_index = np.repeat(np.arange(len(starts)), counts)
    country_value = np.add.reduceat(values, starts)
    slope = work["patterns.area"].to_numpy(float) / work.annual_precip_mean_mm.to_numpy(float)
    exponent = 1.0 if mapping == "horizontal_output" else 1.0 + supply
    require(mapping in {"horizontal_output", "fixed_input_cost"}, "mapping differs")
    a = -(1.0 - demand) / (supply + demand)
    normalization = currency_scalar * (12.0 / 44.0) / (1e9 * PULSE) * USD2020
    scc = 0.0
    gradient = np.zeros(len(coefficients)) if need_gradient else None
    for begin in range(0, len(temperature), CHUNK):
        end = min(begin + CHUNK, len(temperature))
        t = temperature[begin:end]
        x = slope[:, None] * t[None, :]
        response = linear[:, None] * x + squared[:, None] * (2.0 * x + x * x)
        output = np.exp(exponent * response) * values[:, None]
        country_output = np.add.reduceat(output, starts, axis=0)
        ratio = country_output / country_value[:, None]
        shift = np.log(ratio)
        damage = -country_value[:, None] * np.expm1(a * shift) / (a * (1.0 + supply))
        factors = discount[begin:end] * normalization
        scc += float(np.sum(damage.sum(axis=0) * factors))
        if need_gradient:
            country_factor = -np.exp(a * shift) / ((1.0 + supply) * ratio)
            weights = (output * (exponent * country_factor[country_index, :])).T
            design_a = slope[:, None] * (linear_design + 2.0 * squared_design)
            design_b = np.square(slope)[:, None] * squared_design
            annual_gradient = (
                t[:, None] * np.einsum("yc,ck->yk", weights, design_a, optimize=False)
                + np.square(t)[:, None] * np.einsum("yc,ck->yk", weights, design_b, optimize=False)
            )
            gradient += np.sum(annual_gradient * factors[:, None], axis=0)
    return scc, gradient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-receipt", type=Path, required=True)
    parser.add_argument("--slopes", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--cpc", type=Path, required=True)
    parser.add_argument("--diagnostic-receipt", type=Path, required=True)
    parser.add_argument("--coefficient-grid-receipt", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    panel_receipt = json.loads(args.panel_receipt.read_text())
    diagnostic = json.loads(args.diagnostic_receipt.read_text())
    prior_grid = json.loads(args.coefficient_grid_receipt.read_text())
    registry = tomllib.loads(args.registry.read_text())
    panel_path = Path(panel_receipt["output"]["path"])
    market_receipt = json.loads(Path(diagnostic["sources"]["market_paths"]["receipt"]).read_text())
    coefficient_path = Path(panel_receipt["published_response"]["coefficients"]["path"])
    covariance_path = Path(panel_receipt["published_response"]["covariance"]["path"])
    for path, expected_hash in (
        (panel_path, panel_receipt["output"]["sha256"]),
        (args.slopes, market_receipt["sources"]["slopes"]["sha256"]),
        (args.fair, market_receipt["sources"]["fair"]["sha256"]),
        (args.cpc, diagnostic["sources"]["give_cpc"]["sha256"]),
        (coefficient_path, panel_receipt["published_response"]["coefficients"]["sha256"]),
        (covariance_path, panel_receipt["published_response"]["covariance"]["sha256"]),
    ):
        require(digest(path) == expected_hash, f"source hash differs: {path}")
    estimate = PublishedEstimate.from_exports(coefficient_path, covariance_path)
    coefficients = np.asarray(estimate.coefficients, float)
    covariance = np.asarray(estimate.covariance, float)
    covariance = (covariance + covariance.T) / 2.0
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    direction = math.sqrt(max(float(eigenvalues[-1]), 0.0)) * eigenvectors[:, -1]
    epsilon = 1e-4
    panel = pd.read_parquet(panel_path)
    slopes = pd.read_csv(args.slopes)
    fair = pd.read_csv(args.fair)
    years = np.arange(2020, 2301)
    temperature = fair.loc[fair.pulse_size_gtc.eq(PULSE) & fair.year.isin(years)].sort_values("year").difference_k.to_numpy(float)
    cpc = pd.read_csv(args.cpc).set_index("year").loc[years, "net_cpc_2005usd_per_person"].to_numpy(float)
    schedule = next(row for row in diagnostic["discounting"]["rates"] if row["label"] == "2.0%")
    discount = np.power(cpc[0] / cpc, float(schedule["eta"])) / np.power(1.0 + float(schedule["prtp"]), years - 2020)
    models = sorted(slopes.source.unique())
    expected = pd.read_csv(Path(diagnostic["output"]["path"]))
    expected = expected.loc[
        expected.pulse_size_gtc.eq(PULSE) & expected.adaptation.eq("fixed")
        & expected.tail_rule.eq("uncapped") & expected.discount_rate_label.eq("2.0%")
    ].set_index(["elasticity_id", "yield_to_supply_mapping", "climate_model"])
    specs = []
    for row in registry["elasticity_pairs"]:
        supply, demand = float(row["supply"]), -float(row["demand_signed"])
        for mapping in ("horizontal_output", "fixed_input_cost"):
            specs.append((str(row["id"]), supply, demand, mapping))
    require(len(specs) == 6, "market registry differs")
    terms = tuple(estimate.terms)
    currency_scalar = float(market_receipt["currency"]["central_scalar"])
    results = []
    maximum_value_error = 0.0
    maximum_directional_relative_error = 0.0
    for elasticity_id, supply, demand, mapping in specs:
        values, gradients = [], []
        for model in models:
            value, gradient = evaluate(panel, slopes, model, temperature, discount, coefficients, terms,
                                       currency_scalar, supply, demand, mapping, True)
            assert gradient is not None
            values.append(value)
            gradients.append(gradient)
            maximum_value_error = max(maximum_value_error, abs(value - float(expected.loc[(elasticity_id, mapping, model), "partial_scc_diagnostic_usd2020_per_tco2"])))
        mean = float(np.mean(values))
        mean_gradient = np.mean(np.vstack(gradients), axis=0)
        variance = float(np.sum(np.multiply.outer(mean_gradient, mean_gradient) * covariance, dtype=np.float64))
        require(variance >= -1e-18, "negative delta variance")
        se = math.sqrt(max(variance, 0.0))
        perturbed_means = []
        for sign in (-1.0, 1.0):
            beta = coefficients + sign * epsilon * direction
            perturbed_means.append(float(np.mean([
                evaluate(panel, slopes, model, temperature, discount, beta, terms, currency_scalar,
                         supply, demand, mapping, False)[0] for model in models
            ])))
        finite = (perturbed_means[1] - perturbed_means[0]) / (2.0 * epsilon)
        analytic = float(mean_gradient @ direction)
        relative_error = abs(finite - analytic) / max(abs(analytic), 1e-30)
        maximum_directional_relative_error = max(maximum_directional_relative_error, relative_error)
        require(relative_error <= 5e-4, f"directional derivative differs: {elasticity_id}/{mapping}")
        results.append({
            "elasticity_id": elasticity_id, "supply_elasticity": supply,
            "demand_elasticity_magnitude": demand, "yield_to_supply_mapping": mapping,
            "central_equal_model_mean_usd2020_per_tco2": mean,
            "coefficient_only_delta_standard_error_usd2020_per_tco2": se,
            "normal_approximation_95_interval_usd2020_per_tco2": [mean - 1.96 * se, mean + 1.96 * se],
            "directional_derivative_relative_error": relative_error,
        })
    require(maximum_value_error <= 2e-14, "diagnostic reconstruction differs")
    central = next(row for row in results if row["elasticity_id"] == "hultgren_pair_010_004" and row["yield_to_supply_mapping"] == "horizontal_output")
    prior = next(row for row in prior_grid["results"] if row["discount_rate_label"] == "2.0%")
    maximum_prior_error = max(
        abs(central["central_equal_model_mean_usd2020_per_tco2"] - prior["central_mean_usd2020_per_tco2"]),
        abs(central["coefficient_only_delta_standard_error_usd2020_per_tco2"] - prior["coefficient_only_delta_standard_error_usd2020_per_tco2"]),
    )
    require(maximum_prior_error <= 5e-15, "central prior receipt differs")
    output = {
        "schema": "quantity_coefficient_delta_market_grid/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "fixed_uncapped_two_percent_market_grid_complete",
        "estimand": "equal-26-model fixed-adaptation uncapped annual-maize rainfall-quantity SCC by registered market at GIVE 2% schedule",
        "results": results,
        "validation": {
            "maximum_diagnostic_reconstruction_error_usd2020_per_tco2": maximum_value_error,
            "maximum_central_prior_receipt_error_usd2020_per_tco2": maximum_prior_error,
            "maximum_directional_derivative_relative_error": maximum_directional_relative_error,
            "directional_derivative_relative_tolerance": 5e-4,
        },
        "claim_gates": {
            "published_coefficient_covariance_delta_method": True,
            "market_grid_fixed_uncapped_only": True,
            "joint_structural_coefficient_distribution": False,
            "full_precipitation_agriculture_scc": False,
        },
        "sources": {
            "diagnostic_receipt": {"path": str(args.diagnostic_receipt), "sha256": digest(args.diagnostic_receipt)},
            "panel_receipt": {"path": str(args.panel_receipt), "sha256": digest(args.panel_receipt)},
            "coefficient_grid_receipt": {"path": str(args.coefficient_grid_receipt), "sha256": digest(args.coefficient_grid_receipt)},
            "registry": {"path": str(args.registry), "sha256": digest(args.registry)},
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "results": results, "validation": output["validation"]}, indent=2))


if __name__ == "__main__":
    main()
