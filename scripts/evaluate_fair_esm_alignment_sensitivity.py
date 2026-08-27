#!/usr/bin/env python3
"""Evaluate two algebraically equivalent FAIR-to-ESM affine alignments.

This is a bounded sensitivity and support diagnostic.  It deliberately does
not select a production reference window, feature response, damage, or SCC.
"""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_isimip3b_five_esm_holdout_smoke import _display_path, _path, sha256
from validate_give_fair_temperature_paths import validate as validate_fair_paths
from validate_paired_feature_emulator import validate_pairs, validate_training_design


CONFIG_SCHEMA = "fair_esm_alignment_sensitivity_config_v1"
CONFIG_ROLE = "bounded_affine_fair_to_esm_alignment_sensitivity_not_production_feature_response_damage_or_scc"
METHODS = {"absolute_anomaly_mapping", "centered_coordinate_mapping"}


def support(value: float, lower: float, upper: float) -> str:
    if value < lower:
        return "below"
    if value > upper:
        return "above"
    return "within"


def fit_affine_surface(gmst: np.ndarray, feature: np.ndarray) -> tuple[float, float]:
    gmst = np.asarray(gmst, dtype=float)
    feature = np.asarray(feature, dtype=float)
    if gmst.shape != feature.shape or gmst.size < 2:
        raise ValueError("affine surface requires matched nontrivial arrays")
    if not np.isfinite(gmst).all() or not np.isfinite(feature).all():
        raise ValueError("affine surface inputs must be finite")
    centered = gmst - float(gmst.mean())
    denominator = float(np.sum(centered * centered))
    if denominator <= 0 or not np.isfinite(denominator):
        raise ValueError("affine surface has degenerate GMST support")
    slope = float(np.sum(centered * (feature - float(feature.mean()))) / denominator)
    intercept = float(feature.mean() - slope * gmst.mean())
    return intercept, slope


def aligned_feature(
    method: str,
    fair_temperature: float,
    fair_reference: float,
    esm_reference: float,
    intercept: float,
    slope: float,
) -> tuple[float, float]:
    """Return mapped absolute ESM temperature and conditional-mean feature."""
    if method not in METHODS:
        raise ValueError(f"unknown alignment method: {method}")
    mapped_temperature = esm_reference + (fair_temperature - fair_reference)
    if method == "absolute_anomaly_mapping":
        feature = intercept + slope * mapped_temperature
    else:
        feature_at_reference = intercept + slope * esm_reference
        feature = feature_at_reference + slope * (fair_temperature - fair_reference)
    return float(mapped_temperature), float(feature)


def validate_method_equivalence(pairs: pd.DataFrame, atol: float) -> float:
    keys = ["esm_id", "member_id", "year", "feature_family", "pulse_scale"]
    if set(pairs["alignment_method"].astype(str)) != METHODS:
        raise ValueError("alignment output lacks the exact registered method set")
    if pairs.duplicated(keys + ["alignment_method"]).any():
        raise ValueError("alignment output has duplicate method/key rows")
    maxima: list[float] = []
    for column in (
        "baseline_temperature_k",
        "pulse_temperature_k",
        "baseline_feature",
        "pulse_feature",
        "direct_difference",
        "centered_difference",
    ):
        wide = pairs.pivot(index=keys, columns="alignment_method", values=column)
        if set(wide.columns.astype(str)) != METHODS or wide.isna().any().any():
            raise ValueError(f"alignment comparison is incomplete for {column}")
        difference = np.abs(
            wide["absolute_anomaly_mapping"].to_numpy(float)
            - wide["centered_coordinate_mapping"].to_numpy(float)
        )
        maximum = float(difference.max(initial=0.0))
        maxima.append(maximum)
        if maximum > atol:
            raise ValueError(f"affine alignment methods disagree for {column}: {maximum}")
    return max(maxima, default=0.0)


def build(config_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("FAIR-to-ESM alignment sensitivity contract identity changed")
    limitations = config.get("limitations", {})
    for gate in (
        "production_alignment_selected",
        "production_emulator_authorized",
        "damage_or_scc_authorized",
    ):
        if limitations.get(gate) is not False:
            raise ValueError(f"alignment sensitivity unexpectedly opens {gate}")

    root = config_path.parent.parent
    inputs = config["inputs"]
    paths = {
        "training": _path(root, str(inputs["training_path"])),
        "fair_paths": _path(root, str(inputs["fair_paths_path"])),
        "fair_config": _path(root, str(inputs["fair_config_path"])),
    }
    for name, path in paths.items():
        if not path.is_file() or sha256(path) != str(inputs[f"{name}_sha256"]):
            raise ValueError(f"{name} input hash changed")
    fair_audit = validate_fair_paths(paths["fair_config"], paths["fair_paths"])

    alignment = config["alignment"]
    methods = [str(value) for value in alignment["methods"]]
    if set(methods) != METHODS or len(methods) != len(METHODS):
        raise ValueError("alignment methods changed")
    reference_start = int(alignment["reference_start_year"])
    reference_end = int(alignment["reference_end_year"])
    evaluation_start = int(alignment["evaluation_start_year"])
    evaluation_end = int(alignment["evaluation_end_year"])
    first_divergence_year = int(alignment["first_divergence_year"])
    pulse_scale_unit = str(alignment["pairing_pulse_scale_unit"])
    if pulse_scale_unit != "tonnes_C":
        raise ValueError("paired feature validator pulse-scale unit must remain tonnes_C")
    if not evaluation_start <= reference_start <= reference_end <= evaluation_end:
        raise ValueError("reference window must lie inside the evaluation interval")

    training = pd.read_parquet(paths["training"])
    members, families = validate_training_design(training)
    annual = (
        training.groupby(
            ["esm_id", "member_id", "scenario", "year", "feature_family", "gmst_value_k"],
            as_index=False,
            observed=True,
        )["feature_value"]
        .mean()
    )
    fair = pd.read_csv(paths["fair_paths"])
    fair = fair.loc[fair["year"].between(evaluation_start, evaluation_end)].copy()
    if fair.empty:
        raise ValueError("FAIR evaluation interval is empty")
    fair_reference_rows = fair.loc[
        (fair["pulse_size_gtc"] == 0)
        & fair["year"].between(reference_start, reference_end),
        "baseline_temperature_c",
    ]
    if len(fair_reference_rows) != reference_end - reference_start + 1:
        raise ValueError("FAIR reference window is incomplete")
    fair_reference = float(fair_reference_rows.mean())

    rows: list[dict[str, object]] = []
    receipts: list[dict[str, object]] = []
    reference_scenario = str(alignment["reference_scenario"])
    for (esm_id, family), fit in annual.groupby(["esm_id", "feature_family"], sort=True):
        fit = fit.copy()
        intercept, slope = fit_affine_surface(
            fit["gmst_value_k"].to_numpy(float), fit["feature_value"].to_numpy(float)
        )
        reference = fit.loc[
            (fit["scenario"].astype(str) == reference_scenario)
            & fit["year"].between(reference_start, reference_end),
            "gmst_value_k",
        ]
        if len(reference) != reference_end - reference_start + 1:
            raise ValueError(f"{esm_id}/{family}: incomplete ESM reference window")
        esm_reference = float(reference.mean())
        feature_min = float(fit["feature_value"].min())
        feature_max = float(fit["feature_value"].max())
        temperature_min = float(fit["gmst_value_k"].min())
        temperature_max = float(fit["gmst_value_k"].max())
        receipts.append({
            "esm_id": str(esm_id),
            "feature_family": str(family),
            "training_rows": int(len(fit)),
            "intercept": intercept,
            "slope_per_k": slope,
            "esm_reference_temperature_k": esm_reference,
            "fair_reference_temperature_c": fair_reference,
            "training_temperature_min_k": temperature_min,
            "training_temperature_max_k": temperature_max,
            "training_feature_min": feature_min,
            "training_feature_max": feature_max,
        })
        member_id = members[str(esm_id)]
        for record in fair.itertuples(index=False):
            for method in methods:
                baseline_temperature, baseline_feature = aligned_feature(
                    method,
                    float(record.baseline_temperature_c),
                    fair_reference,
                    esm_reference,
                    intercept,
                    slope,
                )
                pulse_temperature, raw_pulse_feature = aligned_feature(
                    method,
                    float(record.pulse_temperature_c),
                    fair_reference,
                    esm_reference,
                    intercept,
                    slope,
                )
                # Evaluate the affine finite difference directly from the pinned
                # FAIR delta.  Subtracting two O(1) feature levels for a
                # O(1e-8 K) pulse loses enough precision to create a false
                # non-convergence failure at the smallest pulse size.
                direct_difference = slope * float(record.difference_k)
                centered_difference = slope * float(record.difference_k)
                pulse_feature = baseline_feature + direct_difference
                residual_id = (
                    f"{esm_id}-{member_id}-{int(record.year)}-conditional-mean-zero-residual-v1"
                )
                rows.append({
                    "draw_id": f"fair-alignment-{method}-v1",
                    "alignment_method": method,
                    "esm_id": str(esm_id),
                    "member_id": member_id,
                    "year": int(record.year),
                    "first_divergence_year": first_divergence_year,
                    "feature_family": str(family),
                    # The generic paired-feature validator's convergence
                    # column is unitless.  Use the declared tonnes-C scale here so
                    # its absolute numerical tolerance is not applied to a
                    # needlessly tiny GtC representation.
                    "pulse_scale": float(record.pulse_size_gtc) * 1.0e9,
                    "pulse_scale_unit": pulse_scale_unit,
                    "pulse_size_gtc": float(record.pulse_size_gtc),
                    "baseline_residual_id": residual_id,
                    "pulse_residual_id": residual_id,
                    "residual_value": 0.0,
                    "fair_reference_temperature_c": fair_reference,
                    "esm_reference_temperature_k": esm_reference,
                    "baseline_temperature_k": baseline_temperature,
                    "pulse_temperature_k": pulse_temperature,
                    "raw_pulse_feature_evaluation": raw_pulse_feature,
                    "temperature_support_min_k": temperature_min,
                    "temperature_support_max_k": temperature_max,
                    "baseline_temperature_support": support(
                        baseline_temperature, temperature_min, temperature_max
                    ),
                    "pulse_temperature_support": support(
                        pulse_temperature, temperature_min, temperature_max
                    ),
                    "baseline_feature": baseline_feature,
                    "pulse_feature": pulse_feature,
                    "support_min": feature_min,
                    "support_max": feature_max,
                    "baseline_support": support(baseline_feature, feature_min, feature_max),
                    "pulse_support": support(pulse_feature, feature_min, feature_max),
                    "direct_difference": direct_difference,
                    "centered_difference": centered_difference,
                })
    pairs = pd.DataFrame(rows)
    validate_pairs(pairs, members)
    equivalence_atol = float(alignment["equivalence_atol"])
    raw_level_disagreement = float(
        np.max(np.abs(
            pairs["raw_pulse_feature_evaluation"].to_numpy(float)
            - pairs["pulse_feature"].to_numpy(float)
        ))
    )
    if raw_level_disagreement > equivalence_atol:
        raise ValueError(
            "stable affine pulse evaluation disagrees with direct level evaluation: "
            f"{raw_level_disagreement}"
        )
    maximum_method_disagreement = validate_method_equivalence(pairs, equivalence_atol)
    metadata = {
        "config": {"path": _display_path(config_path, root), "sha256": sha256(config_path)},
        "inputs": [
            {"name": name, "path": _display_path(path, root), "sha256": sha256(path)}
            for name, path in paths.items()
        ],
        "members": members,
        "feature_families": sorted(families),
        "reference_scenario": reference_scenario,
        "reference_years": [reference_start, reference_end],
        "evaluation_years": [evaluation_start, evaluation_end],
        "first_divergence_year": first_divergence_year,
        "pairing_pulse_scale_unit": pulse_scale_unit,
        "fair_reference_temperature_c": fair_reference,
        "fair_temperature_audit": fair_audit,
        "fits": receipts,
        "maximum_alignment_method_disagreement": maximum_method_disagreement,
        "maximum_raw_level_vs_stable_pulse_feature_disagreement": raw_level_disagreement,
        "equivalence_atol": equivalence_atol,
    }
    return pairs, metadata


def _support_counts(pairs: pd.DataFrame, prefix: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for method, block in pairs.groupby("alignment_method", sort=True):
        result[str(method)] = {
            side: block[f"{side}_{prefix}"].value_counts().sort_index().astype(int).to_dict()
            for side in ("baseline", "pulse")
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--pairs-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    pairs, metadata = build(config_path)
    args.pairs_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(args.pairs_out, index=False)
    root = config_path.parent.parent
    implementation = Path(__file__).resolve()
    audit = {
        "schema": "fair_esm_alignment_sensitivity_v1",
        "role": CONFIG_ROLE,
        **metadata,
        "implementation": {"path": _display_path(implementation, root), "sha256": sha256(implementation)},
        "pair_rows": int(len(pairs)),
        "alignment_methods": sorted(METHODS),
        "feature_support_counts": _support_counts(pairs, "support"),
        "temperature_support_counts": _support_counts(pairs, "temperature_support"),
        "common_zero_residual": True,
        "zero_pulse_identity": True,
        "pre_divergence_identity": True,
        "direct_centered_agreement": True,
        "decreasing_pulse_convergence": True,
        "affine_method_equivalence": True,
        "pairs_output": {"artifact_name": args.pairs_out.name, "sha256": sha256(args.pairs_out)},
        "production_alignment_selected": False,
        "production_emulator_authorized": False,
        "damage_or_scc_authorized": False,
        "limitations": [
            "The 2012--2014 reference window is an engineering sensitivity, not a production choice.",
            "The affine aggregate feature surfaces were not promoted by holdout evidence.",
            "The zero residual is shared exactly but is not a stochastic production weather path.",
            "No yield response, damage, welfare, or SCC value is produced.",
        ],
        "result": "passed",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "FAIR-to-ESM alignment sensitivity passed: "
        f"{len(pairs)} rows; maximum method disagreement "
        f"{metadata['maximum_alignment_method_disagreement']:.3g}"
    )


if __name__ == "__main__":
    main()
