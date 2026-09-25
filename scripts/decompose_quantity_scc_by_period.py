#!/usr/bin/env python3
"""Decompose the central annual-rainfall quantity SCC across time periods."""

from __future__ import annotations

import argparse
import json
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


PERIODS = ((2020, 2050), (2051, 2100), (2101, 2200), (2201, 2300))


def annual_scc(
    panel: pd.DataFrame,
    slopes: pd.DataFrame,
    model: str,
    years: np.ndarray,
    temperature: np.ndarray,
    discount: np.ndarray,
    coefficients: np.ndarray,
    terms: tuple[str, ...],
    currency_scalar: float,
) -> pd.DataFrame:
    selected = slopes.loc[
        slopes.source.eq(model) & slopes.slope_available, ["iso3", "patterns.area"]
    ]
    work = (
        panel.merge(selected, on="iso3", how="inner", validate="many_to_one")
        .sort_values(["iso3", "native_lat_index", "native_lon_index"])
        .reset_index(drop=True)
    )
    linear_design, squared_design, _ = coefficient_design(work, terms)
    linear = np.einsum("ij,j->i", linear_design, coefficients, optimize=False)
    squared = np.einsum("ij,j->i", squared_design, coefficients, optimize=False)
    values = work[VALUE].to_numpy(float)
    iso = work.iso3.to_numpy()
    starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
    country_values = np.add.reduceat(values, starts)
    slope = work["patterns.area"].to_numpy(float) / work.annual_precip_mean_mm.to_numpy(float)
    market_a = -(1.0 - DEMAND) / (SUPPLY + DEMAND)
    normalization = currency_scalar * (12.0 / 44.0) / (1e9 * PULSE) * USD2020
    contributions = np.zeros(len(years), dtype=float)
    undiscounted = np.zeros(len(years), dtype=float)
    for begin in range(0, len(years), CHUNK):
        end = min(begin + CHUNK, len(years))
        pulse_temperature = temperature[begin:end]
        precip_change = slope[:, None] * pulse_temperature[None, :]
        response = (
            linear[:, None] * precip_change
            + squared[:, None] * (2.0 * precip_change + np.square(precip_change))
        )
        country_output = np.add.reduceat(np.exp(response) * values[:, None], starts, axis=0)
        log_shift = np.log(country_output / country_values[:, None])
        damage = (
            -country_values[:, None]
            * np.expm1(market_a * log_shift)
            / (market_a * (1.0 + SUPPLY))
        ).sum(axis=0)
        undiscounted[begin:end] = damage * normalization
        contributions[begin:end] = damage * normalization * discount[begin:end]
    return pd.DataFrame(
        {
            "climate_model": model,
            "year": years,
            "undiscounted_scc_equivalent_usd2020_per_tco2_year": undiscounted,
            "discounted_scc_contribution_usd2020_per_tco2": contributions,
        }
    )


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
    require(not args.output.exists() and not args.output_table.exists(), "fresh outputs required")
    panel_receipt = json.loads(args.panel_receipt.read_text())
    diagnostic = json.loads(args.diagnostic_receipt.read_text())
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
    models = sorted(slopes.source.unique())
    frames = [
        annual_scc(
            panel,
            slopes,
            model,
            years,
            temperature,
            discount,
            np.asarray(estimate.coefficients, float),
            tuple(estimate.terms),
            float(market_receipt["currency"]["central_scalar"]),
        )
        for model in models
    ]
    result = pd.concat(frames, ignore_index=True)
    args.output_table.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output_table, index=False)

    expected_path = Path(diagnostic["output"]["path"])
    expected = pd.read_csv(expected_path)
    expected = expected.loc[
        expected.pulse_size_gtc.eq(PULSE)
        & expected.adaptation.eq("fixed")
        & expected.tail_rule.eq("uncapped")
        & expected.elasticity_id.eq("hultgren_pair_010_004")
        & expected.yield_to_supply_mapping.eq("horizontal_output")
        & expected.discount_rate_label.eq("2.0%")
    ].set_index("climate_model")
    totals = result.groupby("climate_model").discounted_scc_contribution_usd2020_per_tco2.sum()
    require(set(totals.index) == set(expected.index), "climate-model labels differ")
    errors = totals.reindex(expected.index) - expected.partial_scc_diagnostic_usd2020_per_tco2
    maximum_error = float(errors.abs().max())
    require(maximum_error <= 2e-14, f"annual contributions do not reconstruct diagnostic: {maximum_error}")

    annual_mean = result.groupby("year", as_index=False).agg(
        equal_model_mean_discounted_contribution=("discounted_scc_contribution_usd2020_per_tco2", "mean"),
        equal_model_mean_undiscounted_equivalent=("undiscounted_scc_equivalent_usd2020_per_tco2_year", "mean"),
    )
    period_rows = []
    total_mean = float(annual_mean.equal_model_mean_discounted_contribution.sum())
    post_pulse = result.loc[result.year > 2020]
    model_signs = post_pulse.groupby("climate_model").discounted_scc_contribution_usd2020_per_tco2.agg(
        all_negative=lambda values: bool((values < 0).all()),
        all_positive=lambda values: bool((values > 0).all()),
    )
    negative_models = model_signs.index[model_signs.all_negative].tolist()
    positive_models = model_signs.index[model_signs.all_positive].tolist()
    require(len(negative_models) == 25 and positive_models == ["MPI-ESM1-2-LR"],
            "post-pulse model sign support differs")
    require((model_signs.all_negative | model_signs.all_positive).all(),
            "a climate model changes annual contribution sign")
    for start, end in PERIODS:
        selected = annual_mean.loc[annual_mean.year.between(start, end)]
        contribution = float(selected.equal_model_mean_discounted_contribution.sum())
        period_rows.append(
            {
                "years": [start, end],
                "discounted_contribution_usd2020_per_tco2": contribution,
                "share_of_signed_total": contribution / total_mean,
                "mean_undiscounted_equivalent_usd2020_per_tco2_year": float(selected.equal_model_mean_undiscounted_equivalent.mean()),
            }
        )
    receipt = {
        "schema": "quantity_scc_period_decomposition/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "central_fixed_uncapped_two_percent_period_decomposition_complete",
        "estimand": "time-period contributions to the equal-26-model central annual-maize rainfall-quantity SCC at the GIVE 2% schedule",
        "summary": {
            "global_equal_model_mean_usd2020_per_tco2": total_mean,
            "periods": period_rows,
            "annual_contribution_min_usd2020_per_tco2": float(annual_mean.equal_model_mean_discounted_contribution.min()),
            "annual_contribution_max_usd2020_per_tco2": float(annual_mean.equal_model_mean_discounted_contribution.max()),
            "equal_model_post_pulse_negative_years": int((annual_mean.loc[annual_mean.year > 2020, "equal_model_mean_discounted_contribution"] < 0).sum()),
            "climate_models_negative_every_post_pulse_year": negative_models,
            "climate_models_positive_every_post_pulse_year": positive_models,
            "climate_models_with_post_pulse_sign_change": [],
        },
        "validation": {"maximum_model_reconstruction_error_usd2020_per_tco2": maximum_error},
        "output": {"path": str(args.output_table), "rows": len(result), "sha256": digest(args.output_table)},
        "sources": {
            "panel_receipt": {"path": str(args.panel_receipt), "sha256": digest(args.panel_receipt)},
            "diagnostic_receipt": {"path": str(args.diagnostic_receipt), "sha256": digest(args.diagnostic_receipt)},
            "slopes": {"path": str(args.slopes), "sha256": digest(args.slopes)},
            "fair": {"path": str(args.fair), "sha256": digest(args.fair)},
            "cpc": {"path": str(args.cpc), "sha256": digest(args.cpc)},
        },
        "claim_gates": {
            "central_quantity_channel_temporal_accounting": True,
            "causal_timing_effect": False,
            "full_precipitation_agriculture_scc": False,
        },
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
