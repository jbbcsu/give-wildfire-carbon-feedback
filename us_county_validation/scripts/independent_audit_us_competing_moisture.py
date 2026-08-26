#!/usr/bin/env python3
"""Independent audit of the U.S. competing-moisture predictive diagnostic.

This implementation deliberately does not import the registered builder,
evaluator, or validator.  It reconstructs common consecutive-year changes by
self-joining the raw level tables and fits each split with an unpivoted QR
least-squares solve.  Singular values are used only to audit the registered
rank cutoff; they are not used to solve the regression.

Only aggregate comparison diagnostics are written.  Regression coefficients
and row predictions remain in memory and are never serialized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


KEYS = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice"]
PAIR_KEYS = ["county_geoid", "outcome_crop", "harvest_year"]
GROUP_KEYS = ["county_geoid", "outcome_crop", "irrigation_practice"]
EXPECTED_RESULTS_SHA256 = "12d32bec7b9ff6a74339123f95b9282263fdc7675280d9a019c1710dcaaf0b66"
EXPECTED_VALIDATION_SHA256 = "778e2fbc2f1dd2351eb0ad91bd1565a7bb7582d68c42b88434ab0c67f697d28c"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} is not a JSON object")
    return value


def key_tuples(frame: pd.DataFrame) -> set[tuple[Any, ...]]:
    return set(frame[KEYS].itertuples(index=False, name=None))


def require_unique(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    if frame.empty:
        raise AssertionError(f"{label} is empty")
    if frame.duplicated(columns).any():
        raise AssertionError(f"{label} duplicates {columns}")


def require_finite(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    values = frame[columns].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise AssertionError(f"{label} contains missing or nonfinite analysis values")


def require_boolean(frame: pd.DataFrame, column: str, expected: bool, label: str) -> None:
    values = frame[column]
    if values.isna().any() or not values.map(lambda value: isinstance(value, (bool, np.bool_))).all():
        raise AssertionError(f"{label}.{column} is not strictly boolean")
    if not values.eq(expected).all():
        raise AssertionError(f"{label}.{column} differs from {expected}")


def compare_key_support(left: pd.DataFrame, right: pd.DataFrame, label: str) -> None:
    left_keys, right_keys = key_tuples(left), key_tuples(right)
    if left_keys != right_keys:
        raise AssertionError(
            f"{label} key support differs: left-only={len(left_keys-right_keys)}, "
            f"right-only={len(right_keys-left_keys)}"
        )


def compare_columns(
    rebuilt: pd.DataFrame,
    stored: pd.DataFrame,
    columns: list[str],
    label: str,
    tolerance: float = 2e-14,
) -> dict[str, float]:
    require_unique(rebuilt, KEYS, f"rebuilt {label}")
    require_unique(stored, KEYS, f"stored {label}")
    compare_key_support(rebuilt, stored, label)
    joined = rebuilt[KEYS + columns].merge(
        stored[KEYS + columns], on=KEYS, validate="one_to_one", suffixes=("_rebuilt", "_stored")
    )
    maximum_numeric_difference: dict[str, float] = {}
    for column in columns:
        left, right = joined[f"{column}_rebuilt"], joined[f"{column}_stored"]
        if pd.api.types.is_numeric_dtype(left) and not pd.api.types.is_bool_dtype(left):
            difference = np.abs(left.to_numpy(dtype=float) - right.to_numpy(dtype=float))
            maximum = float(np.max(difference)) if len(difference) else 0.0
            maximum_numeric_difference[column] = maximum
            if not np.isfinite(difference).all() or maximum > tolerance:
                raise AssertionError(f"{label}.{column} differs by {maximum:.17g}")
        else:
            if not left.astype("string").equals(right.astype("string")):
                mismatch = int((left.astype("string") != right.astype("string")).sum())
                raise AssertionError(f"{label}.{column} has {mismatch} mismatches")
    return maximum_numeric_difference


def reconstruct_from_raw(
    direct_path: Path,
    pdsi_path: Path,
    calendar_path: Path,
    protocol: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Rebuild level support and first differences without the project builder."""
    direct_raw = pd.read_parquet(direct_path)
    pdsi_raw = pd.read_parquet(pdsi_path)
    calendar_raw = pd.read_csv(calendar_path, dtype={"state": "string"})
    crops = set(map(str, protocol["sample"]["crops"]))
    practices = set(map(str, protocol["sample"]["irrigation_practices"]))
    role = str(protocol["sample"]["calendar_role"])
    year_min = int(protocol["sample"]["year_min"])
    year_max = int(protocol["sample"]["year_max"])

    def sample_mask(frame: pd.DataFrame) -> pd.Series:
        return (
            frame.outcome_crop.astype(str).isin(crops)
            & frame.irrigation_practice.astype(str).isin(practices)
            & frame.calendar_role.astype(str).eq(role)
            & frame.harvest_year.astype(int).between(year_min, year_max)
        )

    direct = direct_raw.loc[sample_mask(direct_raw)].copy()
    pdsi_long = pdsi_raw.loc[sample_mask(pdsi_raw)].copy()
    for frame in (direct, pdsi_long):
        frame["county_geoid"] = frame.county_geoid.astype(str).str.zfill(5)
        frame["outcome_crop"] = frame.outcome_crop.astype(str)
        frame["irrigation_practice"] = frame.irrigation_practice.astype(str)
        frame["state"] = frame.state.astype(str).str.upper()
        frame["harvest_year"] = frame.harvest_year.astype(int)

    require_unique(direct, KEYS, "raw direct-weather locked sample")
    require_unique(pdsi_long, KEYS + ["window_id"], "raw PDSI locked sample")
    expected_windows = {"preplant90", "season", "stage1", "stage2", "stage3"}
    observed_windows = set(pdsi_long.window_id.astype(str))
    if observed_windows != expected_windows:
        raise AssertionError(f"PDSI windows differ: {sorted(observed_windows)}")
    window_sets = pdsi_long.groupby(KEYS, observed=True).window_id.agg(
        lambda values: set(map(str, values))
    )
    if not window_sets.map(lambda value: value == expected_windows).all():
        raise AssertionError("a raw PDSI outcome key lacks exactly five locked windows")

    direct_features = [
        *map(str, protocol["features"]["common_temperature_controls"]),
        *map(str, protocol["features"]["direct_quantity"]),
        *map(str, protocol["features"]["direct_distribution_extension"]),
    ]
    pdsi_features = [
        *map(str, protocol["features"]["pdsi_primary"]),
        *map(str, protocol["features"]["pdsi_stage_sensitivity"]),
    ]
    require_finite(direct, ["yield_bu_acre", *direct_features], "raw direct weather")
    require_finite(pdsi_long, ["yield_bu_acre", "index_day_weighted_mean"], "raw PDSI")
    if (direct.yield_bu_acre <= 0).any() or (pdsi_long.yield_bu_acre <= 0).any():
        raise AssertionError("raw outcomes are not strictly positive")

    for flag, expected in [
        ("feature_construction_eligible", True),
        ("response_estimation_authorized", False),
        ("scc_authorized", False),
        ("weather_exposure_shared_across_practices", True),
        ("crop_pixel_exposure", False),
    ]:
        require_boolean(direct, flag, expected, "direct")
    for flag, expected in [
        ("feature_construction_eligible", True),
        ("response_estimation_authorized_pdsi", False),
        ("scc_authorized_pdsi", False),
        ("irrigation_in_index", False),
        ("monthly_value_day_weighted_not_daily_observation", True),
    ]:
        require_boolean(pdsi_long, flag, expected, "pdsi")

    pdsi_metadata_columns = [
        "state", "yield_bu_acre", "outcome_source_id", "calendar_source_id",
        "calendar_vintage", "boundary_rule", "stage_definition",
    ]
    metadata_nunique = pdsi_long.groupby(KEYS, observed=True)[pdsi_metadata_columns].nunique(
        dropna=False
    )
    if metadata_nunique.ne(1).any().any():
        raise AssertionError("PDSI metadata varies across windows for an outcome key")
    metadata = pdsi_long.groupby(KEYS, observed=True, sort=False)[pdsi_metadata_columns].first()
    season = pdsi_long.loc[
        pdsi_long.window_id.astype(str).eq("season"), KEYS + ["window_start", "window_end"]
    ].set_index(KEYS)
    wide = pdsi_long.pivot(index=KEYS, columns="window_id", values="index_day_weighted_mean")
    wide = wide.rename(columns={window: f"pdsi_{window}_mean" for window in expected_windows})
    pdsi = metadata.join(season).join(wide).reset_index().rename(
        columns={
            "boundary_rule": "calendar_boundary_rule",
            "window_start": "season_start",
            "window_end": "season_end",
        }
    )
    if set(pdsi_features) - set(pdsi.columns):
        raise AssertionError("independent PDSI pivot lacks registered predictors")
    require_unique(pdsi, KEYS, "independently pivoted PDSI")
    compare_key_support(direct, pdsi, "raw direct/PDSI common levels")

    lineage = [
        "state", "yield_bu_acre", "outcome_source_id", "calendar_source_id",
        "calendar_vintage", "calendar_boundary_rule", "stage_definition",
        "season_start", "season_end",
    ]
    levels = direct[KEYS + lineage + direct_features].merge(
        pdsi[KEYS + lineage + pdsi_features],
        on=KEYS,
        validate="one_to_one",
        suffixes=("", "_pdsi"),
    )
    for column in lineage:
        other = f"{column}_pdsi"
        if column in {"yield_bu_acre"}:
            difference = np.abs(
                levels[column].to_numpy(dtype=float) - levels[other].to_numpy(dtype=float)
            )
            if float(np.max(difference)) > 1e-10:
                raise AssertionError("raw direct/PDSI outcomes differ")
        elif column in {"season_start", "season_end"}:
            if not pd.to_datetime(levels[column]).eq(pd.to_datetime(levels[other])).all():
                raise AssertionError(f"raw direct/PDSI {column} differs")
        elif not levels[column].astype("string").eq(levels[other].astype("string")).all():
            raise AssertionError(f"raw direct/PDSI {column} differs")
        levels = levels.drop(columns=other)
    if len(levels) != len(direct) or len(levels) != len(pdsi):
        raise AssertionError("raw direct/PDSI common support is not exact")

    calendar = calendar_raw.loc[
        calendar_raw.calendar_crop.astype(str).isin(crops)
        & calendar_raw.calendar_role.astype(str).eq(role)
        & calendar_raw.harvest_year.astype(int).between(year_min, year_max)
    ].copy()
    calendar["state"] = calendar.state.astype(str).str.upper()
    calendar["calendar_crop"] = calendar.calendar_crop.astype(str)
    calendar["harvest_year"] = calendar.harvest_year.astype(int)
    calendar_keys = ["state", "calendar_crop", "harvest_year"]
    require_unique(calendar, calendar_keys, "bound calendar locked sample")
    bound = calendar.rename(
        columns={"calendar_crop": "outcome_crop", "boundary_rule": "calendar_boundary_rule"}
    )[[
        "state", "outcome_crop", "harvest_year", "season_start", "season_end",
        "calendar_source_id", "calendar_vintage", "calendar_boundary_rule", "stage_definition",
    ]]
    calendar_join = levels.merge(
        bound,
        on=["state", "outcome_crop", "harvest_year"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_bound"),
        indicator=True,
    )
    if not calendar_join._merge.eq("both").all():
        raise AssertionError("a common raw level lacks a bound calendar row")
    for column in [
        "season_start", "season_end", "calendar_source_id", "calendar_vintage",
        "calendar_boundary_rule", "stage_definition",
    ]:
        other = f"{column}_bound"
        if column in {"season_start", "season_end"}:
            equal = pd.to_datetime(calendar_join[column]).eq(pd.to_datetime(calendar_join[other]))
        else:
            equal = calendar_join[column].astype("string").eq(
                calendar_join[other].astype("string")
            )
        if not equal.all():
            raise AssertionError(f"raw common level {column} differs from bound calendar")

    all_features = direct_features + pdsi_features
    practice_sets = levels.groupby(PAIR_KEYS, observed=True).irrigation_practice.agg(set)
    if not practice_sets.map(lambda value: set(map(str, value)) == practices).all():
        raise AssertionError("raw common levels do not contain exact practice pairs")
    shared_columns = [
        "state", "outcome_source_id", "calendar_source_id", "calendar_vintage",
        "calendar_boundary_rule", "stage_definition", "season_start", "season_end",
        *all_features,
    ]
    shared_counts = levels.groupby(PAIR_KEYS, observed=True)[shared_columns].nunique(dropna=False)
    if shared_counts.ne(1).any().any():
        raise AssertionError("a raw weather/index exposure differs by irrigation practice")

    # Independent consecutive-year construction: align each current level with a
    # copy whose year has been advanced by one, rather than using groupwise shift.
    current_columns = KEYS + ["state", "yield_bu_acre", *all_features]
    current = levels[current_columns].copy()
    previous = current.copy()
    previous["harvest_year"] = previous.harvest_year.astype(int) + 1
    previous = previous.rename(
        columns={column: f"previous_{column}" for column in current.columns if column not in KEYS}
    )
    differences = current.merge(previous, on=KEYS, how="inner", validate="one_to_one")
    differences["difference_previous_harvest_year"] = differences.harvest_year.astype(int) - 1
    differences["delta_log_yield"] = np.log(differences.yield_bu_acre.to_numpy(dtype=float)) - np.log(
        differences.previous_yield_bu_acre.to_numpy(dtype=float)
    )
    for column in all_features:
        differences[f"d_{column}"] = (
            differences[column].to_numpy(dtype=float)
            - differences[f"previous_{column}"].to_numpy(dtype=float)
        )
    differences["level_precip_mm"] = differences.precip_mm.to_numpy(dtype=float)
    differences["geographic_group"] = differences.state.astype(str)
    differences["is_temporal_holdout"] = differences.harvest_year.ge(
        int(protocol["validation"]["terminal_temporal_holdout_start"])
    )
    differences["is_precipitation_extreme"] = False
    cutoff_receipt: dict[str, dict[str, float]] = {}
    lower_q = float(protocol["validation"]["extreme_lower_quantile"])
    upper_q = float(protocol["validation"]["extreme_upper_quantile"])
    for (crop, practice), positions in differences.groupby(
        ["outcome_crop", "irrigation_practice"], observed=True, sort=True
    ).groups.items():
        positions_array = np.asarray(list(positions), dtype=int)
        development_positions = positions_array[
            ~differences.loc[positions_array, "is_temporal_holdout"].to_numpy(dtype=bool)
        ]
        values = differences.loc[development_positions, "level_precip_mm"].to_numpy(dtype=float)
        lower, upper = map(float, np.quantile(values, [lower_q, upper_q], method="linear"))
        stratum_values = differences.loc[positions_array, "level_precip_mm"].to_numpy(dtype=float)
        differences.loc[positions_array, "is_precipitation_extreme"] = (
            (stratum_values <= lower) | (stratum_values >= upper)
        )
        cutoff_receipt[f"{crop}/{practice}"] = {"lower_mm": lower, "upper_mm": upper}
    differences = differences.sort_values(KEYS).reset_index(drop=True)
    if len(differences) != 20228:
        raise AssertionError(f"independent raw rebuild yielded {len(differences)} differences")
    return differences, {
        "direct_level_rows": int(len(direct)),
        "pdsi_level_rows": int(len(pdsi)),
        "common_level_rows": int(len(levels)),
        "common_consecutive_difference_rows": int(len(differences)),
        "calendar_rows": int(len(calendar)),
        "precipitation_extreme_cutoffs": cutoff_receipt,
        "exact_direct_pdsi_level_support": True,
        "exact_practice_pairs_and_shared_exposures": True,
        "all_common_levels_reconciled_to_bound_calendar": True,
    }


def endpoint_set(frame: pd.DataFrame, mask: np.ndarray) -> set[tuple[str, str, str, int]]:
    endpoints: set[tuple[str, str, str, int]] = set()
    for row in frame.loc[
        mask,
        ["county_geoid", "outcome_crop", "irrigation_practice", "harvest_year"],
    ].itertuples(index=False):
        prefix = (str(row.county_geoid), str(row.outcome_crop), str(row.irrigation_practice))
        endpoints.add((*prefix, int(row.harvest_year) - 1))
        endpoints.add((*prefix, int(row.harvest_year)))
    return endpoints


def purge_endpoints(
    frame: pd.DataFrame, train_before: np.ndarray, test: np.ndarray
) -> tuple[np.ndarray, int]:
    test_endpoints = endpoint_set(frame, test)
    keep = train_before.copy()
    for position in np.flatnonzero(train_before):
        row = frame.iloc[int(position)]
        prefix = (str(row.county_geoid), str(row.outcome_crop), str(row.irrigation_practice))
        if {
            (*prefix, int(row.harvest_year) - 1),
            (*prefix, int(row.harvest_year)),
        } & test_endpoints:
            keep[position] = False
    if endpoint_set(frame, keep) & test_endpoints:
        raise AssertionError("independent endpoint purge left overlap")
    return keep, int(train_before.sum() - keep.sum())


def qr_fit_metrics(
    frame: pd.DataFrame,
    features: list[str],
    train: np.ndarray,
    test: np.ndarray,
    relative_cutoff: float,
    relative_scale_floor: float,
    absolute_scale_floor: float,
) -> dict[str, Any]:
    year = frame.harvest_year.to_numpy(dtype=float)
    year_mean = float(np.mean(year[train]))
    year_scale = float(np.std(year[train], ddof=0))
    standardized_year = (year - year_mean) / year_scale
    raw = np.column_stack(
        [frame[features].to_numpy(dtype=float), standardized_year, standardized_year**2]
    )
    training_mean = np.mean(raw[train], axis=0)
    training_scale = np.std(raw[train], axis=0, ddof=0)
    training_magnitude = np.max(np.abs(raw[train]), axis=0)
    floor = np.maximum(absolute_scale_floor, relative_scale_floor * training_magnitude)
    retain = np.isfinite(training_scale) & (training_scale > floor)
    design = (raw[:, retain] - training_mean[retain]) / training_scale[retain]
    design = np.column_stack([np.ones(len(frame)), design])
    training_design = design[train]
    singular = np.linalg.svd(training_design, full_matrices=False, compute_uv=False)
    cutoff_rank = int(np.count_nonzero(singular > relative_cutoff * singular[0]))
    q_matrix, r_matrix = np.linalg.qr(training_design, mode="reduced")
    qr_rank = int(np.linalg.matrix_rank(r_matrix, tol=relative_cutoff * singular[0]))
    if cutoff_rank != training_design.shape[1] or qr_rank != cutoff_rank:
        raise AssertionError(
            "current diagnostic is not full rank under both SVD-cutoff and QR rank checks"
        )
    projected_outcome = np.einsum(
        "ij,i->j",
        q_matrix,
        frame.loc[train, "delta_log_yield"].to_numpy(dtype=float),
        optimize=False,
    )
    coefficients = np.linalg.solve(r_matrix, projected_outcome)
    prediction = np.einsum("ij,j->i", design[test], coefficients, optimize=False)
    y_test = frame.loc[test, "delta_log_yield"].to_numpy(dtype=float)
    y_train_mean = float(frame.loc[train, "delta_log_yield"].mean())
    error = y_test - prediction
    denominator = float(np.sum((y_test - y_train_mean) ** 2))
    correlation = None
    if len(y_test) > 1 and np.std(y_test) > 0 and np.std(prediction) > 0:
        correlation = float(np.corrcoef(y_test, prediction)[0, 1])
    return {
        "rmse": float(np.sqrt(np.mean(error**2))),
        "mae": float(np.mean(np.abs(error))),
        "r2_oos": None if denominator <= 0 else float(1 - np.sum(error**2) / denominator),
        "correlation": correlation,
        "train_rows": int(train.sum()),
        "test_rows": int(test.sum()),
        "design_columns_including_intercept": int(design.shape[1]),
        "design_rank": cutoff_rank,
        "qr_rank": qr_rank,
        "zero_variance_columns_dropped_train_only": int((~retain).sum()),
        "smallest_retained_to_largest_singular_value_ratio": float(
            singular[cutoff_rank - 1] / singular[0]
        ),
        "maximum_absolute_training_scaled_mean": float(
            np.max(np.abs(np.mean(design[train, 1:], axis=0)))
        ),
        "maximum_absolute_training_scaled_std_minus_one": float(
            np.max(np.abs(np.std(design[train, 1:], axis=0, ddof=0) - 1))
        ),
    }


def metric_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["crop"]), str(row["irrigation_practice"]), str(row["split"]),
        str(row["split_id"]), str(row["model"]),
    )


def independent_metrics(
    differences: pd.DataFrame, protocol: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    controls = [f"d_{name}" for name in map(str, protocol["features"]["common_temperature_controls"])]
    quantity = [f"d_{name}" for name in map(str, protocol["features"]["direct_quantity"])]
    distribution = [
        f"d_{name}" for name in map(str, protocol["features"]["direct_distribution_extension"])
    ]
    pdsi_primary = [f"d_{name}" for name in map(str, protocol["features"]["pdsi_primary"])]
    pdsi_stage = [
        f"d_{name}" for name in map(str, protocol["features"]["pdsi_stage_sensitivity"])
    ]
    specs = {
        "controls_only": controls,
        "direct_quantity": controls + quantity,
        "direct_quantity_distribution": controls + quantity + distribution,
        "pdsi_season_mean": controls + pdsi_primary,
        "pdsi_stage_sensitivity": controls + pdsi_stage,
    }
    direct_tokens, pdsi_tokens = set(quantity + distribution), set(pdsi_primary + pdsi_stage)
    for model, features in specs.items():
        if set(features) & direct_tokens and set(features) & pdsi_tokens:
            raise AssertionError(f"independent model {model} stacks moisture families")

    validation = protocol["validation"]
    minimum_test = int(validation["minimum_test_rows"])
    relative_cutoff = float(validation["svd_relative_tolerance"])
    relative_scale_floor = float(validation["minimum_relative_training_scale"])
    absolute_scale_floor = float(validation["minimum_absolute_training_scale"])
    rows: list[dict[str, Any]] = []
    split_receipt: dict[str, Any] = {}
    for (crop, practice), stratum in differences.groupby(
        ["outcome_crop", "irrigation_practice"], observed=True, sort=True
    ):
        stratum = stratum.reset_index(drop=True)
        temporal = stratum.is_temporal_holdout.to_numpy(dtype=bool)
        extreme = stratum.is_precipitation_extreme.to_numpy(dtype=bool)
        state_values = stratum.geographic_group.astype(str).to_numpy()
        development_counts = pd.Series(state_values[~temporal]).value_counts().sort_index()
        eligible = list(map(str, development_counts[development_counts >= minimum_test].index))
        splits: list[tuple[str, str, np.ndarray, np.ndarray]] = []
        for state in eligible:
            splits.append(
                ("development_leave_state_out", state, (~temporal) & (state_values != state),
                 (~temporal) & (state_values == state))
            )
        development_counties = set(stratum.loc[~temporal, "county_geoid"].astype(str))
        terminal_test = temporal & stratum.county_geoid.astype(str).isin(
            development_counties
        ).to_numpy(dtype=bool)
        splits.extend([
            ("terminal_temporal_same_counties", "terminal", ~temporal, terminal_test),
            ("development_precipitation_extreme", "tails", (~temporal) & (~extreme),
             (~temporal) & extreme),
        ])
        stratum_receipt: dict[str, Any] = {}
        for split, split_id, train_before, test in splits:
            if int(test.sum()) < minimum_test:
                raise AssertionError(f"independent split {crop}/{practice}/{split}/{split_id} too small")
            train, purged = purge_endpoints(stratum, train_before, test)
            receipt_key = f"{split}/{split_id}"
            stratum_receipt[receipt_key] = {
                "train_rows_before_endpoint_purge": int(train_before.sum()),
                "train_rows_purged_shared_level_endpoint": purged,
                "train_rows": int(train.sum()),
                "test_rows": int(test.sum()),
                "level_endpoints_disjoint": True,
            }
            for model, features in specs.items():
                metrics = qr_fit_metrics(
                    stratum, features, train, test, relative_cutoff,
                    relative_scale_floor, absolute_scale_floor,
                )
                rows.append({
                    "crop": str(crop),
                    "irrigation_practice": str(practice),
                    "split": split,
                    "split_id": split_id,
                    "model": model,
                    "feature_count_excluding_year_terms": len(features),
                    "train_rows_before_endpoint_purge": int(train_before.sum()),
                    "train_rows_purged_shared_level_endpoint": purged,
                    "first_difference_level_endpoints_disjoint": True,
                    **metrics,
                })
        split_receipt[f"{crop}/{practice}"] = {
            "eligible_leave_state_out_groups": eligible,
            "splits": stratum_receipt,
        }
    if len(rows) != 120 or len({metric_key(row) for row in rows}) != 120:
        raise AssertionError("independent split/model construction did not yield 120 unique metrics")
    return rows, {
        "method": "unpivoted_reduced_QR_then_triangular_solve; SVD_used_only_for_registered_rank_audit",
        "model_feature_columns": specs,
        "moisture_families_stacked": False,
        "splits": split_receipt,
    }


def compare_metrics(
    independent: list[dict[str, Any]], registered: list[dict[str, Any]], tolerance: float
) -> dict[str, Any]:
    independent_map = {metric_key(row): row for row in independent}
    registered_map = {metric_key(row): row for row in registered}
    if len(independent_map) != len(independent) or len(registered_map) != len(registered):
        raise AssertionError("duplicate aggregate metric identity")
    if independent_map.keys() != registered_map.keys():
        raise AssertionError("independent and registered aggregate metric identities differ")
    float_fields = [
        "rmse", "mae", "r2_oos", "correlation",
        "smallest_retained_to_largest_singular_value_ratio",
    ]
    exact_fields = [
        "train_rows", "test_rows", "design_columns_including_intercept", "design_rank",
        "zero_variance_columns_dropped_train_only", "feature_count_excluding_year_terms",
        "train_rows_before_endpoint_purge", "train_rows_purged_shared_level_endpoint",
        "first_difference_level_endpoints_disjoint",
    ]
    maxima = {field: 0.0 for field in float_fields}
    for key in sorted(independent_map):
        left, right = independent_map[key], registered_map[key]
        for field in exact_fields:
            if left[field] != right[field]:
                raise AssertionError(f"metric {key} differs at {field}: {left[field]} != {right[field]}")
        for field in float_fields:
            if left[field] is None or right[field] is None:
                if left[field] is not right[field]:
                    raise AssertionError(f"metric {key} null mismatch at {field}")
                difference = 0.0
            else:
                difference = abs(float(left[field]) - float(right[field]))
            maxima[field] = max(maxima[field], difference)
            if difference > tolerance:
                raise AssertionError(f"metric {key} differs at {field} by {difference:.17g}")
    return {
        "metric_rows_compared": len(independent_map),
        "maximum_absolute_discrepancy_by_field": maxima,
        "comparison_tolerance": tolerance,
        "all_exact_integer_boolean_fields_match": True,
    }


def promotion_summaries(
    independent: list[dict[str, Any]], protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    by_key = {metric_key(row): row for row in independent}
    absolute_floor = float(
        protocol["validation"]["distribution_minimum_absolute_rmse_improvement"]
    )
    relative_floor = float(
        protocol["validation"]["distribution_minimum_relative_rmse_improvement"]
    )
    summaries: list[dict[str, Any]] = []
    strata = sorted({(row["crop"], row["irrigation_practice"]) for row in independent})
    for crop, practice in strata:
        states = sorted({
            row["split_id"] for row in independent
            if row["crop"] == crop and row["irrigation_practice"] == practice
            and row["split"] == "development_leave_state_out"
        })
        improvements: dict[str, float] = {}
        floors: dict[str, float] = {}
        excess: dict[str, float] = {}
        pdsi_differences: dict[str, float] = {}
        for state in states:
            quantity = float(by_key[(crop, practice, "development_leave_state_out", state, "direct_quantity")]["rmse"])
            distribution = float(by_key[(crop, practice, "development_leave_state_out", state, "direct_quantity_distribution")]["rmse"])
            pdsi = float(by_key[(crop, practice, "development_leave_state_out", state, "pdsi_season_mean")]["rmse"])
            improvement = quantity - distribution
            required = max(absolute_floor, relative_floor * quantity)
            improvements[state] = improvement
            floors[state] = required
            excess[state] = improvement - required
            pdsi_differences[state] = quantity - pdsi

        def paired(split: str, split_id: str, second: str) -> float:
            quantity = float(by_key[(crop, practice, split, split_id, "direct_quantity")]["rmse"])
            alternative = float(by_key[(crop, practice, split, split_id, second)]["rmse"])
            return quantity - alternative

        summaries.append({
            "crop": crop,
            "irrigation_practice": practice,
            "direct_distribution_selected_on_development_leave_state_out": bool(
                excess and all(value >= 0 for value in excess.values())
            ),
            "direct_distribution_rmse_improvement_each_eligible_state": improvements,
            "direct_distribution_required_material_rmse_floor_each_eligible_state": floors,
            "direct_distribution_rmse_excess_over_material_floor_each_eligible_state": excess,
            "direct_distribution_minimum_absolute_rmse_improvement": absolute_floor,
            "direct_distribution_minimum_relative_rmse_improvement": relative_floor,
            "direct_distribution_mean_leave_state_out_rmse_improvement": float(
                np.mean(list(improvements.values()))
            ),
            "direct_distribution_terminal_rmse_improvement_not_used_for_selection": paired(
                "terminal_temporal_same_counties", "terminal", "direct_quantity_distribution"
            ),
            "direct_distribution_extreme_rmse_improvement_not_used_for_selection": paired(
                "development_precipitation_extreme", "tails", "direct_quantity_distribution"
            ),
            "direct_quantity_minus_pdsi_season_rmse_by_eligible_state": pdsi_differences,
            "direct_quantity_minus_pdsi_season_terminal_rmse": paired(
                "terminal_temporal_same_counties", "terminal", "pdsi_season_mean"
            ),
            "rmse_difference_sign": "positive means the second named model has lower RMSE",
        })
    return summaries


def compare_nested(left: Any, right: Any, tolerance: float, path: str = "") -> float:
    maximum = 0.0
    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            raise AssertionError(f"nested keys differ at {path}")
        for key in left:
            maximum = max(maximum, compare_nested(left[key], right[key], tolerance, f"{path}.{key}"))
        return maximum
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise AssertionError(f"nested list length differs at {path}")
        for index, (left_child, right_child) in enumerate(zip(left, right, strict=True)):
            maximum = max(
                maximum,
                compare_nested(left_child, right_child, tolerance, f"{path}[{index}]")
            )
        return maximum
    if isinstance(left, (float, int)) and not isinstance(left, bool) and isinstance(
        right, (float, int)
    ) and not isinstance(right, bool):
        difference = abs(float(left) - float(right))
        if difference > tolerance:
            raise AssertionError(f"nested numeric value differs at {path} by {difference:.17g}")
        return difference
    if left != right:
        raise AssertionError(f"nested value differs at {path}: {left!r} != {right!r}")
    return maximum


def forbidden_output_keys(value: Any, prefix: str = "") -> list[str]:
    forbidden: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if "coefficient" in lowered and key != "coefficients_in_output":
                forbidden.append(path)
            if "prediction" in lowered and key != "row_predictions_in_output":
                forbidden.append(path)
            forbidden.extend(forbidden_output_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            forbidden.extend(forbidden_output_keys(child, f"{prefix}[{index}]"))
    return forbidden


def audit_hashes(
    paths: dict[str, Path], results: dict[str, Any], validation: dict[str, Any]
) -> dict[str, Any]:
    actual = {name: file_sha256(path) for name, path in paths.items()}
    if actual["results"] != EXPECTED_RESULTS_SHA256:
        raise AssertionError("results.json SHA-256 differs from registered audit target")
    if actual["validation"] != EXPECTED_VALIDATION_SHA256:
        raise AssertionError("validation.json SHA-256 differs from registered audit target")
    expected_internal = {
        "protocol": results["protocol_sha256"],
        "input_audit": results["input_audit_sha256"],
        "common": results["input_table_sha256"]["common"],
        "direct_input": results["input_table_sha256"]["direct_weather"],
        "pdsi_input": results["input_table_sha256"]["pdsi"],
        "direct_raw": results["raw_source_sha256"]["direct_weather"],
        "pdsi_raw": results["raw_source_sha256"]["pdsi_join"],
        "calendar_raw": results["raw_source_sha256"]["calendar"],
        "direct_receipt": results["source_validation_receipt_sha256"]["direct_weather"],
        "pdsi_receipt": results["source_validation_receipt_sha256"]["pdsi"],
        "calendar_receipt": results["source_validation_receipt_sha256"]["calendar"],
    }
    for name, expected in expected_internal.items():
        if actual[name] != expected:
            raise AssertionError(f"results internal hash for {name} does not match the selected file")
    if validation["candidate"]["sha256"] != actual["results"]:
        raise AssertionError("validation candidate hash differs from results.json")
    if validation["input_audit"]["sha256"] != actual["input_audit"]:
        raise AssertionError("validation input-audit hash differs")
    for name, receipt_name in [
        ("direct_weather", "direct_receipt"), ("pdsi", "pdsi_receipt"),
        ("calendar", "calendar_receipt"),
    ]:
        if validation["source_validation_receipts"][name]["sha256"] != actual[receipt_name]:
            raise AssertionError(f"validation source receipt hash differs for {name}")
    for name, raw_name in [
        ("direct_weather", "direct_raw"), ("pdsi_join", "pdsi_raw"),
        ("calendar", "calendar_raw"),
    ]:
        if validation["raw_sources"][name]["sha256"] != actual[raw_name]:
            raise AssertionError(f"validation raw source hash differs for {name}")

    input_audit = load_json(paths["input_audit"])
    for name, actual_name in [
        ("common", "common"), ("direct_weather", "direct_input"), ("pdsi", "pdsi_input")
    ]:
        if input_audit["outputs"][name]["sha256"] != actual[actual_name]:
            raise AssertionError(f"input audit output hash differs for {name}")
    receipt_bindings = [
        ("direct_receipt", "direct_raw", "direct_weather"),
        ("pdsi_receipt", "pdsi_raw", "pdsi"),
        ("calendar_receipt", "calendar_raw", "calendar"),
    ]
    for receipt_name, source_name, family in receipt_bindings:
        receipt = load_json(paths[receipt_name])
        if receipt.get("status") != "validated_us_competing_moisture_source_input":
            raise AssertionError(f"{family} receipt status differs")
        if receipt.get("family") != family:
            raise AssertionError(f"{family} receipt family differs")
        if receipt["candidate"]["sha256"] != actual[source_name]:
            raise AssertionError(f"{family} receipt raw hash differs")
        if receipt["protocol"]["sha256"] != actual["protocol"]:
            raise AssertionError(f"{family} receipt protocol hash differs")
    return {
        "all_selected_files_match_internal_hash_bindings": True,
        "sha256": actual,
    }


def run_audit(root: Path, metric_tolerance: float) -> dict[str, Any]:
    paths = {
        "audit_script": Path(__file__).resolve(),
        "audit_test": root / "us_county_validation/scripts/test_independent_audit_us_competing_moisture.py",
        "registered_builder": root / "us_county_validation/scripts/build_us_competing_moisture_inputs.py",
        "registered_evaluator": root / "us_county_validation/scripts/evaluate_us_competing_moisture.py",
        "registered_validator": root / "us_county_validation/scripts/validate_us_competing_moisture.py",
        "protocol": root / "us_county_validation/us_competing_moisture_predictive_v1.toml",
        "direct_raw": root / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet",
        "pdsi_raw": root / "data/interim/us_county/nass_direct_practice_pdsi_join_1981_2019.parquet",
        "calendar_raw": root / "data/interim/us_county/nass_usual_date_calendars_1981_2022.csv",
        "common": root / "data/interim/us_county/competing_moisture_predictive_v1/common_outcomes_controls_folds.parquet",
        "direct_input": root / "data/interim/us_county/competing_moisture_predictive_v1/direct_weather.parquet",
        "pdsi_input": root / "data/interim/us_county/competing_moisture_predictive_v1/pdsi.parquet",
        "input_audit": root / "outputs/us_county/competing_moisture_predictive_v1/input_audit.json",
        "direct_receipt": root / "outputs/us_county/competing_moisture_predictive_v1/direct_source_validation.json",
        "pdsi_receipt": root / "outputs/us_county/competing_moisture_predictive_v1/pdsi_source_validation.json",
        "calendar_receipt": root / "outputs/us_county/competing_moisture_predictive_v1/calendar_source_validation.json",
        "results": root / "outputs/us_county/competing_moisture_predictive_v1/results.json",
        "validation": root / "outputs/us_county/competing_moisture_predictive_v1/validation.json",
    }
    protocol = tomllib.loads(paths["protocol"].read_text(encoding="utf-8"))
    results, validation = load_json(paths["results"]), load_json(paths["validation"])
    hash_audit = audit_hashes(paths, results, validation)
    differences, raw_rebuild = reconstruct_from_raw(
        paths["direct_raw"], paths["pdsi_raw"], paths["calendar_raw"], protocol
    )

    stored_common = pd.read_parquet(paths["common"])
    stored_direct = pd.read_parquet(paths["direct_input"])
    stored_pdsi = pd.read_parquet(paths["pdsi_input"])
    common_columns = [
        "state", "difference_previous_harvest_year", "delta_log_yield", "geographic_group",
        "is_temporal_holdout", "is_precipitation_extreme", "d_stage1_tmean_c",
        "d_stage2_tmean_c", "d_stage3_tmean_c",
    ]
    direct_columns = [column for column in stored_direct if column.startswith("d_")]
    pdsi_columns = [column for column in stored_pdsi if column.startswith("d_")]
    stored_comparison = {
        "common": compare_columns(differences, stored_common, common_columns, "common"),
        "direct_weather": compare_columns(
            differences, stored_direct, direct_columns, "direct_weather"
        ),
        "pdsi": compare_columns(differences, stored_pdsi, pdsi_columns, "pdsi"),
    }
    if raw_rebuild["precipitation_extreme_cutoffs"] != load_json(paths["input_audit"])[
        "precipitation_extreme_cutoffs_from_development_inputs_without_outcomes"
    ]:
        raise AssertionError("independent extreme cutoffs differ from input audit")

    independent, design_receipt = independent_metrics(differences, protocol)
    metric_comparison = compare_metrics(
        independent, list(results["metrics"]), metric_tolerance
    )
    independent_summaries = promotion_summaries(independent, protocol)
    maximum_summary_difference = compare_nested(
        independent_summaries, results["comparison_summaries"], metric_tolerance,
        "comparison_summaries",
    )

    if forbidden := forbidden_output_keys(results):
        raise AssertionError(f"registered result contains coefficient/prediction fields: {forbidden}")
    required_false = [
        "coefficients_in_output", "row_predictions_in_output", "causal_effect_estimated",
        "damage_calculated", "scc_calculated", "terminal_temporal_holdout_used_for_selection",
    ]
    for key in required_false:
        if results.get(key) is not False:
            raise AssertionError(f"registered result {key} is not false")
    if results.get("required_disclaimer") != protocol["output"]["required_disclaimer"]:
        raise AssertionError("registered noncausal disclaimer differs from protocol")
    if results.get("status") != "aggregate_noncausal_predictive_diagnostic_complete":
        raise AssertionError("registered result status is not the bounded predictive status")
    if validation.get("status") != "validated_exact_recomputation_aggregate_predictive_diagnostic":
        raise AssertionError("registered validation status differs")
    if validation.get("metric_rows_recomputed") != 120:
        raise AssertionError("registered validation metric count differs")

    promotion_outcomes = {
        f"{row['crop']}/{row['irrigation_practice']}": row[
            "direct_distribution_selected_on_development_leave_state_out"
        ]
        for row in independent_summaries
    }
    all_ratios = [row["smallest_retained_to_largest_singular_value_ratio"] for row in independent]
    all_scaled_means = [row["maximum_absolute_training_scaled_mean"] for row in independent]
    all_scaled_std_errors = [
        row["maximum_absolute_training_scaled_std_minus_one"] for row in independent
    ]
    return {
        "status": "CLEAR_independent_noncausal_predictive_audit",
        "analysis_role": "independent_audit_of_noncausal_predictive_diagnostic_only",
        "independent_of_registered_builder_evaluator_validator": True,
        "raw_rebuild": raw_rebuild,
        "stored_input_comparison": {
            "exact_key_support_all_three_tables": True,
            "maximum_absolute_value_discrepancy_by_table_and_column": stored_comparison,
        },
        "aggregate_metric_comparison": metric_comparison,
        "promotion_gate_comparison": {
            "all_registered_summary_fields_match": True,
            "maximum_absolute_discrepancy": maximum_summary_difference,
            "outcomes": promotion_outcomes,
            "terminal_and_extreme_not_used_for_selection": True,
        },
        "split_and_preprocessing_audit": {
            **design_receipt,
            "all_candidate_columns_retained": all(
                row["zero_variance_columns_dropped_train_only"] == 0 for row in independent
            ),
            "all_designs_full_rank_under_registered_cutoff": all(
                row["design_rank"] == row["design_columns_including_intercept"]
                for row in independent
            ),
            "minimum_smallest_retained_to_largest_singular_ratio": float(min(all_ratios)),
            "registered_relative_rank_cutoff": float(
                protocol["validation"]["svd_relative_tolerance"]
            ),
            "maximum_absolute_training_scaled_mean": float(max(all_scaled_means)),
            "maximum_absolute_training_scaled_std_minus_one": float(max(all_scaled_std_errors)),
            "scaling_statistics_computed_from_training_rows_only": True,
        },
        "artifact_content_audit": {
            "aggregate_metric_rows": 120,
            "coefficient_fields_present": False,
            "row_prediction_fields_present": False,
            "causal_effect_estimated": False,
            "damage_calculated": False,
            "scc_calculated": False,
            "required_disclaimer_matches_protocol": True,
        },
        "hash_audit": hash_audit,
        "discrepancies": [],
        "required_disclaimer": protocol["output"]["required_disclaimer"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--metric-tolerance", type=float, default=2e-12)
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()
    with np.errstate(all="raise"):
        receipt = run_audit(arguments.root.resolve(), arguments.metric_tolerance)
    serialized = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if arguments.out:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
