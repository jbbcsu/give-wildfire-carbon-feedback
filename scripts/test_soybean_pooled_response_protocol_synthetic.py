#!/usr/bin/env python3
"""Synthetic-only tests for the pooled soybean response protocol mechanics."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def residualize(values: np.ndarray, groups: np.ndarray) -> np.ndarray:
    codes, inverse = np.unique(groups, return_inverse=True)
    matrix = values[:, None] if values.ndim == 1 else values
    totals = np.zeros((len(codes), matrix.shape[1]), dtype=float)
    np.add.at(totals, inverse, matrix)
    counts = np.bincount(inverse).astype(float)
    centered = matrix - totals[inverse] / counts[inverse, None]
    return centered[:, 0] if values.ndim == 1 else centered


def pooled_fit(y: np.ndarray, x: np.ndarray, fixed_effect_group: np.ndarray, block: np.ndarray) -> dict[str, Any]:
    yr = residualize(y, fixed_effect_group)
    xr = residualize(x, fixed_effect_group)
    rank = int(np.linalg.matrix_rank(xr))
    if rank < xr.shape[1]:
        return {"full_rank": False, "rank": rank, "columns": xr.shape[1]}
    gram_inverse = np.linalg.inv(xr.T @ xr)
    coefficient = gram_inverse @ (xr.T @ yr)
    with np.errstate(all="ignore"):
        residual = yr - xr @ coefficient
    require(np.isfinite(residual).all(), "nonfinite synthetic residual")
    unique_blocks = np.unique(block)
    meat = np.zeros((x.shape[1], x.shape[1]), dtype=float)
    for label in unique_blocks:
        score = xr[block == label].T @ residual[block == label]
        meat += np.outer(score, score)
    n, k, clusters = len(y), x.shape[1], len(unique_blocks)
    correction = clusters / (clusters - 1) * (n - 1) / (n - k)
    covariance = correction * gram_inverse @ meat @ gram_inverse
    standard_error = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    return {
        "full_rank": True, "rank": rank, "columns": k,
        "coefficient": coefficient, "cluster_standard_error": standard_error,
        "residual": residual,
    }


def numerical_design(x: np.ndarray, fixed_effect_group: np.ndarray) -> dict[str, Any]:
    xr = residualize(x, fixed_effect_group)
    scale = np.sqrt(np.mean(xr * xr, axis=0))
    if np.any(scale <= np.finfo(float).eps):
        return {"full_rank": False, "rank": int(np.linalg.matrix_rank(xr)), "columns": x.shape[1], "condition": None}
    standardized = xr / scale
    singular = np.linalg.svd(standardized, compute_uv=False)
    rank = int((singular > 1e-10 * singular[0]).sum())
    return {
        "full_rank": rank == x.shape[1], "rank": rank, "columns": x.shape[1],
        "condition": float(singular[0] / singular[-1]) if rank == x.shape[1] else None,
    }


def overlap_gate(moisture: np.ndarray, block: np.ndarray, minimum_fraction: float) -> dict[str, Any]:
    global_low, global_high = np.quantile(moisture, [0.05, 0.95])
    records = []
    for label in np.unique(block):
        values = moisture[block == label]
        p05, p95 = np.quantile(values, [0.05, 0.95])
        fraction = float(np.mean((values >= global_low) & (values <= global_high)))
        records.append(bool(p05 < 0 < p95 and fraction >= minimum_fraction))
    return {"blocks": len(records), "passing_blocks": int(sum(records)), "passes": all(records)}


def influence_gate(y: np.ndarray, x: np.ndarray, fixed_effect_group: np.ndarray, block: np.ndarray, primary_index: int, config: dict[str, Any]) -> dict[str, Any]:
    full = pooled_fit(y, x, fixed_effect_group, block)
    require(full["full_rank"], "influence test requires full rank")
    value = float(full["coefficient"][primary_index])
    standard_error = float(full["cluster_standard_error"][primary_index])
    require(standard_error > 0 and np.isfinite(standard_error), "invalid synthetic clustered standard error")
    leave_one_out = []
    for label in np.unique(block):
        keep = block != label
        fit = pooled_fit(y[keep], x[keep], fixed_effect_group[keep], block[keep])
        require(fit["full_rank"], "leave-one-block-out rank failure")
        leave_one_out.append(float(fit["coefficient"][primary_index]))
    leave_one_out_array = np.asarray(leave_one_out)
    sign_concordance = float(np.mean(np.sign(leave_one_out_array) == np.sign(value)))
    maximum_shift = float(np.max(np.abs(leave_one_out_array - value)) / standard_error)
    gates = config["postfit_influence_gates"]
    passes = sign_concordance >= float(gates["minimum_leave_one_block_out_primary_sign_concordance"]) and maximum_shift <= float(gates["maximum_leave_one_block_out_absolute_shift_in_primary_cr2_se"])
    return {"full_primary": value, "sign_concordance": sign_concordance, "maximum_shift_in_cluster_se": maximum_shift, "passes": passes}


def family_nonstacking_gate(columns: list[str]) -> bool:
    has_direct = any(column in {"log1p_precip_mm", "stage1_precip_share", "stage2_precip_share", "cdd_max_days", "rx5day_mm", "precipitation_concentration_hhi"} for column in columns)
    has_scpdsi = any("scpdsi" in column for column in columns)
    return not (has_direct and has_scpdsi)


def geographic_slope_gate(scope: str) -> bool:
    return scope == "pooled_global"


def later_gate(point: float, upper: float, improving_years: int, pairs: int, blocks: int, config: dict[str, Any]) -> bool:
    rule = config["later_period_validation"]
    return (
        point < 0 and upper < 0 and improving_years >= int(rule["minimum_improving_terminal_years_of_five"])
        and pairs >= int(rule["minimum_terminal_pairs"]) and blocks >= int(rule["minimum_terminal_blocks10"])
    )


def synthetic_panel(config: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    settings = config["synthetic_tests"]
    rng = np.random.default_rng(int(settings["seed"]))
    block_count, cells_per_block, years = 40, 12, 12
    block = np.repeat(np.arange(block_count), cells_per_block * years)
    cell_within_block = np.tile(np.repeat(np.arange(cells_per_block), years), block_count)
    year = np.tile(np.arange(years), block_count * cells_per_block)
    country = block // 4
    fixed_effect_group = country * years + year
    n = len(block)
    latent = rng.normal(size=(n, 3))
    heat = np.column_stack([
        latent[:, 0] + rng.normal(scale=0.8, size=n),
        latent[:, 1] + rng.normal(scale=0.8, size=n),
        latent[:, 2] + rng.normal(scale=0.8, size=n),
        0.4 * latent[:, 0] + rng.normal(size=n),
        0.4 * latent[:, 1] + rng.normal(size=n),
        0.4 * latent[:, 2] + rng.normal(size=n),
    ])
    moisture = 0.25 * latent[:, 0] - 0.20 * latent[:, 1] + rng.normal(size=n)
    x = np.column_stack([heat, moisture])
    target = np.array([0.04, -0.03, 0.02, 0.01, -0.015, 0.005, float(settings["known_primary_coefficient"])])
    fixed_effect = rng.normal(scale=0.25, size=country.max() * years + years)[fixed_effect_group]
    block_year_shock = rng.normal(scale=0.03, size=(block_count, years))[block, year]
    cell_noise = rng.normal(scale=0.07, size=n) + 0.005 * cell_within_block
    with np.errstate(all="ignore"):
        y = x @ target + fixed_effect + block_year_shock + cell_noise
    require(np.isfinite(y).all(), "nonfinite synthetic outcome")
    return y, x, fixed_effect_group, block, x.shape[1] - 1


def run_tests(config: dict[str, Any]) -> dict[str, Any]:
    y, x, group, block, primary_index = synthetic_panel(config)
    fit = pooled_fit(y, x, group, block)
    estimate = float(fit["coefficient"][primary_index])
    target = float(config["synthetic_tests"]["known_primary_coefficient"])
    recovery_error = abs(estimate - target)
    recovery = {
        "synthetic_only": True, "known_coefficient": target, "recovered_coefficient": estimate,
        "absolute_error": recovery_error, "full_rank": fit["full_rank"],
        "finite_positive_cluster_standard_error": bool(np.isfinite(fit["cluster_standard_error"][primary_index]) and fit["cluster_standard_error"][primary_index] > 0),
        "passes": bool(fit["full_rank"] and recovery_error <= float(config["synthetic_tests"]["maximum_absolute_recovery_error"])),
    }
    stable_influence = influence_gate(y, x, group, block, primary_index, config)

    collinear = np.column_stack([x, x[:, 0]])
    rank_result = numerical_design(collinear, group)
    rank_failure = {"detected": not rank_result["full_rank"], "diagnostic": rank_result, "passes": not rank_result["full_rank"]}

    bad_moisture = x[:, primary_index].copy()
    bad_moisture[block == 0] = np.abs(bad_moisture[block == 0]) + 0.01
    overlap = overlap_gate(bad_moisture, block, float(config["prefit_gates"]["minimum_each_block_fraction_inside_global_quantity_p05_p95"]))
    overlap_failure = {"detected": not overlap["passes"], "diagnostic": overlap, "passes": not overlap["passes"]}

    rng = np.random.default_rng(int(config["synthetic_tests"]["seed"]) + 1)
    influence_y = rng.normal(scale=0.08, size=len(y))
    influence_y[block == 0] += 6.0 * x[block == 0, primary_index]
    unstable = influence_gate(influence_y, x, group, block, primary_index, config)
    influence_failure = {"detected": not unstable["passes"], "diagnostic": unstable, "passes": not unstable["passes"]}

    stacking_allowed = family_nonstacking_gate(["log1p_precip_mm", "season_scpdsi_mean"])
    family_failure = {"detected": not stacking_allowed, "passes": not stacking_allowed}
    geographic_allowed = geographic_slope_gate("country_proxy") or geographic_slope_gate("block10")
    geographic_failure = {"detected": not geographic_allowed, "passes": not geographic_allowed}

    later_failed = later_gate(-0.001, 0.0002, 3, 25000, 55, config)
    later_passed = later_gate(-0.001, -0.0002, 4, 25000, 55, config)
    later_test = {"failing_case_rejected": not later_failed, "passing_case_accepted": later_passed, "passes": bool(not later_failed and later_passed)}

    tests = {
        "coefficient_recovery": recovery,
        "stable_influence_acceptance": {**stable_influence, "passes": stable_influence["passes"]},
        "rank_failure": rank_failure,
        "overlap_failure": overlap_failure,
        "influence_failure": influence_failure,
        "family_nonstacking_failure": family_failure,
        "geographic_slope_prohibition": geographic_failure,
        "later_validation_fail_closed": later_test,
    }
    return {"tests": tests, "all_pass": all(record["passes"] for record in tests.values())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh synthetic-test output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    require(config["prohibitions"]["real_outcome_fit_during_protocol_validation"] is True, "real-fit prohibition changed")
    result = run_tests(config)
    require(result["all_pass"], "one or more synthetic protocol tests failed")
    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"memory cap exceeded: {rss}")
    payload = {
        "schema": "soybean_pooled_response_protocol_synthetic_tests/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_synthetic_only_no_real_outcome_fit",
        "config": {"path": str(args.config), "sha256": digest(args.config)},
        "real_outcome_data_read": False,
        "results": result,
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "results": result, "resources": payload["resources"]}, indent=2))


if __name__ == "__main__":
    main()
