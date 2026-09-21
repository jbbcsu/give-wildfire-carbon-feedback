#!/usr/bin/env python3
"""Render the audited five-ESM weather ledger without manual transcription."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from compare_five_esm_maize_area_weather import ESMS
from compare_three_esm_maize_area_weather import FEATURES, SCENARIOS


LABELS = {
    "precip_mm": "Season rainfall (mm)",
    "stage1_precip_mm": "Early-stage rainfall (mm)",
    "stage2_precip_mm": "Middle-stage rainfall (mm)",
    "stage3_precip_mm": "Late-stage rainfall (mm)",
    "wet_days_n": "Wet days (days)",
    "cdd_max_days": "Longest dry spell (days)",
    "rx1day_mm": "Rx1day (mm)",
    "rx5day_mm": "Rx5day (mm)",
    "tmean_c": "Season mean temperature (C)",
}
SHORT = {
    "gfdl-esm4": "GFDL",
    "ipsl-cm6a-lr": "IPSL",
    "mpi-esm1-2-hr": "MPI",
    "mri-esm2-0": "MRI",
    "ukesm1-0-ll": "UKESM",
}
SCENARIO_LABEL = {"ssp370": "SSP3-7.0", "ssp585": "SSP5-8.5"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sign_counts(values: list[float]) -> str:
    positive = sum(value > 0 for value in values)
    negative = sum(value < 0 for value in values)
    zero = len(values) - positive - negative
    return f"{positive} positive / {negative} negative / {zero} zero"


def render(result: dict, audit: dict, result_sha: str, audit_sha: str) -> str:
    if result["status"] != "five_esm_fixed_maize_area_weather_only_not_forced_response_or_scc":
        raise ValueError("wrong primary result status")
    if audit["status"] != "independent_five_esm_fixed_area_weather_ledger_and_source_sample_passed":
        raise ValueError("independent audit did not pass")
    if audit["primary_sha256"] != result_sha:
        raise ValueError("audit is not bound to the supplied primary result")
    if result["esms"] != list(ESMS) or result["scenarios"] != list(SCENARIOS):
        raise ValueError("five-ESM matrix identity changed")
    if (result.get("models_are_not_probability_draws") is not True
            or result.get("yield_damage_scc_estimated") is not False
            or audit.get("bound_annual_source_manifests") != 120
            or audit.get("no_yield_damage_scc_estimated") is not True):
        raise ValueError("interpretation or audit-completeness gate changed")
    contrasts = result["scenario_minus_ssp126"]
    lines = [
        "# Five-ESM crop-area-weighted rainfed-maize weather contrasts",
        "",
        "This is a **direct daily [ISIMIP3b climate-input](https://doi.org/10.48364/ISIMIP.842396.1)",
        "diagnostic**, not an",
        "anthropogenic or per-kelvin precipitation response, agricultural yield",
        "effect, damage estimate, or SCC result. Fixed [MIRCA-OS v2](https://www.hydroshare.org/resource/e4582ca0042148338bb5e0148b749ed6/)",
        "year-2000",
        f"rainfed-maize weights retain {result['matched_calendar_cells']:,} cells",
        f"and {result['matched_area_fraction']:.4%} of mapped positive crop area",
        "identically across all 120 ESM-by-scenario-by-year panels. Unsupported",
        "cells are not imputed.",
        "",
    ]
    for scenario in SCENARIOS[1:]:
        lines.extend([
            f"## {SCENARIO_LABEL[scenario]} minus SSP1-2.6, 2092--2099 mean",
            "",
            "| Daily-derived crop-season feature | " + " | ".join(SHORT[x] for x in ESMS) + " | Signs |",
            "|---|" + "---:|" * len(ESMS) + "---:|",
        ])
        for feature in FEATURES:
            values = [contrasts[esm][scenario][feature]["area_weighted"] for esm in ESMS]
            lines.append("| " + LABELS[feature] + " | "
                         + " | ".join(f"{value:+.3f}" for value in values)
                         + " | " + sign_counts(values) + " |")
        lines.append("")
    lines.extend([
        "The sign column is a count across five named models, **not** a probability,",
        "confidence interval, or model-weighted estimate. Scenario contrasts combine",
        "forcing differences, non-CO2 influences, bias-adjustment behavior, and one",
        "realization's internal variability. The eight terminal years do not define a",
        "sampling distribution.",
        "",
        "The independent checker rebound all 120 annual source manifests, recomputed",
        f"{audit['annual_numeric_checks']:,} annual ledger values and",
        f"{audit['contrast_numeric_checks']:,} scenario contrasts, and performed",
        f"{audit['fixed_source_tile_checks']:,} fixed source-tile checks. The primary",
        f"result SHA-256 is `{result_sha}` and the audit SHA-256 is `{audit_sha}`.",
        "No yield, crop price, irrigation adaptation, agricultural welfare, or GIVE",
        "SCC pathway was evaluated by this weather-only comparison.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("fresh output required")
    result_sha, audit_sha = sha(args.result), sha(args.audit)
    text = render(json.loads(args.result.read_text()), json.loads(args.audit.read_text()),
                  result_sha, audit_sha)
    args.out.write_text(text)
    print(args.out)


if __name__ == "__main__":
    main()
