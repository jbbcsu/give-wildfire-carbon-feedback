#!/usr/bin/env python3
"""Clean-room numerical audit of the direct-practice precipitation fits."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT / "us_county_validation/us_direct_practice_precipitation_association_v1.toml"
DEFAULT_CANDIDATE = PROJECT / "data/provenance/us_direct_practice_precipitation_association_20260826.json"
DEFAULT_OUTPUT = PROJECT / "data/provenance/us_direct_practice_precipitation_association_independent_validation_20260826.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def residualize(values: np.ndarray, groups: list[np.ndarray]) -> np.ndarray:
    """Independent alternating-projection implementation."""
    result = values.astype(float, copy=True)
    for _ in range(1000):
        prior = result.copy()
        for group in groups:
            count = np.bincount(group).astype(float)
            totals = np.vstack([
                np.bincount(group, weights=result[:, column], minlength=len(count))
                for column in range(result.shape[1])
            ]).T
            result -= (totals / count[:, None])[group]
        if np.max(np.abs(result - prior)) <= 1e-10:
            return result
    raise AssertionError("clean-room fixed-effect projection did not converge")


def qr_cluster_fit(y: np.ndarray, x: np.ndarray, clusters: np.ndarray) -> dict[str, np.ndarray | float | int]:
    """Solve by reduced QR and independently form the county sandwich."""
    scale = x.std(axis=0)
    z = x / scale
    q, r = np.linalg.qr(z, mode="reduced")
    beta_z = np.linalg.solve(r, np.einsum("ni,n->i", q, y, optimize=False))
    error = y - np.einsum("ni,i->n", z, beta_z, optimize=False)
    bread = np.linalg.inv(np.einsum("ni,nj->ij", z, z, optimize=False))
    codes, labels = pd.factorize(pd.Series(clusters, dtype="string"), sort=True)
    meat = np.zeros((z.shape[1], z.shape[1]))
    for code in range(len(labels)):
        score = np.einsum(
            "ni,n->i", z[codes == code], error[codes == code], optimize=False
        )
        meat += np.outer(score, score)
    n, k = z.shape
    correction = (len(labels) / (len(labels) - 1)) * ((n - 1) / (n - k))
    se_z = np.sqrt(np.maximum(np.diag(correction * bread @ meat @ bread), 0))
    beta = beta_z / scale
    se = se_z / scale
    return {
        "beta": beta,
        "se": se,
        "covariance": correction * bread @ meat @ bread / np.outer(scale, scale),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "r2": float(1 - np.sum(error**2) / np.sum(y**2)),
        "clusters": len(labels),
    }


def design(frame: pd.DataFrame, form: str) -> tuple[np.ndarray, list[str]]:
    columns: list[np.ndarray] = []
    names: list[str] = []
    for name in ("stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c"):
        value = frame[name].to_numpy(float)
        columns += [value, value**2]
        names += [name, f"{name}_squared"]
    rain = frame.precip_mm.to_numpy(float) / 100
    columns += [rain, rain**2]
    names += ["precipitation_per_100mm", "precipitation_per_100mm_squared"]
    if form == "quantity_timing":
        columns += [frame.stage1_precip_share.to_numpy(float), frame.stage2_precip_share.to_numpy(float)]
        names += ["stage1_precip_share", "stage2_precip_share"]
    return np.column_stack(columns), names


def audit(config_path: Path, candidate_path: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text())
    candidate = json.loads(candidate_path.read_text())
    panel_path = PROJECT / config["input"]["panel"]
    if digest(panel_path) != config["input"]["expected_panel_sha256"]:
        raise AssertionError("panel hash changed")
    if candidate["input"]["sha256"] != digest(panel_path):
        raise AssertionError("candidate does not bind the audited panel")
    primitives = PROJECT / candidate["estimation_primitives"]["path"]
    if candidate["estimation_primitives"]["sha256"] != digest(primitives):
        raise AssertionError("candidate estimation-primitives dependency changed")
    panel = pd.read_parquet(panel_path)
    panel = panel.loc[
        panel.outcome_crop.isin(config["input"]["crops"])
        & panel.irrigation_practice.isin(config["input"]["practices"])
        & panel.harvest_year.between(config["input"]["year_min"], config["input"]["year_max"])
    ].copy()
    panel["log_yield"] = np.log(panel.yield_bu_acre.astype(float))
    maximum = 0.0
    comparisons = 0
    for reported in candidate["estimates"]:
        subset = panel.loc[
            panel.outcome_crop.eq(reported["crop"])
            & panel.irrigation_practice.eq(reported["irrigation_practice"])
        ].copy()
        county, _ = pd.factorize(subset.county_geoid.astype(str), sort=True)
        state_year, _ = pd.factorize(subset.state.astype(str) + "_" + subset.harvest_year.astype(str), sort=True)
        x, names = design(subset, reported["form"])
        transformed = residualize(np.column_stack([subset.log_yield.to_numpy(), x]), [county, state_year])
        fit = qr_cluster_fit(transformed[:, 0], transformed[:, 1:], subset.county_geoid.to_numpy())
        checks: list[tuple[float, float]] = [
            (float(fit["rmse"]), reported["residual_rmse_log_yield"]),
            (float(fit["r2"]), reported["within_r_squared"]),
            (float(fit["clusters"]), reported["cluster_count"]),
        ]
        for index, coefficient in enumerate(reported["coefficients"]):
            if coefficient["term"] != names[index]:
                raise AssertionError("coefficient order changed")
            beta = float(np.asarray(fit["beta"])[index])
            se = float(np.asarray(fit["se"])[index])
            p = math.erfc(abs(beta / se) / math.sqrt(2))
            checks += [(beta, coefficient["estimate"]), (se, coefficient["standard_error_cluster_county"]), (p, coefficient["normal_approx_p_value"])]
        covariance = np.asarray(fit["covariance"])
        p_index = names.index("precipitation_per_100mm")
        p2_index = names.index("precipitation_per_100mm_squared")
        for contrast in reported["contrasts"]["quantity_increment_contrasts"]:
            reference = contrast["reference_precipitation_mm"] / 100
            gradient = np.zeros(len(names))
            gradient[p_index] = 1
            gradient[p2_index] = (reference + 1) ** 2 - reference**2
            delta = float(gradient @ np.asarray(fit["beta"]))
            se_delta = float(np.sqrt(max(gradient @ covariance @ gradient, 0)))
            checks += [
                (delta, contrast["fitted_log_yield_difference"]),
                (se_delta, contrast["standard_error_cluster_county_log_difference"]),
                (100 * math.expm1(delta), contrast["fitted_percent_yield_difference"]),
            ]
        if reported["form"] == "quantity_timing":
            contrast = reported["contrasts"]["stage3_to_stage2_shift"]
            gradient = np.zeros(len(names))
            gradient[names.index("stage2_precip_share")] = 0.1
            delta = float(gradient @ np.asarray(fit["beta"]))
            se_delta = float(np.sqrt(max(gradient @ covariance @ gradient, 0)))
            checks += [
                (delta, contrast["fitted_log_yield_difference"]),
                (se_delta, contrast["standard_error_cluster_county_log_difference"]),
                (100 * math.expm1(delta), contrast["fitted_percent_yield_difference"]),
            ]
        for actual, expected in checks:
            maximum = max(maximum, abs(actual - float(expected)))
            comparisons += 1
    if maximum > 1e-10:
        raise AssertionError(f"clean-room disagreement exceeds tolerance: {maximum}")
    return {
        "schema": "us_direct_practice_precipitation_association_independent_validation_v1",
        "status": "validated_independent_qr_reimplementation",
        "candidate": {"path": str(candidate_path.relative_to(PROJECT)), "sha256": digest(candidate_path)},
        "config": {"path": str(config_path.relative_to(PROJECT)), "sha256": digest(config_path)},
        "panel": {"path": str(panel_path.relative_to(PROJECT)), "sha256": digest(panel_path)},
        "audit_implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
        "estimates_audited": len(candidate["estimates"]),
        "numeric_comparisons": comparisons,
        "maximum_absolute_disagreement": maximum,
        "tolerance": 1e-10,
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = audit(args.config.resolve(), args.candidate.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    partial = args.out.with_suffix(args.out.suffix + ".partial")
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    partial.replace(args.out)
    print(f"independent audit passed: {result['numeric_comparisons']} comparisons, max disagreement {result['maximum_absolute_disagreement']:.3g}")


if __name__ == "__main__":
    main()
