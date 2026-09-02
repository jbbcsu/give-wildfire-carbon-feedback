#!/usr/bin/env python3
"""Validate the preregistered RIME-X empirical-copula coupling contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd


SCHEMA = "isimip3b_rimex_joint_dependence_contract_v1"
COORDINATES = [
    "tmean_c", "log_precip", "wet_logit", "cdd_logit", "rx5_share_logit",
    "rx1_given_rx5_logit", "stage_alr1", "stage_alr2",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _open_logit(value: np.ndarray, epsilon: float) -> np.ndarray:
    opened = (value + epsilon) / (1.0 + 2.0 * epsilon)
    return np.log(opened / (1.0 - opened))


def _close_logit(value: np.ndarray, epsilon: float) -> np.ndarray:
    probability = 1.0 / (1.0 + np.exp(-value))
    return np.clip(probability * (1.0 + 2.0 * epsilon) - epsilon, 0.0, 1.0)


def encode_physical(frame: pd.DataFrame, epsilon: float) -> pd.DataFrame:
    needed = {"tmean_c", "precip_mm", "season_days", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm", "stage1_precip_share", "stage2_precip_share", "stage3_precip_share"}
    if missing := needed - set(frame.columns):
        raise ValueError(f"physical feature frame lacks {sorted(missing)}")
    numeric = frame[list(needed)].to_numpy(dtype=float)
    require(np.isfinite(numeric).all(), "physical features must be finite")
    require(((frame.precip_mm > 0) & (frame.rx5day_mm > 0)).all(), "nonpositive quantity/Rx5 support fails closed")
    require(((frame.rx1day_mm >= 0) & (frame.rx1day_mm <= frame.rx5day_mm) & (frame.rx5day_mm <= frame.precip_mm)).all(), "rainfall extremes violate their physical order")
    require(((frame.wet_days_n >= 0) & (frame.wet_days_n <= frame.season_days) & (frame.cdd_max_days >= 0) & (frame.cdd_max_days <= frame.season_days)).all(), "day fractions leave [0,1]")
    shares = frame[["stage1_precip_share", "stage2_precip_share", "stage3_precip_share"]].to_numpy(dtype=float)
    require((shares >= 0).all() and np.allclose(shares.sum(axis=1), 1.0, rtol=0, atol=1e-12), "stage shares must be a closed nonnegative simplex")
    adjusted = (shares + epsilon) / (1.0 + 3.0 * epsilon)
    return pd.DataFrame({
        "tmean_c": frame.tmean_c.to_numpy(dtype=float),
        "log_precip": np.log(frame.precip_mm.to_numpy(dtype=float)),
        "wet_logit": _open_logit(frame.wet_days_n.to_numpy(dtype=float) / frame.season_days, epsilon),
        "cdd_logit": _open_logit(frame.cdd_max_days.to_numpy(dtype=float) / frame.season_days, epsilon),
        "rx5_share_logit": _open_logit(frame.rx5day_mm.to_numpy(dtype=float) / frame.precip_mm, epsilon),
        "rx1_given_rx5_logit": _open_logit(frame.rx1day_mm.to_numpy(dtype=float) / frame.rx5day_mm, epsilon),
        "stage_alr1": np.log(adjusted[:, 0] / adjusted[:, 2]),
        "stage_alr2": np.log(adjusted[:, 1] / adjusted[:, 2]),
    })


def decode_physical(linked: pd.DataFrame, season_days: np.ndarray, epsilon: float) -> pd.DataFrame:
    require(list(linked.columns) == COORDINATES, "linked coordinate order changed")
    days = np.asarray(season_days, dtype=float)
    total = np.exp(linked.log_precip.to_numpy(dtype=float))
    rx5 = total * _close_logit(linked.rx5_share_logit.to_numpy(dtype=float), epsilon)
    rx1 = rx5 * _close_logit(linked.rx1_given_rx5_logit.to_numpy(dtype=float), epsilon)
    exp_alr = np.column_stack([np.exp(linked.stage_alr1), np.exp(linked.stage_alr2), np.ones(len(linked))])
    adjusted = exp_alr / exp_alr.sum(axis=1, keepdims=True)
    shares = np.clip(adjusted * (1.0 + 3.0 * epsilon) - epsilon, 0.0, 1.0)
    shares /= shares.sum(axis=1, keepdims=True)
    return pd.DataFrame({
        "tmean_c": linked.tmean_c,
        "precip_mm": total,
        "season_days": days,
        "wet_days_n": days * _close_logit(linked.wet_logit.to_numpy(dtype=float), epsilon),
        "cdd_max_days": days * _close_logit(linked.cdd_logit.to_numpy(dtype=float), epsilon),
        "rx1day_mm": rx1,
        "rx5day_mm": rx5,
        "stage1_precip_share": shares[:, 0],
        "stage2_precip_share": shares[:, 1],
        "stage3_precip_share": shares[:, 2],
    })


def ecc_q(marginal_samples: np.ndarray, templates: np.ndarray, seed: str) -> np.ndarray:
    marginal = np.asarray(marginal_samples, dtype=float)
    raw = np.asarray(templates, dtype=float)
    require(marginal.ndim == 2 and marginal.shape == raw.shape, "marginal/template arrays must share a two-dimensional shape")
    require(np.isfinite(marginal).all() and np.isfinite(raw).all(), "ECC-Q inputs must be finite")
    output = np.empty_like(marginal)
    rows = np.arange(len(raw))
    for dimension in range(raw.shape[1]):
        tie = np.array([
            int.from_bytes(hashlib.sha256(f"{seed}|{dimension}|{row}".encode()).digest()[:8], "big")
            for row in rows
        ], dtype=np.uint64)
        order = np.lexsort((tie, raw[:, dimension]))
        output[order, dimension] = np.sort(marginal[:, dimension], kind="mergesort")
    return output


def synthetic_smoke(epsilon: float, seed: str) -> dict[str, object]:
    draws = 51
    q = (np.arange(draws) + 0.5) / draws
    frame = pd.DataFrame({
        "tmean_c": 18 + 8 * q, "precip_mm": 80 + 240 * q, "season_days": 120.0,
        "wet_days_n": 12 + 55 * q, "cdd_max_days": 3 + 25 * (1 - q),
        "rx1day_mm": 4 + 15 * q, "rx5day_mm": 12 + 50 * q,
        "stage1_precip_share": 0.2 + 0.1 * q,
        "stage2_precip_share": 0.5 - 0.1 * q,
        "stage3_precip_share": 0.3,
    })
    linked = encode_physical(frame, epsilon)
    rng = np.random.default_rng(20260902)
    templates = rng.normal(size=(draws, len(COORDINATES)))
    templates[:, 1] = 0.7 * templates[:, 0] + 0.3 * templates[:, 1]
    coupled = ecc_q(linked.to_numpy(), templates, seed)
    marginal_error = max(float(np.max(np.abs(np.sort(coupled[:, j]) - np.sort(linked.iloc[:, j])))) for j in range(len(COORDINATES)))
    template_spearman = pd.DataFrame(templates).rank(method="first").corr().to_numpy()
    coupled_spearman = pd.DataFrame(coupled).rank(method="first").corr().to_numpy()
    decoded = decode_physical(pd.DataFrame(coupled, columns=COORDINATES), np.full(draws, 120.0), epsilon)
    physical_failures = int(((decoded.rx1day_mm < 0) | (decoded.rx1day_mm > decoded.rx5day_mm) | (decoded.rx5day_mm > decoded.precip_mm) | (decoded.wet_days_n < 0) | (decoded.wet_days_n > decoded.season_days) | (decoded.cdd_max_days < 0) | (decoded.cdd_max_days > decoded.season_days)).sum())
    simplex_error = float(np.max(np.abs(decoded[["stage1_precip_share", "stage2_precip_share", "stage3_precip_share"]].sum(axis=1) - 1)))
    zero_pulse = ecc_q(linked.to_numpy(), templates, seed)
    return {
        "joint_draws": draws,
        "maximum_marginal_multiset_error": marginal_error,
        "maximum_spearman_matrix_error": float(np.max(np.abs(template_spearman - coupled_spearman))),
        "physical_failures": physical_failures,
        "maximum_stage_simplex_error": simplex_error,
        "zero_pulse_identity": bool(np.array_equal(coupled, zero_pulse)),
        "pilot_template_support": False,
        "real_fit_authorized": False,
    }


def validate(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "contract schema changed")
    require(config.get("primary_climate_route") == "direct_isimip3b_daily_feature_response", "primary route changed")
    for gate in ("real_joint_fit_authorized", "fair_feature_response_authorized", "response_estimation_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")
    method = config.get("method", {})
    require(method.get("name") == "ECC-Q empirical-copula coupling", "joint method changed")
    require(method.get("primary_reference_doi") == "10.1214/13-STS443", "ECC reference changed")
    for forbidden in ("independent_marginal_sampling_allowed", "one_shared_rank_for_all_features_allowed", "gaussian_copula_substitution_allowed"):
        require(method.get(forbidden) is False, f"forbidden dependence shortcut opened: {forbidden}")
    template = config.get("template", {})
    require(template.get("joint_draw_count") == 51 and template.get("minimum_distinct_training_templates") == 51, "joint draw/template minimum changed")
    require(template.get("pilot_distinct_templates") == 8 and template.get("pilot_mechanics_only") is True, "pilot support boundary changed")
    for gate in ("whole_esm_holdout_required", "whole_scenario_holdout_required", "held_out_templates_excluded_from_training"):
        require(template.get(gate) is True, f"template holdout gate changed: {gate}")
    physical = config.get("physical_coordinates", {})
    epsilon = float(physical.get("boundary_epsilon", np.nan))
    require(epsilon == 1e-6, "physical boundary epsilon changed")
    require(len(physical.get("required_future_extensions", [])) == 3, "required feature extensions changed")
    pairing = config.get("pairing", {})
    for gate in ("common_template_ids_baseline_pulse", "common_marginal_probability_grid_baseline_pulse", "separate_baseline_pulse_support_flags", "zero_pulse_identity", "pre_divergence_identity", "out_of_support_extrapolation_forbidden"):
        require(pairing.get(gate) is True, f"pairing gate changed: {gate}")
    require(pairing.get("decreasing_positive_pulse_scales") == [0.01, 0.005, 0.0025], "pulse scales changed")
    validation = config.get("validation", {})
    require(validation.get("physical_failures_allowed") == 0, "physical gate weakened")
    require(validation.get("whole_esm_and_whole_scenario_results_must_both_pass") is True, "holdout promotion gate weakened")
    sources = []
    for source in config.get("source_receipts", []):
        path = root / source["path"]
        observed = sha256(path)
        require(observed == source["sha256"], "source receipt hash changed")
        sources.append({**source, "sha256": observed})
    smoke = synthetic_smoke(epsilon, str(template["template_seed"]))
    require(smoke["maximum_marginal_multiset_error"] <= 1e-12, "ECC-Q changed a marginal sample")
    require(smoke["maximum_spearman_matrix_error"] <= 1e-12, "ECC-Q did not reproduce template ranks")
    require(smoke["physical_failures"] == 0 and smoke["maximum_stage_simplex_error"] <= 1e-12, "physical reconstruction failed")
    return {
        "schema": "isimip3b_rimex_joint_dependence_validation_v1",
        "status": "preregistered_synthetic_mechanics_pass_pilot_template_support_insufficient",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "sources": sources,
        "synthetic_smoke": smoke,
        "real_joint_fit_authorized": False,
        "fair_feature_response_authorized": False,
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
    print("RIME-X joint-dependence contract and synthetic ECC-Q mechanics passed")


if __name__ == "__main__":
    main()
