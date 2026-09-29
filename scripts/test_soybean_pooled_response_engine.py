#!/usr/bin/env python3
"""Deterministic synthetic/unit tests for the pooled soybean response engine."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import resource
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import soybean_pooled_response_engine as engine

ROOT = Path(__file__).resolve().parents[1]
np.seterr(all="ignore")  # Accelerate may emit stale floating flags for finite matmul results in this synthetic test process.


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def make_panel(config: dict[str, Any], years: list[int], seed: int, cells_per_block: int = 5, noise: float = 0.04) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(seed)
    block_locations = [(5 + row, column) for row in range(3) for column in range(4)]
    rows = []
    beta = np.array([0.04, -0.03, 0.02, 0.012, -0.008, 0.006, -0.14])
    country_year_effect = rng.normal(scale=0.20, size=(6, max(years) - min(years) + 1))
    block_year_effect = rng.normal(scale=0.025, size=(len(block_locations), len(years)))
    for block_id, (lat_bin, lon_bin) in enumerate(block_locations):
        country = block_id // 2
        lat = lat_bin * 10 - 90 + 5
        lon = lon_bin * 10 + 5
        for cell in range(cells_per_block):
            cell_id = f"c{block_id:02d}_{cell:02d}"
            latent_cell = rng.normal(size=3)
            for year_index, year in enumerate(years):
                latent = latent_cell + rng.normal(scale=0.8, size=3)
                heat = np.array([
                    latent[0] + rng.normal(scale=0.7), latent[1] + rng.normal(scale=0.7), latent[2] + rng.normal(scale=0.7),
                    0.35 * latent[0] + rng.normal(), 0.35 * latent[1] + rng.normal(), 0.35 * latent[2] + rng.normal(),
                ])
                moisture = 0.20 * latent[0] - 0.15 * latent[1] + rng.normal()
                x = np.r_[heat, moisture]
                d_log_yield = float(x @ beta + country_year_effect[country, year - min(years)] + block_year_effect[block_id, year_index] + rng.normal(scale=noise))
                prior_yield = 3.0 + 0.02 * cell
                current_yield = prior_yield * np.exp(d_log_yield)
                record = {
                    "cell_id": cell_id, "lat": float(lat), "lon_360": float(lon), "country_label": f"K{country:02d}", "country_count": 1,
                    "prior_year": year - 1, "pair_end_year": year, "yield_observed_prior": True, "yield_observed_current": True,
                    "yield_t_ha_prior": prior_yield, "yield_t_ha_current": current_yield,
                }
                for name, value in zip(config["controls"]["heat_columns"], heat): record[f"d_{name}"] = float(value)
                record["d_log1p_precip_mm"] = float(moisture)
                record["d_stage1_precip_share"] = float(rng.normal(scale=0.2))
                record["d_stage2_precip_share"] = float(rng.normal(scale=0.2))
                record["d_cdd_max_days"] = float(rng.normal(scale=5.0))
                record["d_rx5day_mm"] = float(rng.normal(scale=30.0))
                record["d_precipitation_concentration_hhi"] = float(rng.normal(scale=0.08))
                record["d_season_scpdsi_mean"] = float(0.5 * moisture + rng.normal(scale=0.8))
                rows.append(record)
    frame = pd.DataFrame(rows)
    frame["block10"] = engine.derive_block10(frame.lat.to_numpy(float), frame.lon_360.to_numpy(float))
    return frame, beta


def reference_residual(frame: pd.DataFrame, columns: list[str], mode: str) -> tuple[np.ndarray, np.ndarray]:
    y = np.log(frame.yield_t_ha_current.to_numpy(float)) - np.log(frame.yield_t_ha_prior.to_numpy(float))
    values = frame[columns].to_numpy(float)
    if mode == "country_year": keys = [frame.country_label, frame.pair_end_year]
    elif mode == "global_year": keys = [frame.pair_end_year]
    elif mode == "block10_year": keys = [frame.block10, frame.pair_end_year]
    else: raise AssertionError(mode)
    index = pd.MultiIndex.from_arrays(keys) if len(keys) > 1 else keys[0]
    y_series = pd.Series(y)
    y_residual = y_series - y_series.groupby(index).transform("mean")
    x_frame = pd.DataFrame(values, columns=columns)
    x_residual = x_frame - x_frame.groupby(index).transform("mean")
    return y_residual.to_numpy(float), x_residual.to_numpy(float)


def reference_residual_codes(values: np.ndarray, codes: np.ndarray) -> np.ndarray:
    series = pd.Series(values)
    return (series - series.groupby(pd.Series(codes)).transform("mean")).to_numpy(float)


def inverse_sqrt(matrix: np.ndarray) -> np.ndarray:
    values, vectors = np.linalg.eigh(matrix)
    require(np.all(values > 1e-10), "reference adjustment is singular")
    return (vectors / np.sqrt(values)) @ vectors.T


def reference_cr2(y: np.ndarray, x: np.ndarray, blocks: np.ndarray) -> dict[str, Any]:
    bread = np.linalg.inv(x.T @ x)
    coefficient = bread @ (x.T @ y)
    residual = y - x @ coefficient
    labels = np.unique(blocks)
    scores, adjustment_matrices, indices = [], [], []
    for label in labels:
        index = np.flatnonzero(blocks == label)
        xg = x[index]
        adjustment = inverse_sqrt(np.eye(len(index)) - xg @ bread @ xg.T)
        scores.append(xg.T @ adjustment @ residual[index])
        adjustment_matrices.append(adjustment); indices.append(index)
    scores = np.asarray(scores)
    covariance = bread @ (scores.T @ scores) @ bread
    dfs = []
    residual_maker = np.eye(len(y)) - x @ bread @ x.T
    for column in range(x.shape[1]):
        contrast = np.zeros(x.shape[1]); contrast[column] = 1
        direction = bread @ contrast
        l_vectors = []
        for index, adjustment in zip(indices, adjustment_matrices):
            embedded = np.zeros(len(y))
            embedded[index] = adjustment @ x[index] @ direction
            l_vectors.append(residual_maker @ embedded)
        gram = np.asarray(l_vectors) @ np.asarray(l_vectors).T
        dfs.append(float(np.trace(gram) ** 2 / np.sum(gram * gram)))
    return {
        "bread": bread, "coefficient": coefficient, "residual": residual, "covariance": covariance,
        "df": np.asarray(dfs), "scores": scores, "adjustments": adjustment_matrices, "indices": indices,
    }


def reference_bootstrap(fit: engine.FitResult, reference: dict[str, Any], config: dict[str, Any], draws: int, seed: int) -> dict[str, Any]:
    target = fit.features.index("d_log1p_precip_mm")
    nuisance = [index for index in range(fit.x.shape[1]) if index != target]
    x0 = fit.x[:, nuisance]
    fitted0 = x0 @ np.linalg.solve(x0.T @ x0, x0.T @ fit.y)
    residual0 = fit.y - fitted0
    labels, codes = np.unique(fit.blocks, return_inverse=True)
    webb = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        weights = webb[rng.integers(0, 6, size=len(labels))]
        y_star = fitted0 + residual0 * weights[codes]
        y_star = reference_residual_codes(y_star, fit.groups)
        coefficient = reference["bread"] @ fit.x.T @ y_star
        residual = y_star - fit.x @ coefficient
        scores = np.asarray([fit.x[index].T @ adjustment @ residual[index] for index, adjustment in zip(reference["indices"], reference["adjustments"])])
        covariance = reference["bread"] @ scores.T @ scores @ reference["bread"]
        values.append(coefficient[target] / np.sqrt(covariance[target, target]))
    values = np.asarray(values)
    observed = fit.coefficient[target] / np.sqrt(reference["covariance"][target, target])
    alpha = float(config["inference"]["alpha"])
    low, high = np.quantile(values, [alpha / 2, 1 - alpha / 2])
    return {"p": float((1 + np.sum(np.abs(values) >= abs(observed))) / (draws + 1)), "quantiles": np.array([low, high])}


def reference_terminal(training: pd.DataFrame, terminal: pd.DataFrame, config: dict[str, Any], draws: int, seed: int) -> dict[str, Any]:
    candidate_features = engine.family_features(config, "quantity")
    reference_features = [f"d_{column}" for column in config["controls"]["heat_columns"]]
    train_y, train_x = reference_residual(training, candidate_features, "country_year")
    beta_candidate = np.linalg.solve(train_x.T @ train_x, train_x.T @ train_y)
    _, train_reference_x = reference_residual(training, reference_features, "country_year")
    beta_reference = np.linalg.solve(train_reference_x.T @ train_reference_x, train_reference_x.T @ train_y)
    terminal_y, terminal_x = reference_residual(terminal, candidate_features, "country_year")
    _, terminal_reference_x = reference_residual(terminal, reference_features, "country_year")
    error_candidate = terminal_y - terminal_x @ beta_candidate
    error_reference = terminal_y - terminal_reference_x @ beta_reference
    blocks, codes = np.unique(terminal.block10.astype(str), return_inverse=True)
    count = np.bincount(codes)
    candidate_sse = np.bincount(codes, weights=error_candidate**2)
    reference_sse = np.bincount(codes, weights=error_reference**2)
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(draws):
        sample = rng.integers(0, len(blocks), size=len(blocks))
        n = count[sample].sum()
        boot.append(np.sqrt(candidate_sse[sample].sum() / n) - np.sqrt(reference_sse[sample].sum() / n))
    return {
        "point": float(np.sqrt(np.mean(error_candidate**2)) - np.sqrt(np.mean(error_reference**2))),
        "interval": np.quantile(boot, [0.025, 0.975]),
    }


def expect_violation(function, message: str) -> None:
    try:
        function()
    except engine.ProtocolViolation:
        return
    raise AssertionError(message)


def run_tests(config: dict[str, Any]) -> dict[str, Any]:
    training, target = make_panel(config, list(range(1999, 2011)), 20260928)
    terminal, _ = make_panel(config, list(range(2012, 2017)), 20260929)
    features = engine.family_features(config, "quantity")
    prepared = engine.prepare_pair_frame(training, features)
    require(np.max(np.abs(prepared.d_log_yield - (np.log(training.yield_t_ha_current) - np.log(training.yield_t_ha_prior)))) < 1e-14, "log difference contract")

    expect_violation(
        lambda: engine.fit_pooled(training, config, "quantity", "country_year"),
        "alternate synthetic years accepted without test_mode",
    )
    expect_violation(
        lambda: engine.fit_pooled(training, config, "quantity", "country_year", test_mode=1),
        "non-boolean test_mode bypassed the production-year contract",
    )
    fit = engine.fit_pooled(training, config, "quantity", "country_year", test_mode=True)
    reference_y, reference_x = reference_residual(training, features, "country_year")
    reference = reference_cr2(reference_y, reference_x, training.block10.astype(str).to_numpy())
    require(np.max(np.abs(fit.y - reference_y)) < 1e-12 and np.max(np.abs(fit.x - reference_x)) < 1e-12, "residualization differs")
    require(np.max(np.abs(fit.coefficient - reference["coefficient"])) < 1e-11, "OLS coefficient differs")
    require(np.max(np.abs(fit.covariance - reference["covariance"])) < 1e-10, "CR2 covariance differs")
    require(np.max(np.abs(fit.degrees_of_freedom - reference["df"])) < 1e-8, "Satterthwaite df differs")

    bootstrap_draws, bootstrap_seed = 199, 1441
    bootstrap = engine.wild_cluster_bootstrap_t(fit, config, draws=bootstrap_draws, seed=bootstrap_seed, test_mode=True)
    bootstrap_reference = reference_bootstrap(fit, reference, config, bootstrap_draws, bootstrap_seed)
    require(abs(bootstrap["two_sided_p_value"] - bootstrap_reference["p"]) < 1e-14, "wild bootstrap p differs")
    require(np.max(np.abs(np.asarray(bootstrap["bootstrap_t_quantiles"]) - bootstrap_reference["quantiles"])) < 1e-10, "wild bootstrap quantiles differ")
    expect_violation(lambda: engine.wild_cluster_bootstrap_t(fit, config, draws=199, seed=1, test_mode=False), "reduced production bootstrap accepted")

    controls = engine.control_sensitivities(training, config, test_mode=True)
    independent_controls = {}
    for mode in ("country_year", "global_year", "block10_year"):
        yr, xr = reference_residual(training, features, mode)
        independent_controls[mode] = float(np.linalg.solve(xr.T @ xr, xr.T @ yr)[-1])
    require(max(abs(controls["estimates"][key] - value) for key, value in independent_controls.items()) < 1e-11, "control sensitivity differs")

    influence = engine.leave_one_block_influence(training, config, test_mode=True)
    require(len(influence["leave_one_out"]) == training.block10.nunique(), "leave-one-block inventory differs")
    first_label = influence["leave_one_out"][0]["block10"]
    subset = training.loc[training.block10.ne(first_label)]
    yr, xr = reference_residual(subset, features, "country_year")
    reference_deleted = float(np.linalg.solve(xr.T @ xr, xr.T @ yr)[-1])
    require(abs(influence["leave_one_out"][0]["coefficient"] - reference_deleted) < 1e-11, "leave-one-block coefficient differs")

    synthetic_config = copy.deepcopy(config)
    synthetic_config["later_period_validation"]["minimum_terminal_pairs"] = 100
    synthetic_config["later_period_validation"]["minimum_terminal_blocks10"] = 10
    terminal_draws, terminal_seed = 199, 1771
    terminal_result = engine.terminal_transport_score(training, terminal, synthetic_config, "quantity", None, draws=terminal_draws, seed=terminal_seed, test_mode=True)
    terminal_reference = reference_terminal(training, terminal, synthetic_config, terminal_draws, terminal_seed)
    require(abs(terminal_result["point_rmse_difference"] - terminal_reference["point"]) < 1e-12, "terminal point loss differs")
    require(np.max(np.abs(np.asarray(terminal_result["cluster_bootstrap_interval"]) - terminal_reference["interval"])) < 1e-12, "terminal bootstrap differs")
    expect_violation(lambda: engine.terminal_transport_score(training, terminal, synthetic_config, "quantity", None, draws=199, seed=1, test_mode=False), "reduced production terminal bootstrap accepted")
    expect_violation(lambda: engine.wild_cluster_bootstrap_t(fit, config, draws=0, seed=1, test_mode=True), "zero wild-bootstrap draws accepted")
    expect_violation(lambda: engine.terminal_transport_score(training, terminal, synthetic_config, "quantity", None, draws=0, seed=1, test_mode=True), "zero terminal-bootstrap draws accepted")

    expect_violation(lambda: engine.family_features(config, "quantity", "country_proxy"), "country slopes accepted")
    stacked = copy.deepcopy(config)
    stacked["families"]["distribution"]["moisture_columns"].append("season_scpdsi_mean")
    expect_violation(lambda: engine.family_features(stacked, "distribution"), "direct/scPDSI stacking accepted")
    nonpositive = training.copy(); nonpositive.loc[0, "yield_t_ha_prior"] = 0.0
    expect_violation(lambda: engine.prepare_pair_frame(nonpositive, features), "nonpositive yield accepted")
    nonconsecutive = training.copy(); nonconsecutive.loc[0, "prior_year"] -= 1
    expect_violation(lambda: engine.prepare_pair_frame(nonconsecutive, features), "nonconsecutive pair accepted")
    wrong_block = training.copy(); wrong_block.loc[0, "block10"] = "wrong"
    expect_violation(lambda: engine.prepare_pair_frame(wrong_block, features), "incorrect spatial block accepted")
    duplicate = pd.concat([training, training.iloc[[0]]], ignore_index=True)
    expect_violation(lambda: engine.prepare_pair_frame(duplicate, features), "duplicate cell-year accepted")

    for column, value in (("lat", -90.0001), ("lat", 90.0001), ("lon_360", -0.0001), ("lon_360", 360.0)):
        invalid_coordinate = training.copy(); invalid_coordinate.loc[0, column] = value
        expect_violation(lambda data=invalid_coordinate: engine.prepare_pair_frame(data, features), f"out-of-range {column} accepted")
    integer_flag = training.copy(); integer_flag["yield_observed_prior"] = 1
    expect_violation(lambda: engine.prepare_pair_frame(integer_flag, features), "integer endpoint flag accepted as boolean")
    false_flag = training.copy(); false_flag.loc[0, "yield_observed_current"] = False
    expect_violation(lambda: engine.prepare_pair_frame(false_flag, features), "false endpoint flag accepted")
    for column in ("prior_year", "pair_end_year"):
        float_year = training.copy(); float_year[column] = float_year[column].astype(float)
        expect_violation(lambda data=float_year: engine.prepare_pair_frame(data, features), f"non-integer {column} dtype accepted")

    production_training, _ = make_panel(config, list(range(1983, 2011)), 20260930, cells_per_block=2)
    missing_training_year = production_training.loc[production_training.pair_end_year.ne(1983)].copy()
    expect_violation(
        lambda: engine.fit_pooled(missing_training_year, config, "quantity", "country_year"),
        "incomplete production training years accepted",
    )
    missing_terminal_boundary = terminal.loc[terminal.pair_end_year.ne(2012)].copy()
    expect_violation(
        lambda: engine.terminal_transport_score(production_training, missing_terminal_boundary, synthetic_config, "quantity", None),
        "terminal support missing 2012 accepted",
    )
    terminal_2011, _ = make_panel(config, [2011], 20260931, cells_per_block=2)
    buffer_leak = pd.concat([terminal_2011, terminal], ignore_index=True)
    expect_violation(
        lambda: engine.terminal_transport_score(production_training, buffer_leak, synthetic_config, "quantity", None),
        "2011 buffer leakage accepted",
    )
    terminal_2017, _ = make_panel(config, [2017], 20260932, cells_per_block=2)
    beyond_terminal = pd.concat([terminal, terminal_2017], ignore_index=True)
    expect_violation(
        lambda: engine.terminal_transport_score(production_training, beyond_terminal, synthetic_config, "quantity", None),
        "post-2016 terminal year accepted",
    )

    primary_index = features.index("d_log1p_precip_mm")
    recovery_error = float(abs(fit.coefficient[primary_index] - target[-1]))
    require(recovery_error < 0.02, "synthetic primary coefficient not recovered")
    tests = {
        "first_difference_input_contract": True,
        "country_year_residualization_matches_pandas_reference": True,
        "pooled_ols_matches_reference": True,
        "cr2_matches_bruteforce_reference": True,
        "satterthwaite_matches_bruteforce_reference": True,
        "restricted_null_webb_bootstrap_matches_reference": True,
        "leave_one_block_matches_reference": True,
        "control_sensitivities_match_reference": True,
        "terminal_transport_matches_reference": True,
        "reduced_draws_rejected_outside_test_mode": True,
        "zero_draws_fail_closed": True,
        "family_nonstacking_enforced": True,
        "geographic_slopes_prohibited": True,
        "invalid_input_contracts_fail_closed": True,
        "coordinate_bounds_fail_closed": True,
        "strict_boolean_flags_fail_closed": True,
        "integer_years_fail_closed": True,
        "production_training_years_enforced": True,
        "synthetic_alternate_years_require_test_mode": True,
        "test_mode_requires_boolean": True,
        "terminal_years_and_buffer_enforced": True,
        "synthetic_coefficient_recovery": True,
    }
    return {
        "all_pass": all(tests.values()), "tests": tests,
        "synthetic_recovery": {"known": float(target[-1]), "recovered": float(fit.coefficient[primary_index]), "absolute_error": recovery_error},
        "reference_tolerances": {"coefficient": 1e-11, "cr2_covariance": 1e-10, "satterthwaite_df": 1e-8, "bootstrap": 1e-10, "terminal": 1e-12},
        "synthetic_support": {"training_pairs": len(training), "terminal_pairs": len(terminal), "blocks10": training.block10.nunique(), "countries": training.country_label.nunique()},
        "test_bootstrap_draws": bootstrap_draws, "test_terminal_bootstrap_draws": terminal_draws,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh engine-test output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    results = run_tests(config)
    require(results["all_pass"], "one or more engine tests failed")
    rss = peak_rss_bytes(); cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"memory cap exceeded: {rss}")
    engine_path = ROOT / "scripts/soybean_pooled_response_engine.py"
    payload = {
        "schema": "soybean_pooled_response_engine_synthetic_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_engine_on_synthetic_data_only_no_real_outcome_read",
        "config": {"path": str(args.config), "sha256": digest(args.config)},
        "engine": {"path": str(engine_path.relative_to(ROOT)), "sha256": digest(engine_path)},
        "tests": results, "real_outcome_data_read": False, "real_coefficient_fit": False,
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "tests": results, "resources": payload["resources"]}, indent=2))


if __name__ == "__main__":
    main()
