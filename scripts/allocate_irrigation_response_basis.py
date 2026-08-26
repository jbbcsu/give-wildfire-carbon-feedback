#!/usr/bin/env python3
"""Build regime bases before fixed-area allocation to one GDHY outcome.

This executable implements the required order-of-operations for the frozen
minimal predictive diagnostic. Its seasonal/stage basis is not the complete or
frozen production feature set. It intentionally does not emit primitive
precipitation, and a diagnostic fit requires the evaluator's explicit
contract-aware prebuilt-basis mode. It fits no response and authorizes no
causal interpretation or SCC input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from allocate_outcome_exposures import (
    PANEL_REQUIRED,
    allocate,
    read_table,
    require_columns,
    write_table,
)


CONTRACT_ID = "gdhy_aggregate_irrigation_basis_v1"
BASIS_ORDER = "regime_basis_before_fixed_area_weighting"
VALID_BLOCK = "seasonal or a nonblank alphanumeric stage label"


def block_prefix(block: str) -> str:
    normalized = str(block).strip()
    if normalized == "seasonal":
        return ""
    if not normalized or not normalized.replace("_", "").isalnum():
        raise ValueError(f"Basis block must be {VALID_BLOCK}")
    return f"{normalized}_"


def basis_names(block: str) -> dict[str, str]:
    prefix = block_prefix(block)
    return {
        "temperature": f"{prefix}tmean_c",
        "precipitation": f"{prefix}precip_mm",
        "dry_spell": f"{prefix}cdd_max_days",
        "wet_extreme": f"{prefix}rx1day_mm",
        "log_precipitation": f"{prefix}log1p_precip_mm",
        "interaction": f"{prefix}tmean_x_log1p_precip",
    }


def build_regime_basis(
    panel: pd.DataFrame, blocks: list[str]
) -> tuple[pd.DataFrame, list[str]]:
    """Return a copy with registered nonlinear bases built within each regime."""
    if not blocks or len(blocks) != len(set(blocks)):
        raise ValueError("Declare at least one unique basis block")
    require_columns(panel, PANEL_REQUIRED, "Exposure panel")
    frame = panel.copy()
    features: list[str] = []
    for block in blocks:
        names = basis_names(block)
        regime_inputs = [
            names["temperature"],
            names["precipitation"],
            names["dry_spell"],
            names["wet_extreme"],
        ]
        require_columns(frame, set(regime_inputs), f"{block} regime weather inputs")
        derived = [names["log_precipitation"], names["interaction"]]
        if any(name in panel.columns for name in derived):
            raise ValueError(
                f"Derived basis columns for {block} already exist; rebuild them from "
                "regime-specific primitives before any irrigation aggregation"
            )
        numeric = frame[regime_inputs].apply(pd.to_numeric, errors="coerce")
        if not np.isfinite(numeric.to_numpy(dtype=float)).all():
            raise ValueError(f"{block} regime weather inputs must be finite numeric values")
        for name in [names["precipitation"], names["dry_spell"], names["wet_extreme"]]:
            if (numeric[name] < 0).any():
                raise ValueError(f"{name} must be nonnegative")
        frame[regime_inputs] = numeric
        frame[names["log_precipitation"]] = np.log1p(frame[names["precipitation"]])
        frame[names["interaction"]] = (
            frame[names["temperature"]] * frame[names["log_precipitation"]]
        )
        features.extend(
            [
                names["temperature"],
                names["log_precipitation"],
                names["dry_spell"],
                names["wet_extreme"],
                names["interaction"],
            ]
        )
    frame["response_basis_contract_id"] = CONTRACT_ID
    frame["basis_allocation_order"] = BASIS_ORDER
    return frame, features


def allocate_registered_basis(
    panel: pd.DataFrame,
    weights: pd.DataFrame,
    expected: list[str],
    blocks: list[str],
    *,
    exclude_missing_weight_cells: bool = False,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Construct bases by regime, then area-weight them to one outcome row."""
    basis_panel, features = build_regime_basis(panel, blocks)
    output, audit = allocate(
        basis_panel,
        weights,
        features,
        expected,
        exclude_missing_weight_cells=exclude_missing_weight_cells,
    )
    output["exposure_allocation"] = BASIS_ORDER
    output["basis_allocation_order"] = BASIS_ORDER
    output["response_basis_contract_id"] = CONTRACT_ID
    output["nonlinear_post_allocation_transform_authorized"] = False
    output["legacy_diagnostic_evaluator_compatible"] = False
    output["explicit_prebuilt_diagnostic_mode_compatible"] = True
    output["diagnostic_fit_authorized"] = True
    output["production_feature_basis_complete"] = False
    output["production_fit_authorized"] = False
    audit.update(
        {
            "response_basis_contract_id": CONTRACT_ID,
            "basis_blocks": blocks,
            "basis_allocation_order": BASIS_ORDER,
            "basis_features": features,
            "primitive_precipitation_emitted": False,
            "nonlinear_post_allocation_transform_authorized": False,
            "legacy_diagnostic_evaluator_compatible": False,
            "explicit_prebuilt_diagnostic_mode_compatible": True,
            "diagnostic_fit_authorized": True,
            "production_feature_basis_complete": False,
            "production_fit_authorized": False,
            "estimand": "aggregate_log_yield_reduced_form_design_only",
        }
    )
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--panel",
        action="append",
        required=True,
        help="Regime-specific primitive-weather panel; repeat for separate files",
    )
    parser.add_argument("--weights", required=True)
    parser.add_argument(
        "--basis-block",
        action="append",
        required=True,
        help="Use seasonal, or repeat stage labels such as stage1, stage2, stage3",
    )
    parser.add_argument("--expected-irrigation", action="append", required=True)
    parser.add_argument("--exclude-missing-weight-cells", action="store_true")
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()

    frames = [read_table(Path(filename)) for filename in args.panel]
    panel = pd.concat(frames, ignore_index=True)
    weights = read_table(Path(args.weights))
    output, audit = allocate_registered_basis(
        panel,
        weights,
        args.expected_irrigation,
        args.basis_block,
        exclude_missing_weight_cells=args.exclude_missing_weight_cells,
    )
    audit["input_panel_files"] = [str(Path(filename)) for filename in args.panel]
    write_table(output, Path(args.out))
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
