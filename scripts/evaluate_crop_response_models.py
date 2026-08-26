#!/usr/bin/env python3
"""Evaluate crop-response specifications on outcome-blind blocked holdouts.

The workflow first-differences consecutive observations within crop/grid/
irrigation cells, removing time-invariant grid productivity. It estimates
crop-specific weather-response models and reports predictive metrics only;
coefficients are intentionally omitted. This diagnostic does not authorize a
causal response or an SCC input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


KEYS = ["crop", "irrigation", "lat", "lon_360", "harvest_year"]
LABELS = ["spatial_fold", "is_temporal_holdout", "is_climate_extreme"]
BOUNDARY = "diagnostic_held_out_prediction_not_causal_or_scc_authorized"
PAIR_GROUP_KEYS = KEYS[:-1]
RAW_REGIME_INPUT = "regime_primitive_weather"
PREBUILT_WEIGHTED_INPUT = "prebuilt_irrigation_weighted_basis"
PREBUILT_CONTRACT_ID = "gdhy_aggregate_irrigation_basis_v1"
PREBUILT_ALLOCATION_ORDER = "regime_basis_before_fixed_area_weighting"


def _as_bool(series: pd.Series, name: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    if not normalized.isin({"true", "false", "1", "0"}).all():
        raise ValueError(f"{name} must contain only Boolean values")
    return normalized.isin({"true", "1"})


def load_spec(path: Path) -> tuple[dict[str, list[str]], int, int, str]:
    raw = path.read_bytes()
    spec = tomllib.loads(raw.decode("utf-8"))
    models = {
        str(name): [str(value) for value in entry["features"]]
        for name, entry in spec["models"].items()
    }
    if not models or any(not values or len(values) != len(set(values)) for values in models.values()):
        raise ValueError("Every model must declare a nonempty unique feature list")
    return (
        models,
        int(spec["minimum_train_rows"]),
        int(spec["minimum_test_rows"]),
        hashlib.sha256(raw).hexdigest(),
    )


def prepare_levels(
    panel: pd.DataFrame,
    models: dict[str, list[str]],
    input_basis_mode: str = RAW_REGIME_INPUT,
) -> pd.DataFrame:
    if input_basis_mode not in {RAW_REGIME_INPUT, PREBUILT_WEIGHTED_INPUT}:
        raise ValueError(f"Unrecognized input-basis mode {input_basis_mode!r}")
    prebuilt = input_basis_mode == PREBUILT_WEIGHTED_INPUT
    if prebuilt:
        metadata = {
            "response_basis_contract_id": PREBUILT_CONTRACT_ID,
            "basis_allocation_order": PREBUILT_ALLOCATION_ORDER,
        }
        for column, expected in metadata.items():
            if column not in panel.columns or set(panel[column].dropna().astype(str)) != {expected}:
                raise ValueError(f"Prebuilt basis requires {column}={expected!r}")
        if set(panel["irrigation"].dropna().astype(str)) != {"area_weighted"}:
            raise ValueError("Prebuilt basis must contain only one area_weighted outcome row")
        if (
            "diagnostic_fit_authorized" not in panel.columns
            or not panel["diagnostic_fit_authorized"].isin([True]).all()
        ):
            raise ValueError("Prebuilt basis is not authorized for diagnostic fitting")
        if (
            "nonlinear_post_allocation_transform_authorized" not in panel.columns
            or not panel["nonlinear_post_allocation_transform_authorized"].isin([False]).all()
        ):
            raise ValueError("Prebuilt basis lacks the no-post-allocation-transform gate")
    else:
        if "response_basis_contract_id" in panel.columns:
            raise ValueError(
                "Prebuilt irrigation response-basis panels require the explicit "
                "prebuilt_irrigation_weighted_basis evaluator mode"
            )
        if (
            "irrigation" in panel.columns
            and panel["irrigation"].astype(str).eq("area_weighted").any()
        ):
            raise ValueError(
                "Area-weighted irrigation panels are forbidden in primitive-weather mode "
                "because it constructs nonlinear terms after exposure aggregation"
            )
    required = set(KEYS + LABELS + ["yield_t_ha", "yield_observed"])
    if missing := required - set(panel.columns):
        raise ValueError(f"Panel missing required fields {sorted(missing)}")
    frame = panel.copy()
    if frame.duplicated(KEYS).any():
        raise ValueError("Panel has duplicate crop/irrigation/grid/year keys")
    frame["yield_observed"] = _as_bool(frame["yield_observed"], "yield_observed")
    for label in LABELS[1:]:
        frame[label] = _as_bool(frame[label], label)
    years = pd.to_numeric(frame.harvest_year, errors="coerce")
    yields = pd.to_numeric(frame.yield_t_ha, errors="coerce")
    folds = pd.to_numeric(frame.spatial_fold, errors="coerce")
    if years.isna().any() or not np.equal(years, np.floor(years)).all():
        raise ValueError("harvest_year must be an integer")
    if folds.isna().any() or not np.equal(folds, np.floor(folds)).all():
        raise ValueError("spatial_fold must be an integer")
    frame["harvest_year"] = years.astype(int)
    frame["spatial_fold"] = folds.astype(int)
    frame["yield_t_ha"] = yields
    observed = frame.yield_observed
    if yields.loc[observed].isna().any() or (yields.loc[observed] <= 0).any():
        raise ValueError("Observed yield must be finite and positive")
    grid_keys = KEYS[:-1]
    if not frame.groupby(grid_keys, observed=True).spatial_fold.nunique().eq(1).all():
        raise ValueError("spatial_fold changes within a crop/irrigation/grid cell")
    for label, group in frame.groupby(["crop", "irrigation"], observed=True):
        year_labels = group.groupby("harvest_year", observed=True).is_temporal_holdout.nunique()
        if not year_labels.eq(1).all():
            raise ValueError(f"Temporal holdout label differs within year for {label}")
        ordered = group.groupby("harvest_year", observed=True).is_temporal_holdout.first().sort_index()
        if not ordered.any() or ordered.all() or (ordered.astype(int).diff().fillna(0) < 0).any():
            raise ValueError(f"Temporal holdout must be one nonempty final-year block for {label}")

    if not prebuilt:
        precip_columns = {"precip_mm"}
        precip_columns.update(
            name.replace("log1p_", "") for values in models.values() for name in values
            if "log1p_precip_mm" in name
        )
        for precip in precip_columns:
            if precip not in frame:
                raise ValueError(f"Panel missing precipitation source {precip}")
            numeric = pd.to_numeric(frame[precip], errors="coerce")
            if numeric.isna().any() or (numeric < 0).any():
                raise ValueError(f"{precip} must be finite and nonnegative")
            prefix = precip.removesuffix("precip_mm")
            frame[f"{prefix}log1p_precip_mm"] = np.log1p(numeric)
            temp = f"{prefix}tmean_c"
            if temp in frame:
                temp_numeric = pd.to_numeric(frame[temp], errors="coerce")
                frame[f"{prefix}tmean_x_log1p_precip"] = temp_numeric * frame[f"{prefix}log1p_precip_mm"]

    all_features = sorted({feature for values in models.values() for feature in values})
    if missing := set(all_features) - set(frame.columns):
        raise ValueError(f"Panel missing model fields {sorted(missing)}")
    frame[all_features] = frame[all_features].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(frame[all_features].to_numpy(dtype=float)).all():
        raise ValueError("Model features must be finite")
    return frame


def make_first_differences(frame: pd.DataFrame, features: Iterable[str]) -> pd.DataFrame:
    features = list(features)
    observed = frame.loc[frame.yield_observed].copy()
    observed["log_yield"] = np.log(observed.yield_t_ha)
    group_keys = KEYS[:-1]
    observed = observed.sort_values(KEYS).reset_index(drop=True)
    grouped = observed.groupby(group_keys, observed=True, sort=False)
    previous_year = grouped.harvest_year.shift(1)
    consecutive = observed.harvest_year.eq(previous_year + 1)
    differenced = observed.loc[consecutive, KEYS + LABELS].copy()
    differenced["delta_log_yield"] = (
        observed.log_yield - grouped.log_yield.shift(1)
    ).loc[consecutive].to_numpy()
    differenced["pair_start_year"] = previous_year.loc[consecutive].astype(int).to_numpy()
    differenced["pair_end_year"] = differenced["harvest_year"].astype(int)
    for feature in features:
        differenced[f"delta__{feature}"] = (
            observed[feature] - grouped[feature].shift(1)
        ).loc[consecutive].to_numpy()
    previous_extreme = grouped.is_climate_extreme.shift(1)
    previous_extreme = previous_extreme.where(previous_extreme.notna(), False).astype(bool)
    differenced["pair_is_climate_extreme"] = (
        observed.is_climate_extreme | previous_extreme
    ).loc[consecutive].to_numpy()
    if differenced.empty:
        raise ValueError("No consecutive observed-yield pairs available")
    numeric = ["delta_log_yield"] + [f"delta__{feature}" for feature in features]
    if not np.isfinite(differenced[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Differenced response or features are nonfinite")
    return differenced


def endpoint_set(frame: pd.DataFrame) -> set[tuple[object, ...]]:
    endpoints: set[tuple[object, ...]] = set()
    columns = PAIR_GROUP_KEYS + ["pair_start_year", "pair_end_year"]
    for row in frame[columns].itertuples(index=False, name=None):
        group = tuple(row[:-2])
        endpoints.add((*group, int(row[-2])))
        endpoints.add((*group, int(row[-1])))
    return endpoints


def endpoint_overlap_count(train: pd.DataFrame, test: pd.DataFrame) -> int:
    return len(endpoint_set(train) & endpoint_set(test))


def purged_temporal_masks(data: pd.DataFrame) -> tuple[pd.Series, pd.Series, dict[str, object]]:
    test = data.is_temporal_holdout.astype(bool)
    if not test.any() or test.all():
        raise ValueError("Temporal split must contain train and test pairs")
    test_start = int(data.loc[test, "pair_end_year"].min())
    candidate_train = ~test
    # Pair ending in test_start-1 shares that year's endpoint with the first
    # test pair, so the last admissible training pair ends at test_start-2.
    train = candidate_train & data.pair_end_year.le(test_start - 2)
    overlap = endpoint_overlap_count(data.loc[train], data.loc[test])
    if overlap:
        raise AssertionError("Purged temporal split retains shared yield endpoints")
    return train, test, {
        "purge_rule": "drop_training_pairs_sharing_either_yield_endpoint_with_temporal_test",
        "purged_train_rows": int((candidate_train & ~train).sum()),
        "endpoint_overlap_count": overlap,
    }


def purged_extreme_masks(data: pd.DataFrame) -> tuple[pd.Series, pd.Series, dict[str, object]]:
    test = data.pair_is_climate_extreme.astype(bool)
    if not test.any() or test.all():
        raise ValueError("Climate-extreme split must contain train and test pairs")
    test_endpoints = endpoint_set(data.loc[test])
    candidate_train = ~test
    keep: list[bool] = []
    columns = PAIR_GROUP_KEYS + ["pair_start_year", "pair_end_year"]
    for row in data.loc[candidate_train, columns].itertuples(index=False, name=None):
        group = tuple(row[:-2])
        start = (*group, int(row[-2]))
        end = (*group, int(row[-1]))
        keep.append(start not in test_endpoints and end not in test_endpoints)
    train = pd.Series(False, index=data.index)
    train.loc[candidate_train] = keep
    overlap = endpoint_overlap_count(data.loc[train], data.loc[test])
    if overlap:
        raise AssertionError("Purged climate-extreme split retains shared yield endpoints")
    return train, test, {
        "purge_rule": "drop_training_pairs_sharing_either_yield_endpoint_with_extreme_test",
        "purged_train_rows": int((candidate_train & ~train).sum()),
        "endpoint_overlap_count": overlap,
    }


def _fit_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    minimum_train_rows: int,
    minimum_test_rows: int,
) -> tuple[np.ndarray, dict[str, object]]:
    if len(train) < minimum_train_rows or len(test) < minimum_test_rows:
        raise ValueError(
            f"Insufficient split rows: train={len(train)}, test={len(test)}, "
            f"required={minimum_train_rows}/{minimum_test_rows}"
        )
    columns = [f"delta__{feature}" for feature in features]
    train_x = train[columns].to_numpy(dtype=float)
    test_x = test[columns].to_numpy(dtype=float)
    scale = train_x.std(axis=0, ddof=0)
    if np.any(scale <= 0) or not np.isfinite(scale).all():
        bad = [feature for feature, value in zip(features, scale) if not np.isfinite(value) or value <= 0]
        raise ValueError(f"Zero/nonfinite training variation in {bad}")
    center = train_x.mean(axis=0)
    design = np.column_stack([np.ones(len(train)), (train_x - center) / scale])
    test_design = np.column_stack([np.ones(len(test)), (test_x - center) / scale])
    outcome = train.delta_log_yield.to_numpy(dtype=float)
    coefficients, _, rank, singular = np.linalg.lstsq(design, outcome, rcond=1e-12)
    if rank != design.shape[1]:
        raise ValueError(f"Training design is rank deficient ({rank}/{design.shape[1]})")
    # Some sandboxed BLAS builds leave floating-point status flags set despite
    # finite inputs and output; validate values explicitly immediately below.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        prediction = test_design @ coefficients
    if not np.isfinite(prediction).all():
        raise ValueError("Predictions are nonfinite")
    return prediction, {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "matrix_rank": int(rank),
        "condition_number": float(singular[0] / singular[-1]),
    }


def _metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float | None]:
    residual = observed - predicted
    zero_rmse = float(np.sqrt(np.mean(np.square(observed))))
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    centered_total = float(np.sum(np.square(observed - observed.mean())))
    r_squared = None if centered_total == 0 else float(1 - np.sum(np.square(residual)) / centered_total)
    correlation = None
    if np.std(observed) > 0 and np.std(predicted) > 0:
        correlation = float(np.corrcoef(observed, predicted)[0, 1])
    return {
        "rmse": rmse,
        "mae": float(np.mean(np.abs(residual))),
        "r_squared": r_squared,
        "correlation": correlation,
        "zero_change_rmse": zero_rmse,
        "rmse_improvement_vs_zero": float(zero_rmse - rmse),
    }


def _evaluate_split(
    data: pd.DataFrame,
    train_mask: pd.Series,
    test_mask: pd.Series,
    features: list[str],
    minimum_train_rows: int,
    minimum_test_rows: int,
) -> dict[str, object]:
    train = data.loc[train_mask]
    test = data.loc[test_mask]
    prediction, audit = _fit_predict(train, test, features, minimum_train_rows, minimum_test_rows)
    audit.update(_metrics(test.delta_log_yield.to_numpy(dtype=float), prediction))
    return audit


def evaluate(
    panel: pd.DataFrame,
    models: dict[str, list[str]],
    minimum_train_rows: int,
    minimum_test_rows: int,
    spec_sha256: str,
    input_basis_mode: str = RAW_REGIME_INPUT,
) -> dict[str, object]:
    frame = prepare_levels(panel, models, input_basis_mode)
    all_features = sorted({feature for values in models.values() for feature in values})
    pairs = make_first_differences(frame, all_features)
    folds = sorted(pairs.spatial_fold.unique())
    if len(folds) < 2:
        raise ValueError("Spatial validation requires at least two populated folds")
    crops = sorted(pairs.crop.astype(str).unique())
    results: list[dict[str, object]] = []
    for crop in crops:
        crop_data = pairs.loc[pairs.crop.astype(str).eq(crop)].copy()
        for model, features in models.items():
            spatial_observed: list[np.ndarray] = []
            spatial_predicted: list[np.ndarray] = []
            spatial_audits: list[dict[str, object]] = []
            for fold in folds:
                test_mask = crop_data.spatial_fold.eq(fold)
                prediction, audit = _fit_predict(
                    crop_data.loc[~test_mask], crop_data.loc[test_mask], features,
                    minimum_train_rows, minimum_test_rows,
                )
                spatial_observed.append(crop_data.loc[test_mask, "delta_log_yield"].to_numpy(dtype=float))
                spatial_predicted.append(prediction)
                spatial_audits.append({"fold": int(fold), **audit})
            observed = np.concatenate(spatial_observed)
            predicted = np.concatenate(spatial_predicted)
            results.append({
                "crop": crop, "model": model, "holdout": "spatial_block",
                "folds": spatial_audits, "test_rows": int(len(observed)),
                **_metrics(observed, predicted),
            })

            temporal_train, temporal_test, temporal_purge = purged_temporal_masks(crop_data)
            temporal = _evaluate_split(
                crop_data, temporal_train, temporal_test,
                features, minimum_train_rows, minimum_test_rows,
            )
            temporal.update(temporal_purge)
            results.append({"crop": crop, "model": model, "holdout": "temporal", **temporal})

            extreme_train, extreme_test, extreme_purge = purged_extreme_masks(crop_data)
            extreme = _evaluate_split(
                crop_data, extreme_train, extreme_test,
                features, minimum_train_rows, minimum_test_rows,
            )
            extreme.update(extreme_purge)
            results.append({"crop": crop, "model": model, "holdout": "climate_extreme", **extreme})
    return {
        "status": BOUNDARY,
        "spec_sha256": spec_sha256,
        "n_level_rows": int(len(frame)),
        "n_observed_level_rows": int(frame.yield_observed.sum()),
        "n_consecutive_pairs": int(len(pairs)),
        "harvest_year_start": int(frame.harvest_year.min()),
        "harvest_year_end": int(frame.harvest_year.max()),
        "harvest_years": sorted(int(value) for value in frame.harvest_year.unique()),
        "crops": crops,
        "models": list(models),
        "input_basis_mode": input_basis_mode,
        "response_basis_contract_id": (
            PREBUILT_CONTRACT_ID if input_basis_mode == PREBUILT_WEIGHTED_INPUT else None
        ),
        "nonspatial_split_contract": "yield_endpoint_disjoint_purged_training_pairs",
        "results": results,
        "warning": (
            "First-difference predictive diagnostics omit coefficients and do not establish causality, "
            "external validity, welfare calibration, or permission to create an SCC response bundle."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--spec", default="config/response_evaluation_spec.toml")
    parser.add_argument("--out", required=True)
    parser.add_argument("--minimum-train-rows", type=int)
    parser.add_argument("--minimum-test-rows", type=int)
    parser.add_argument(
        "--input-basis-mode",
        choices=[RAW_REGIME_INPUT, PREBUILT_WEIGHTED_INPUT],
        default=RAW_REGIME_INPUT,
        help="Use explicit prebuilt mode only for contract-marked basis-before-weighting panels.",
    )
    args = parser.parse_args()
    models, minimum_train, minimum_test, digest = load_spec(Path(args.spec))
    if args.minimum_train_rows is not None:
        minimum_train = args.minimum_train_rows
    if args.minimum_test_rows is not None:
        minimum_test = args.minimum_test_rows
    if minimum_train < 1 or minimum_test < 1:
        raise ValueError("Minimum split sizes must be positive")
    audit = evaluate(
        pd.read_parquet(args.panel), models, minimum_train, minimum_test, digest,
        input_basis_mode=args.input_basis_mode,
    )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "results"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
