#!/usr/bin/env python3
"""File-I/O-free pooled soybean response/inference engine.

The engine implements the frozen protocol mechanics. It does not locate or read
real outcome data. Callers must provide an in-memory pair table that satisfies
the strict input contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_integer_dtype
from scipy import stats


class ProtocolViolation(ValueError):
    """Raised whenever an input or requested analysis violates the protocol."""


def require(value: bool, message: str) -> None:
    if not value:
        raise ProtocolViolation(message)


def require_test_mode_flag(test_mode: bool) -> None:
    require(type(test_mode) is bool, "test_mode must be an explicit boolean")


def family_features(config: dict[str, Any], family: str, slope_scope: str = "pooled_global") -> list[str]:
    require(slope_scope == "pooled_global", "country-, block-, cell-, and irrigation-specific slopes are prohibited")
    require(family in config["families"], f"undeclared family: {family}")
    require(family in {"quantity", "distribution", "scpdsi_season"}, "family is not authorized for the v1 engine")
    moisture = list(config["families"][family]["moisture_columns"])
    direct = {"log1p_precip_mm", "stage1_precip_share", "stage2_precip_share", "cdd_max_days", "rx5day_mm", "precipitation_concentration_hhi"}
    has_direct = any(column in direct for column in moisture)
    has_scpdsi = any("scpdsi" in column for column in moisture)
    require(not (has_direct and has_scpdsi), "direct precipitation and scPDSI may not be stacked")
    if family == "quantity": require(moisture == ["log1p_precip_mm"], "quantity family changed")
    if family == "scpdsi_season": require(moisture == ["season_scpdsi_mean"], "scPDSI family changed")
    return [f"d_{column}" for column in list(config["controls"]["heat_columns"]) + moisture]


def derive_block10(lat: np.ndarray, lon_360: np.ndarray) -> np.ndarray:
    lat_bin = np.minimum(np.floor((lat + 90.0) / 10.0).astype(int), 17)
    lon_bin = np.floor(np.mod(lon_360, 360.0) / 10.0).astype(int)
    return np.asarray([f"b{a:02d}_{b:02d}" for a, b in zip(lat_bin, lon_bin)], dtype=object)


def prepare_pair_frame(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    required = {
        "cell_id", "lat", "lon_360", "country_label", "country_count", "prior_year", "pair_end_year",
        "yield_observed_prior", "yield_observed_current", "yield_t_ha_prior", "yield_t_ha_current",
    } | set(features)
    require(required <= set(frame.columns), f"missing input-contract columns: {sorted(required - set(frame.columns))}")
    require(len(frame) > 0, "empty pair table")
    require(not frame.duplicated(["cell_id", "pair_end_year"]).any(), "duplicate cell/pair-end-year rows")
    for column in ("yield_observed_prior", "yield_observed_current"):
        require(is_bool_dtype(frame[column].dtype), f"{column} must have strict boolean dtype")
        require(frame[column].notna().all() and frame[column].eq(True).all(), "unobserved yield endpoint")
    for column in ("prior_year", "pair_end_year", "country_count"):
        require(is_integer_dtype(frame[column].dtype) and not is_bool_dtype(frame[column].dtype), f"{column} must have integer dtype")
        require(frame[column].notna().all(), f"{column} contains a missing value")
    require(frame["yield_t_ha_prior"].gt(0).all() and frame["yield_t_ha_current"].gt(0).all(), "yield endpoints must be strictly positive")
    require(frame["pair_end_year"].sub(frame["prior_year"]).eq(1).all(), "pair endpoints must be consecutive")
    require(frame["country_count"].eq(1).all(), "primary pooled input requires singleton country proxies")
    require(frame["country_label"].notna().all() and frame["country_label"].astype(str).str.len().gt(0).all(), "missing country proxy")
    numeric = ["lat", "lon_360", "yield_t_ha_prior", "yield_t_ha_current"] + features
    require(np.isfinite(frame[numeric].to_numpy(dtype=float)).all(), "nonfinite outcome endpoint or regressor")
    require(frame["lat"].between(-90.0, 90.0, inclusive="both").all(), "latitude must lie in [-90, 90]")
    require(frame["lon_360"].ge(0.0).all() and frame["lon_360"].lt(360.0).all(), "longitude must lie in [0, 360)")
    derived = derive_block10(frame["lat"].to_numpy(float), frame["lon_360"].to_numpy(float))
    if "block10" in frame:
        require(np.array_equal(frame["block10"].astype(str).to_numpy(), derived.astype(str)), "provided block10 differs from coordinates")
    out = frame.copy()
    out["block10"] = derived
    out["d_log_yield"] = np.log(out["yield_t_ha_current"].to_numpy(float)) - np.log(out["yield_t_ha_prior"].to_numpy(float))
    require(np.isfinite(out["d_log_yield"]).all(), "nonfinite log-yield first difference")
    return out


def require_training_year_contract(frame: pd.DataFrame, config: dict[str, Any], test_mode: bool) -> None:
    require_test_mode_flag(test_mode)
    if test_mode:
        return
    sample = config["sample"]
    expected = set(range(int(sample["training_pair_end_year_minimum"]), int(sample["training_pair_end_year_maximum"]) + 1))
    observed = set(frame["pair_end_year"].astype(int).unique())
    require(observed == expected, f"production training pair years must equal {min(expected)}-{max(expected)}")
    require(int(sample["buffer_year"]) == max(expected) + 1, "frozen buffer year is not immediately after training")


def require_terminal_year_contract(training: pd.DataFrame, terminal: pd.DataFrame, config: dict[str, Any], test_mode: bool) -> None:
    require_test_mode_flag(test_mode)
    if test_mode:
        return
    sample = config["sample"]
    expected_training = set(range(int(sample["training_pair_end_year_minimum"]), int(sample["training_pair_end_year_maximum"]) + 1))
    expected_terminal = set(range(int(sample["terminal_level_year_minimum"]), int(sample["terminal_level_year_maximum"]) + 1))
    training_years = set(training["pair_end_year"].astype(int).unique())
    terminal_years = set(terminal["pair_end_year"].astype(int).unique())
    buffer_year = int(sample["buffer_year"])
    require(training_years == expected_training, "terminal scoring training years differ from the frozen 1983-2010 contract")
    require(terminal_years == expected_terminal, "production terminal pair years must equal 2012-2016")
    require(max(training_years) == buffer_year - 1 and min(terminal_years) == buffer_year + 1, "the frozen 2011 buffer is not preserved")
    require(buffer_year not in training_years and buffer_year not in terminal_years, "buffer year entered training or terminal support")


def group_codes(frame: pd.DataFrame, mode: str) -> np.ndarray:
    if mode == "country_year":
        labels = pd.MultiIndex.from_arrays([frame["country_label"].astype(str), frame["pair_end_year"].astype(int)])
    elif mode == "global_year":
        labels = frame["pair_end_year"].astype(int)
    elif mode == "block10_year":
        labels = pd.MultiIndex.from_arrays([frame["block10"].astype(str), frame["pair_end_year"].astype(int)])
    else:
        raise ProtocolViolation(f"undeclared group-year control: {mode}")
    codes, _ = pd.factorize(labels, sort=True)
    require(np.all(codes >= 0), "missing group-year control")
    return codes.astype(np.int64, copy=False)


def residualize(values: np.ndarray, codes: np.ndarray) -> np.ndarray:
    matrix = values[:, None] if values.ndim == 1 else values
    groups = int(codes.max()) + 1
    totals = np.zeros((groups, matrix.shape[1]), dtype=float)
    np.add.at(totals, codes, matrix)
    counts = np.bincount(codes, minlength=groups).astype(float)
    centered = matrix - totals[codes] / counts[codes, None]
    return centered[:, 0] if values.ndim == 1 else centered


@dataclass
class ClusterAdjustment:
    label: str
    index: np.ndarray
    x: np.ndarray
    u: np.ndarray
    delta: np.ndarray

    def apply(self, values: np.ndarray) -> np.ndarray:
        if self.u.shape[1] == 0:
            return values.copy()
        return values + self.u @ (self.delta[:, None] * (self.u.T @ values) if values.ndim == 2 else self.delta * (self.u.T @ values))


def build_adjustments(x: np.ndarray, block: np.ndarray, bread: np.ndarray) -> list[ClusterAdjustment]:
    eigen_bread, vectors_bread = np.linalg.eigh(bread)
    require(np.all(eigen_bread > 0), "non-positive OLS bread")
    bread_root = (vectors_bread * np.sqrt(eigen_bread)) @ vectors_bread.T
    adjustments: list[ClusterAdjustment] = []
    for label in np.unique(block):
        index = np.flatnonzero(block == label)
        xg = x[index]
        w = xg @ bread_root
        eigen, vectors = np.linalg.eigh(w.T @ w)
        keep = eigen > 1e-12
        eigen = eigen[keep]
        vectors = vectors[:, keep]
        require(np.all(eigen < 1.0 - 1e-10), f"cluster hat eigenvalue reaches one: {label}")
        u = w @ vectors / np.sqrt(eigen)[None, :] if len(eigen) else np.zeros((len(index), 0))
        delta = 1.0 / np.sqrt(1.0 - eigen) - 1.0
        adjustments.append(ClusterAdjustment(str(label), index, xg, u, delta))
    return adjustments


def cr2_from_residual(residual: np.ndarray, adjustments: list[ClusterAdjustment], bread: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scores = []
    for adjustment in adjustments:
        adjusted = adjustment.apply(residual[adjustment.index])
        scores.append(adjustment.x.T @ adjusted)
    score_matrix = np.asarray(scores)
    covariance = bread @ (score_matrix.T @ score_matrix) @ bread
    require(np.isfinite(covariance).all(), "nonfinite CR2 covariance")
    return covariance, score_matrix


def satterthwaite_df(x: np.ndarray, bread: np.ndarray, adjustments: list[ClusterAdjustment], contrast: np.ndarray) -> float:
    direction = bread @ contrast
    norms = []
    b_vectors = []
    for adjustment in adjustments:
        a = adjustment.apply(adjustment.x @ direction)
        norms.append(float(a @ a))
        b_vectors.append(adjustment.x.T @ a)
    b = np.asarray(b_vectors)
    with np.errstate(all="ignore"):
        cross = -(b @ bread @ b.T)
    require(np.isfinite(cross).all(), "nonfinite Satterthwaite cross-products")
    cross[np.diag_indices_from(cross)] += np.asarray(norms)
    trace = float(np.trace(cross))
    denominator = float(np.sum(cross * cross))
    require(trace > 0 and denominator > 0, "invalid Satterthwaite quadratic form")
    return trace * trace / denominator


@dataclass
class FitResult:
    family: str
    group_mode: str
    features: list[str]
    prepared: pd.DataFrame
    y: np.ndarray
    x: np.ndarray
    groups: np.ndarray
    blocks: np.ndarray
    coefficient: np.ndarray
    residual: np.ndarray
    bread: np.ndarray
    covariance: np.ndarray
    standard_error: np.ndarray
    degrees_of_freedom: np.ndarray
    t_statistic: np.ndarray
    p_value: np.ndarray
    confidence_interval: np.ndarray
    score_matrix: np.ndarray
    adjustments: list[ClusterAdjustment]

    def summary(self) -> dict[str, Any]:
        return {
            "family": self.family, "group_mode": self.group_mode, "features": self.features,
            "pairs": len(self.y), "clusters": len(self.adjustments),
            "rank": int(np.linalg.matrix_rank(self.x)), "columns": self.x.shape[1],
            "coefficient": self.coefficient.tolist(), "standard_error": self.standard_error.tolist(),
            "degrees_of_freedom": self.degrees_of_freedom.tolist(), "t_statistic": self.t_statistic.tolist(),
            "p_value": self.p_value.tolist(), "confidence_interval": self.confidence_interval.tolist(),
        }


def fit_pooled(frame: pd.DataFrame, config: dict[str, Any], family: str = "quantity", group_mode: str = "country_year", slope_scope: str = "pooled_global", test_mode: bool = False) -> FitResult:
    features = family_features(config, family, slope_scope)
    prepared = prepare_pair_frame(frame, features)
    require_training_year_contract(prepared, config, test_mode)
    groups = group_codes(prepared, group_mode)
    y = residualize(prepared["d_log_yield"].to_numpy(float), groups)
    x = residualize(prepared[features].to_numpy(float), groups)
    require(np.linalg.matrix_rank(x) == x.shape[1], "residualized design is rank deficient")
    gram = x.T @ x
    bread = np.linalg.inv(gram)
    with np.errstate(all="ignore"):
        coefficient = bread @ (x.T @ y)
        residual = y - x @ coefficient
    require(np.isfinite(coefficient).all() and np.isfinite(residual).all(), "nonfinite pooled fit")
    blocks = prepared["block10"].astype(str).to_numpy()
    require(len(np.unique(blocks)) >= 2, "at least two spatial clusters are required")
    adjustments = build_adjustments(x, blocks, bread)
    covariance, score_matrix = cr2_from_residual(residual, adjustments, bread)
    standard_error = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    require(np.all(np.isfinite(standard_error) & (standard_error > 0)), "invalid CR2 standard error")
    dfs, statistics, probabilities, intervals = [], [], [], []
    alpha = float(config["inference"]["alpha"])
    for column in range(x.shape[1]):
        contrast = np.zeros(x.shape[1]); contrast[column] = 1.0
        df = satterthwaite_df(x, bread, adjustments, contrast)
        statistic = coefficient[column] / standard_error[column]
        probability = 2.0 * stats.t.sf(abs(statistic), df)
        critical = stats.t.ppf(1.0 - alpha / 2.0, df)
        dfs.append(df); statistics.append(statistic); probabilities.append(probability)
        intervals.append([coefficient[column] - critical * standard_error[column], coefficient[column] + critical * standard_error[column]])
    return FitResult(
        family, group_mode, features, prepared, y, x, groups, blocks, coefficient, residual, bread,
        covariance, standard_error, np.asarray(dfs), np.asarray(statistics), np.asarray(probabilities),
        np.asarray(intervals), score_matrix, adjustments,
    )


def wild_cluster_bootstrap_t(fit: FitResult, config: dict[str, Any], target_feature: str = "d_log1p_precip_mm", draws: int | None = None, seed: int | None = None, test_mode: bool = False) -> dict[str, Any]:
    require_test_mode_flag(test_mode)
    require(target_feature in fit.features, "target feature absent from fitted family")
    target = fit.features.index(target_feature)
    configured_draws = int(config["inference"]["wild_cluster_bootstrap_draws"])
    draws = configured_draws if draws is None else int(draws)
    require(draws == configured_draws or test_mode, "reduced bootstrap draws are allowed only in synthetic/unit-test mode")
    require(draws > 0, "bootstrap draws must be positive")
    seed = int(config["inference"]["wild_cluster_bootstrap_seed"] if seed is None else seed)
    nuisance = [index for index in range(fit.x.shape[1]) if index != target]
    if nuisance:
        x0 = fit.x[:, nuisance]
        restricted_coefficient = np.linalg.solve(x0.T @ x0, x0.T @ fit.y)
        with np.errstate(all="ignore"):
            restricted_fitted = x0 @ restricted_coefficient
    else:
        restricted_fitted = np.zeros_like(fit.y)
    restricted_residual = fit.y - restricted_fitted
    labels, block_codes = np.unique(fit.blocks, return_inverse=True)
    webb = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])
    rng = np.random.default_rng(seed)
    statistics = np.empty(draws, dtype=float)
    for draw in range(draws):
        weights = webb[rng.integers(0, 6, size=len(labels))]
        y_star = restricted_fitted + restricted_residual * weights[block_codes]
        # Block weights break country-year orthogonality when fixed-effect groups
        # span multiple blocks, so every bootstrap draw must be re-absorbed.
        y_star = residualize(y_star, fit.groups)
        with np.errstate(all="ignore"):
            coefficient = fit.bread @ (fit.x.T @ y_star)
            residual = y_star - fit.x @ coefficient
        require(np.isfinite(coefficient).all() and np.isfinite(residual).all(), "nonfinite bootstrap fit")
        covariance, _ = cr2_from_residual(residual, fit.adjustments, fit.bread)
        standard_error = float(np.sqrt(max(covariance[target, target], 0.0)))
        require(np.isfinite(standard_error) and standard_error > 0, "invalid bootstrap CR2 standard error")
        statistics[draw] = coefficient[target] / standard_error
    observed = float(fit.t_statistic[target])
    p_value = float((1 + np.sum(np.abs(statistics) >= abs(observed))) / (draws + 1))
    alpha = float(config["inference"]["alpha"])
    low, high = np.quantile(statistics, [alpha / 2.0, 1.0 - alpha / 2.0])
    confidence_interval = [
        float(fit.coefficient[target] - high * fit.standard_error[target]),
        float(fit.coefficient[target] - low * fit.standard_error[target]),
    ]
    return {
        "target_feature": target_feature, "draws": draws, "seed": seed, "weights": "Webb_six_point",
        "restricted_null": 0.0, "observed_t": observed, "two_sided_p_value": p_value,
        "percentile_t_confidence_interval": confidence_interval,
        "bootstrap_t_quantiles": [float(low), float(high)],
    }


def leave_one_block_influence(frame: pd.DataFrame, config: dict[str, Any], family: str = "quantity", target_feature: str = "d_log1p_precip_mm", test_mode: bool = False) -> dict[str, Any]:
    full = fit_pooled(frame, config, family, "country_year", test_mode=test_mode)
    require(target_feature in full.features, "influence target absent")
    target = full.features.index(target_feature)
    full_value = float(full.coefficient[target])
    full_se = float(full.standard_error[target])
    leave_one_out = []
    for label in np.unique(full.blocks):
        subset = full.prepared.loc[full.prepared["block10"].astype(str).ne(label)].copy()
        refit = fit_pooled(subset, config, family, "country_year", test_mode=test_mode)
        leave_one_out.append({"block10": str(label), "coefficient": float(refit.coefficient[target])})
    values = np.asarray([record["coefficient"] for record in leave_one_out])
    concordance = float(np.mean(np.sign(values) == np.sign(full_value)))
    maximum_shift = float(np.max(np.abs(values - full_value)) / full_se)
    contrast = full.bread[:, target]
    contributions = full.score_matrix @ contrast
    score_denominator = float(np.abs(contributions).sum())
    require(np.isfinite(score_denominator) and score_denominator > 0, "zero or nonfinite block-score denominator")
    score_share = np.abs(contributions) / score_denominator
    residual_sums = np.asarray([np.sum(full.residual[adjustment.index] ** 2) for adjustment in full.adjustments])
    residual_denominator = float(residual_sums.sum())
    require(np.isfinite(residual_denominator) and residual_denominator > 0, "zero or nonfinite squared-residual denominator")
    residual_share = residual_sums / residual_denominator
    gates = config["postfit_influence_gates"]
    checks = {
        "sign_concordance": concordance >= float(gates["minimum_leave_one_block_out_primary_sign_concordance"]),
        "maximum_shift": maximum_shift <= float(gates["maximum_leave_one_block_out_absolute_shift_in_primary_cr2_se"]),
        "maximum_score_share": float(score_share.max()) <= float(gates["maximum_single_block_score_share"]),
        "maximum_squared_residual_share": float(residual_share.max()) <= float(gates["maximum_single_block_squared_residual_share"]),
    }
    return {
        "target_feature": target_feature, "leave_one_out": leave_one_out, "sign_concordance": concordance,
        "maximum_shift_in_primary_cr2_se": maximum_shift, "maximum_score_share": float(score_share.max()),
        "maximum_squared_residual_share": float(residual_share.max()), "checks": checks, "passes": all(checks.values()),
    }


def control_sensitivities(frame: pd.DataFrame, config: dict[str, Any], family: str = "quantity", target_feature: str = "d_log1p_precip_mm", test_mode: bool = False) -> dict[str, Any]:
    fits = {mode: fit_pooled(frame, config, family, mode, test_mode=test_mode) for mode in ("country_year", "global_year", "block10_year")}
    target = fits["country_year"].features.index(target_feature)
    primary = float(fits["country_year"].coefficient[target])
    primary_se = float(fits["country_year"].standard_error[target])
    estimates = {mode: float(fit.coefficient[target]) for mode, fit in fits.items()}
    shifts = {mode: abs(value - primary) / primary_se for mode, value in estimates.items() if mode != "country_year"}
    gates = config["postfit_influence_gates"]
    checks = {
        "sign_match": all(np.sign(value) == np.sign(primary) for value in estimates.values()),
        "maximum_shift": max(shifts.values()) <= float(gates["maximum_control_sensitivity_absolute_shift_in_primary_cr2_se"]),
    }
    return {"target_feature": target_feature, "estimates": estimates, "shifts_in_primary_cr2_se": shifts, "checks": checks, "passes": all(checks.values())}


def terminal_transport_score(
    training_frame: pd.DataFrame,
    terminal_frame: pd.DataFrame,
    config: dict[str, Any],
    candidate_family: str,
    reference_family: str | None,
    draws: int | None = None,
    seed: int | None = None,
    test_mode: bool = False,
) -> dict[str, Any]:
    require_terminal_year_contract(training_frame, terminal_frame, config, test_mode)
    candidate = fit_pooled(training_frame, config, candidate_family, "country_year", test_mode=test_mode)
    if reference_family is None:
        reference_features = [f"d_{column}" for column in config["controls"]["heat_columns"]]
        reference_prepared = prepare_pair_frame(training_frame, reference_features)
        reference_groups = group_codes(reference_prepared, "country_year")
        reference_y = residualize(reference_prepared["d_log_yield"].to_numpy(float), reference_groups)
        reference_x = residualize(reference_prepared[reference_features].to_numpy(float), reference_groups)
        reference_coefficient = np.linalg.solve(reference_x.T @ reference_x, reference_x.T @ reference_y)
    else:
        reference = fit_pooled(training_frame, config, reference_family, "country_year", test_mode=test_mode)
        reference_features = reference.features
        reference_coefficient = reference.coefficient
    terminal_features = list(dict.fromkeys(candidate.features + reference_features))
    candidate_terminal = prepare_pair_frame(terminal_frame, terminal_features)
    terminal_groups = group_codes(candidate_terminal, "country_year")
    y_terminal = residualize(candidate_terminal["d_log_yield"].to_numpy(float), terminal_groups)
    x_candidate = residualize(candidate_terminal[candidate.features].to_numpy(float), terminal_groups)
    with np.errstate(all="ignore"):
        candidate_error = y_terminal - x_candidate @ candidate.coefficient
    x_reference = residualize(candidate_terminal[reference_features].to_numpy(float), terminal_groups)
    with np.errstate(all="ignore"):
        reference_error = y_terminal - x_reference @ reference_coefficient
    require(np.isfinite(candidate_error).all() and np.isfinite(reference_error).all(), "nonfinite terminal transport error")
    point = float(np.sqrt(np.mean(candidate_error**2)) - np.sqrt(np.mean(reference_error**2)))
    blocks, block_codes = np.unique(candidate_terminal["block10"].astype(str).to_numpy(), return_inverse=True)
    count = np.bincount(block_codes).astype(float)
    candidate_sse = np.bincount(block_codes, weights=candidate_error**2)
    reference_sse = np.bincount(block_codes, weights=reference_error**2)
    configured_draws = int(config["later_period_validation"]["bootstrap_draws"])
    draws = configured_draws if draws is None else int(draws)
    require(draws == configured_draws or test_mode, "reduced terminal bootstrap draws are allowed only in synthetic/unit-test mode")
    require(draws > 0, "terminal bootstrap draws must be positive")
    seed = int(config["later_period_validation"]["bootstrap_seed"] if seed is None else seed)
    rng = np.random.default_rng(seed)
    bootstrap = np.empty(draws)
    for draw in range(draws):
        sampled = rng.integers(0, len(blocks), size=len(blocks))
        denominator = count[sampled].sum()
        require(np.isfinite(denominator) and denominator > 0, "zero or nonfinite terminal bootstrap denominator")
        bootstrap[draw] = np.sqrt(candidate_sse[sampled].sum() / denominator) - np.sqrt(reference_sse[sampled].sum() / denominator)
    low, high = np.quantile(bootstrap, [0.025, 0.975])
    year_results = {}
    for year in sorted(candidate_terminal["pair_end_year"].unique()):
        mask = candidate_terminal["pair_end_year"].eq(year).to_numpy()
        difference = float(np.sqrt(np.mean(candidate_error[mask] ** 2)) - np.sqrt(np.mean(reference_error[mask] ** 2)))
        year_results[str(int(year))] = difference
    improving = sum(value < 0 for value in year_results.values())
    rule = config["later_period_validation"]
    checks = {
        "minimum_terminal_pairs": len(candidate_terminal) >= int(rule["minimum_terminal_pairs"]),
        "minimum_terminal_blocks10": len(blocks) >= int(rule["minimum_terminal_blocks10"]),
        "point_below_zero": point < 0,
        "bootstrap_upper_below_zero": high < 0,
        "minimum_improving_years": improving >= int(rule["minimum_improving_terminal_years_of_five"]),
    }
    return {
        "candidate_family": candidate_family, "reference_family": reference_family or "heat_controls_only",
        "pairs": len(candidate_terminal), "blocks10": len(blocks), "point_rmse_difference": point,
        "cluster_bootstrap_interval": [float(low), float(high)], "bootstrap_draws": draws, "bootstrap_seed": seed,
        "year_rmse_differences": year_results, "improving_years": improving, "checks": checks, "passes": all(checks.values()),
    }
