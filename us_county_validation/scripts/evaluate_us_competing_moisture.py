#!/usr/bin/env python3
"""Evaluate mutually exclusive U.S. moisture predictors out of sample.

Only aggregate predictive metrics are returned.  Coefficients and row-level
predictions are intentionally discarded.
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from build_us_competing_moisture_inputs import (
    KEYS,
    DEFAULT_PROTOCOL,
    EXPECTED_MODEL_BLOCKS,
    load_protocol,
    sha256,
    strict_bool,
    validate_source_receipt,
)


FILES = {
    "common": "common_outcomes_controls_folds.parquet",
    "direct_weather": "direct_weather.parquet",
    "pdsi": "pdsi.parquet",
}


def _key_index(frame: pd.DataFrame) -> pd.MultiIndex:
    return pd.MultiIndex.from_frame(frame[KEYS], names=KEYS)


def load_validated_inputs(
    input_dir: Path,
    audit_path: Path,
    protocol: dict[str, Any],
    protocol_path: Path,
    direct_weather_path: Path,
    direct_validation_path: Path,
    pdsi_join_path: Path,
    pdsi_validation_path: Path,
    calendar_path: Path,
    calendar_validation_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "common_first_difference_inputs_constructed_not_fitted":
        raise ValueError("input audit has the wrong status")
    if audit.get("protocol_id") != protocol.get("protocol_id"):
        raise ValueError("input audit and protocol identities differ")
    required_audit_gates = {
        "moisture_families_stacked_in_any_model": False,
        "predictive_fit_executed": False,
        "causal_effect_estimated": False,
        "damage_calculated": False,
        "scc_calculated": False,
        "upstream_daily_weather_recomputed_in_this_step": False,
        "all_direct_and_pdsi_level_rows_reconciled_to_bound_calendar": True,
    }
    for gate, expected_value in required_audit_gates.items():
        if audit.get(gate) is not expected_value:
            raise ValueError(f"input audit has an invalid semantic gate {gate}")
    if audit.get("inputs", {}).get("protocol", {}).get("sha256") != sha256(protocol_path):
        raise ValueError("input audit protocol hash differs from the selected protocol")
    source_bindings = {
        "direct_weather": direct_weather_path,
        "direct_validation": direct_validation_path,
        "pdsi_join": pdsi_join_path,
        "pdsi_validation": pdsi_validation_path,
        "calendar": calendar_path,
        "calendar_validation": calendar_validation_path,
    }
    for name, path in source_bindings.items():
        if audit.get("inputs", {}).get(name, {}).get("sha256") != sha256(path):
            raise ValueError(f"input audit {name} hash differs from the selected source")
    validate_source_receipt(
        direct_validation_path, direct_weather_path, "direct_weather", protocol_path
    )
    validate_source_receipt(pdsi_validation_path, pdsi_join_path, "pdsi", protocol_path)
    validate_source_receipt(
        calendar_validation_path, calendar_path, "calendar", protocol_path
    )
    frames: dict[str, pd.DataFrame] = {}
    for name, filename in FILES.items():
        path = input_dir / filename
        expected = audit.get("outputs", {}).get(name, {})
        if expected.get("sha256") != sha256(path):
            raise ValueError(f"{name} input hash differs from its audit")
        frame = pd.read_parquet(path).sort_values(KEYS).reset_index(drop=True)
        if frame.empty or frame.duplicated(KEYS).any():
            raise ValueError(f"{name} input is empty or duplicates keys")
        frames[name] = frame
    expected_keys = _key_index(frames["common"])
    for name in ["direct_weather", "pdsi"]:
        if not _key_index(frames[name]).equals(expected_keys):
            raise ValueError(f"{name} keys differ from common outcome support")
    common, direct, pdsi = frames["common"], frames["direct_weather"], frames["pdsi"]
    if set(direct.feature_family.astype(str)) != {"direct_weather"}:
        raise ValueError("direct family identity changed")
    if set(pdsi.feature_family.astype(str)) != {"pdsi"}:
        raise ValueError("PDSI family identity changed")
    for label, frame in frames.items():
        for flag in [
            "predictive_diagnostic_authorized", "causal_claim_authorized",
            "damage_claim_authorized", "scc_claim_authorized",
        ]:
            values = strict_bool(frame[flag], f"{label} {flag}")
            expected_value = flag == "predictive_diagnostic_authorized"
            if not values.eq(expected_value).all():
                raise ValueError(f"{label} has an invalid {flag} gate")
    if any("pdsi" in column.lower() for column in direct.columns):
        raise ValueError("direct family contains a PDSI column")
    direct_terms = [column for column in direct.columns if column.startswith("d_")]
    if any(any(token in column.lower() for token in ["precip", "rain", "wet", "cdd", "rx"])
           for column in pdsi.columns):
        raise ValueError("PDSI family contains a direct-rainfall column")
    if not direct_terms or not any(column.startswith("d_pdsi_") for column in pdsi.columns):
        raise ValueError("one moisture family lacks predictors")
    if set(common.outcome_crop.astype(str)) != set(map(str, protocol["sample"]["crops"])):
        raise ValueError("common input crop support differs from protocol")
    if set(common.irrigation_practice.astype(str)) != set(
        map(str, protocol["sample"]["irrigation_practices"])
    ):
        raise ValueError("common input practice support differs from protocol")
    if "geographic_group" not in common:
        raise ValueError("common input lacks geographic_group")
    if "difference_previous_harvest_year" not in common:
        raise ValueError("common input lacks first-difference endpoint identity")
    previous = pd.to_numeric(
        common.difference_previous_harvest_year, errors="raise"
    ).astype("int64")
    if not common.harvest_year.sub(previous).eq(1).all():
        raise ValueError("common input contains nonconsecutive first-difference endpoints")
    common["difference_previous_harvest_year"] = previous
    if not common.geographic_group.astype("string").eq(common.state.astype("string")).all():
        raise ValueError("geographic_group must equal the locked state holdout unit")
    if common.groupby("county_geoid", observed=True).state.nunique().gt(1).any():
        raise ValueError("a county changes state/geographic group")
    holdout = strict_bool(common.is_temporal_holdout, "temporal holdout")
    if not holdout.any() or holdout.all():
        raise ValueError("terminal temporal holdout is empty or exhaustive")
    if int(common.loc[~holdout, "harvest_year"].max()) >= int(common.loc[holdout, "harvest_year"].min()):
        raise ValueError("temporal holdout is not terminal")
    common["is_temporal_holdout"] = holdout
    common["is_precipitation_extreme"] = strict_bool(
        common.is_precipitation_extreme, "precipitation extreme"
    )
    return common, direct, pdsi, audit


def model_specs(protocol: dict[str, Any]) -> dict[str, list[str]]:
    configured_models = {
        str(model): list(map(str, configured_blocks))
        for model, configured_blocks in protocol["models"].items()
    }
    if configured_models != EXPECTED_MODEL_BLOCKS:
        raise ValueError("[models] differs from the exact locked model schema")
    features = protocol["features"]
    controls = [f"d_{name}" for name in map(str, features["common_temperature_controls"])]
    quantity = [f"d_{name}" for name in map(str, features["direct_quantity"])]
    distribution = [f"d_{name}" for name in map(str, features["direct_distribution_extension"])]
    pdsi_primary = [f"d_{name}" for name in map(str, features["pdsi_primary"])]
    pdsi_stage = [f"d_{name}" for name in map(str, features["pdsi_stage_sensitivity"])]
    blocks = {
        "direct_quantity": quantity,
        "direct_distribution_extension": distribution,
        "pdsi_primary": pdsi_primary,
        "pdsi_stage_sensitivity": pdsi_stage,
    }
    specs = {
        str(model): controls + [
            column
            for block in map(str, configured_blocks)
            for column in blocks[block]
        ]
        for model, configured_blocks in configured_models.items()
    }
    direct_tokens = set(quantity + distribution)
    pdsi_tokens = set(pdsi_primary + pdsi_stage)
    for name, columns in specs.items():
        if set(columns) & direct_tokens and set(columns) & pdsi_tokens:
            raise ValueError(f"model {name} stacks direct precipitation and PDSI")
    return specs


def regression_metrics(y: np.ndarray, prediction: np.ndarray, training_mean: float) -> dict[str, Any]:
    error = y - prediction
    rmse = float(np.sqrt(np.mean(np.square(error))))
    mae = float(np.mean(np.abs(error)))
    denominator = float(np.sum(np.square(y - training_mean)))
    r2 = None if denominator <= 0 else float(1 - np.sum(np.square(error)) / denominator)
    correlation = None
    if len(y) > 1 and np.std(y) > 0 and np.std(prediction) > 0:
        correlation = float(np.corrcoef(y, prediction)[0, 1])
    return {"rmse": rmse, "mae": mae, "r2_oos": r2, "correlation": correlation}


def fit_predictive_ols(
    frame: pd.DataFrame, columns: list[str], train: np.ndarray, test: np.ndarray,
    svd_relative_tolerance: float, minimum_relative_scale: float,
    minimum_absolute_scale: float,
) -> dict[str, Any]:
    if train.dtype != bool or test.dtype != bool or train.shape != test.shape:
        raise ValueError("train/test masks must be aligned boolean arrays")
    if np.any(train & test) or not train.any() or not test.any():
        raise ValueError("train/test rows overlap or one side is empty")
    year = frame.harvest_year.to_numpy(dtype=float)
    year_scale = float(year[train].std(ddof=0))
    if not np.isfinite(year_scale) or year_scale <= 0:
        raise ValueError("training years do not vary")
    year_standardized = (year - float(year[train].mean())) / year_scale
    raw = frame[columns].to_numpy(dtype=float)
    raw = np.column_stack([raw, year_standardized, np.square(year_standardized)])
    if not np.isfinite(raw).all():
        raise ValueError("predictor matrix contains missing/nonfinite values")
    mean = raw[train].mean(axis=0)
    scale = raw[train].std(axis=0, ddof=0)
    if minimum_relative_scale <= 0 or minimum_absolute_scale <= 0:
        raise ValueError("training-scale floors must be positive")
    magnitude = np.max(np.abs(raw[train]), axis=0)
    scale_floor = np.maximum(minimum_absolute_scale, minimum_relative_scale * magnitude)
    retain = np.isfinite(scale) & (scale > scale_floor)
    if not retain.any():
        raise ValueError("all candidate predictors are constant in training")
    design = (raw[:, retain] - mean[retain]) / scale[retain]
    design = np.column_stack([np.ones(len(frame)), design])
    y = frame.delta_log_yield.to_numpy(dtype=float)
    if not np.isfinite(y).all():
        raise ValueError("outcome contains missing/nonfinite values")
    if not 0 < svd_relative_tolerance < 1:
        raise ValueError("SVD relative tolerance must lie strictly between zero and one")
    training_design = design[train]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            coefficients, _, rank, singular = np.linalg.lstsq(
                training_design,
                y[train],
                rcond=svd_relative_tolerance,
            )
    except (np.linalg.LinAlgError, RuntimeWarning, FloatingPointError) as error:
        raise ValueError("numerically invalid least-squares fit") from error
    rank = int(rank)
    if (
        rank <= 0
        or singular.ndim != 1
        or not np.isfinite(singular).all()
        or len(singular) == 0
        or singular[0] <= 0
    ):
        raise ValueError("least-squares solver returned an invalid training rank")
    if not np.isfinite(coefficients).all():
        raise ValueError("OLS fit produced nonfinite coefficients")
    prediction = np.einsum("ij,j->i", design[test], coefficients, optimize=False)
    if not np.isfinite(prediction).all():
        raise ValueError("OLS fit produced nonfinite coefficients or predictions")
    metrics = regression_metrics(y[test], prediction, float(y[train].mean()))
    metrics.update({
        "train_rows": int(train.sum()),
        "test_rows": int(test.sum()),
        "design_columns_including_intercept": int(design.shape[1]),
        "design_rank": int(rank),
        "zero_variance_columns_dropped_train_only": int((~retain).sum()),
        "svd_relative_tolerance": float(svd_relative_tolerance),
        "minimum_relative_training_scale": float(minimum_relative_scale),
        "minimum_absolute_training_scale": float(minimum_absolute_scale),
        "linear_solver": "numpy_lstsq_with_registered_relative_svd_cutoff",
        "smallest_retained_to_largest_singular_value_ratio": float(
            singular[rank - 1] / singular[0]
        ),
    })
    return metrics


def paired_rmse_difference(
    rows: list[dict[str, Any]], crop: str, practice: str, split: str, split_id: str,
    left: str, right: str,
) -> float:
    selected = {
        row["model"]: float(row["rmse"])
        for row in rows
        if row["crop"] == crop and row["irrigation_practice"] == practice
        and row["split"] == split and row["split_id"] == split_id
        and row["model"] in {left, right}
    }
    if set(selected) != {left, right}:
        raise ValueError("paired metric lookup did not find exactly two models")
    return selected[left] - selected[right]


def _level_endpoint_keys(frame: pd.DataFrame, mask: np.ndarray) -> set[tuple[str, str, str, int]]:
    selected = frame.loc[
        mask,
        [
            "county_geoid", "outcome_crop", "irrigation_practice",
            "difference_previous_harvest_year", "harvest_year",
        ],
    ]
    endpoints: set[tuple[str, str, str, int]] = set()
    for row in selected.itertuples(index=False):
        prefix = (str(row.county_geoid), str(row.outcome_crop), str(row.irrigation_practice))
        endpoints.add((*prefix, int(row.difference_previous_harvest_year)))
        endpoints.add((*prefix, int(row.harvest_year)))
    return endpoints


def purge_shared_first_difference_endpoints(
    frame: pd.DataFrame, train: np.ndarray, test: np.ndarray
) -> tuple[np.ndarray, int]:
    """Remove training differences sharing either level endpoint with any test row."""
    if train.dtype != bool or test.dtype != bool or train.shape != test.shape:
        raise ValueError("endpoint-purge masks must be aligned boolean arrays")
    if np.any(train & test):
        raise ValueError("endpoint-purge train and test rows overlap")
    test_endpoints = _level_endpoint_keys(frame, test)
    keep = train.copy()
    for position in np.flatnonzero(train):
        row = frame.iloc[int(position)]
        prefix = (str(row.county_geoid), str(row.outcome_crop), str(row.irrigation_practice))
        endpoints = {
            (*prefix, int(row.difference_previous_harvest_year)),
            (*prefix, int(row.harvest_year)),
        }
        if endpoints & test_endpoints:
            keep[position] = False
    remaining_overlap = _level_endpoint_keys(frame, keep) & test_endpoints
    if remaining_overlap:
        raise ValueError("first-difference endpoint purge left train/test endpoint overlap")
    return keep, int(train.sum() - keep.sum())


def distribution_promotion_details(
    rows: list[dict[str, Any]],
    crop: str,
    practice: str,
    geographic_groups: list[str],
    minimum_absolute_improvement: float,
    minimum_relative_improvement: float,
) -> dict[str, Any]:
    improvements: dict[str, float] = {}
    floors: dict[str, float] = {}
    excess: dict[str, float] = {}
    for group in geographic_groups:
        selected = {
            row["model"]: float(row["rmse"])
            for row in rows
            if row["crop"] == crop
            and row["irrigation_practice"] == practice
            and row["split"] == "development_leave_state_out"
            and row["split_id"] == group
            and row["model"] in {"direct_quantity", "direct_quantity_distribution"}
        }
        if set(selected) != {"direct_quantity", "direct_quantity_distribution"}:
            raise ValueError("distribution promotion lookup lacks paired development metrics")
        improvement = selected["direct_quantity"] - selected["direct_quantity_distribution"]
        floor = max(
            minimum_absolute_improvement,
            minimum_relative_improvement * selected["direct_quantity"],
        )
        improvements[group] = float(improvement)
        floors[group] = float(floor)
        excess[group] = float(improvement - floor)
    return {
        "selected": bool(excess and all(value >= 0 for value in excess.values())),
        "improvements": improvements,
        "required_floors": floors,
        "excess_over_floor": excess,
    }


def evaluate_frames(
    common: pd.DataFrame,
    direct: pd.DataFrame,
    pdsi: pd.DataFrame,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    specs = model_specs(protocol)
    combined = common.merge(
        direct[KEYS + [column for column in direct if column.startswith("d_")]],
        on=KEYS, how="left", validate="one_to_one",
    ).merge(
        pdsi[KEYS + [column for column in pdsi if column.startswith("d_")]],
        on=KEYS, how="left", validate="one_to_one",
    )
    required = sorted(set(column for columns in specs.values() for column in columns))
    if missing := set(required) - set(combined.columns):
        raise ValueError(f"combined diagnostic input lacks {sorted(missing)}")
    if combined[required + ["delta_log_yield"]].isna().any().any():
        raise ValueError("combined common support contains missing analysis values")
    minimum_test = int(protocol["validation"]["minimum_test_rows"])
    minimum_geographic_groups = int(
        protocol["validation"]["minimum_geographic_groups_per_crop_practice"]
    )
    svd_relative_tolerance = float(protocol["validation"]["svd_relative_tolerance"])
    minimum_relative_scale = float(protocol["validation"]["minimum_relative_training_scale"])
    minimum_absolute_scale = float(protocol["validation"]["minimum_absolute_training_scale"])
    rows: list[dict[str, Any]] = []
    for (crop, practice), stratum in combined.groupby(
        ["outcome_crop", "irrigation_practice"], observed=True, sort=True
    ):
        stratum = stratum.reset_index(drop=True)
        temporal = stratum.is_temporal_holdout.to_numpy(dtype=bool)
        extreme = stratum.is_precipitation_extreme.to_numpy(dtype=bool)
        split_masks: list[tuple[str, str, np.ndarray, np.ndarray]] = []
        geographic_counts = (
            stratum.loc[~temporal].geographic_group.astype(str).value_counts().sort_index()
        )
        geographic_groups = list(
            map(str, geographic_counts.loc[geographic_counts.ge(minimum_test)].index)
        )
        if len(geographic_groups) < minimum_geographic_groups:
            raise ValueError(f"{crop}/{practice} lacks enough eligible leave-state-out groups")
        for group in geographic_groups:
            test = (~temporal) & stratum.geographic_group.astype(str).eq(group).to_numpy(dtype=bool)
            train = (~temporal) & ~stratum.geographic_group.astype(str).eq(group).to_numpy(dtype=bool)
            split_masks.append(("development_leave_state_out", group, train, test))
        development_counties = set(stratum.loc[~temporal, "county_geoid"].astype(str))
        same_county_temporal = temporal & stratum.county_geoid.astype(str).isin(
            development_counties
        ).to_numpy(dtype=bool)
        split_masks.append(("terminal_temporal_same_counties", "terminal", ~temporal, same_county_temporal))
        split_masks.append(("development_precipitation_extreme", "tails", (~temporal) & ~extreme, (~temporal) & extreme))
        for split, split_id, train, test in split_masks:
            if int(test.sum()) < minimum_test:
                raise ValueError(f"{crop}/{practice}/{split}/{split_id} fails minimum test rows")
            train_rows_before_endpoint_purge = int(train.sum())
            train, endpoint_purge_rows = purge_shared_first_difference_endpoints(
                stratum, train, test
            )
            if not train.any():
                raise ValueError(f"{crop}/{practice}/{split}/{split_id} has no training rows after endpoint purge")
            train_keys = set(map(tuple, stratum.loc[train, KEYS].itertuples(index=False, name=None)))
            test_keys = set(map(tuple, stratum.loc[test, KEYS].itertuples(index=False, name=None)))
            if train_keys & test_keys:
                raise ValueError("train and test keys overlap")
            for model, columns in specs.items():
                metrics = fit_predictive_ols(
                    stratum, columns, train, test, svd_relative_tolerance,
                    minimum_relative_scale, minimum_absolute_scale,
                )
                rows.append({
                    "crop": str(crop),
                    "irrigation_practice": str(practice),
                    "split": split,
                    "split_id": split_id,
                    "model": model,
                    "feature_count_excluding_year_terms": len(columns),
                    "train_rows_before_endpoint_purge": train_rows_before_endpoint_purge,
                    "train_rows_purged_shared_level_endpoint": endpoint_purge_rows,
                    "first_difference_level_endpoints_disjoint": True,
                    **metrics,
                })
    summaries: list[dict[str, Any]] = []
    for crop in sorted(set(common.outcome_crop.astype(str))):
        for practice in sorted(set(common.irrigation_practice.astype(str))):
            geographic_groups = sorted({
                str(row["split_id"])
                for row in rows
                if row["crop"] == crop and row["irrigation_practice"] == practice
                and row["split"] == "development_leave_state_out"
            })
            minimum_absolute_improvement = float(
                protocol["validation"]["distribution_minimum_absolute_rmse_improvement"]
            )
            minimum_relative_improvement = float(
                protocol["validation"]["distribution_minimum_relative_rmse_improvement"]
            )
            promotion = distribution_promotion_details(
                rows,
                crop,
                practice,
                geographic_groups,
                minimum_absolute_improvement,
                minimum_relative_improvement,
            )
            geographic_improvements = promotion["improvements"]
            temporal_improvement = paired_rmse_difference(
                rows, crop, practice, "terminal_temporal_same_counties", "terminal",
                "direct_quantity", "direct_quantity_distribution",
            )
            extreme_improvement = paired_rmse_difference(
                rows, crop, practice, "development_precipitation_extreme", "tails",
                "direct_quantity", "direct_quantity_distribution",
            )
            summaries.append({
                "crop": crop,
                "irrigation_practice": practice,
                "direct_distribution_selected_on_development_leave_state_out": bool(
                    promotion["selected"]
                ),
                "direct_distribution_rmse_improvement_each_eligible_state": geographic_improvements,
                "direct_distribution_required_material_rmse_floor_each_eligible_state": promotion[
                    "required_floors"
                ],
                "direct_distribution_rmse_excess_over_material_floor_each_eligible_state": promotion[
                    "excess_over_floor"
                ],
                "direct_distribution_minimum_absolute_rmse_improvement": minimum_absolute_improvement,
                "direct_distribution_minimum_relative_rmse_improvement": minimum_relative_improvement,
                "direct_distribution_mean_leave_state_out_rmse_improvement": float(
                    np.mean(list(geographic_improvements.values()))
                ),
                "direct_distribution_terminal_rmse_improvement_not_used_for_selection": temporal_improvement,
                "direct_distribution_extreme_rmse_improvement_not_used_for_selection": extreme_improvement,
                "direct_quantity_minus_pdsi_season_rmse_by_eligible_state": {
                    group: paired_rmse_difference(
                        rows, crop, practice, "development_leave_state_out", group,
                        "direct_quantity", "pdsi_season_mean",
                    )
                    for group in geographic_groups
                },
                "direct_quantity_minus_pdsi_season_terminal_rmse": paired_rmse_difference(
                    rows, crop, practice, "terminal_temporal_same_counties", "terminal",
                    "direct_quantity", "pdsi_season_mean",
                ),
                "rmse_difference_sign": "positive means the second named model has lower RMSE",
            })
    return {
        "status": "aggregate_noncausal_predictive_diagnostic_complete",
        "protocol_id": str(protocol["protocol_id"]),
        "estimand": "out-of-sample prediction of consecutive-year change in log county yield",
        "models_are_mutually_exclusive_moisture_representations": True,
        "development_leave_state_out_used_for_distribution_selection": True,
        "distribution_selection_requires_predeclared_material_improvement_floor": True,
        "terminal_temporal_holdout_used_for_selection": False,
        "train_test_first_difference_level_endpoints_purged": True,
        "train_only_scaling": True,
        "wheat_included": False,
        "metrics": rows,
        "comparison_summaries": summaries,
        "coefficients_in_output": False,
        "row_predictions_in_output": False,
        "predictive_fit_executed": True,
        "causal_effect_estimated": False,
        "damage_calculated": False,
        "scc_calculated": False,
        "required_disclaimer": str(protocol["output"]["required_disclaimer"]),
    }


def evaluate(
    input_dir: Path,
    audit_path: Path,
    direct_weather_path: Path,
    direct_validation_path: Path,
    pdsi_join_path: Path,
    pdsi_validation_path: Path,
    calendar_path: Path,
    calendar_validation_path: Path,
    protocol_path: Path = DEFAULT_PROTOCOL,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    common, direct, pdsi, audit = load_validated_inputs(
        input_dir,
        audit_path,
        protocol,
        protocol_path,
        direct_weather_path,
        direct_validation_path,
        pdsi_join_path,
        pdsi_validation_path,
        calendar_path,
        calendar_validation_path,
    )
    result = evaluate_frames(common, direct, pdsi, protocol)
    result["input_audit_sha256"] = sha256(audit_path)
    result["input_table_sha256"] = {
        name: audit["outputs"][name]["sha256"] for name in FILES
    }
    result["protocol_sha256"] = sha256(protocol_path)
    result["raw_source_sha256"] = {
        "direct_weather": sha256(direct_weather_path),
        "pdsi_join": sha256(pdsi_join_path),
        "calendar": sha256(calendar_path),
    }
    result["source_validation_receipt_sha256"] = {
        "direct_weather": sha256(direct_validation_path),
        "pdsi": sha256(pdsi_validation_path),
        "calendar": sha256(calendar_validation_path),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--input-audit", required=True)
    parser.add_argument("--direct-weather", required=True)
    parser.add_argument("--direct-validation", required=True)
    parser.add_argument("--pdsi-join", required=True)
    parser.add_argument("--pdsi-validation", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--calendar-validation", required=True)
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = evaluate(
        Path(args.input_dir),
        Path(args.input_audit),
        Path(args.direct_weather),
        Path(args.direct_validation),
        Path(args.pdsi_join),
        Path(args.pdsi_validation),
        Path(args.calendar),
        Path(args.calendar_validation),
        Path(args.protocol),
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {len(result['metrics'])} aggregate predictive metrics; "
        "no coefficients, causal effect, damage, or SCC"
    )


if __name__ == "__main__":
    main()
