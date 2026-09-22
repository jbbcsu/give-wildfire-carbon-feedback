#!/usr/bin/env python3
"""State-cluster and leave-one-state-out sensitivity for the USDM benchmark."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t


HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "estimate_usdm_drought_only.py"
SPEC = importlib.util.spec_from_file_location("drought_base_robust", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load drought estimator")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
KEYS = ["county_geoid", "outcome_crop", "harvest_year"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fit_core(frame: pd.DataFrame, terms: list[str]) -> dict[str, Any]:
    frame = frame.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
    y = np.log(frame.yield_bu_acre.to_numpy(dtype=float))
    x = frame[terms].to_numpy(dtype=float)
    nuisance, dimensions = BASE.nuisance_matrix(frame)
    residual_y, _ = BASE.residualize(nuisance, y)
    residual_x = np.column_stack([
        BASE.residualize(nuisance, x[:, index])[0] for index in range(x.shape[1])
    ])
    gram = np.einsum("ni,nj->ij", residual_x, residual_x)
    condition = float(np.linalg.cond(gram))
    if not np.isfinite(condition) or condition > 1e12:
        raise ValueError(f"ill-conditioned leave-state-out design: {condition}")
    cross_product = np.array([
        np.dot(residual_x[:, index], residual_y) for index in range(x.shape[1])
    ])
    beta = np.linalg.solve(gram, cross_product)
    residual = residual_y - np.sum(residual_x * beta[None, :], axis=1)
    if not np.isfinite(beta).all() or not np.isfinite(residual).all():
        raise ValueError("nonfinite coefficient or residual in robustness fit")
    return {
        "beta": beta,
        "residual_x": residual_x,
        "residual": residual,
        "gram_inverse": np.linalg.inv(gram),
        "condition_number_xtx": condition,
        "nuisance_dimensions": dimensions,
        "rows": len(frame),
    }


def cluster_covariance(
    residual_x: np.ndarray,
    residual: np.ndarray,
    gram_inverse: np.ndarray,
    groups: pd.Series,
) -> tuple[np.ndarray, int]:
    codes, labels = pd.factorize(groups, sort=True)
    cluster_count = len(labels)
    n, q = residual_x.shape
    if cluster_count <= 1 or n <= q:
        raise ValueError("insufficient clusters for CR1 covariance")
    meat = np.zeros((q, q))
    for code in range(cluster_count):
        mask = codes == code
        score = np.sum(residual_x[mask] * residual[mask, None], axis=0)
        meat += np.outer(score, score)
    correction = cluster_count / (cluster_count - 1) * (n - 1) / (n - q)
    covariance = correction * np.einsum(
        "ij,jk,kl->il", gram_inverse, meat, gram_inverse
    )
    return covariance, cluster_count


def coefficient_summary(full: float, rows: list[dict[str, Any]], term: str) -> dict[str, Any]:
    values = np.array([row["coefficients"][term] for row in rows], dtype=float)
    states = [str(row["left_out_state"]) for row in rows]
    deltas = np.abs(values - full)
    maximum = int(np.argmax(deltas))
    sign = np.sign(full)
    agreement = float(np.mean(np.sign(values) == sign)) if sign != 0 else None
    return {
        "term": term,
        "full_estimate": full,
        "leaveout_minimum": float(values.min()),
        "leaveout_median": float(np.median(values)),
        "leaveout_maximum": float(values.max()),
        "maximum_absolute_change": float(deltas[maximum]),
        "state_with_maximum_absolute_change": states[maximum],
        "same_nonzero_sign_fraction": agreement,
        "leaveout_fits": len(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--base-result", type=Path, required=True)
    parser.add_argument("--yields", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--drought", type=Path, required=True)
    parser.add_argument("--weather", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    base_result = json.loads(arguments.base_result.read_text(encoding="utf-8"))
    if base_result.get("schema") != contract["base_result_schema"]:
        raise ValueError("base-result schema differs from robustness contract")
    for label, path in {
        "yields": arguments.yields, "classifier": arguments.classifier,
        "drought": arguments.drought, "weather": arguments.weather,
    }.items():
        if base_result["inputs"][label]["sha256"] != sha256(path):
            raise ValueError(f"{label} hash differs from frozen base result")
    base_contract = base_result["contract"]
    year_min, year_max = int(base_contract["year_min"]), int(base_contract["year_max"])
    crops = list(map(str, base_contract["crops"]))
    classes = list(map(str, base_contract["irrigation_classes"]))
    drought_terms = list(map(str, base_contract["drought_terms"]))
    weather_terms = list(map(str, base_contract["weather_terms"]))
    terms = drought_terms + weather_terms

    yields = pd.read_parquet(arguments.yields)
    yields = yields.loc[
        yields.harvest_year.between(year_min, year_max)
        & yields.outcome_crop.isin(crops)
    ].copy()
    classifier = pd.read_csv(arguments.classifier, dtype={"county_geoid": "string"})
    classifier = classifier.loc[classifier.classifier_eligible.eq(True)].copy()
    drought = pd.read_parquet(arguments.drought)
    weather = pd.read_parquet(arguments.weather)
    panel = yields.merge(
        classifier[["county_geoid", "irrigation_class"]], on="county_geoid",
        how="inner", validate="many_to_one",
    ).merge(
        drought[KEYS + drought_terms], on=KEYS, how="inner", validate="one_to_one",
    ).merge(
        weather[KEYS + weather_terms], on=KEYS, how="inner", validate="one_to_one",
    )
    if len(panel) != int(base_result["common_panel_rows"]):
        raise ValueError("common panel row count differs from base result")
    base_models = {
        (row["outcome_crop"], row["irrigation_class"]): row
        for row in base_result["results"] if row["family"] == contract["family"]
    }
    outputs = []
    maximum_base_difference = 0.0
    for crop in crops:
        for irrigation_class in classes:
            sample = panel.loc[
                panel.outcome_crop.eq(crop)
                & panel.irrigation_class.eq(irrigation_class)
            ].copy()
            fit = fit_core(sample, terms)
            base_model = base_models[(crop, irrigation_class)]
            reported = np.array([
                row["estimate_log_points_per_area_equivalent_week"]
                for row in base_model["coefficients"]
            ])
            difference = float(np.max(np.abs(fit["beta"] - reported)))
            maximum_base_difference = max(maximum_base_difference, difference)
            if difference > 5e-8:
                raise ValueError(f"full coefficient differs from base result: {difference}")
            covariance, state_count = cluster_covariance(
                fit["residual_x"], fit["residual"], fit["gram_inverse"], sample.state
            )
            if state_count < int(contract["minimum_full_sample_states"]):
                raise ValueError("full sample has too few state clusters")
            se = np.sqrt(np.diag(covariance))
            statistics = fit["beta"] / se
            p_values = 2 * t.sf(np.abs(statistics), df=state_count - 1)
            state_inference = [{
                "term": term,
                "estimate": float(fit["beta"][index]),
                "standard_error_state_cluster_cr1": float(se[index]),
                "t_statistic": float(statistics[index]),
                "degrees_of_freedom": state_count - 1,
                "p_value_t_reference": float(p_values[index]),
            } for index, term in enumerate(terms)]
            leaveouts = []
            for state in sorted(map(str, sample.state.unique())):
                reduced = sample.loc[~sample.state.eq(state)].copy()
                reduced_fit = fit_core(reduced, terms)
                leaveouts.append({
                    "left_out_state": state,
                    "rows": int(reduced_fit["rows"]),
                    "states": int(reduced.state.nunique()),
                    "condition_number_xtx": reduced_fit["condition_number_xtx"],
                    "coefficients": {
                        term: float(reduced_fit["beta"][index])
                        for index, term in enumerate(terms)
                    },
                })
            outputs.append({
                "outcome_crop": crop,
                "irrigation_class": irrigation_class,
                "rows": int(fit["rows"]),
                "counties": int(sample.county_geoid.nunique()),
                "states": state_count,
                "terms": terms,
                "full_state_cluster_inference": state_inference,
                "state_cluster_covariance_cr1": covariance.tolist(),
                "leave_one_state_out": leaveouts,
                "leaveout_summaries": [
                    coefficient_summary(float(fit["beta"][index]), leaveouts, term)
                    for index, term in enumerate(terms)
                ],
            })
    payload = {
        "schema": "usdm_weather_robustness_result_v1",
        "contract": contract,
        "inputs": {
            label: {"path": str(path), "sha256": sha256(path)}
            for label, path in {
                "config": arguments.config, "base_result": arguments.base_result,
                "yields": arguments.yields, "classifier": arguments.classifier,
                "drought": arguments.drought, "weather": arguments.weather,
            }.items()
        },
        "maximum_absolute_full_coefficient_difference_from_base": maximum_base_difference,
        "models": outputs,
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote state-cluster and leave-state-out sensitivity for {len(outputs)} models")


if __name__ == "__main__":
    main()
