#!/usr/bin/env python3
"""Propagate published Hultgren coefficient covariance to the central SCC mean."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.hultgren_maize_response import PublishedEstimate

PULSE = 0.000025
VALUE = "maize_gross_production_value_common_price_2014_2016_usd"
LINEAR = [f"prcp_poly_1_bin{phase}" for phase in (1, 2, 3)]
SQUARED = [f"prcp_poly_2_bin{phase}" for phase in (1, 2, 3)]
SUPPLY = 0.10
DEMAND = 0.04
PRTP = math.exp(0.001972641) - 1.0
ETA = 1.244458999
USD2020 = 113.648 / 87.504
CHUNK = 16


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def coefficient_design(frame: pd.DataFrame, terms: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray, int]:
    primitives = {
        "ln_gdppc": frame.ln_gdppc.to_numpy(float),
        "irrigated_share": frame.irrigated_share.to_numpy(float),
        "lr_tmax_crop": frame.lr_tmax_crop.to_numpy(float),
        "pbarcut_prcp": np.minimum(frame.lr_prcp_crop.to_numpy(float), 250.0),
    }
    linear = np.zeros((len(frame), len(terms)))
    squared = np.zeros_like(linear)
    used = 0
    for index, term in enumerate(terms):
        factors = [factor.removeprefix("c.") for factor in term.split("#")]
        weather = [factor for factor in factors if factor in LINEAR + SQUARED]
        if not weather:
            continue
        require(len(weather) == 1 and factors.count(weather[0]) == 1, f"unsupported precipitation term: {term}")
        values = np.ones(len(frame))
        for factor in factors:
            if factor != weather[0]:
                require(factor in primitives, f"unsupported moderator: {term}")
                values *= primitives[factor]
        target = linear if weather[0] in LINEAR else squared
        target[:, index] = frame[weather[0]].to_numpy(float) * values
        used += 1
    require(used == 36, "precipitation term support differs")
    return linear, squared, used


def evaluate_model(
    frame: pd.DataFrame,
    slope_frame: pd.DataFrame,
    model: str,
    temperature: np.ndarray,
    discount: np.ndarray,
    coefficients: np.ndarray,
    terms: tuple[str, ...],
    currency_scalar: float,
    need_gradient: bool,
) -> tuple[float, np.ndarray | None, float]:
    selected = slope_frame.loc[slope_frame.source.eq(model) & slope_frame.slope_available, ["iso3", "patterns.area"]]
    require(not selected.duplicated("iso3").any(), f"duplicate slopes for {model}")
    work = frame.merge(selected, on="iso3", how="inner", validate="many_to_one").sort_values(["iso3", "native_lat_index", "native_lon_index"]).reset_index(drop=True)
    linear_design, squared_design, _ = coefficient_design(work, terms)
    linear_index = np.einsum("ij,j->i", linear_design, coefficients, optimize=False)
    squared_index = np.einsum("ij,j->i", squared_design, coefficients, optimize=False)
    if need_gradient:
        require(np.max(np.abs(linear_index - work.baseline_linear_precipitation_index.to_numpy(float))) <= 2e-13, "linear index differs")
        require(np.max(np.abs(squared_index - work.baseline_squared_precipitation_index.to_numpy(float))) <= 2e-13, "squared index differs")
    values = work[VALUE].to_numpy(float)
    iso = work.iso3.to_numpy()
    starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
    counts = np.diff(np.r_[starts, len(work)])
    country_index = np.repeat(np.arange(len(starts)), counts)
    country_value = np.add.reduceat(values, starts)
    slope = work["patterns.area"].to_numpy(float) / work.annual_precip_mean_mm.to_numpy(float)
    a = -(1.0 - DEMAND) / (SUPPLY + DEMAND)
    normalization = currency_scalar * (12.0 / 44.0) / (1e9 * PULSE) * USD2020
    scc = 0.0
    gradient = np.zeros(len(coefficients)) if need_gradient else None
    max_annual_reconstruction = 0.0
    for begin in range(0, len(temperature), CHUNK):
        end = min(begin + CHUNK, len(temperature))
        t = temperature[begin:end]
        x = slope[:, None] * t[None, :]
        response = linear_index[:, None] * x + squared_index[:, None] * (2.0 * x + x * x)
        output = np.exp(response) * values[:, None]
        country_output = np.add.reduceat(output, starts, axis=0)
        ratio = country_output / country_value[:, None]
        shift = np.log(ratio)
        damage = -country_value[:, None] * np.expm1(a * shift) / (a * (1.0 + SUPPLY))
        annual = damage.sum(axis=0)
        factors = discount[begin:end] * normalization
        scc += float(np.sum(annual * factors))
        if need_gradient:
            country_factor = -np.exp(a * shift) / ((1.0 + SUPPLY) * ratio)
            weights = (output * country_factor[country_index, :]).T
            design_a = slope[:, None] * (linear_design + 2.0 * squared_design)
            design_b = np.square(slope)[:, None] * squared_design
            annual_gradient = t[:, None] * np.einsum("yc,ck->yk", weights, design_a, optimize=False) + np.square(t)[:, None] * np.einsum("yc,ck->yk", weights, design_b, optimize=False)
            gradient += np.sum(annual_gradient * factors[:, None], axis=0)
        reconstructed = -country_value[:, None] * shift / (1.0 + SUPPLY)
        nonzero = a * shift != 0
        reconstructed[nonzero] *= np.expm1(a * shift[nonzero]) / (a * shift[nonzero])
        max_annual_reconstruction = max(max_annual_reconstruction, float(np.max(np.abs(reconstructed.sum(axis=0) - annual))))
    return scc, gradient, max_annual_reconstruction


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-receipt", type=Path, required=True)
    parser.add_argument("--slopes", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--cpc", type=Path, required=True)
    parser.add_argument("--diagnostic-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    panel_receipt = json.loads(args.panel_receipt.read_text())
    diagnostic = json.loads(args.diagnostic_receipt.read_text())
    require(panel_receipt["schema"] == "hultgren_quantity_response_panel/v1", "panel receipt differs")
    panel_path = Path(panel_receipt["output"]["path"])
    require(digest(panel_path) == panel_receipt["output"]["sha256"], "panel hash differs")
    require(digest(args.cpc) == diagnostic["sources"]["give_cpc"]["sha256"], "CPC hash differs")
    market_receipt = json.loads(Path(diagnostic["sources"]["market_paths"]["receipt"]).read_text())
    require(digest(args.slopes) == market_receipt["sources"]["slopes"]["sha256"], "slope hash differs")
    require(digest(args.fair) == market_receipt["sources"]["fair"]["sha256"], "FAIR hash differs")
    coefficients_path = Path(panel_receipt["published_response"]["coefficients"]["path"])
    covariance_path = Path(panel_receipt["published_response"]["covariance"]["path"])
    require(digest(coefficients_path) == panel_receipt["published_response"]["coefficients"]["sha256"], "coefficient hash differs")
    require(digest(covariance_path) == panel_receipt["published_response"]["covariance"]["sha256"], "covariance hash differs")
    estimate = PublishedEstimate.from_exports(coefficients_path, covariance_path)
    covariance = np.asarray(estimate.covariance, dtype=float)
    require(covariance.shape == (49, 49) and np.max(np.abs(covariance - covariance.T)) <= 1e-12, "covariance differs")
    eigenvalues, eigenvectors = np.linalg.eigh((covariance + covariance.T) / 2.0)
    require(eigenvalues.min() >= -1e-10, "covariance materially indefinite")

    panel = pd.read_parquet(panel_path)
    slopes = pd.read_csv(args.slopes)
    fair = pd.read_csv(args.fair)
    years = np.arange(2020, 2301)
    temperature = fair.loc[fair.pulse_size_gtc.eq(PULSE) & fair.year.isin(years)].sort_values("year").difference_k.to_numpy(float)
    cpc_frame = pd.read_csv(args.cpc).set_index("year")
    cpc = cpc_frame.loc[years, "net_cpc_2005usd_per_person"].to_numpy(float)
    discount = np.power(cpc[0] / cpc, ETA) / np.power(1.0 + PRTP, years - 2020)
    currency_scalar = float(market_receipt["currency"]["central_scalar"])
    models = sorted(slopes.source.unique())
    expected_path = Path(diagnostic["output"]["path"])
    expected = pd.read_csv(expected_path)
    expected = expected.loc[expected.pulse_size_gtc.eq(PULSE) & expected.adaptation.eq("fixed") & expected.tail_rule.eq("uncapped") & expected.elasticity_id.eq("hultgren_pair_010_004") & expected.yield_to_supply_mapping.eq("horizontal_output") & expected.discount_rate_label.eq("2.0%")].set_index("climate_model")
    require(len(expected) == 26, "expected central support differs")

    central_values = []
    gradients = []
    max_central_error = 0.0
    max_formula_error = 0.0
    terms = tuple(estimate.terms)
    coefficients = np.asarray(estimate.coefficients, dtype=float)
    for model in models:
        value, gradient, formula_error = evaluate_model(panel, slopes, model, temperature, discount, coefficients, terms, currency_scalar, True)
        assert gradient is not None
        central_values.append(value)
        gradients.append(gradient)
        max_central_error = max(max_central_error, abs(value - float(expected.loc[model, "partial_scc_diagnostic_usd2020_per_tco2"])))
        max_formula_error = max(max_formula_error, formula_error)
    require(max_central_error <= 2e-14, f"central SCC reconstruction differs: {max_central_error}")
    mean_value = float(np.mean(central_values))
    mean_gradient = np.mean(np.vstack(gradients), axis=0)
    variance = float(np.sum(np.multiply.outer(mean_gradient, mean_gradient) * covariance, dtype=np.float64))
    require(variance >= -1e-18, "negative delta variance")
    standard_error = math.sqrt(max(variance, 0.0))

    largest = int(np.argmax(eigenvalues))
    direction = math.sqrt(max(float(eigenvalues[largest]), 0.0)) * eigenvectors[:, largest]
    epsilon = 1e-4
    directional_values = []
    for sign in (-1.0, 1.0):
        beta = coefficients + sign * epsilon * direction
        values = [evaluate_model(panel, slopes, model, temperature, discount, beta, terms, currency_scalar, False)[0] for model in models]
        directional_values.append(float(np.mean(values)))
    finite_difference = (directional_values[1] - directional_values[0]) / (2.0 * epsilon)
    analytic_direction = float(np.einsum("i,i->", mean_gradient, direction, optimize=False))
    directional_error = abs(finite_difference - analytic_direction)
    directional_relative_error = directional_error / max(abs(analytic_direction), 1e-30)
    directional_relative_tolerance = 5e-4
    print(json.dumps({"analytic_direction": analytic_direction, "finite_difference_direction": finite_difference, "directional_error": directional_error, "directional_relative_error": directional_relative_error}), flush=True)
    require(directional_relative_error <= directional_relative_tolerance, "directional derivative check failed")

    result = {
        "schema": "quantity_coefficient_delta_uncertainty/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "published_coefficient_covariance_delta_method_complete",
        "estimand": "equal-climate-model mean central fixed-adaptation uncapped annual-maize rainfall-quantity SCC at the 2% Ramsey schedule",
        "result": {
            "central_mean_usd2020_per_tco2": mean_value,
            "coefficient_only_delta_standard_error_usd2020_per_tco2": standard_error,
            "normal_approximation_95_interval_usd2020_per_tco2": [mean_value - 1.96 * standard_error, mean_value + 1.96 * standard_error],
        },
        "support": {"climate_models": len(models), "published_coefficients": len(coefficients), "published_covariance_shape": [49, 49], "precipitation_terms_used": 36, "years": [2020, 2300]},
        "validation": {
            "maximum_central_scc_reconstruction_error_usd2020_per_tco2": max_central_error,
            "maximum_market_formula_reconstruction_error_source_usd": max_formula_error,
            "minimum_covariance_eigenvalue": float(eigenvalues.min()),
            "finite_difference_direction_epsilon_in_standard_deviation_units": epsilon,
            "analytic_directional_derivative": analytic_direction,
            "finite_difference_directional_derivative": finite_difference,
            "directional_derivative_absolute_error": directional_error,
            "directional_derivative_relative_error": directional_relative_error,
            "directional_derivative_relative_tolerance": directional_relative_tolerance,
        },
        "sources": {
            "response_panel": {"path": str(panel_path), "sha256": digest(panel_path), "receipt": str(args.panel_receipt), "receipt_sha256": digest(args.panel_receipt)},
            "coefficients": {"path": str(coefficients_path), "sha256": digest(coefficients_path)},
            "covariance": {"path": str(covariance_path), "sha256": digest(covariance_path)},
            "slopes": {"path": str(args.slopes), "sha256": digest(args.slopes)},
            "fair": {"path": str(args.fair), "sha256": digest(args.fair)},
            "cpc": {"path": str(args.cpc), "sha256": digest(args.cpc)},
            "diagnostic": {"path": str(expected_path), "sha256": digest(expected_path), "receipt": str(args.diagnostic_receipt), "receipt_sha256": digest(args.diagnostic_receipt)},
        },
        "claim_gates": {"published_coefficient_covariance_delta_method": True, "joint_climate_structural_or_adaptation_uncertainty": False, "probabilistic_total_scc_interval": False, "full_precipitation_agriculture_scc": False},
        "limitations": [
            "The interval is a first-order normal delta approximation using only the published 49-by-49 coefficient covariance.",
            "The coefficient draw is common across climate models; climate-model spread is not treated as sampling uncertainty.",
            "Market structure, adaptation, tail, transport, valuation, climate response, and omitted precipitation mechanisms are not probabilistically combined.",
        ],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "result": result["result"], "validation": result["validation"]}, indent=2))


if __name__ == "__main__":
    main()
