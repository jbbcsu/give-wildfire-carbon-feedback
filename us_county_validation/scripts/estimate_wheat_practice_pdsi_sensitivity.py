#!/usr/bin/env python3
"""Estimate a bounded state-share-weighted wheat/PDSI sensitivity.

The analysis is deliberately narrow and retrospective.  It combines the
already-built winter/spring/durum PDSI calendar candidates using fixed official
2009 state harvested-acre shares, then fits historical paired-practice
associations.  It emits aggregate results only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[2]
WHEAT_CLASSES = ("durum_wheat", "spring_wheat", "winter_wheat")
PRACTICES = ("irrigated", "non_irrigated")
KEYS = ["county_geoid", "state", "harvest_year", "irrigation_practice"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative")
    result = (PROJECT / path).resolve()
    result.relative_to(PROJECT.resolve())
    return result


def wheat_state_weights(calendar_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(calendar_path, dtype={"state": "string", "calendar_crop": "string"})
    required = {"state", "calendar_crop", "published_harvested_acres_2009_thousand"}
    if not required.issubset(frame.columns):
        raise ValueError("calendar definitions lack wheat-weight columns")
    frame = frame.loc[frame.calendar_crop.isin(WHEAT_CLASSES), list(required)].copy()
    frame["published_harvested_acres_2009_thousand"] = pd.to_numeric(
        frame.published_harvested_acres_2009_thousand, errors="raise"
    )
    if frame.empty or frame.duplicated(["state", "calendar_crop"]).any():
        raise ValueError("wheat calendar weights are empty or duplicated")
    if (frame.published_harvested_acres_2009_thousand <= 0).any():
        raise ValueError("wheat class acreage must be positive")
    frame["state_wheat_acres_2009_thousand"] = frame.groupby("state", observed=True)[
        "published_harvested_acres_2009_thousand"
    ].transform("sum")
    frame["class_weight"] = (
        frame.published_harvested_acres_2009_thousand
        / frame.state_wheat_acres_2009_thousand
    )
    error = (frame.groupby("state", observed=True).class_weight.sum() - 1).abs().max()
    if float(error) > 1e-12:
        raise ValueError("state wheat weights do not sum to one")
    return frame.sort_values(["state", "calendar_crop"]).reset_index(drop=True)


def prepare_panel(join_path: Path, weights: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    columns = [
        "county_geoid", "state", "outcome_crop", "harvest_year",
        "irrigation_practice", "yield_bu_acre", "calendar_crop",
        "calendar_mapping_role", "calendar_role", "window_id",
        "index_day_weighted_mean", "geography_eligible",
        "calendar_mapping_status", "response_estimation_authorized",
        "scc_authorized", "response_estimation_authorized_pdsi",
        "scc_authorized_pdsi",
    ]
    frame = pd.read_parquet(join_path, columns=columns)
    frame = frame.loc[
        frame.outcome_crop.astype(str).eq("wheat_all_classes")
        & frame.calendar_role.astype(str).eq("fixed_primary")
        & frame.window_id.astype(str).eq("season")
        & frame.geography_eligible.fillna(False).astype(bool)
    ].copy()
    if frame.empty:
        raise ValueError("eligible wheat season panel is empty")
    if set(frame.irrigation_practice.astype(str)) != set(PRACTICES):
        raise ValueError("wheat panel practice support changed")
    if set(frame.calendar_mapping_role.astype(str)) != {
        "unresolved_all_classes_wheat_candidate_not_poolable"
    }:
        raise ValueError("upstream wheat candidate role changed")
    if set(frame.calendar_mapping_status.astype(str)) != {
        "blocked_all_classes_wheat_requires_class_weights"
    }:
        raise ValueError("upstream wheat mapping status changed")
    for gate in (
        "response_estimation_authorized", "scc_authorized",
        "response_estimation_authorized_pdsi", "scc_authorized_pdsi",
    ):
        if frame[gate].fillna(True).astype(bool).any():
            raise ValueError(f"upstream source unexpectedly opens {gate}")
    frame["yield_bu_acre"] = pd.to_numeric(frame.yield_bu_acre, errors="raise")
    frame["index_day_weighted_mean"] = pd.to_numeric(
        frame.index_day_weighted_mean, errors="raise"
    )
    if (frame.yield_bu_acre <= 0).any() or not np.isfinite(
        frame[["yield_bu_acre", "index_day_weighted_mean"]]
    ).all().all():
        raise ValueError("wheat yield/PDSI contains invalid values")
    if frame.duplicated(KEYS + ["calendar_crop"]).any():
        raise ValueError("duplicate wheat calendar candidates")

    used_states = set(frame.state.astype(str))
    available = weights.loc[weights.state.astype(str).isin(used_states)].copy()
    if set(available.state.astype(str)) != used_states:
        raise ValueError("one or more wheat states lacks official acreage weights")
    expected_classes = {
        state: set(part.calendar_crop.astype(str))
        for state, part in available.groupby("state", observed=True)
    }
    observed_classes = {
        state: set(part.calendar_crop.astype(str))
        for state, part in frame.groupby("state", observed=True)
    }
    for state in sorted(used_states):
        if observed_classes[state] != expected_classes[state]:
            raise ValueError(
                f"wheat candidate classes differ from official weights for {state}: "
                f"observed={sorted(observed_classes[state])}, "
                f"expected={sorted(expected_classes[state])}"
            )

    merged = frame.merge(
        available[["state", "calendar_crop", "class_weight"]],
        on=["state", "calendar_crop"], how="left", validate="many_to_one",
    )
    if merged.class_weight.isna().any():
        raise ValueError("wheat candidate lacks a class weight")
    grouped = merged.groupby(KEYS, observed=True, sort=True)
    checks = grouped.agg(
        candidate_classes=("calendar_crop", "nunique"),
        weight_sum=("class_weight", "sum"),
        yield_count=("yield_bu_acre", "nunique"),
    ).reset_index()
    if (checks.yield_count != 1).any():
        raise ValueError("candidate rows disagree on the NASS outcome")
    if float((checks.weight_sum - 1).abs().max()) > 1e-12:
        raise ValueError("candidate weights do not sum to one within a practice row")

    merged["weighted_pdsi_component"] = (
        merged.class_weight * merged.index_day_weighted_mean
    )
    panel = grouped.agg(
        yield_bu_acre=("yield_bu_acre", "first"),
        pdsi=("weighted_pdsi_component", "sum"),
        candidate_classes=("calendar_crop", "nunique"),
    ).reset_index()
    if panel.duplicated(KEYS).any():
        raise ValueError("weighted panel duplicates practice keys")

    pair_keys = ["county_geoid", "state", "harvest_year"]
    wide_y = panel.pivot(index=pair_keys, columns="irrigation_practice", values="yield_bu_acre")
    wide_p = panel.pivot(index=pair_keys, columns="irrigation_practice", values="pdsi")
    if list(wide_y.columns.astype(str)) != list(PRACTICES):
        # Pandas sorts the columns; require the set and normalize below.
        if set(wide_y.columns.astype(str)) != set(PRACTICES):
            raise ValueError("weighted panel lacks complete practice pairs")
    if wide_y.isna().any().any() or wide_p.isna().any().any():
        raise ValueError("weighted panel contains incomplete practice pairs")
    if not np.allclose(
        wide_p["irrigated"].to_numpy(dtype=float),
        wide_p["non_irrigated"].to_numpy(dtype=float),
        rtol=0, atol=1e-14,
    ):
        raise ValueError("paired practices do not share identical weighted PDSI")

    pairs = wide_y.reset_index().rename_axis(columns=None)
    pairs["pdsi"] = wide_p["irrigated"].to_numpy(dtype=float)
    pairs["log_yield_irrigated"] = np.log(pairs["irrigated"].to_numpy(dtype=float))
    pairs["log_yield_non_irrigated"] = np.log(
        pairs["non_irrigated"].to_numpy(dtype=float)
    )
    pairs["log_yield_gap"] = (
        pairs.log_yield_irrigated - pairs.log_yield_non_irrigated
    )
    if len(pairs) < 500 or pairs.county_geoid.nunique() < 50 or pairs.state.nunique() < 5:
        raise ValueError("frozen minimum support gate failed")
    audit = {
        "candidate_rows": int(len(frame)),
        "paired_county_years": int(len(pairs)),
        "counties": int(pairs.county_geoid.nunique()),
        "states": int(pairs.state.nunique()),
        "year_min": int(pairs.harvest_year.min()),
        "year_max": int(pairs.harvest_year.max()),
        "pdsi_mean": float(pairs.pdsi.mean()),
        "pdsi_standard_deviation": float(pairs.pdsi.std(ddof=0)),
    }
    return pairs.sort_values(pair_keys).reset_index(drop=True), audit


def alternating_residualize(
    values: np.ndarray, groups: list[np.ndarray], tolerance: float = 1e-10,
    max_iterations: int = 10000,
) -> tuple[np.ndarray, int, float]:
    residual = np.asarray(values, dtype=float).copy()
    if residual.ndim == 1:
        residual = residual[:, None]
    final_change = math.inf
    for iteration in range(1, max_iterations + 1):
        before = residual.copy()
        for codes in groups:
            count = np.bincount(codes).astype(float)
            if np.any(count <= 0):
                raise ValueError("fixed-effect codes contain gaps")
            for column in range(residual.shape[1]):
                means = np.bincount(codes, weights=residual[:, column]) / count
                residual[:, column] -= means[codes]
        final_change = float(np.max(np.abs(residual - before)))
        if final_change <= tolerance:
            return residual, iteration, final_change
    raise ValueError("fixed-effect residualization did not converge")


def clustered_ols(y: np.ndarray, x: np.ndarray, cluster: np.ndarray) -> dict[str, Any]:
    scale = x.std(axis=0, ddof=0)
    if np.any(~np.isfinite(scale)) or np.any(scale <= 0):
        raise ValueError("residualized predictor has invalid scale")
    standardized = x / scale
    # LAPACK is allowed to overwrite its work arrays.  Pass copies so the
    # standardized design used below for residuals and covariance remains
    # byte-for-byte unchanged.
    beta_s, _, rank, singular = np.linalg.lstsq(
        standardized.copy(), y.copy(), rcond=1e-12
    )
    if rank != x.shape[1]:
        raise ValueError("residualized design is rank deficient")
    residual = y - np.einsum("ij,j->i", standardized, beta_s, optimize=False)
    if not np.isfinite(residual).all():
        raise ValueError("OLS residuals are nonfinite")
    xtx = np.einsum("ni,nj->ij", standardized, standardized, optimize=False)
    xtx_inv = np.linalg.inv(xtx)
    codes, labels = pd.factorize(pd.Series(cluster, dtype="string"), sort=True)
    g = len(labels)
    if g <= 1:
        raise ValueError("county clustering requires multiple counties")
    meat = np.zeros((x.shape[1], x.shape[1]), dtype=float)
    for code in range(g):
        score = np.einsum(
            "ni,n->i", standardized[codes == code], residual[codes == code],
            optimize=False,
        )
        meat += np.outer(score, score)
    n, k = x.shape
    correction = (g / (g - 1)) * ((n - 1) / (n - k))
    covariance_s = correction * np.linalg.multi_dot([xtx_inv, meat, xtx_inv])
    beta = beta_s / scale
    covariance = covariance_s / np.outer(scale, scale)
    if not np.isfinite(beta).all() or not np.isfinite(covariance).all():
        raise ValueError("OLS coefficient or covariance is nonfinite")
    se = np.sqrt(np.maximum(np.diag(covariance), 0))
    z = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)
    p = np.array([math.erfc(abs(float(value)) / math.sqrt(2)) for value in z])
    return {
        "beta": beta, "covariance": covariance, "standard_error": se,
        "p_value": p, "clusters": g,
        "residual_rmse": float(np.sqrt(np.mean(np.square(residual)))),
        "within_r_squared": float(1 - np.sum(np.square(residual)) / np.sum(np.square(y))),
        "rank": int(rank),
        "standardized_condition_number": float(singular[0] / singular[-1]),
    }


def estimate(frame: pd.DataFrame, outcome: str, form: str) -> dict[str, Any]:
    p = frame.pdsi.to_numpy(dtype=float)
    x = p[:, None] if form == "linear" else np.column_stack([p, np.square(p)])
    names = ["pdsi"] if form == "linear" else ["pdsi", "pdsi_squared"]
    if form not in {"linear", "quadratic"}:
        raise ValueError("unknown form")
    county_codes, _ = pd.factorize(frame.county_geoid.astype(str), sort=True)
    state_year_codes, _ = pd.factorize(
        frame.state.astype(str) + "_" + frame.harvest_year.astype(str), sort=True
    )
    stacked = np.column_stack([frame[outcome].to_numpy(dtype=float), x])
    residual, iterations, change = alternating_residualize(
        stacked, [county_codes, state_year_codes]
    )
    fit = clustered_ols(residual[:, 0], residual[:, 1:], frame.county_geoid.to_numpy())
    coefficients = []
    for index, name in enumerate(names):
        beta = float(fit["beta"][index])
        se = float(fit["standard_error"][index])
        coefficients.append({
            "term": name, "estimate": beta,
            "standard_error_cluster_county": se,
            "ci95_normal": [beta - 1.96 * se, beta + 1.96 * se],
            "normal_approx_p_value": float(fit["p_value"][index]),
        })
    reference = float(frame.pdsi.median())
    log_contrast = float(fit["beta"][0])
    gradient = np.array([1.0])
    if form == "quadratic":
        log_contrast += float(fit["beta"][1]) * (2 * reference + 1)
        gradient = np.array([1.0, 2 * reference + 1])
    contrast_se = float(np.sqrt(np.linalg.multi_dot([
        gradient, fit["covariance"], gradient,
    ])))
    return {
        "outcome": outcome, "form": form, "rows": int(len(frame)),
        "counties": int(frame.county_geoid.nunique()),
        "states": int(frame.state.nunique()),
        "year_min": int(frame.harvest_year.min()),
        "year_max": int(frame.harvest_year.max()),
        "demeaning_iterations": iterations,
        "demeaning_final_max_change": change,
        "within_r_squared": fit["within_r_squared"],
        "residual_rmse": fit["residual_rmse"],
        "rank": fit["rank"],
        "standardized_condition_number": fit["standardized_condition_number"],
        "coefficients": coefficients,
        "plus_one_pdsi_at_sample_median": {
            "reference_pdsi": reference,
            "log_yield_difference": log_contrast,
            "exact_percent_difference": float(100 * np.expm1(log_contrast)),
            "standard_error_delta_log_scale": contrast_se,
            "ci95_normal_log_scale": [
                log_contrast - 1.96 * contrast_se,
                log_contrast + 1.96 * contrast_se,
            ],
        },
        "covariance_cluster_county": fit["covariance"].tolist(),
    }


def coefficient_vector(result: dict[str, Any]) -> np.ndarray:
    return np.array([row["estimate"] for row in result["coefficients"]], dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--join", default="data/interim/us_county/nass_direct_practice_pdsi_join_1981_2019.parquet"
    )
    parser.add_argument(
        "--calendar", default="config/us_county_nass_usual_date_definitions_2010.csv"
    )
    parser.add_argument(
        "--protocol", default="US_WHEAT_PRACTICE_PDSI_PROTOCOL_20260925.md"
    )
    parser.add_argument("--out", required=True)
    arguments = parser.parse_args()
    join_path = project_path(arguments.join)
    calendar_path = project_path(arguments.calendar)
    protocol_path = project_path(arguments.protocol)
    output_path = project_path(arguments.out)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite {output_path}")

    weights = wheat_state_weights(calendar_path)
    pairs, panel_audit = prepare_panel(join_path, weights)
    estimates = []
    for form in ("linear", "quadratic"):
        for outcome in (
            "log_yield_irrigated", "log_yield_non_irrigated", "log_yield_gap"
        ):
            estimates.append(estimate(pairs, outcome, form))
    indexed = {(row["outcome"], row["form"]): row for row in estimates}
    identities = []
    for form in ("linear", "quadratic"):
        expected = (
            coefficient_vector(indexed[("log_yield_irrigated", form)])
            - coefficient_vector(indexed[("log_yield_non_irrigated", form)])
        )
        actual = coefficient_vector(indexed[("log_yield_gap", form)])
        identities.append({
            "form": form,
            "maximum_absolute_gap_vs_practice_difference": float(
                np.max(np.abs(actual - expected))
            ),
        })
    if max(row["maximum_absolute_gap_vs_practice_difference"] for row in identities) > 1e-10:
        raise ValueError("paired-gap coefficient identity failed")

    leaveouts = []
    full_gap = float(coefficient_vector(indexed[("log_yield_gap", "linear")])[0])
    for state in sorted(pairs.state.astype(str).unique()):
        subset = pairs.loc[~pairs.state.astype(str).eq(state)].copy()
        row = estimate(subset, "log_yield_gap", "linear")
        value = float(coefficient_vector(row)[0])
        leaveouts.append({
            "omitted_state": state, "rows": int(len(subset)),
            "counties": int(subset.county_geoid.nunique()),
            "pdsi_coefficient": value,
            "same_nonzero_sign_as_full": bool(np.sign(value) == np.sign(full_gap) and value != 0),
        })

    used_states = set(pairs.state.astype(str))
    reported_weights = []
    for row in weights.loc[weights.state.astype(str).isin(used_states)].itertuples(index=False):
        reported_weights.append({
            "state": str(row.state), "calendar_crop": str(row.calendar_crop),
            "published_harvested_acres_2009_thousand": float(
                row.published_harvested_acres_2009_thousand
            ),
            "class_weight": float(row.class_weight),
        })
    payload = {
        "schema": "us_wheat_practice_pdsi_sensitivity_v1",
        "status": "exploratory_retrospective_measurement_sensitivity",
        "analysis_role": "regional_historical_association_only",
        "inputs": {
            "joined_panel": {"path": arguments.join, "sha256": sha256(join_path)},
            "calendar_definitions": {
                "path": arguments.calendar, "sha256": sha256(calendar_path),
            },
            "protocol": {"path": arguments.protocol, "sha256": sha256(protocol_path)},
            "implementation": {
                "path": "us_county_validation/scripts/estimate_wheat_practice_pdsi_sensitivity.py",
                "sha256": sha256(Path(__file__).resolve()),
            },
        },
        "panel": panel_audit,
        "fixed_state_wheat_class_weights": reported_weights,
        "estimates": estimates,
        "numerical_identities": identities,
        "linear_gap_leave_one_state_out": {
            "full_sample_pdsi_coefficient": full_gap,
            "omissions": leaveouts,
            "minimum": min(row["pdsi_coefficient"] for row in leaveouts),
            "maximum": max(row["pdsi_coefficient"] for row in leaveouts),
            "same_sign_count": sum(row["same_nonzero_sign_as_full"] for row in leaveouts),
            "omission_count": len(leaveouts),
        },
        "limitations": [
            "all-classes wheat is combined with fixed 2009 state harvested-acre shares rather than observed county-year class composition",
            "paired NASS support is regionally selected and ends in 2007",
            "NOAA PDSI combines precipitation and temperature-driven water balance",
            "fixed usual-date seasons do not observe annual phenology",
            "county-cluster normal intervals do not address wider spatial dependence or model selection",
        ],
        "predictive_claim_authorized": False,
        "causal_claim_authorized": False,
        "irrigation_treatment_claim_authorized": False,
        "national_representativeness_claim_authorized": False,
        "future_drought_claim_authorized": False,
        "global_transfer_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": arguments.out, "panel": panel_audit,
        "identity_max": max(
            row["maximum_absolute_gap_vs_practice_difference"] for row in identities
        ),
        "gap_leaveout_same_sign": (
            f"{payload['linear_gap_leave_one_state_out']['same_sign_count']}/"
            f"{payload['linear_gap_leave_one_state_out']['omission_count']}"
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
