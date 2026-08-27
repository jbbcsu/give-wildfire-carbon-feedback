#!/usr/bin/env python3
"""Build a bounded empirical common-random-number feature-pairing smoke."""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_isimip3b_five_esm_holdout_smoke import _display_path, _path, sha256
from validate_paired_feature_emulator import (
    validate_holdouts,
    validate_pairs,
    validate_training_design,
)


CONFIG_SCHEMA = "isimip3b_bounded_paired_feature_path_config_v1"
CONFIG_ROLE = "aggregate_feature_common_random_number_numerical_gate_not_fair_pulse_production_emulator_damage_or_scc"


def support(value: float, lower: float, upper: float) -> str:
    if value < lower:
        return "below"
    if value > upper:
        return "above"
    return "within"


def build(config_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("paired feature-path contract identity changed")
    limits = config.get("limitations", {})
    for gate in ("production_emulator_authorized", "damage_or_scc_authorized"):
        if limits.get(gate) is not False:
            raise ValueError(f"bounded paired path unexpectedly opens {gate}")
    root = config_path.parent.parent
    inputs = config["inputs"]
    paths = {
        name: _path(root, str(inputs[f"{name}_path"]))
        for name in ("training", "esm_holdouts", "scenario_holdouts")
    }
    for name, path in paths.items():
        if not path.is_file() or sha256(path) != str(inputs[f"{name}_sha256"]):
            raise ValueError(f"{name} input hash changed")

    training = pd.read_parquet(paths["training"])
    members, families = validate_training_design(training)
    holdouts = pd.concat(
        [pd.read_csv(paths["esm_holdouts"]), pd.read_csv(paths["scenario_holdouts"])],
        ignore_index=True,
    )
    validate_holdouts(holdouts, set(members), families)

    pairing = config["pairing"]
    baseline_scenario = str(pairing["baseline_scenario"])
    first_divergence_year = int(pairing["first_divergence_year"])
    pulse_scales = [float(value) for value in pairing["pulse_scales_k"]]
    if pulse_scales.count(0.0) != 1 or len({value for value in pulse_scales if value > 0}) < 3:
        raise ValueError("pairing requires one zero and at least three distinct positive scales")
    if any(value < 0 for value in pulse_scales):
        raise ValueError("pulse scales must be nonnegative")

    annual = (
        training.groupby(
            ["esm_id", "member_id", "scenario", "year", "feature_family", "gmst_value_k"],
            as_index=False,
            observed=True,
        )["feature_value"]
        .mean()
    )
    rows: list[dict[str, object]] = []
    fit_receipts: list[dict[str, object]] = []
    for (esm_id, family), fit in annual.groupby(["esm_id", "feature_family"], sort=True):
        member_id = members[str(esm_id)]
        x = fit["gmst_value_k"].to_numpy(float)
        y = fit["feature_value"].to_numpy(float)
        centered = x - x.mean()
        denominator = float(np.sum(centered * centered))
        if denominator <= 0 or not np.isfinite(denominator):
            raise ValueError(f"{esm_id}/{family}: degenerate GMST support")
        slope = float(np.sum(centered * (y - y.mean())) / denominator)
        support_min, support_max = float(y.min()), float(y.max())
        baseline = fit.loc[fit["scenario"].astype(str) == baseline_scenario].copy()
        if baseline.empty:
            raise ValueError(f"{esm_id}/{family}: baseline scenario absent")
        fit_receipts.append({
            "esm_id": str(esm_id),
            "feature_family": str(family),
            "training_rows": int(len(fit)),
            "gmst_slope_per_k": slope,
            "support_min": support_min,
            "support_max": support_max,
        })
        for record in baseline.itertuples(index=False):
            baseline_feature = float(record.feature_value)
            residual_id = f"{esm_id}-{member_id}-{baseline_scenario}-{int(record.year)}-aggregate-residual"
            for pulse_scale in pulse_scales:
                delta = 0.0 if int(record.year) < first_divergence_year else pulse_scale
                if delta == 0:
                    pulse_feature = baseline_feature
                    centered_difference = 0.0
                    direct_difference = 0.0
                else:
                    direct_difference = slope * delta
                    pulse_feature = baseline_feature + direct_difference
                    centered_difference = direct_difference
                rows.append({
                    "draw_id": str(pairing["draw_id"]),
                    "esm_id": str(esm_id),
                    "member_id": member_id,
                    "year": int(record.year),
                    "first_divergence_year": first_divergence_year,
                    "feature_family": str(family),
                    "pulse_scale": pulse_scale,
                    "baseline_residual_id": residual_id,
                    "pulse_residual_id": residual_id,
                    "baseline_feature": baseline_feature,
                    "pulse_feature": pulse_feature,
                    "support_min": support_min,
                    "support_max": support_max,
                    "baseline_support": support(baseline_feature, support_min, support_max),
                    "pulse_support": support(pulse_feature, support_min, support_max),
                    "direct_difference": direct_difference,
                    "centered_difference": centered_difference,
                })
    pairs = pd.DataFrame(rows)
    validate_pairs(pairs, members)
    metadata = {
        "config": {"path": _display_path(config_path, root), "sha256": sha256(config_path)},
        "inputs": [
            {"name": name, "path": _display_path(path, root), "sha256": sha256(path)}
            for name, path in paths.items()
        ],
        "members": members,
        "feature_families": sorted(families),
        "fits": fit_receipts,
        "baseline_scenario": baseline_scenario,
        "first_divergence_year": first_divergence_year,
        "pulse_scales_k": pulse_scales,
    }
    return pairs, holdouts, metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--pairs-out", type=Path, required=True)
    parser.add_argument("--holdouts-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    pairs, holdouts, metadata = build(config_path)
    for path in (args.pairs_out, args.holdouts_out, args.audit_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(args.pairs_out, index=False)
    holdouts.to_csv(args.holdouts_out, index=False)
    root = config_path.parent.parent
    implementation = Path(__file__).resolve()
    support_counts = {
        side: pairs[f"{side}_support"].value_counts().sort_index().astype(int).to_dict()
        for side in ("baseline", "pulse")
    }
    audit = {
        "schema": "isimip3b_bounded_paired_feature_path_v1",
        "role": CONFIG_ROLE,
        **metadata,
        "implementation": {"path": _display_path(implementation, root), "sha256": sha256(implementation)},
        "pair_rows": int(len(pairs)),
        "holdout_rows": int(len(holdouts)),
        "support_counts": support_counts,
        "zero_pulse_all_year_identity": True,
        "pre_divergence_identity": True,
        "common_residual_innovations": True,
        "separate_baseline_pulse_support_flags": True,
        "direct_centered_agreement": True,
        "decreasing_pulse_convergence": True,
        "pairs_output": {"artifact_name": args.pairs_out.name, "sha256": sha256(args.pairs_out)},
        "holdouts_output": {"artifact_name": args.holdouts_out.name, "sha256": sha256(args.holdouts_out)},
        "fair_baseline_pulse_paths": False,
        "production_emulator_authorized": False,
        "damage_or_scc_authorized": False,
        "limitations": [
            "The paired path uses area-unweighted aggregate bounded cells and an artificial Kelvin perturbation, not FAIR.",
            "The linear surface is a numerical identity/convergence smoke and is not selected by the holdout scores.",
            "No yield response, damage, welfare, or SCC value is produced.",
        ],
        "result": "passed",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"bounded paired feature-path gate passed: {len(pairs)} pairs, {len(holdouts)} holdouts")


if __name__ == "__main__":
    main()
