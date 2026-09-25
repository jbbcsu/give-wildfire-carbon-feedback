#!/usr/bin/env python3
"""Summarize country winners/losers in five-ESM maize rainfall components."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = ["native_lat_index", "native_lon_index"]
COMPONENTS = {
    "net": "precipitation_delta_log_yield",
    "quantity": "quantity_delta_log_yield",
    "timing_distribution": "timing_distribution_delta_log_yield",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component-directory", type=Path, required=True)
    parser.add_argument("--moderators", type=Path, required=True)
    parser.add_argument("--country-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.country_output.exists() and not args.receipt.exists(), "fresh outputs required")

    mapping = pd.read_parquet(args.moderators, columns=[*KEYS, "country_code"])
    require(len(mapping) == len(mapping.drop_duplicates(KEYS)), "duplicate country mapping")
    mapping = mapping.loc[mapping.country_code.notna()].copy()
    require(len(mapping) > 0, "country mapping is empty")
    grouped_frames = []
    input_records = []
    model_reconstructions = []
    paths = sorted(args.component_directory.glob("*_timing_component_cells_20260925.parquet"))
    require(len(paths) == 5, "five component-cell files required")
    for path in paths:
        receipt_path = path.with_name(path.name.replace("_cells_", "_transport_").replace(".parquet", ".json"))
        # Wrapper names contain one fewer repeated 'transport' token.
        if not receipt_path.exists():
            slug = path.name.split("_")[1]
            receipt_path = args.component_directory / f"hultgren_{slug}_timing_component_transport_20260925.json"
        receipt = json.loads(receipt_path.read_text())
        require(receipt["component_cell_output"]["sha256"] == digest(path), "component hash differs")
        frame = pd.read_parquet(path)
        require(len(frame) == len(frame.drop_duplicates(["climate_model", "harvest_year", *KEYS])), "duplicate cell-year")
        require(np.isfinite(frame[["analysis_weight", *COMPONENTS.values()]]).all().all(), "nonfinite component input")
        require((frame.analysis_weight > 0.0).all(), "nonpositive analysis weight")
        require(
            np.allclose(
                frame[COMPONENTS["net"]],
                frame[COMPONENTS["quantity"]] + frame[COMPONENTS["timing_distribution"]],
                rtol=0.0,
                atol=1e-10,
            ),
            "cell decomposition differs",
        )
        frame = frame.merge(mapping, on=KEYS, how="left", validate="many_to_one")
        require(frame.country_code.notna().all(), "unmapped component cell")
        model = frame.climate_model.iloc[0]
        require(frame.climate_model.eq(model).all(), "multiple climate models in component file")
        total_weight = float(frame.analysis_weight.sum())
        reconstructed = {}
        for label, column in COMPONENTS.items():
            mean = float(np.average(frame[column], weights=frame.analysis_weight))
            source_label = {
                "net": "precipitation_common_positive_support",
                "quantity": "precipitation_quantity_reference_scaling",
                "timing_distribution": "precipitation_distribution_residual",
            }[label]
            expected = float(receipt["pooled_weighted"]["fixed"][source_label]["weighted_mean_delta_log_yield"])
            require(abs(mean - expected) <= 2e-12, f"{model} {label} aggregate reconstruction failed")
            reconstructed[label] = {"reconstructed": mean, "source": expected, "absolute_error": abs(mean - expected)}

        for column in COMPONENTS.values():
            frame[f"weighted_{column}"] = frame.analysis_weight * frame[column]
        grouped = frame.groupby(["climate_model", "country_code"], as_index=False).agg(
            analysis_weight=("analysis_weight", "sum"),
            rows=("analysis_weight", "size"),
            **{f"weighted_{label}": (f"weighted_{column}", "sum") for label, column in COMPONENTS.items()},
        )
        for label in COMPONENTS:
            grouped[f"mean_{label}_delta_log_yield"] = grouped[f"weighted_{label}"] / grouped.analysis_weight
            grouped[f"global_{label}_contribution"] = grouped[f"weighted_{label}"] / total_weight
        grouped_frames.append(grouped)
        model_reconstructions.append({"climate_model": model, "total_weight": total_weight, "components": reconstructed})
        input_records.append({"path": str(path), "sha256": digest(path), "rows": len(frame), "receipt": str(receipt_path), "receipt_sha256": digest(receipt_path)})

    country_model = pd.concat(grouped_frames, ignore_index=True).sort_values(["country_code", "climate_model"])
    require(country_model.climate_model.nunique() == 5, "five climate models not retained")
    args.country_output.parent.mkdir(parents=True, exist_ok=True)
    country_model.to_csv(args.country_output, index=False)

    country = country_model.groupby("country_code", as_index=False).agg(
        climate_models=("climate_model", "nunique"),
        mean_net_contribution=("global_net_contribution", "mean"),
        mean_quantity_contribution=("global_quantity_contribution", "mean"),
        mean_timing_distribution_contribution=("global_timing_distribution_contribution", "mean"),
        minimum_net_contribution=("global_net_contribution", "min"),
        maximum_net_contribution=("global_net_contribution", "max"),
        negative_net_models=("global_net_contribution", lambda values: int((values < 0).sum())),
        positive_net_models=("global_net_contribution", lambda values: int((values > 0).sum())),
    )
    require((country.climate_models == 5).all(), "country support is not balanced across models")
    require(np.allclose(country.mean_net_contribution, country.mean_quantity_contribution + country.mean_timing_distribution_contribution, rtol=0.0, atol=2e-12), "country mean decomposition differs")
    equal_model = {
        label: float(country[f"mean_{label}_contribution"].sum())
        for label in COMPONENTS
    }
    gross = {
        "negative_net": float(country.loc[country.mean_net_contribution < 0, "mean_net_contribution"].sum()),
        "positive_net": float(country.loc[country.mean_net_contribution > 0, "mean_net_contribution"].sum()),
    }
    ranked = country.reindex(country.mean_net_contribution.abs().sort_values(ascending=False).index)
    top = ranked.head(15).to_dict(orient="records")
    result = {
        "schema": "hultgren_timing_country_heterogeneity/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "scenario_heterogeneity_diagnostic_not_damage_or_scc",
        "estimand": "country contributions to physical-production-weighted maize log-yield response, SSP5-8.5 minus SSP1-2.6, 2092-2100, equal mean across five named ESMs",
        "country_count": int(len(country)),
        "equal_model_global_log_yield_components": equal_model,
        "gross_country_net_contributions": gross,
        "countries": {
            "mean_net_negative": int((country.mean_net_contribution < 0).sum()),
            "mean_net_positive": int((country.mean_net_contribution > 0).sum()),
            "negative_all_five_models": int((country.negative_net_models == 5).sum()),
            "positive_all_five_models": int((country.positive_net_models == 5).sum()),
            "mixed_sign_across_models": int(((country.negative_net_models > 0) & (country.positive_net_models > 0)).sum()),
        },
        "timing": {
            "absolute_global_share_of_quantity": abs(equal_model["timing_distribution"]) / abs(equal_model["quantity"]),
            "countries_timing_amplifies_quantity_sign": int(((country.mean_quantity_contribution * country.mean_timing_distribution_contribution) > 0).sum()),
            "countries_timing_offsets_quantity_sign": int(((country.mean_quantity_contribution * country.mean_timing_distribution_contribution) < 0).sum()),
        },
        "top_absolute_country_contributions": top,
        "model_reconstructions": model_reconstructions,
        "sources": {
            "component_files": input_records,
            "moderators": {"path": str(args.moderators), "sha256": digest(args.moderators)},
        },
        "output": {"path": str(args.country_output), "sha256": digest(args.country_output), "rows": len(country_model)},
        "claim_gates": {
            "country_scenario_heterogeneity": True,
            "causal_country_damage": False,
            "timing_marginal_scc": False,
            "total_precipitation_scc": False,
        },
        "limitations": [
            "Scenario endpoints include multiple forcings and internal variability and are not a marginal CO2 pulse.",
            "The timing component is a quantity-reference residual, not a uniquely identified causal effect.",
            "Country contributions use conditional maize production-value weights and are not welfare damages.",
            "Five named climate models are structural scenarios, not probability draws.",
        ],
        "implementation": {"path": str(Path(__file__)), "sha256": digest(Path(__file__))},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "country_count", "equal_model_global_log_yield_components", "gross_country_net_contributions", "countries", "timing")}, indent=2))


if __name__ == "__main__":
    main()
