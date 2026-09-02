#!/usr/bin/env python3
"""Validate the literature-constrained RIME-X feature benchmark contract.

This implements only independently written interpolation mechanics needed for a
bounded engineering smoke. It does not vendor RIME-X, fit the real feature
panel, or authorize a climate response, damages, or SCC use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np

from validate_isimip3b_structural_feature_response_contract import ESMS, FEATURES, SCENARIOS


SCHEMA = "isimip3b_rimex_feature_response_benchmark_contract_v1"
ARTICLE_DOI = "10.5194/gmd-19-6797-2026"
ARCHIVE_DOI = "10.5281/zenodo.21061984"
REPOSITORY_HEAD = "22f992114fdc8808710b1f5ef100d01d011aa6a6"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def interpolate_quantile_map(
    warming_levels: np.ndarray,
    quantiles: np.ndarray,
    values: np.ndarray,
    gmst: float,
    quantile: float,
) -> tuple[float, bool]:
    """Linearly interpolate a scalar indicator in quantile and warming level."""
    levels = np.asarray(warming_levels, dtype=float)
    probabilities = np.asarray(quantiles, dtype=float)
    surface = np.asarray(values, dtype=float)
    require(levels.ndim == probabilities.ndim == 1, "map coordinates must be one-dimensional")
    require(len(levels) >= 2 and len(probabilities) >= 2, "map needs at least two coordinates per axis")
    require(np.isfinite(levels).all() and np.isfinite(probabilities).all(), "map coordinates are nonfinite")
    require((np.diff(levels) > 0).all(), "warming levels must be strictly increasing")
    require((np.diff(probabilities) > 0).all(), "quantiles must be strictly increasing")
    require(surface.shape == (len(levels), len(probabilities)), "quantile-map shape changed")
    require(np.isfinite(surface).all(), "quantile map contains nonfinite values")
    require(((0 <= probabilities) & (probabilities <= 1)).all(), "quantiles leave [0,1]")
    require(np.isfinite(gmst) and np.isfinite(quantile), "query is nonfinite")
    support = bool(levels[0] <= gmst <= levels[-1] and probabilities[0] <= quantile <= probabilities[-1])
    if not support:
        return float("nan"), False
    at_levels = np.array([np.interp(quantile, probabilities, row) for row in surface])
    return float(np.interp(gmst, levels, at_levels)), True


def synthetic_pulse_smoke() -> dict[str, object]:
    levels = np.round(np.arange(-0.1, 0.1001, 0.1), 10)
    quantiles = np.linspace(0.0, 1.0, 101)
    values = np.array([[100.0 + 4.0 * level + 8.0 * q + 0.5 * level * q for q in quantiles] for level in levels])
    fixed_quantile = 0.37
    baseline = np.array([-0.02, 0.00, 0.02, 0.04])
    divergence_index = 2
    pulse_scales = [0.04, 0.02, 0.01]

    baseline_values = []
    baseline_support = []
    for gmst in baseline:
        value, support = interpolate_quantile_map(levels, quantiles, values, gmst, fixed_quantile)
        baseline_values.append(value)
        baseline_support.append(support)
    baseline_values = np.asarray(baseline_values)
    require(all(baseline_support), "synthetic baseline left support")

    zero_values = np.array([interpolate_quantile_map(levels, quantiles, values, gmst, fixed_quantile)[0] for gmst in baseline])
    require(np.array_equal(baseline_values, zero_values), "zero-pulse identity failed")

    normalized = []
    pulse_support_counts = []
    for scale in pulse_scales:
        pulse = baseline.copy()
        pulse[divergence_index:] += scale
        pulse_values = []
        support_flags = []
        for gmst in pulse:
            value, support = interpolate_quantile_map(levels, quantiles, values, gmst, fixed_quantile)
            pulse_values.append(value)
            support_flags.append(support)
        pulse_values = np.asarray(pulse_values)
        require(np.array_equal(pulse_values[:divergence_index], baseline_values[:divergence_index]), "pre-divergence identity failed")
        require(all(support_flags), "synthetic pulse left support")
        normalized.append((pulse_values - baseline_values) / scale)
        pulse_support_counts.append(sum(support_flags))
    max_normalized_disagreement = float(np.max(np.abs(normalized[0] - normalized[-1])))
    require(max_normalized_disagreement <= 1e-10, "decreasing-pulse convergence failed")

    outside_value, outside_support = interpolate_quantile_map(levels, quantiles, values, 0.11, fixed_quantile)
    require(not outside_support and np.isnan(outside_value), "out-of-support query was extrapolated")
    return {
        "schema": "isimip3b_rimex_quantile_map_engineering_smoke_v1",
        "status": "validated_synthetic_interpolation_and_pulse_mechanics_only",
        "warming_levels": levels.tolist(),
        "quantile_count": len(quantiles),
        "fixed_common_random_quantile": fixed_quantile,
        "time_steps": len(baseline),
        "zero_pulse_identity": True,
        "pre_divergence_identity": True,
        "baseline_support_count": sum(baseline_support),
        "pulse_support_counts": pulse_support_counts,
        "decreasing_positive_pulse_scales": pulse_scales,
        "maximum_normalized_pulse_disagreement": max_normalized_disagreement,
        "out_of_support_extrapolation_rejected": True,
    }


def validate(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "contract schema changed")
    require(config.get("primary_climate_route") == "direct_isimip3b_daily_feature_response", "primary route changed")
    require(config.get("fallback_climate_route") == "mesmer_m_tp_plus_published_daily_generator", "fallback route changed")
    for gate in ("production_promoted", "real_feature_fit_authorized", "fair_feature_response_authorized", "response_estimation_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")
    require(config.get("required_feature_families") == FEATURES, "feature family set changed")
    require(config.get("required_esm_ids") == ESMS, "ESM set changed")
    require(config.get("required_scenarios") == SCENARIOS, "scenario set changed")

    method = config.get("published_method", {})
    require(method.get("name") == "RIME-X" and method.get("software_version") == "1.0.0", "published method/version changed")
    require(method.get("article_doi") == ARTICLE_DOI, "article DOI changed")
    require(method.get("software_exact_archive_doi") == ARCHIVE_DOI, "exact software archive changed")
    require(method.get("reviewed_repository_head") == REPOSITORY_HEAD, "reviewed repository head changed")
    require(method.get("implementation_rule") == "independent_minimal_mechanics_smoke_only_no_vendored_rimex_code", "implementation boundary changed")

    quantile_map = config.get("quantile_map", {})
    require(quantile_map.get("warming_level_step_k") == 0.1, "warming-level grid changed")
    require(quantile_map.get("quantile_count") == 101, "quantile grid changed")
    require(quantile_map.get("running_mean_years") == 21, "published smoothing window changed")
    require(quantile_map.get("same_realization_gmst_required") is True, "same-realization GMST gate changed")
    require(quantile_map.get("scenario_identity_as_predictor") is False, "scenario shortcut is forbidden")
    require(quantile_map.get("extrapolation_forbidden") is True, "extrapolation gate changed")

    support = config.get("current_training_support", {})
    training_path = root / str(support.get("training_artifact"))
    require(sha256(training_path) == support.get("training_artifact_sha256"), "training artifact hash changed")
    require(support.get("available_year_blocks") == ["2012-2014", "2042-2049", "2092-2099"], "bounded year blocks changed")
    require(support.get("available_unique_years") == 23, "bounded year count changed")
    require(support.get("published_running_mean_supported") is False, "unsupported real smoothing was opened")

    dependence = config.get("dependence_boundary", {})
    require(dependence.get("published_quantile_maps_are_univariate") is True, "univariate method boundary changed")
    require(dependence.get("joint_crop_feature_dependence_preserved") is False, "joint dependence was not established")
    require(dependence.get("shared_quantile_rank_substitution_allowed") is False, "unvalidated comonotonic substitution opened")
    require(dependence.get("multivariate_production_sampling_authorized") is False, "multivariate gate opened")

    sources = []
    for source in config.get("source_receipts", []):
        path = root / str(source["path"])
        observed = sha256(path)
        require(observed == source.get("sha256"), f"source receipt hash changed: {path}")
        sources.append({"role": source["role"], "path": source["path"], "sha256": observed})
    require([item["role"] for item in sources] == ["complete_bounded_early_mid_end_training", "actual_give_fair_common_random_number_support"], "source roles changed")

    validation = config.get("validation", {})
    require(validation.get("outer_holdouts_required_before_real_promotion") == ["whole_esm", "whole_scenario"], "holdout gates changed")
    for gate in ("common_random_numbers_within_feature_required", "separate_baseline_and_pulse_support_flags_required", "zero_pulse_identity_required", "pre_divergence_identity_required", "multicrop_validation_required", "rainfed_irrigated_validation_required", "actual_fair_evaluation_forbidden_until_real_holdouts_pass"):
        require(validation.get(gate) is True, f"validation gate changed: {gate}")
    require(validation.get("decreasing_positive_pulse_scales_required") >= 3, "pulse convergence gate weakened")

    return {
        "schema": "isimip3b_rimex_feature_response_benchmark_validation_v1",
        "status": "validated_preregistered_benchmark_real_fit_blocked_by_contiguous_support_and_joint_dependence",
        "config": {"path": config_path.resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(config_path)},
        "implementation": {"path": Path(__file__).resolve().relative_to(root.resolve()).as_posix(), "sha256": sha256(Path(__file__))},
        "published_method": method,
        "source_receipts": sources,
        "engineering_smoke": synthetic_pulse_smoke(),
        "real_feature_fit_authorized": False,
        "actual_fair_feature_response_authorized": False,
        "whole_esm_holdout_completed": False,
        "whole_scenario_holdout_completed": False,
        "production_promoted": False,
        "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.config, args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("ISIMIP3b RIME-X feature benchmark contract passed")


if __name__ == "__main__":
    main()
