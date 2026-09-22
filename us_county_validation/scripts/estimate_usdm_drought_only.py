#!/usr/bin/env python3
"""Estimate the frozen drought-only U.S. county benchmark without dense FE matrices."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import sparse
from scipy.sparse.linalg import lsmr
from scipy.stats import chi2, norm


KEYS = ["county_geoid", "outcome_crop", "harvest_year"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nuisance_matrix(frame: pd.DataFrame) -> tuple[sparse.csr_matrix, dict[str, int]]:
    county_codes, counties = pd.factorize(frame.county_geoid, sort=True)
    year_codes, years = pd.factorize(frame.harvest_year, sort=True)
    state_codes, states = pd.factorize(frame.state, sort=True)
    n = len(frame)
    rows = np.arange(n)
    county = sparse.coo_matrix(
        (np.ones(n), (rows, county_codes)), shape=(n, len(counties))
    )
    year = sparse.coo_matrix(
        (np.ones(n), (rows, year_codes)), shape=(n, len(years))
    )
    centered_time = frame.harvest_year.to_numpy(dtype=float) - frame.harvest_year.mean()
    state_trend = sparse.coo_matrix(
        (centered_time, (rows, state_codes)), shape=(n, len(states))
    )
    matrix = sparse.hstack([county, year, state_trend], format="csr")
    return matrix, {
        "counties": len(counties), "years": len(years), "states": len(states),
        "nuisance_columns_including_rank_redundancy": matrix.shape[1],
    }


def residualize(matrix: sparse.csr_matrix, values: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    solution = lsmr(matrix, values, atol=1e-12, btol=1e-12, maxiter=20_000)
    residual = values - matrix @ solution[0]
    return np.asarray(residual), {
        "lsmr_stop_code": int(solution[1]),
        "lsmr_iterations": int(solution[2]),
        "lsmr_norm_residual": float(solution[3]),
        "maximum_absolute_nuisance_orthogonality": float(
            np.max(np.abs(matrix.T @ residual))
        ),
    }


def fit_one(frame: pd.DataFrame, terms: list[str]) -> dict[str, Any]:
    frame = frame.sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
    y = np.log(frame.yield_bu_acre.to_numpy(dtype=float))
    x = frame[terms].to_numpy(dtype=float)
    if not np.isfinite(y).all() or not np.isfinite(x).all():
        raise ValueError("model input contains nonfinite values")
    nuisance, dimensions = nuisance_matrix(frame)
    residual_y, y_audit = residualize(nuisance, y)
    residual_columns = []
    x_audits = []
    for index in range(x.shape[1]):
        residual, audit = residualize(nuisance, x[:, index])
        residual_columns.append(residual)
        x_audits.append(audit)
    residual_x = np.column_stack(residual_columns)
    gram = np.einsum("ni,nj->ij", residual_x, residual_x)
    condition = float(np.linalg.cond(gram))
    if not np.isfinite(condition) or condition > 1e12:
        raise ValueError(f"residualized drought design is ill-conditioned: {condition}")
    gram_inverse = np.linalg.inv(gram)
    cross_product = np.array([
        np.dot(residual_x[:, index], residual_y) for index in range(x.shape[1])
    ])
    beta = np.linalg.solve(gram, cross_product)
    residual = residual_y - np.sum(residual_x * beta[None, :], axis=1)

    county_codes, counties = pd.factorize(frame.county_geoid, sort=True)
    meat = np.zeros((len(terms), len(terms)))
    for code in range(len(counties)):
        mask = county_codes == code
        score = np.sum(residual_x[mask] * residual[mask, None], axis=0)
        meat += np.outer(score, score)
    n = len(frame)
    q = len(terms)
    clusters = len(counties)
    if clusters <= 1 or n <= q:
        raise ValueError("insufficient county clusters")
    correction = clusters / (clusters - 1) * (n - 1) / (n - q)
    covariance = correction * np.einsum("ij,jk,kl->il", gram_inverse, meat, gram_inverse)
    standard_errors = np.sqrt(np.diag(covariance))
    if not np.isfinite(standard_errors).all():
        raise ValueError("cluster covariance is nonfinite")
    z = beta / standard_errors
    p_values = 2 * norm.sf(np.abs(z))
    coefficients = []
    for index, term in enumerate(terms):
        coefficients.append({
            "term": term,
            "estimate_log_points_per_area_equivalent_week": float(beta[index]),
            "standard_error_county_cluster_cr1": float(standard_errors[index]),
            "ci95_low": float(beta[index] - 1.959963984540054 * standard_errors[index]),
            "ci95_high": float(beta[index] + 1.959963984540054 * standard_errors[index]),
            "p_value_normal_reference": float(p_values[index]),
            "exact_percent_change_per_week": float(100 * np.expm1(beta[index])),
        })
    try:
        inverse_covariance = np.linalg.inv(covariance)
    except np.linalg.LinAlgError as error:
        raise ValueError("cluster covariance is singular for joint test") from error
    wald = float(np.einsum("i,ij,j->", beta, inverse_covariance, beta))
    denominator = float(np.dot(residual_y, residual_y))
    within_r2 = 1 - float(np.dot(residual, residual)) / denominator if denominator > 0 else None
    return {
        "rows": n,
        "counties": clusters,
        "states": int(frame.state.nunique()),
        "years": int(frame.harvest_year.nunique()),
        "year_min": int(frame.harvest_year.min()),
        "year_max": int(frame.harvest_year.max()),
        "nuisance_dimensions": dimensions,
        "condition_number_xtx": condition,
        "within_r_squared": within_r2,
        "coefficients": coefficients,
        "covariance_term_order": terms,
        "covariance_county_cluster_cr1": covariance.tolist(),
        "joint_zero_wald_chi_square": wald,
        "joint_zero_degrees_of_freedom": q,
        "joint_zero_p_value": float(chi2.sf(wald, q)),
        "residualization_audit": {"outcome": y_audit, "predictors": x_audits},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--yields", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--exposures", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    terms = [str(value) for value in contract["exposure_terms"]]
    crops = [str(value) for value in contract["crops"]]
    classes = [str(value) for value in contract["irrigation_classes"]]
    year_min, year_max = int(contract["year_min"]), int(contract["year_max"])

    yields = pd.read_parquet(arguments.yields)
    required_yields = {*KEYS, "state", "yield_bu_acre"}
    if missing := required_yields - set(yields.columns):
        raise ValueError(f"yield panel lacks {sorted(missing)}")
    yields = yields.loc[
        yields.harvest_year.between(year_min, year_max)
        & yields.outcome_crop.isin(crops)
    ].copy()
    if yields.duplicated(KEYS).any() or (yields.yield_bu_acre <= 0).any():
        raise ValueError("yield panel has duplicate keys or nonpositive outcomes")

    classifier = pd.read_csv(arguments.classifier, dtype={"county_geoid": "string"})
    required_classifier = {"county_geoid", "classifier_eligible", "irrigation_class"}
    if missing := required_classifier - set(classifier.columns):
        raise ValueError(f"classifier lacks {sorted(missing)}")
    classifier = classifier.loc[classifier.classifier_eligible.eq(True)].copy()
    if classifier.duplicated("county_geoid").any():
        raise ValueError("classifier duplicates county GEOIDs")

    exposures = pd.read_parquet(arguments.exposures)
    required_exposures = {*KEYS, *terms, "source_area_basis", "scc_authorized"}
    if missing := required_exposures - set(exposures.columns):
        raise ValueError(f"exposure panel lacks {sorted(missing)}")
    if exposures.duplicated(KEYS).any():
        raise ValueError("exposure panel duplicates model keys")
    expected_area_basis = str(contract.get("source_area_basis_value", "county_area"))
    if set(exposures.source_area_basis) != {expected_area_basis} or exposures.scc_authorized.any():
        raise ValueError("exposure claim boundary changed")

    panel = yields.merge(
        classifier[["county_geoid", "irrigation_class"]],
        on="county_geoid", how="inner", validate="many_to_one",
    ).merge(exposures[KEYS + terms], on=KEYS, how="inner", validate="one_to_one")
    if panel.empty:
        raise ValueError("model panel is empty")
    results = []
    for crop in crops:
        for irrigation_class in classes:
            sample = panel.loc[
                panel.outcome_crop.eq(crop)
                & panel.irrigation_class.eq(irrigation_class)
            ].copy()
            if sample.empty:
                raise ValueError(f"empty sample for {crop} {irrigation_class}")
            fit = fit_one(sample, terms)
            fit.update({"outcome_crop": crop, "irrigation_class": irrigation_class})
            results.append(fit)
    payload = {
        "schema": "usdm_kuwayama_drought_only_result_v1",
        "contract": contract,
        "inputs": {
            label: {"path": str(path), "sha256": sha256(path)}
            for label, path in {
                "config": arguments.config, "yields": arguments.yields,
                "classifier": arguments.classifier, "exposures": arguments.exposures,
            }.items()
        },
        "joined_panel_rows": int(len(panel)),
        "joined_panel_counties": int(panel.county_geoid.nunique()),
        "results": results,
        "limitations": [
            str(contract.get(
                "spatial_exposure_limitation",
                "USDM REST exposure is county-area weighted; published benchmark is agricultural-area weighted.",
            )),
            "County-cluster CR1 is provisional; the published study uses spatial-correlation-robust inference.",
            "This drought-only stage does not yet include the frozen April-September weather controls.",
            "Historical validation coefficients are not global response, damage, or SCC coefficients.",
        ],
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"estimated {len(results)} frozen drought-only models on {len(panel)} joined rows"
    )


if __name__ == "__main__":
    main()
