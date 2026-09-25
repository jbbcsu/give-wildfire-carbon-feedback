#!/usr/bin/env python3
"""Decompose the central annual-rainfall quantity SCC by country and climate model."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from estimate_quantity_coefficient_delta_uncertainty import (
    CHUNK,
    DEMAND,
    ETA,
    PRTP,
    PULSE,
    SUPPLY,
    USD2020,
    VALUE,
    PublishedEstimate,
    coefficient_design,
    digest,
    require,
)


def country_scc(
    panel: pd.DataFrame,
    slopes: pd.DataFrame,
    model: str,
    temperature: np.ndarray,
    discount: np.ndarray,
    coefficients: np.ndarray,
    terms: tuple[str, ...],
    currency_scalar: float,
) -> pd.DataFrame:
    selected = slopes.loc[
        slopes.source.eq(model) & slopes.slope_available, ["iso3", "patterns.area"]
    ]
    require(not selected.duplicated("iso3").any(), f"duplicate slopes for {model}")
    work = (
        panel.merge(selected, on="iso3", how="inner", validate="many_to_one")
        .sort_values(["iso3", "native_lat_index", "native_lon_index"])
        .reset_index(drop=True)
    )
    linear_design, squared_design, _ = coefficient_design(work, terms)
    linear = np.einsum("ij,j->i", linear_design, coefficients, optimize=False)
    squared = np.einsum("ij,j->i", squared_design, coefficients, optimize=False)
    require(
        np.max(np.abs(linear - work.baseline_linear_precipitation_index.to_numpy(float)))
        <= 2e-13,
        f"linear index differs for {model}",
    )
    require(
        np.max(np.abs(squared - work.baseline_squared_precipitation_index.to_numpy(float)))
        <= 2e-13,
        f"squared index differs for {model}",
    )

    values = work[VALUE].to_numpy(float)
    iso = work.iso3.to_numpy()
    starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
    countries = iso[starts]
    country_values = np.add.reduceat(values, starts)
    slope = work["patterns.area"].to_numpy(float) / work.annual_precip_mean_mm.to_numpy(float)
    market_a = -(1.0 - DEMAND) / (SUPPLY + DEMAND)
    normalization = currency_scalar * (12.0 / 44.0) / (1e9 * PULSE) * USD2020
    result = np.zeros(len(starts), dtype=float)
    for begin in range(0, len(temperature), CHUNK):
        end = min(begin + CHUNK, len(temperature))
        pulse_temperature = temperature[begin:end]
        precip_change = slope[:, None] * pulse_temperature[None, :]
        response = (
            linear[:, None] * precip_change
            + squared[:, None] * (2.0 * precip_change + np.square(precip_change))
        )
        country_output = np.add.reduceat(np.exp(response) * values[:, None], starts, axis=0)
        log_shift = np.log(country_output / country_values[:, None])
        damages = (
            -country_values[:, None]
            * np.expm1(market_a * log_shift)
            / (market_a * (1.0 + SUPPLY))
        )
        result += np.sum(
            damages * (discount[begin:end] * normalization)[None, :], axis=1
        )
    return pd.DataFrame(
        {
            "climate_model": model,
            "iso3": countries,
            "partial_scc_usd2020_per_tco2": result,
        }
    )


def summarize_country_components(result: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    """Average country components over a fixed model denominator, filling absent support with zero."""
    require(set(result.climate_model.unique()).issubset(set(models)), "unexpected climate model")
    require(not result.duplicated(["climate_model", "iso3"]).any(), "duplicate country-model component")
    support = result.groupby("iso3").climate_model.nunique()
    matrix = result.pivot(
        index="iso3", columns="climate_model", values="partial_scc_usd2020_per_tco2"
    )
    matrix = matrix.reindex(columns=models).fillna(0.0)
    return pd.DataFrame(
        {
            "iso3": matrix.index,
            "equal_model_mean_usd2020_per_tco2": matrix.mean(axis=1),
            "climate_model_min_usd2020_per_tco2": matrix.min(axis=1),
            "climate_model_max_usd2020_per_tco2": matrix.max(axis=1),
            "climate_models_with_slope": support.reindex(matrix.index).astype(int),
        }
    ).sort_values("equal_model_mean_usd2020_per_tco2").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-receipt", type=Path, required=True)
    parser.add_argument("--slopes", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--cpc", type=Path, required=True)
    parser.add_argument("--diagnostic-receipt", type=Path, required=True)
    parser.add_argument("--output-table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh receipt output required")
    require(not args.output_table.exists(), "fresh table output required")

    panel_receipt = json.loads(args.panel_receipt.read_text())
    diagnostic = json.loads(args.diagnostic_receipt.read_text())
    require(panel_receipt["schema"] == "hultgren_quantity_response_panel/v1", "panel receipt differs")
    panel_path = Path(panel_receipt["output"]["path"])
    market_receipt_path = Path(diagnostic["sources"]["market_paths"]["receipt"])
    market_receipt = json.loads(market_receipt_path.read_text())
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
    panel = pd.read_parquet(panel_path)
    slopes = pd.read_csv(args.slopes)
    fair = pd.read_csv(args.fair)
    years = np.arange(2020, 2301)
    temperature = (
        fair.loc[fair.pulse_size_gtc.eq(PULSE) & fair.year.isin(years)]
        .sort_values("year")
        .difference_k.to_numpy(float)
    )
    cpc = pd.read_csv(args.cpc).set_index("year").loc[years, "net_cpc_2005usd_per_person"].to_numpy(float)
    discount = np.power(cpc[0] / cpc, ETA) / np.power(1.0 + PRTP, years - 2020)
    currency_scalar = float(market_receipt["currency"]["central_scalar"])
    models = sorted(slopes.source.unique())
    require(len(models) == 26, "climate-model support differs")

    frames = [
        country_scc(
            panel,
            slopes,
            model,
            temperature,
            discount,
            np.asarray(estimate.coefficients, float),
            tuple(estimate.terms),
            currency_scalar,
        )
        for model in models
    ]
    result = pd.concat(frames, ignore_index=True)

    expected_path = Path(diagnostic["output"]["path"])
    require(digest(expected_path) == diagnostic["output"]["sha256"], "diagnostic hash differs")
    expected = pd.read_csv(expected_path)
    expected = expected.loc[
        expected.pulse_size_gtc.eq(PULSE)
        & expected.adaptation.eq("fixed")
        & expected.tail_rule.eq("uncapped")
        & expected.elasticity_id.eq("hultgren_pair_010_004")
        & expected.yield_to_supply_mapping.eq("horizontal_output")
        & expected.discount_rate_label.eq("2.0%")
    ].set_index("climate_model")
    reconstructed = result.groupby("climate_model").partial_scc_usd2020_per_tco2.sum()
    require(set(reconstructed.index) == set(expected.index), "diagnostic climate-model labels differ")
    errors = reconstructed.reindex(expected.index) - expected.partial_scc_diagnostic_usd2020_per_tco2
    maximum_error = float(errors.abs().max())
    require(math.isfinite(maximum_error), "nonfinite model reconstruction error")
    require(maximum_error <= 2e-14, f"country decomposition does not reconstruct diagnostic: {maximum_error}")

    # A country can lack an eligible precipitation slope in a particular model.
    # The global estimand assigns that model-country zero contribution, rather
    # than averaging the country only over models in which it is present.
    country = summarize_country_components(result, models)
    args.output_table.parent.mkdir(parents=True, exist_ok=True)
    country.to_csv(args.output_table, index=False)
    mean_global = float(country.equal_model_mean_usd2020_per_tco2.sum())
    expected_mean = float(expected.partial_scc_diagnostic_usd2020_per_tco2.mean())
    require(abs(mean_global - expected_mean) <= 2e-14, "equal-model global mean differs")
    negative = country.loc[country.equal_model_mean_usd2020_per_tco2 < 0]
    positive = country.loc[country.equal_model_mean_usd2020_per_tco2 > 0]

    def records(frame: pd.DataFrame, n: int = 10) -> list[dict]:
        return json.loads(frame.head(n).to_json(orient="records", double_precision=15))

    receipt = {
        "schema": "quantity_scc_country_decomposition/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "central_fixed_uncapped_two_percent_country_decomposition_complete",
        "estimand": "country contributions to the equal-26-model central annual-maize rainfall-quantity SCC at the GIVE 2% schedule",
        "summary": {
            "countries": int(len(country)),
            "climate_models": len(models),
            "global_equal_model_mean_usd2020_per_tco2": mean_global,
            "negative_country_count": int(len(negative)),
            "positive_country_count": int(len(positive)),
            "gross_negative_country_sum_usd2020_per_tco2": float(negative.equal_model_mean_usd2020_per_tco2.sum()),
            "gross_positive_country_sum_usd2020_per_tco2": float(positive.equal_model_mean_usd2020_per_tco2.sum()),
            "largest_negative_contributors": records(negative),
            "largest_positive_contributors": records(positive.sort_values("equal_model_mean_usd2020_per_tco2", ascending=False)),
        },
        "validation": {
            "maximum_model_reconstruction_error_usd2020_per_tco2": maximum_error,
            "global_mean_reconstruction_error_usd2020_per_tco2": abs(mean_global - expected_mean),
        },
        "output": {
            "path": str(args.output_table),
            "rows": int(len(country)),
            "sha256": digest(args.output_table),
        },
        "sources": {
            "panel_receipt": {"path": str(args.panel_receipt), "sha256": digest(args.panel_receipt)},
            "diagnostic_receipt": {"path": str(args.diagnostic_receipt), "sha256": digest(args.diagnostic_receipt)},
            "slopes": {"path": str(args.slopes), "sha256": digest(args.slopes)},
            "fair": {"path": str(args.fair), "sha256": digest(args.fair)},
            "cpc": {"path": str(args.cpc), "sha256": digest(args.cpc)},
        },
        "claim_gates": {
            "central_quantity_channel_geographic_accounting": True,
            "country_causal_effects": False,
            "country_total_precipitation_agriculture_scc": False,
            "full_precipitation_agriculture_scc": False,
        },
        "limitations": [
            "Country contributions are accounting components of the narrow annual-maize rainfall-quantity benchmark, not local causal estimates.",
            "The decomposition holds the published response, fixed adaptation, uncapped tail rule, central market, and GIVE 2% schedule fixed.",
            "Equal climate-model weighting is a design summary and does not assign probabilities to models.",
        ],
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "summary": receipt["summary"], "validation": receipt["validation"]}, indent=2))


if __name__ == "__main__":
    main()
