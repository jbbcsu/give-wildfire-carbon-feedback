#!/usr/bin/env python3
"""Leave one state out of the registered U.S. paired-practice diagnostic.

This is a support-sensitivity audit of historical associations. It does not
turn the selected paired-practice sample into a causal irrigation estimate,
nationally representative result, damage function, or SCC input.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from estimate_us_paired_practice_gap_association import (
    PROJECT,
    build_paired_frame,
    fit,
    load_config,
    project_path,
    run,
    sha256,
)


DEFAULT_CONFIG = PROJECT / "us_county_validation/us_paired_practice_gap_association_v1.toml"
DEFAULT_REGISTERED = PROJECT / "data/provenance/us_paired_practice_gap_association_20260827.json"


def extract_contrasts(estimate: dict[str, Any]) -> dict[str, float]:
    result = {
        "quantity_increment_at_median_log_difference": float(
            estimate["contrasts"]["quantity_increment_at_median"]["fitted_log_yield_gap_difference"]
        )
    }
    if estimate["form"] == "quantity_timing":
        result["stage3_to_stage2_shift_log_difference"] = float(
            estimate["contrasts"]["stage3_to_stage2_shift"]["fitted_log_yield_gap_difference"]
        )
    if not all(math.isfinite(value) for value in result.values()):
        raise ValueError("contrast is nonfinite")
    return result


def summarize_jackknife(
    full: dict[str, float],
    omissions: list[dict[str, Any]],
    expected_states: set[str],
) -> dict[str, Any]:
    states = [str(row["omitted_state"]) for row in omissions]
    if len(states) != len(set(states)) or set(states) != expected_states:
        raise ValueError("jackknife does not omit every state exactly once")
    if not full or any(not math.isfinite(float(value)) or float(value) == 0 for value in full.values()):
        raise ValueError("full-sample contrasts must be finite and nonzero")
    summaries: dict[str, Any] = {}
    for name, full_value_raw in full.items():
        full_value = float(full_value_raw)
        values = [float(row["contrasts"][name]) for row in omissions]
        if any(not math.isfinite(value) for value in values):
            raise ValueError("jackknife contrast is nonfinite")
        summaries[name] = {
            "full_sample": full_value,
            "minimum_leave_one_state_out": min(values),
            "maximum_leave_one_state_out": max(values),
            "maximum_absolute_change_from_full": max(abs(value - full_value) for value in values),
            "same_sign_count": sum((value > 0) == (full_value > 0) for value in values),
            "omission_count": len(values),
        }
    return summaries


def registered_index(result: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    if result.get("schema") != "us_paired_practice_gap_association_result_v1":
        raise ValueError("registered paired-practice result schema changed")
    if result.get("causal_claim_authorized") is not False or result.get("scc_claim_authorized") is not False:
        raise ValueError("registered paired-practice result opens causal or SCC use")
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for estimate in result.get("estimates", []):
        key = (str(estimate["crop"]), str(estimate["form"]))
        if key in indexed:
            raise ValueError("registered paired-practice result duplicates an estimate")
        indexed[key] = estimate
    return indexed


def audit(config_path: Path, registered_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    panel_path = project_path(config["input"]["panel"])
    if sha256(panel_path) != config["input"]["expected_panel_sha256"]:
        raise ValueError("paired-practice panel hash differs from contract")
    paired = build_paired_frame(pd.read_parquet(panel_path), config)
    registered = json.loads(registered_path.read_text(encoding="utf-8"))
    indexed = registered_index(registered)
    reproduced = registered_index(run(config_path))
    expected_keys = {
        (str(crop), str(form))
        for crop in config["input"]["crops"] for form in config["models"]["forms"]
    }
    if set(indexed) != expected_keys or set(reproduced) != expected_keys:
        raise ValueError("registered or reproduced estimate matrix is incomplete")

    results: list[dict[str, Any]] = []
    for crop, form in sorted(expected_keys):
        full = extract_contrasts(indexed[(crop, form)])
        rerun = extract_contrasts(reproduced[(crop, form)])
        if any(abs(full[name] - rerun[name]) > 1e-12 for name in full):
            raise ValueError("registered paired-practice contrast did not reproduce")
        crop_frame = paired.loc[paired["outcome_crop"] == crop]
        states = set(map(str, crop_frame["state"].unique()))
        if len(states) < 3:
            raise ValueError(f"{crop} has too few states for a state jackknife")
        omissions: list[dict[str, Any]] = []
        for state in sorted(states):
            reduced = paired.loc[~((paired["outcome_crop"] == crop) & (paired["state"].astype(str) == state))]
            estimate = fit(reduced, crop, form, config)
            omissions.append({
                "omitted_state": state,
                "rows": int(estimate["rows"]),
                "counties": int(estimate["counties"]),
                "states": int(estimate["states"]),
                "contrasts": extract_contrasts(estimate),
            })
        results.append({
            "crop": crop,
            "form": form,
            "full_sample_rows": int(indexed[(crop, form)]["rows"]),
            "full_sample_counties": int(indexed[(crop, form)]["counties"]),
            "full_sample_states": sorted(states),
            "summary": summarize_jackknife(full, omissions, states),
            "omissions": omissions,
        })
    implementation = Path(__file__).resolve()
    return {
        "schema": "us_paired_practice_state_jackknife_v1",
        "status": "completed_historical_support_sensitivity_only",
        "input": {"path": config["input"]["panel"], "sha256": sha256(panel_path)},
        "config": {"path": str(config_path.relative_to(PROJECT)), "sha256": sha256(config_path)},
        "registered_result": {"path": str(registered_path.relative_to(PROJECT)), "sha256": sha256(registered_path)},
        "implementation": {"path": str(implementation.relative_to(PROJECT)), "sha256": sha256(implementation)},
        "results": results,
        "causal_claim_authorized": False,
        "national_representativeness_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
        "disclaimer": (
            "Leave-one-state-out stability is a support-sensitivity check for selected historical "
            "reporting counties, not a causal irrigation effect, national estimate, damage function, or SCC input."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--registered", type=Path, default=DEFAULT_REGISTERED)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.config.resolve(), args.registered.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(f"U.S. paired-practice state jackknife passed for {len(result['results'])} crop/model fits")


if __name__ == "__main__":
    main()
