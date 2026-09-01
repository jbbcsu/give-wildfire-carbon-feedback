#!/usr/bin/env python3
"""Compare SSP5-8.5 with SSP1-2.6 in the frozen latitude/window receipt."""

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


def evaluate(source_path: Path, expected_sha256: str) -> dict[str, object]:
    actual_sha256 = sha256(source_path)
    require(actual_sha256 == expected_sha256, "source receipt SHA-256 changed")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    require(
        source.get("schema") == "fishmip_control_adjusted_latitude_band_time_windows_v1",
        "source receipt schema changed",
    )
    for gate in ("forced_response_estimated", "matched_co2_pulse", "welfare_estimated", "damage_estimated", "scc_authorized"):
        require(source.get(gate) is False, f"source evidence boundary changed: {gate}")

    expected = {
        (scenario, start, end, band, forcing, model)
        for scenario in SCENARIOS
        for start, end in WINDOWS
        for band in BANDS
        for forcing in FORCINGS
        for model in MODELS
    }
    indexed: dict[tuple[str, int, int, str, str, str], float] = {}
    for row in source.get("trajectory_results", []):
        period = row.get("future_period")
        require(isinstance(period, dict), "future-period identity is absent")
        key = (
            str(row.get("climate_scenario")),
            int(period.get("start_year", -1)),
            int(period.get("end_year", -1)),
            str(row.get("latitude_band")),
            str(row.get("climate_forcing")),
            str(row.get("ecosystem_model")),
        )
        require(key not in indexed, "source trajectory is duplicated")
        value = float(row.get("band_mean_normalized_control_adjusted_change", np.nan))
        require(np.isfinite(value), "source trajectory mean is nonfinite")
        indexed[key] = value
    require(set(indexed) == expected, "source receipt lacks the exact frozen product")

    comparisons: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    for start, end in WINDOWS:
        for band in BANDS:
            values: list[float] = []
            for forcing in FORCINGS:
                for model in MODELS:
                    low = indexed[("ssp126", start, end, band, forcing, model)]
                    high = indexed[("ssp585", start, end, band, forcing, model)]
                    separation = high - low
                    values.append(separation)
                    comparisons.append({
                        "future_period": {"start_year": start, "end_year": end},
                        "latitude_band": band,
                        "climate_forcing": forcing,
                        "ecosystem_model": model,
                        "ssp126_band_mean_normalized_control_adjusted_change": low,
                        "ssp585_band_mean_normalized_control_adjusted_change": high,
                        "ssp585_minus_ssp126": separation,
                    })
            summaries.append({
                "future_period": {"start_year": start, "end_year": end},
                "latitude_band": band,
                "negative_trajectory_count": int(sum(value < 0 for value in values)),
                "minimum_ssp585_minus_ssp126": min(values),
                "median_ssp585_minus_ssp126": float(np.median(values)),
                "maximum_ssp585_minus_ssp126": max(values),
                "all_four_ssp585_more_negative": all(value < 0 for value in values),
            })

    require(len(comparisons) == 60 and len(summaries) == 15, "scenario-separation output is incomplete")
    return {
        "schema": "fishmip_control_adjusted_latitude_scenario_separation_v1",
        "status": "validated_scenario_separation_structural_sensitivity_only",
        "comparison": "ssp585_minus_ssp126_within_forcing_model_window_and_latitude_band",
        "trajectory_comparisons": comparisons,
        "band_window_summaries": summaries,
        "source": {"path": str(source_path), "sha256": actual_sha256},
        "implementation": {"path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "absolute_model_levels_averaged": False,
        "probability_interpretation": False,
        "forced_response_estimated": False,
        "country_or_eez_allocation_performed": False,
        "matched_co2_pulse": False,
        "welfare_estimated": False,
        "damage_estimated": False,
        "scc_authorized": False,
        "disclaimer": (
            "Scenario separation in structurally adjusted FishMIP density is not a probability, "
            "causal forced response, country allocation, welfare, damage, or SCC estimate."
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
    print("FishMIP latitude-band scenario-separation audit passed")


if __name__ == "__main__":
    main()
