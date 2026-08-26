#!/usr/bin/env python3
"""Estimate locked historical NASS/PDSI fixed-effects associations.

This intentionally narrow diagnostic uses all-practice NASS yields and a
retrospective NOAA PDSI route.  It never emits row predictions and it cannot
identify precipitation separately from temperature-driven water balance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT / "us_county_validation/us_national_all_practice_pdsi_association_v1.toml"
FALSE_GATES = ("causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("configured paths must be project-relative")
    result = (PROJECT / path).resolve()
    result.relative_to(PROJECT.resolve())
    return result


def load_config(path: Path) -> dict[str, Any]:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if config.get("analysis_id") != "us_national_all_practice_pdsi_association_v1":
        raise ValueError("wrong association contract identity")
    if config.get("analysis_role") != "historical_predictive_association_only":
        raise ValueError("association role changed")
    if config.get("predictive_association_authorized") is not True:
        raise ValueError("predictive association is not authorized")
    for gate in FALSE_GATES:
        if config.get(gate) is not False:
            raise ValueError(f"contract unexpectedly opens {gate}")
    if config["models"]["fixed_effects"] != ["county_geoid", "state_by_harvest_year"]:
        raise ValueError("fixed-effects design changed")
    if config["models"]["cluster"] != "county_geoid":
        raise ValueError("cluster design changed")
    return config


def alternating_residualize(
    values: np.ndarray,
    groups: list[np.ndarray],
    tolerance: float,
    max_iterations: int,
) -> tuple[np.ndarray, int, float]:
    """Residualize columns against categorical groups by alternating projections."""
    residual = np.asarray(values, dtype=float).copy()
    if residual.ndim == 1:
        residual = residual[:, None]
    if not np.isfinite(residual).all():
        raise ValueError("residualization input contains nonfinite values")
    if tolerance <= 0 or max_iterations < 1:
        raise ValueError("invalid residualization controls")
    final_change = math.inf
    for iteration in range(1, max_iterations + 1):
        before = residual.copy()
        for codes in groups:
            codes = np.asarray(codes, dtype=np.int64)
            if len(codes) != len(residual) or codes.min(initial=0) < 0:
                raise ValueError("invalid fixed-effect codes")
            count = np.bincount(codes).astype(float)
            if np.any(count <= 0):
                raise ValueError("fixed-effect codes contain gaps")
            for column in range(residual.shape[1]):
                means = np.bincount(codes, weights=residual[:, column]) / count
                residual[:, column] -= means[codes]
        final_change = float(np.max(np.abs(residual - before)))
        if final_change <= tolerance:
            return residual, iteration, final_change
    raise ValueError("alternating fixed-effect residualization did not converge")


def clustered_ols(y: np.ndarray, x: np.ndarray, cluster: np.ndarray) -> dict[str, Any]:
    if x.ndim != 2 or y.ndim != 1 or len(x) != len(y):
        raise ValueError("OLS arrays are not aligned")
    scale = x.std(axis=0, ddof=0)
    if not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError("OLS predictors have invalid within scale")
    standardized = x / scale
    beta_standardized, _, rank, singular = np.linalg.lstsq(standardized, y, rcond=1e-12)
    if rank != x.shape[1] or not np.isfinite(beta_standardized).all():
        raise ValueError("residualized design is rank deficient")
    condition = float(singular[0] / singular[-1])
    if not np.isfinite(condition) or condition > 1e8:
        raise ValueError("residualized standardized design is ill-conditioned")
    residual = y - np.einsum("ij,j->i", standardized, beta_standardized, optimize=False)
    if not np.isfinite(residual).all():
        raise ValueError("OLS residuals are nonfinite")
    xtx = np.einsum("ni,nj->ij", standardized, standardized, optimize=False)
    xtx_inv = np.linalg.inv(xtx)
    codes, labels = pd.factorize(pd.Series(cluster, dtype="string"), sort=True)
    group_count = len(labels)
    if group_count <= 1:
        raise ValueError("cluster covariance requires multiple counties")
    meat = np.zeros((x.shape[1], x.shape[1]), dtype=float)
    for code in range(group_count):
        score = np.einsum(
            "ni,n->i", standardized[codes == code], residual[codes == code], optimize=False
        )
        meat += np.outer(score, score)
    n, k = x.shape
    correction = (group_count / (group_count - 1)) * ((n - 1) / (n - k))
    covariance = correction * (xtx_inv @ meat @ xtx_inv)
    standard_error_standardized = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    beta = beta_standardized / scale
    standard_error = standard_error_standardized / scale
    z = np.divide(beta, standard_error, out=np.full_like(beta, np.nan), where=standard_error > 0)
    p = np.array([math.erfc(abs(float(value)) / math.sqrt(2)) for value in z])
    return {
        "beta": beta,
        "standard_error_cluster_county": standard_error,
        "normal_approx_p_value": p,
        "residual_rmse": float(np.sqrt(np.mean(np.square(residual)))),
        "within_r_squared": float(1 - np.sum(np.square(residual)) / np.sum(np.square(y))),
        "rank": int(rank),
        "minimum_singular_value": float(singular[-1]),
        "standardized_design_condition_number": condition,
        "clusters": int(group_count),
    }


def design(frame: pd.DataFrame, form: str, center_year: int) -> tuple[np.ndarray, list[str]]:
    p = frame.pdsi.to_numpy(dtype=float)
    columns = [p]
    names = ["pdsi"]
    if form in {"quadratic", "quadratic_linear_trend_interaction"}:
        columns.append(np.square(p))
        names.append("pdsi_squared")
    if form == "quadratic_linear_trend_interaction":
        trend = frame.harvest_year.to_numpy(dtype=float) - center_year
        columns.extend([p * trend, np.square(p) * trend])
        names.extend(["pdsi_x_year_centered", "pdsi_squared_x_year_centered"])
    if form not in {"linear", "quadratic", "quadratic_linear_trend_interaction"}:
        raise ValueError(f"unknown form {form}")
    return np.column_stack(columns), names


def validate_and_prepare(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    input_config = config["input"]
    path = project_path(input_config["joined_panel"])
    receipt_path = project_path(input_config["public_receipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    joined_record = receipt.get("files", {}).get("joined")
    if not isinstance(joined_record, dict) or joined_record.get("sha256") != sha256(path):
        raise ValueError("joined PDSI panel differs from its public receipt")
    frame = pd.read_parquet(path)
    expected = input_config
    frame = frame.loc[
        frame.window_id.astype(str).eq(str(expected["window_id"]))
        & frame.calendar_role.astype(str).eq(str(expected["calendar_role"]))
        & frame.outcome_crop.astype(str).isin(map(str, expected["crops"]))
        & frame.irrigation_practice.astype(str).eq(str(expected["practice"]))
        & frame.harvest_year.between(int(expected["year_min"]), int(expected["year_max"]))
    ].copy()
    if frame.empty or frame.duplicated(["county_geoid", "outcome_crop", "harvest_year"]).any():
        raise ValueError("season panel is empty or duplicates crop-county-year keys")
    if set(frame.outcome_source_id.astype(str)) != {str(expected["outcome_source_id"])}:
        raise ValueError("outcome source changed")
    if set(frame.index_source_id.astype(str)) != {str(expected["index_source_id"])}:
        raise ValueError("PDSI source changed")
    if set(frame.calendar_role.astype(str)) != {str(expected["calendar_role"])}:
        raise ValueError("calendar role changed")
    if set(pd.to_numeric(frame.irrigation_share_vintage, errors="raise")) != {
        int(config["samples"]["irrigation_share_vintage"])
    }:
        raise ValueError("irrigation-share vintage changed")
    for gate in ["response_estimation_authorized", "scc_authorized", "response_estimation_authorized_pdsi", "scc_authorized_pdsi"]:
        if frame[gate].fillna(True).astype(bool).any():
            raise ValueError(f"upstream data unexpectedly opens {gate}")
    frame["yield"] = pd.to_numeric(frame.yield_bu_acre, errors="raise")
    frame["pdsi"] = pd.to_numeric(frame[config["models"]["pdsi_feature"]], errors="raise")
    if (frame["yield"] <= 0).any() or not np.isfinite(frame[["yield", "pdsi"]]).all().all():
        raise ValueError("yield/PDSI contains invalid values")
    frame["log_yield"] = np.log(frame["yield"])
    return frame, {"path": input_config["joined_panel"], "sha256": sha256(path), "rows": int(len(frame))}


def sample_mask(frame: pd.DataFrame, sample: str) -> pd.Series:
    if sample == "all_eligible":
        return pd.Series(True, index=frame.index)
    if sample == "irrigation_share_known":
        return frame.irrigation_share_eligible.fillna(False).astype(bool)
    if sample in {"rainfed_dominant_10pct", "rainfed_dominant_20pct", "rainfed_dominant_30pct"}:
        return frame[sample].fillna(False).astype(bool)
    raise ValueError(f"unknown sample {sample}")


def estimate_one(frame: pd.DataFrame, crop: str, sample: str, form: str, config: dict[str, Any]) -> dict[str, Any]:
    subset = frame.loc[frame.outcome_crop.eq(crop) & sample_mask(frame, sample)].copy()
    models = config["models"]
    if len(subset) < int(models["minimum_rows"]) or subset.county_geoid.nunique() < int(models["minimum_counties"]):
        raise ValueError(f"sample gate failed for {crop}/{sample}")
    state_year = subset.state.astype(str) + "_" + subset.harvest_year.astype(str)
    county_codes, _ = pd.factorize(subset.county_geoid.astype(str), sort=True)
    state_year_codes, _ = pd.factorize(state_year, sort=True)
    raw_x, names = design(subset, form, int(models["trend_center_year"]))
    stacked = np.column_stack([subset.log_yield.to_numpy(dtype=float), raw_x])
    residual, iterations, change = alternating_residualize(
        stacked,
        [county_codes, state_year_codes],
        float(models["demeaning_tolerance"]),
        int(models["demeaning_max_iterations"]),
    )
    y, x = residual[:, 0], residual[:, 1:]
    within_sd = x.std(axis=0, ddof=0)
    if np.any(within_sd <= float(models["minimum_within_standard_deviation"])):
        raise ValueError(f"near-constant residualized predictor for {crop}/{sample}/{form}")
    fit = clustered_ols(y, x, subset.county_geoid.to_numpy())
    coefficients = []
    for index, name in enumerate(names):
        beta = float(fit["beta"][index])
        se = float(fit["standard_error_cluster_county"][index])
        coefficients.append({
            "term": name,
            "estimate": beta,
            "standard_error_cluster_county": se,
            "ci95_normal": [beta - 1.96 * se, beta + 1.96 * se],
            "normal_approx_p_value": float(fit["normal_approx_p_value"][index]),
        })
    return {
        "crop": crop,
        "sample": sample,
        "form": form,
        "rows": int(len(subset)),
        "counties": int(subset.county_geoid.nunique()),
        "states": int(subset.state.nunique()),
        "year_min": int(subset.harvest_year.min()),
        "year_max": int(subset.harvest_year.max()),
        "pdsi_mean": float(subset.pdsi.mean()),
        "pdsi_standard_deviation": float(subset.pdsi.std(ddof=0)),
        "demeaning_iterations": iterations,
        "demeaning_final_max_change": change,
        "within_r_squared": fit["within_r_squared"],
        "residual_rmse_log_yield": fit["residual_rmse"],
        "cluster_count": fit["clusters"],
        "coefficients": coefficients,
    }


def run(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    frame, input_record = validate_and_prepare(config)
    samples = [config["samples"]["primary"], *config["samples"]["sensitivity"], *config["samples"]["descriptive"]]
    estimates = [
        estimate_one(frame, crop, sample, form, config)
        for crop in map(str, config["input"]["crops"])
        for sample in map(str, samples)
        for form in map(str, config["models"]["forms"])
    ]
    return {
        "schema": "us_national_all_practice_pdsi_association_result_v1",
        "analysis_id": config["analysis_id"],
        "status": "completed_historical_predictive_association_only",
        "input": input_record,
        "config": {"path": str(config_path.resolve().relative_to(PROJECT)), "sha256": sha256(config_path)},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": sha256(Path(__file__))},
        "fixed_effects": config["models"]["fixed_effects"],
        "cluster": config["models"]["cluster"],
        "primary_sample": config["samples"]["primary"],
        "primary_form": config["models"]["primary_form"],
        "estimates": estimates,
        "coefficients_emitted": True,
        "row_predictions_emitted": False,
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
        "disclaimer": config["output"]["required_disclaimer"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = run(args.config.resolve())
    out = args.out or project_path(load_config(args.config.resolve())["output"]["result"])
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix(out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(out)
    print(f"wrote {len(result['estimates'])} historical predictive associations to {out}")


if __name__ == "__main__":
    main()
