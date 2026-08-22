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


def prepare_levels(panel: pd.DataFrame, models: dict[str, list[str]]) -> pd.DataFrame:
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
) -> dict[str, object]:
    frame = prepare_levels(panel, models)
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

            temporal = _evaluate_split(
                crop_data, ~crop_data.is_temporal_holdout, crop_data.is_temporal_holdout,
                features, minimum_train_rows, minimum_test_rows,
            )
            results.append({"crop": crop, "model": model, "holdout": "temporal", **temporal})

            extreme = _evaluate_split(
                crop_data, ~crop_data.pair_is_climate_extreme, crop_data.pair_is_climate_extreme,
                features, minimum_train_rows, minimum_test_rows,
            )
            results.append({"crop": crop, "model": model, "holdout": "climate_extreme", **extreme})
    return {
        "status": BOUNDARY,
        "spec_sha256": spec_sha256,
        "n_level_rows": int(len(frame)),
        "n_observed_level_rows": int(frame.yield_observed.sum()),
        "n_consecutive_pairs": int(len(pairs)),
        "crops": crops,
        "models": list(models),
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
    args = parser.parse_args()
    models, minimum_train, minimum_test, digest = load_spec(Path(args.spec))
    if args.minimum_train_rows is not None:
        minimum_train = args.minimum_train_rows
    if args.minimum_test_rows is not None:
        minimum_test = args.minimum_test_rows
    if minimum_train < 1 or minimum_test < 1:
        raise ValueError("Minimum split sizes must be positive")
    audit = evaluate(pd.read_parquet(args.panel), models, minimum_train, minimum_test, digest)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "results"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
