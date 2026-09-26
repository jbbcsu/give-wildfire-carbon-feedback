#!/usr/bin/env python3
"""Summarize country heterogeneity under the three registered adaptation rules.

This is scenario accounting for the five-ESM late-century maize transport. It
is not an estimated adaptation response, welfare damage, or marginal SCC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = ["native_lat_index", "native_lon_index"]
SCENARIOS = {
    "fixed": {"annual_attenuation_rate": 0.0, "cap": 0.0},
    "trend": {"annual_attenuation_rate": 0.003, "cap": 0.35},
    "upper": {"annual_attenuation_rate": 0.007, "cap": 0.70},
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


def factor(year: int, scenario: str) -> float:
    spec = SCENARIOS[scenario]
    attenuation = min(spec["annual_attenuation_rate"] * max(year - 2020, 0), spec["cap"])
    return 1.0 - attenuation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component-directory", type=Path, required=True)
    parser.add_argument("--moderators", type=Path, required=True)
    parser.add_argument("--country-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.country_output.exists() and not args.receipt.exists(), "fresh outputs required")

    mapping = pd.read_parquet(args.moderators, columns=[*KEYS, "country_code"])
    require(not mapping.duplicated(KEYS).any(), "duplicate country mapping")
    mapping = mapping.loc[mapping.country_code.notna()].copy()
    paths = sorted(args.component_directory.glob("*_timing_component_cells_20260925.parquet"))
    require(len(paths) == 5, "five component-cell files required")
    frames: list[pd.DataFrame] = []
    sources: list[dict] = []
    reconstruction: list[dict] = []
    for path in paths:
        receipt_path = path.with_name(path.name.replace("_cells_", "_transport_")).with_suffix(".json")
        receipt = json.loads(receipt_path.read_text())
        require(receipt["component_cell_output"]["sha256"] == digest(path), "component hash differs")
        frame = pd.read_parquet(
            path,
            columns=["climate_model", "harvest_year", *KEYS, "analysis_weight", "precipitation_delta_log_yield"],
        )
        require(not frame.duplicated(["climate_model", "harvest_year", *KEYS]).any(), "duplicate cell-year")
        require(np.isfinite(frame[["analysis_weight", "precipitation_delta_log_yield"]]).all().all(), "nonfinite input")
        require((frame.analysis_weight > 0).all(), "nonpositive weight")
        frame = frame.merge(mapping, on=KEYS, how="left", validate="many_to_one")
        require(frame.country_code.notna().all(), "unmapped component cell")
        model = str(frame.climate_model.iloc[0])
        require(frame.climate_model.eq(model).all(), "multiple climate models in file")
        total_weight = float(frame.analysis_weight.sum())
        model_check = {"climate_model": model, "scenarios": {}}
        for scenario in SCENARIOS:
            factors = frame.harvest_year.map(lambda year: factor(int(year), scenario)).to_numpy(float)
            raw = frame.precipitation_delta_log_yield.to_numpy(float)
            adapted = np.where(raw < 0.0, raw * factors, raw)
            work = pd.DataFrame(
                {
                    "climate_model": model,
                    "country_code": frame.country_code.to_numpy(),
                    "scenario": scenario,
                    "weighted_response": frame.analysis_weight.to_numpy(float) * adapted,
                    "analysis_weight": frame.analysis_weight.to_numpy(float),
                }
            )
            grouped = work.groupby(["climate_model", "country_code", "scenario"], as_index=False).agg(
                weighted_response=("weighted_response", "sum"),
                analysis_weight=("analysis_weight", "sum"),
                rows=("analysis_weight", "size"),
            )
            grouped["mean_delta_log_yield"] = grouped.weighted_response / grouped.analysis_weight
            grouped["global_contribution"] = grouped.weighted_response / total_weight
            frames.append(grouped)
            reconstructed = float(grouped.global_contribution.sum())
            expected = float(receipt["pooled_weighted"][scenario]["precipitation_common_positive_support"]["weighted_mean_delta_log_yield"])
            require(abs(reconstructed - expected) <= 2e-12, f"{model}/{scenario} reconstruction failed")
            model_check["scenarios"][scenario] = {
                "reconstructed": reconstructed,
                "source": expected,
                "absolute_error": abs(reconstructed - expected),
            }
        reconstruction.append(model_check)
        sources.append({"path": str(path), "sha256": digest(path), "receipt": str(receipt_path), "receipt_sha256": digest(receipt_path)})

    country_model = pd.concat(frames, ignore_index=True).sort_values(["scenario", "country_code", "climate_model"])
    require(country_model.climate_model.nunique() == 5, "five climate models not retained")
    args.country_output.parent.mkdir(parents=True, exist_ok=True)
    country_model.to_csv(args.country_output, index=False)

    country = country_model.groupby(["scenario", "country_code"], as_index=False).agg(
        climate_models=("climate_model", "nunique"),
        mean_contribution=("global_contribution", "mean"),
        minimum_contribution=("global_contribution", "min"),
        maximum_contribution=("global_contribution", "max"),
        negative_models=("global_contribution", lambda values: int((values < 0).sum())),
        positive_models=("global_contribution", lambda values: int((values > 0).sum())),
    )
    require((country.climate_models == 5).all(), "country support is not balanced")
    summaries = {}
    for scenario in SCENARIOS:
        group = country.loc[country.scenario.eq(scenario)]
        negative = group.loc[group.mean_contribution < 0]
        positive = group.loc[group.mean_contribution > 0]
        summaries[scenario] = {
            "global_equal_model_mean_log_yield": float(group.mean_contribution.sum()),
            "gross_negative_country_contribution": float(negative.mean_contribution.sum()),
            "gross_positive_country_contribution": float(positive.mean_contribution.sum()),
            "countries_mean_negative": int(len(negative)),
            "countries_mean_positive": int(len(positive)),
            "countries_negative_all_five_models": int((group.negative_models == 5).sum()),
            "countries_positive_all_five_models": int((group.positive_models == 5).sum()),
            "countries_mixed_sign_across_models": int(((group.negative_models > 0) & (group.positive_models > 0)).sum()),
        }
    wide = country.pivot(index="country_code", columns="scenario", values="mean_contribution")
    require(set(wide.columns) == set(SCENARIOS), "adaptation columns differ")
    require(np.all(wide["upper"].to_numpy() + 1e-14 >= wide["trend"].to_numpy()), "upper is not monotone")
    require(np.all(wide["trend"].to_numpy() + 1e-14 >= wide["fixed"].to_numpy()), "trend is not monotone")
    sign_flips = {
        "fixed_negative_to_upper_positive": int(((wide.fixed < 0) & (wide.upper > 0)).sum()),
        "fixed_positive_to_upper_negative": int(((wide.fixed > 0) & (wide.upper < 0)).sum()),
    }
    result = {
        "schema": "hultgren_adaptation_country_heterogeneity/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "exogenous_adaptation_scenario_heterogeneity_not_damage_or_scc",
        "estimand": "country contributions to production-weighted late-century maize precipitation log-yield response under registered loss-only attenuation scenarios",
        "scenarios": SCENARIOS,
        "country_count": int(wide.shape[0]),
        "summaries": summaries,
        "sign_flips": sign_flips,
        "model_reconstructions": reconstruction,
        "output": {"path": str(args.country_output), "rows": int(len(country_model)), "sha256": digest(args.country_output)},
        "sources": {"components": sources, "moderators": {"path": str(args.moderators), "sha256": digest(args.moderators)}},
        "claim_gates": {
            "country_scenario_accounting": True,
            "estimated_adaptation_response": False,
            "causal_country_damage": False,
            "marginal_scc": False,
        },
        "limitations": [
            "The adaptation rules are exogenous loss-only attenuation scenarios, not estimated farmer behavior.",
            "Scenario endpoints combine multiple forcings and internal variability and are not marginal CO2 pulses.",
            "Country contributions are physical production-weighted log-yield accounting, not welfare damages.",
            "Five named climate models are structural scenarios, not probability draws.",
        ],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__))},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "country_count": result["country_count"], "summaries": summaries, "sign_flips": sign_flips}, indent=2))


if __name__ == "__main__":
    main()
