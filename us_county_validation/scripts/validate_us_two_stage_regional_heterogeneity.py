#!/usr/bin/env python3
"""Independently validate the two-stage U.S. geographic diagnostic outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--memo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    receipt = json.loads(args.receipt.read_text())
    require(receipt["status"] == "descriptive_geographic_outputs_all_linked_chain_promotion_closed", "receipt status differs")
    for item in receipt["sources"].values():
        path = ROOT / item["path"]
        require(digest(path) == item["sha256"], f"source hash differs: {path}")
    outputs = {}
    for name, item in receipt["outputs"].items():
        path = ROOT / item["path"]
        require(digest(path) == item["sha256"], f"output hash differs: {path}")
        frame = pd.read_csv(path)
        require(len(frame) == item["rows"], f"output rows differ: {name}")
        outputs[name] = frame

    stage2 = outputs["stage2_gates"]
    state = outputs["state_diagnostics"]
    require(len(stage2) == 12 and not stage2.duplicated(["practice", "family", "reference_quantile"]).any(), "stage-2 keys differ")
    recomputed_all = (
        stage2.spatial_inference_pass.astype(bool)
        & stage2.leave_state_gate_pass.astype(bool)
        & stage2.terminal_stability_pass.astype(bool)
        & stage2.preidentified_influence_pass.astype(bool)
    )
    require(recomputed_all.equals(stage2.all_stage2_association_gates_pass.astype(bool)), "stage-2 conjunction differs")
    require(not stage2.causal_effect_gate_pass.astype(bool).any(), "causal gate opened")
    require(len(state) == 20 and not state.duplicated(["state", "practice"]).any(), "state diagnostic keys differ")
    require((state.patterns == 3).all(), "pattern count differs")
    require(not state.stage1_validated_multi_model_gate_pass.astype(bool).any(), "stage-1 ensemble gate opened")
    require(not state.stage2_quantity_all_contrast_gates_pass.astype(bool).any(), "quantity stability gate opened")
    require(not state.linked_chain_promoted.astype(bool).any(), "linked-chain row promoted")
    require((state.climate_slope_min_mm_per_k <= state.climate_slope_max_mm_per_k).all(), "climate ranges invalid")
    require((state.transport_diagnostic_min_percent_yield_per_k <= state.transport_diagnostic_max_percent_yield_per_k).all(), "transport ranges invalid")
    require(receipt["audit"]["stage2_cells_passing_all_association_gates"] == int(recomputed_all.sum()), "stage-2 pass count differs")
    require(receipt["audit"]["linked_chain_rows_promoted"] == 0, "receipt promoted linked chain")
    for gate in ("validated_multi_model_climate_attribution", "stable_quantity_response_all_contrasts", "state_specific_causal_effect", "national_yield_effect", "damage", "scc"):
        require(receipt["claim_gates"][gate] is False, f"claim gate opened: {gate}")
    memo = args.memo.read_text()
    for text in (
        "Stage 1: climate forcing -> crop-season precipitation or drought",
        "Stage 2: precipitation or drought -> county yield",
        "-4.30%",
        "[-5.02%, -3.57%]",
        "Only 4 of 20 state-practice rows",
        "only 3 of 20 have the same nonzero transported-yield",
        "Zero rows are promoted",
        "not state-specific fitted effects",
    ):
        require(text in memo, f"memo lacks evidence boundary: {text}")

    result = {
        "schema": "us_two_stage_regional_heterogeneity_validation/v1",
        "status": "pass",
        "source_receipt": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "memo": {"path": str(args.memo), "sha256": digest(args.memo)},
        "checks": 23,
        "stage2_rows": len(stage2),
        "state_diagnostic_rows": len(state),
        "linked_chain_rows_promoted": int(state.linked_chain_promoted.astype(bool).sum()),
        "claim_gates": receipt["claim_gates"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
