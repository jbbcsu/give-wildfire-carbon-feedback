#!/usr/bin/env python3
"""Contrast ecosystem-model and climate-forcing sensitivity in FishMIP cells."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


SCENARIOS = ("ssp126", "ssp585")
FORCINGS = ("gfdl-esm4", "ipsl-cm6a-lr")
MODELS = ("boats", "ecoocean")
WINDOWS = ((2021, 2030), (2041, 2050), (2081, 2090))
BANDS = ("south_high", "south_mid", "tropics", "north_mid", "north_high")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def contrast_summary(values: list[float]) -> dict[str, object]:
    array = np.asarray(values, dtype=float)
    require(array.shape == (2,) and np.isfinite(array).all(), "contrast pair is invalid")
    return {
        "contrasts": values,
        "mean_absolute_contrast": float(np.abs(array).mean()),
        "root_mean_square_contrast": float(np.sqrt(np.mean(array**2))),
        "same_nonzero_sign": bool(np.all(array > 0) or np.all(array < 0)),
    }


def evaluate(source_path: Path, expected_sha256: str) -> dict[str, object]:
    observed_sha = sha256(source_path)
    require(observed_sha == expected_sha256, "source receipt SHA-256 changed")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    require(
        source.get("schema") == "fishmip_control_adjusted_latitude_band_time_windows_v1",
        "source receipt schema changed",
    )
    for gate in ("forced_response_estimated", "matched_co2_pulse", "welfare_estimated", "damage_estimated", "scc_authorized"):
        require(source.get(gate) is False, f"source evidence boundary changed: {gate}")
    expected = {
        (scenario, start, end, band, forcing, model)
        for scenario in SCENARIOS for start, end in WINDOWS for band in BANDS
        for forcing in FORCINGS for model in MODELS
    }
    indexed: dict[tuple[str, int, int, str, str, str], float] = {}
    for row in source.get("trajectory_results", []):
        period = row.get("future_period")
        require(isinstance(period, dict), "future-period identity is absent")
        key = (
            str(row.get("climate_scenario")), int(period.get("start_year", -1)),
            int(period.get("end_year", -1)), str(row.get("latitude_band")),
            str(row.get("climate_forcing")), str(row.get("ecosystem_model")),
        )
        require(key not in indexed, "source trajectory is duplicated")
        value = float(row.get("band_mean_normalized_control_adjusted_change", np.nan))
        require(np.isfinite(value), "source trajectory mean is nonfinite")
        indexed[key] = value
    require(set(indexed) == expected, "source receipt lacks the exact frozen product")

    cells = []
    for scenario in SCENARIOS:
        for start, end in WINDOWS:
            for band in BANDS:
                model_contrasts = [
                    indexed[(scenario, start, end, band, forcing, "ecoocean")]
                    - indexed[(scenario, start, end, band, forcing, "boats")]
                    for forcing in FORCINGS
                ]
                forcing_contrasts = [
                    indexed[(scenario, start, end, band, "ipsl-cm6a-lr", model)]
                    - indexed[(scenario, start, end, band, "gfdl-esm4", model)]
                    for model in MODELS
                ]
                model_summary = contrast_summary(model_contrasts)
                forcing_summary = contrast_summary(forcing_contrasts)
                model_rms = float(model_summary["root_mean_square_contrast"])
                forcing_rms = float(forcing_summary["root_mean_square_contrast"])
                dominant = "ecosystem_model" if model_rms > forcing_rms else (
                    "climate_forcing" if forcing_rms > model_rms else "tie"
                )
                cells.append({
                    "climate_scenario": scenario,
                    "future_period": {"start_year": start, "end_year": end},
                    "latitude_band": band,
                    "ecosystem_model_contrast_ecoocean_minus_boats": model_summary,
                    "climate_forcing_contrast_ipsl_minus_gfdl": forcing_summary,
                    "larger_rms_structural_contrast": dominant,
                })
    require(len(cells) == 30, "structural contrast output is incomplete")
    counts = {
        label: sum(cell["larger_rms_structural_contrast"] == label for cell in cells)
        for label in ("ecosystem_model", "climate_forcing", "tie")
    }
    return {
        "schema": "fishmip_structural_contrast_sensitivity_v1",
        "status": "validated_factor_contrasts_structural_sensitivity_only",
        "source": {"path": str(source_path), "sha256": observed_sha},
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "cells": cells,
        "larger_rms_structural_contrast_counts": counts,
        "contrast_definition": (
            "Within each scenario/window/latitude cell, ecosystem-model contrasts are EcoOcean minus BOATS "
            "within each forcing; climate-forcing contrasts are IPSL-CM6A-LR minus GFDL-ESM4 within each model."
        ),
        "probability_or_variance_decomposition": False,
        "forced_response_estimated": False,
        "country_or_eez_allocation_performed": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Two-by-two structural contrasts diagnose model dependence; they are not probability weights, "
            "a variance decomposition, causal forced response, allocation, welfare, damage, or SCC evidence."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.source, args.expected_source_sha256)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print("FishMIP structural-contrast sensitivity audit passed")


if __name__ == "__main__":
    main()
