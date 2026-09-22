#!/usr/bin/env python3
"""Independent joint-design checks for USDM state robustness results."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import lsmr


HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "estimate_usdm_drought_only.py"
SPEC = importlib.util.spec_from_file_location("drought_base_robust_validate", BASE_PATH)
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


def joint_fit(frame: pd.DataFrame, terms: list[str]) -> tuple[np.ndarray, np.ndarray]:
    frame = frame.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
    nuisance, _ = BASE.nuisance_matrix(frame)
    x = frame[terms].to_numpy(dtype=float)
    y = np.log(frame.yield_bu_acre.to_numpy(dtype=float))
    design = sparse.hstack([nuisance, sparse.csr_matrix(x)], format="csr")
    solution = lsmr(design, y, atol=1e-12, btol=1e-12, maxiter=50_000)
    beta = solution[0][-len(terms):]
    residual = y - design @ solution[0]
    return np.asarray(beta), np.asarray(residual)


def residualized_x(frame: pd.DataFrame, terms: list[str]) -> np.ndarray:
    frame = frame.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
    nuisance, _ = BASE.nuisance_matrix(frame)
    x = frame[terms].to_numpy(dtype=float)
    columns = []
    for index in range(x.shape[1]):
        solution = lsmr(nuisance, x[:, index], atol=1e-12, btol=1e-12, maxiter=50_000)
        columns.append(np.asarray(x[:, index] - nuisance @ solution[0]))
    return np.column_stack(columns)


def state_covariance(frame: pd.DataFrame, terms: list[str], residual: np.ndarray) -> np.ndarray:
    ordered = frame.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
    rx = residualized_x(ordered, terms)
    gram_inverse = np.linalg.inv(np.einsum("ni,nj->ij", rx, rx))
    codes, labels = pd.factorize(ordered.state, sort=True)
    meat = np.zeros((len(terms), len(terms)))
    for code in range(len(labels)):
        mask = codes == code
        score = np.sum(rx[mask] * residual[mask, None], axis=0)
        meat += np.outer(score, score)
    n, q = rx.shape
    correction = len(labels) / (len(labels) - 1) * (n - 1) / (n - q)
    return correction * np.einsum("ij,jk,kl->il", gram_inverse, meat, gram_inverse)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--base-result", type=Path, required=True)
    parser.add_argument("--yields", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--drought", type=Path, required=True)
    parser.add_argument("--weather", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    result = json.loads(arguments.result.read_text(encoding="utf-8"))
    if result.get("schema") != "usdm_weather_robustness_result_v1":
        raise ValueError("unexpected robustness-result schema")
    for flag in ("causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized"):
        if result.get(flag) is not False:
            raise ValueError(f"claim boundary changed: {flag}")
    for label, path in {
        "base_result": arguments.base_result, "yields": arguments.yields,
        "classifier": arguments.classifier, "drought": arguments.drought,
        "weather": arguments.weather,
    }.items():
        if result["inputs"][label]["sha256"] != sha256(path):
            raise ValueError(f"{label} hash differs from robustness result")
    base_result = json.loads(arguments.base_result.read_text(encoding="utf-8"))
    contract = base_result["contract"]
    years = (int(contract["year_min"]), int(contract["year_max"]))
    drought_terms = list(map(str, contract["drought_terms"]))
    weather_terms = list(map(str, contract["weather_terms"]))
    terms = drought_terms + weather_terms
    crops = list(map(str, contract["crops"]))
    yields = pd.read_parquet(arguments.yields)
    yields = yields.loc[
        yields.harvest_year.between(*years) & yields.outcome_crop.isin(crops)
    ].copy()
    classifier = pd.read_csv(arguments.classifier, dtype={"county_geoid": "string"})
    classifier = classifier.loc[classifier.classifier_eligible.eq(True)]
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

    maximum_full = 0.0
    maximum_covariance = 0.0
    maximum_sentinel = 0.0
    audits = []
    for model in result["models"]:
        if model["terms"] != terms:
            raise ValueError("term ordering changed")
        sample = panel.loc[
            panel.outcome_crop.eq(model["outcome_crop"])
            & panel.irrigation_class.eq(model["irrigation_class"])
        ].copy()
        if len(sample) != int(model["rows"]):
            raise ValueError("model row count differs")
        beta, residual = joint_fit(sample, terms)
        reported = np.array([row["estimate"] for row in model["full_state_cluster_inference"]])
        full_difference = float(np.max(np.abs(beta - reported)))
        maximum_full = max(maximum_full, full_difference)
        covariance = state_covariance(sample, terms, residual)
        reported_covariance = np.asarray(model["state_cluster_covariance_cr1"], dtype=float)
        covariance_difference = float(np.max(np.abs(covariance - reported_covariance)))
        maximum_covariance = max(maximum_covariance, covariance_difference)
        if not np.allclose(reported_covariance, reported_covariance.T, rtol=0, atol=1e-12):
            raise ValueError("reported state covariance is not symmetric")
        if np.linalg.eigvalsh(reported_covariance).min() < -1e-12:
            raise ValueError("reported state covariance is not positive semidefinite")
        leaveouts = model["leave_one_state_out"]
        states = sorted(map(str, sample.state.unique()))
        if [row["left_out_state"] for row in leaveouts] != states:
            raise ValueError("leaveout state coverage or ordering differs")
        sentinels = sorted({states[0], states[len(states) // 2], states[-1]})
        stored = {row["left_out_state"]: row for row in leaveouts}
        sentinel_differences = []
        for state in sentinels:
            reduced = sample.loc[~sample.state.eq(state)].copy()
            candidate, _ = joint_fit(reduced, terms)
            expected = np.array([stored[state]["coefficients"][term] for term in terms])
            difference = float(np.max(np.abs(candidate - expected)))
            sentinel_differences.append({"state": state, "maximum_difference": difference})
            maximum_sentinel = max(maximum_sentinel, difference)
        for summary in model["leaveout_summaries"]:
            values = np.array([
                row["coefficients"][summary["term"]] for row in leaveouts
            ])
            if not np.isclose(values.min(), summary["leaveout_minimum"], rtol=0, atol=1e-15):
                raise ValueError("leaveout summary minimum differs")
            if not np.isclose(values.max(), summary["leaveout_maximum"], rtol=0, atol=1e-15):
                raise ValueError("leaveout summary maximum differs")
        audits.append({
            "outcome_crop": model["outcome_crop"],
            "irrigation_class": model["irrigation_class"],
            "full_joint_design_maximum_difference": full_difference,
            "state_covariance_maximum_difference": covariance_difference,
            "sentinel_leaveouts": sentinel_differences,
        })
    if maximum_full > 5e-8 or maximum_covariance > 5e-8 or maximum_sentinel > 5e-8:
        raise ValueError("independent robustness validation exceeds tolerance")
    payload = {
        "schema": "usdm_weather_robustness_independent_validation_v1",
        "status": "passed",
        "result": {"path": str(arguments.result), "sha256": sha256(arguments.result)},
        "maximum_full_joint_design_coefficient_difference": maximum_full,
        "maximum_state_covariance_difference": maximum_covariance,
        "maximum_sentinel_leaveout_coefficient_difference": maximum_sentinel,
        "models": audits,
        "claim_boundary": "historical noncausal sensitivity only; not damage or SCC",
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print("passed independent state-cluster and sentinel leaveout validation")


if __name__ == "__main__":
    main()
