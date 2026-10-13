#!/usr/bin/env python3
"""Summarize validated U.S. stage-2 gates and state-level linked-chain diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MODELS = [
    "PEEPS_MPI-ESM1-2-HR_published",
    "project_fit_GFDL-ESM4",
    "project_fit_IPSL-CM6A-LR",
]
PRACTICES = ["irrigated", "non_irrigated"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def find_record(records: list[dict], practice: str, family: str) -> dict:
    selected = [row for row in records if row["practice"] == practice and row["family"] == family]
    require(len(selected) == 1, f"expected one record for {practice}/{family}")
    return selected[0]


def stage2_gate_rows(result: dict) -> pd.DataFrame:
    """Create one row per frozen practice/family/reference contrast."""
    rows = []
    for full in result["full_sample"]:
        practice, family = full["practice"], full["family"]
        state = find_record(result["leave_one_state"], practice, family)
        temporal = find_record(result["temporal_validation"], practice, family)
        influence = find_record(result["preidentified_influence"], practice, family)
        for contrast in full["contrasts"]:
            quantile = float(contrast["reference_quantile"])
            state_gate = next(item for item in state["gates"] if float(item["reference_quantile"]) == quantile)
            temporal_gate = next(item for item in temporal["gates"] if float(item["reference_quantile"]) == quantile)
            influence_gate = next(item for item in influence["diagnostics"] if float(item["reference_quantile"]) == quantile)
            spatial_pass = bool(contrast["spatially_robust_excludes_zero"])
            state_pass = bool(state_gate["all_pass"])
            temporal_pass = bool(temporal_gate["all_pass"])
            influence_pass = bool(influence_gate["leave_row_pass"] and influence_gate["leave_county_pass"])
            rows.append({
                "practice": practice,
                "family": family,
                "reference_quantile": quantile,
                "reference_value": float(contrast["reference_value"]),
                "change": float(contrast["change"]),
                "estimate_percent_yield": float(contrast["estimate_percent_yield"]),
                "spatial_500km_ci_low_percent": float(contrast["normal_95_intervals_percent_yield"]["spatial_500km"][0]),
                "spatial_500km_ci_high_percent": float(contrast["normal_95_intervals_percent_yield"]["spatial_500km"][1]),
                "spatial_inference_pass": spatial_pass,
                "leave_state_gate_pass": state_pass,
                "leave_state_max_abs_dfbeta": float(state_gate["maximum_absolute_dfbeta"]),
                "terminal_stability_pass": temporal_pass,
                "terminal_abs_standardized_difference": float(temporal_gate["absolute_standardized_difference"]),
                "preidentified_influence_pass": influence_pass,
                "all_stage2_association_gates_pass": spatial_pass and state_pass and temporal_pass and influence_pass,
                "causal_effect_gate_pass": False,
                "damage_or_scc_gate_pass": False,
            })
    frame = pd.DataFrame(rows).sort_values(["practice", "family", "reference_quantile"]).reset_index(drop=True)
    require(len(frame) == 12 and not frame.duplicated(["practice", "family", "reference_quantile"]).any(), "stage-2 gate rows differ")
    return frame


def same_nonzero_sign(values: pd.Series) -> bool:
    numbers = values.to_numpy(dtype=float)
    return bool((numbers > 0).all() or (numbers < 0).all())


def state_diagnostic_rows(state: pd.DataFrame, stage2: pd.DataFrame, stage1_multi_model_gate: bool) -> pd.DataFrame:
    """Collapse three existing pattern transports without treating them as an ensemble."""
    required = {
        "model", "practice", "state", "counties", "mean_crop_season_precip_slope_mm_per_k",
        "estimate_percent_yield_per_k", "spatially_robust_excludes_zero",
    }
    require(required <= set(state.columns), "state diagnostic columns differ")
    require(set(state.model) == set(MODELS) and set(state.practice) == set(PRACTICES), "state model/practice support differs")
    require(not state.duplicated(["model", "practice", "state"]).any(), "duplicate state diagnostics")
    for (model, region), group in state.groupby(["model", "state"], sort=True):
        require(len(group) == 2, f"practice support differs for {model}/{region}")
        require(group.mean_crop_season_precip_slope_mm_per_k.nunique() == 1, f"climate slope differs by practice for {model}/{region}")

    quantity_all = (
        stage2.loc[stage2.family.eq("quantity")]
        .groupby("practice", sort=True).all_stage2_association_gates_pass.all()
        .to_dict()
    )
    rows = []
    for (practice, region), group in state.groupby(["practice", "state"], sort=True):
        require(set(group.model) == set(MODELS), f"pattern support differs for {practice}/{region}")
        climate = group.mean_crop_season_precip_slope_mm_per_k.astype(float)
        transported = group.estimate_percent_yield_per_k.astype(float)
        stage2_pass = bool(quantity_all[practice])
        rows.append({
            "state": region,
            "practice": practice,
            "patterns": len(group),
            "counties_min": int(group.counties.min()),
            "counties_max": int(group.counties.max()),
            "climate_slope_min_mm_per_k": float(climate.min()),
            "climate_slope_max_mm_per_k": float(climate.max()),
            "climate_slope_same_nonzero_sign": same_nonzero_sign(climate),
            "transport_diagnostic_min_percent_yield_per_k": float(transported.min()),
            "transport_diagnostic_max_percent_yield_per_k": float(transported.max()),
            "transport_diagnostic_same_nonzero_sign": same_nonzero_sign(transported),
            "spatially_robust_pattern_count": int(group.spatially_robust_excludes_zero.astype(bool).sum()),
            "stage1_validated_multi_model_gate_pass": bool(stage1_multi_model_gate),
            "stage2_quantity_all_contrast_gates_pass": stage2_pass,
            "linked_chain_promoted": bool(stage1_multi_model_gate and stage2_pass),
            "interpretation": "descriptive_state_support_pattern_transport_not_state_effect",
        })
    output = pd.DataFrame(rows).sort_values(["state", "practice"]).reset_index(drop=True)
    require(len(output) == 20, "expected ten states by two practices")
    require(not output.linked_chain_promoted.any(), "an unstable linked-chain diagnostic was promoted")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern-receipt", type=Path, required=True)
    parser.add_argument("--response-receipt", type=Path, required=True)
    parser.add_argument("--stage2-output", type=Path, required=True)
    parser.add_argument("--state-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    paths = [args.stage2_output, args.state_output, args.receipt]
    require(all(not path.exists() for path in paths), "fresh outputs required")

    pattern_receipt = json.loads(args.pattern_receipt.read_text())
    response_receipt = json.loads(args.response_receipt.read_text())
    require(pattern_receipt["schema"] == "us_corn_three_pattern_sensitivity/v1", "pattern receipt differs")
    require(pattern_receipt["claim_gates"]["validated_multi_model_climate_ensemble"] is False, "stage-1 gate unexpectedly open")
    require(response_receipt["claim_gates"]["historical_association"] is True, "historical association receipt differs")
    for gate in ("causal_effect", "climate_attribution", "damage", "national_effect", "scc"):
        require(response_receipt["claim_gates"][gate] is False, f"response claim gate opened: {gate}")

    state_path = ROOT / pattern_receipt["state_output"]["path"]
    result_path = ROOT / response_receipt["result"]["path"]
    require(digest(state_path) == pattern_receipt["state_output"]["sha256"], "state diagnostic changed")
    require(digest(result_path) == response_receipt["result"]["sha256"], "response result changed")
    state = pd.read_csv(state_path)
    result = json.loads(result_path.read_text())
    stage2 = stage2_gate_rows(result)
    summary = state_diagnostic_rows(state, stage2, False)

    args.stage2_output.parent.mkdir(parents=True, exist_ok=True)
    stage2.to_csv(args.stage2_output, index=False)
    summary.to_csv(args.state_output, index=False)
    receipt = {
        "schema": "us_two_stage_regional_heterogeneity/v1",
        "status": "descriptive_geographic_outputs_all_linked_chain_promotion_closed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "pattern_receipt": {"path": str(args.pattern_receipt), "sha256": digest(args.pattern_receipt)},
            "pattern_state_output": {"path": str(state_path.relative_to(ROOT)), "sha256": digest(state_path)},
            "response_receipt": {"path": str(args.response_receipt), "sha256": digest(args.response_receipt)},
            "response_result": {"path": str(result_path.relative_to(ROOT)), "sha256": digest(result_path)},
        },
        "outputs": {
            "stage2_gates": {"path": str(args.stage2_output), "rows": len(stage2), "sha256": digest(args.stage2_output)},
            "state_diagnostics": {"path": str(args.state_output), "rows": len(summary), "sha256": digest(args.state_output)},
        },
        "audit": {
            "stage2_cells_passing_all_association_gates": int(stage2.all_stage2_association_gates_pass.sum()),
            "stage2_cells_total": len(stage2),
            "state_practice_rows": len(summary),
            "state_practice_rows_with_climate_sign_agreement": int(summary.climate_slope_same_nonzero_sign.sum()),
            "state_practice_rows_with_transport_sign_agreement": int(summary.transport_diagnostic_same_nonzero_sign.sum()),
            "linked_chain_rows_promoted": int(summary.linked_chain_promoted.sum()),
        },
        "claim_gates": {
            "descriptive_state_support_diagnostic": True,
            "validated_multi_model_climate_attribution": False,
            "stable_quantity_response_all_contrasts": False,
            "state_specific_causal_effect": False,
            "national_yield_effect": False,
            "damage": False,
            "scc": False,
        },
        "required_interpretation": "State rows summarize existing pattern transports on selected support; they are not state-specific fitted effects, a probability-weighted climate ensemble, causal impacts, damages, or SCC inputs.",
        "implementation": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": digest(Path(__file__))},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], **receipt["audit"]}, sort_keys=True))


if __name__ == "__main__":
    main()
