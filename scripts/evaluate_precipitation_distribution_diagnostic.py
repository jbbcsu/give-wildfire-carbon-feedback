#!/usr/bin/env python3
"""Run a locked, coefficient-suppressing precipitation-pattern diagnostic.

This executable consumes the validated 54-column MIRCA-weighted candidate
basis without changing its ``fit_authorized=false`` status.  A separate,
versioned contract permits held-out prediction only.  Fitted coefficients are
used transiently to form predictions and are never returned or written.
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

from evaluate_crop_response_models import (
    KEYS,
    LABELS,
    _fit_predict,
    _metrics,
    endpoint_overlap_count,
    make_first_differences,
    purged_extreme_masks,
    purged_temporal_masks,
)
from make_validation_folds import stable_fold
from validate_irrigation_distribution_basis import validate as validate_candidate_basis


PROJECT = Path(__file__).resolve().parents[1]
SPEC_DEFAULT = PROJECT / "config" / "precipitation_distribution_diagnostic_v1.toml"
LOCK_DEFAULT = PROJECT / "config" / "precipitation_distribution_diagnostic_v1.lock.toml"
SOURCE_CONTRACT_ID = "gdhy_aggregate_irrigation_distribution_candidate_v1"
SOURCE_ALLOCATION_ORDER = "regime_basis_before_fixed_area_weighting"
DIAGNOSTIC_CONTRACT_ID = "gdhy_precipitation_distribution_predictive_diagnostic_v1"
STATUS = "validated_noncausal_distribution_predictive_diagnostic_not_scc_eligible"
NONSPATIAL_SPLIT_CONTRACT = "yield_endpoint_disjoint_purged_training_pairs"
EXPECTED_STAGE_FRACTIONS = [0.0, 0.3, 0.7, 1.0]
EXPECTED_WET_DAY_THRESHOLD_MM = 1.0

EXPECTED_FEATURE_SETS = {
    "temperature_controls": ["stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c"],
    "seasonal_quantity": ["log1p_precip_mm"],
    "timing_concentration": [
        "precipitation_timing_centroid",
        "precipitation_concentration_hhi",
    ],
    "occurrence_intensity": [
        "stage1_wet_day_frequency",
        "stage2_wet_day_frequency",
        "stage3_wet_day_frequency",
        "stage1_mean_wet_day_intensity_mm",
        "stage2_mean_wet_day_intensity_mm",
        "stage3_mean_wet_day_intensity_mm",
    ],
    "dry_spells": [
        "stage1_cdd_fraction",
        "stage2_cdd_fraction",
        "stage3_cdd_fraction",
    ],
    "wet_extremes": [
        "stage1_rx1day_mm",
        "stage2_rx1day_mm",
        "stage3_rx1day_mm",
        "stage1_rx5day_mm",
        "stage2_rx5day_mm",
        "stage3_rx5day_mm",
    ],
}
EXPECTED_MODEL_GROUPS = {
    "temperature_control": ["temperature_controls"],
    "seasonal_quantity": ["temperature_controls", "seasonal_quantity"],
    "quantity_plus_timing_concentration": [
        "temperature_controls", "seasonal_quantity", "timing_concentration"
    ],
    "quantity_plus_occurrence_intensity": [
        "temperature_controls", "seasonal_quantity", "occurrence_intensity"
    ],
    "quantity_plus_dry_spells": [
        "temperature_controls", "seasonal_quantity", "dry_spells"
    ],
    "quantity_plus_wet_extremes": [
        "temperature_controls", "seasonal_quantity", "wet_extremes"
    ],
    "quantity_plus_all_distribution": [
        "temperature_controls",
        "seasonal_quantity",
        "timing_concentration",
        "occurrence_intensity",
        "dry_spells",
        "wet_extremes",
    ],
}
FORBIDDEN_ESTIMATE_KEYS = {
    "coef",
    "coefs",
    "coefficient",
    "coefficients",
    "intercept",
    "beta",
    "betas",
    "parameter_estimate",
    "parameter_estimates",
    "standard_error",
    "standard_errors",
    "p_value",
    "p_values",
    "t_statistic",
    "t_statistics",
}
ALLOWED_COEFFICIENT_METADATA_KEYS = {
    "coefficient_export_authorized",
    "coefficients_suppressed",
}
FORBIDDEN_ESTIMATE_KEY_FRAGMENTS = {
    "coefficient",
    "intercept",
    "standard_error",
    "p_value",
    "t_statistic",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_bool(mapping: dict[str, Any], name: str, expected: bool) -> None:
    value = mapping.get(name)
    if not isinstance(value, bool) or value is not expected:
        raise ValueError(f"{name} must be exactly {expected}")


def _expand_models(spec: dict[str, Any]) -> dict[str, list[str]]:
    feature_sets = {
        str(name): [str(value) for value in entry.get("features", [])]
        for name, entry in spec.get("feature_sets", {}).items()
    }
    if feature_sets != EXPECTED_FEATURE_SETS:
        raise ValueError("Diagnostic feature-set registry drifted from version 1")
    model_groups = {
        str(name): [str(value) for value in entry.get("feature_sets", [])]
        for name, entry in spec.get("models", {}).items()
    }
    if model_groups != EXPECTED_MODEL_GROUPS:
        raise ValueError("Diagnostic model registry drifted from version 1")
    if spec.get("comparison", {}).get("model_order") != list(EXPECTED_MODEL_GROUPS):
        raise ValueError("Diagnostic model order drifted from version 1")
    models: dict[str, list[str]] = {}
    for model, groups in model_groups.items():
        features = [feature for group in groups for feature in feature_sets[group]]
        if len(features) != len(set(features)):
            raise ValueError(f"Model {model} contains duplicate features")
        models[model] = features
    used = {feature for features in models.values() for feature in features}
    if any(f"stage{stage}_precip_share" in used for stage in range(1, 4)):
        raise ValueError("Stage precipitation shares are forbidden by the redundancy rule")
    timing = set(feature_sets["timing_concentration"])
    if timing != {"precipitation_timing_centroid", "precipitation_concentration_hhi"}:
        raise ValueError("Timing basis must use the registered nonredundant pair")
    return models


def load_contract(
    spec_path: Path,
    lock_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, list[str]], str, str]:
    spec_raw = spec_path.read_bytes()
    lock_raw = lock_path.read_bytes()
    spec = tomllib.loads(spec_raw.decode("utf-8"))
    lock = tomllib.loads(lock_raw.decode("utf-8"))
    spec_hash = hashlib.sha256(spec_raw).hexdigest()
    lock_hash = hashlib.sha256(lock_raw).hexdigest()
    if spec.get("schema_version") != 1 or lock.get("schema_version") != 1:
        raise ValueError("Unrecognized diagnostic specification or lock schema")
    for record, label in ((spec, "specification"), (lock, "lock")):
        if record.get("diagnostic_contract_id") != DIAGNOSTIC_CONTRACT_ID:
            raise ValueError(f"Diagnostic contract drift in {label}")
    if lock.get("spec_sha256") != spec_hash:
        raise ValueError("Diagnostic specification hash differs from the lock")
    if spec.get("source_basis_contract_id") != SOURCE_CONTRACT_ID:
        raise ValueError("Source-basis contract drift")
    if spec.get("source_basis_allocation_order") != SOURCE_ALLOCATION_ORDER:
        raise ValueError("Source-basis allocation-order drift")
    if spec.get("source_basis_feature_count") != 54:
        raise ValueError("Source-basis feature-count drift")

    authorization = spec.get("authorization", {})
    _require_bool(authorization, "held_out_predictive_fit_authorized", True)
    for name in (
        "coefficient_export_authorized",
        "causal_interpretation_authorized",
        "production_model_selection_authorized",
        "response_draw_export_authorized",
        "scc_use_authorized",
        "source_basis_fit_authorized_expected",
    ):
        _require_bool(authorization, name, False)
    boundary = lock.get("boundary", {})
    for name in (
        "source_basis_fit_authorized",
        "coefficient_export_authorized",
        "scc_use_authorized",
    ):
        _require_bool(boundary, name, False)
    _require_bool(boundary, "diagnostic_only", True)

    construction = spec.get("construction", {})
    threshold = float(construction.get("wet_day_threshold_mm", math.nan))
    if not math.isclose(threshold, EXPECTED_WET_DAY_THRESHOLD_MM, rel_tol=0, abs_tol=0):
        raise ValueError("Wet-day threshold drifted from the version-1 diagnostic QA choice")
    fractions = [float(value) for value in construction.get("stage_fractions", [])]
    if fractions != EXPECTED_STAGE_FRACTIONS:
        raise ValueError("Stage fractions drifted from the version-1 diagnostic QA choice")
    if construction.get("algebraic_redundancy_rule") != (
        "use_timing_centroid_and_concentration_hhi; omit_all_stage_precipitation_shares"
    ):
        raise ValueError("Algebraic-redundancy rule drift")
    validation = spec.get("validation", {})
    if validation.get("nonspatial_split_contract") != NONSPATIAL_SPLIT_CONTRACT:
        raise ValueError("Nonspatial split-contract drift")
    if validation.get("extreme_features") != ["cdd_max_days", "rx1day_mm"]:
        raise ValueError("Extreme-label feature drift")
    models = _expand_models(spec)
    return spec, lock, models, spec_hash, lock_hash


def locked_input(lock: dict[str, Any], crop: str) -> dict[str, Any]:
    matches = [entry for entry in lock.get("inputs", []) if entry.get("crop") == crop]
    if len(matches) != 1:
        raise ValueError(f"Lock must contain exactly one input entry for {crop}")
    return matches[0]


def resolve_locked_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def _constant_bool(frame: pd.DataFrame, name: str, expected: bool) -> None:
    if name not in frame:
        raise ValueError(f"Source panel requires {name}={expected}")
    values = frame[name]
    if (
        not pd.api.types.is_bool_dtype(values.dtype)
        or values.isna().any()
        or not values.eq(expected).all()
    ):
        raise ValueError(f"Source panel requires {name}={expected}")


def validate_locked_source(
    project_root: Path,
    source: dict[str, Any],
    crop: str,
    spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any], Path, Path]:
    panel_path = resolve_locked_path(project_root, str(source["panel_path"]))
    audit_path = resolve_locked_path(project_root, str(source["allocation_audit_path"]))
    panel_hash = sha256_path(panel_path)
    audit_hash = sha256_path(audit_path)
    if panel_hash != source.get("panel_sha256"):
        raise ValueError(f"Locked source-panel hash drift for {crop}")
    if audit_hash != source.get("allocation_audit_sha256"):
        raise ValueError(f"Locked source allocation-audit hash drift for {crop}")
    panel = pd.read_parquet(panel_path)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    summary = validate_candidate_basis(panel, audit, expected_crop=crop, stages=3)
    _constant_bool(panel, "fit_authorized", False)
    _constant_bool(panel, "scc_authorized", False)
    _constant_bool(panel, "production_model_form_frozen", False)
    _constant_bool(panel, "nonlinear_post_allocation_transform_authorized", False)
    if audit.get("fit_authorized") is not False or audit.get("scc_authorized") is not False:
        raise ValueError("Source allocation audit must remain fit- and SCC-ineligible")
    if audit.get("stage_count") != len(EXPECTED_STAGE_FRACTIONS) - 1:
        raise ValueError("Source allocation audit stage count drift")
    threshold = float(spec["construction"]["wet_day_threshold_mm"])
    if not math.isclose(float(audit.get("wet_day_threshold_mm", math.nan)), threshold, rel_tol=0, abs_tol=0):
        raise ValueError("Source allocation-audit wet-day threshold drift")
    if not math.isclose(float(summary["wet_day_threshold_mm"]), threshold, rel_tol=0, abs_tol=0):
        raise ValueError("Source-panel wet-day threshold drift")
    if len(panel) != source.get("expected_rows"):
        raise ValueError("Source-panel row count differs from lock")
    if int(panel["yield_observed"].sum()) != source.get("expected_observed_outcomes"):
        raise ValueError("Source-panel observed-outcome count differs from lock")
    years = sorted(pd.to_numeric(panel["harvest_year"], errors="raise").astype(int).unique())
    expected_years = list(range(int(source["expected_year_start"]), int(source["expected_year_end"]) + 1))
    if years != expected_years:
        raise ValueError("Source-panel year coverage differs from the complete locked range")
    return panel, audit, summary, panel_path, audit_path


def add_outcome_blind_labels(panel: pd.DataFrame, validation: dict[str, Any]) -> pd.DataFrame:
    frame = panel.copy()
    folds = int(validation["spatial_folds"])
    block_degrees = float(validation["spatial_block_degrees"])
    temporal_years = int(validation["temporal_holdout_years"])
    quantile = float(validation["extreme_quantile"])
    seed = str(validation["seed"])
    if folds < 2 or block_degrees <= 0 or temporal_years < 1 or not 0.5 < quantile < 1:
        raise ValueError("Invalid locked validation settings")
    lat = pd.to_numeric(frame["lat"], errors="coerce")
    lon = pd.to_numeric(frame["lon_360"], errors="coerce")
    if not np.isfinite(lat).all() or not np.isfinite(lon).all():
        raise ValueError("Source grid coordinates must be finite")
    lat_block = np.floor((lat + 90) / block_degrees).astype(int)
    lon_block = np.floor(lon / block_degrees).astype(int)
    frame["spatial_block_id"] = lat_block.astype(str) + "_" + lon_block.astype(str)
    frame["spatial_fold"] = frame["spatial_block_id"].map(
        lambda value: stable_fold(value, folds, seed)
    )
    final_holdout_start = int(frame["harvest_year"].max()) - temporal_years + 1
    frame["is_temporal_holdout"] = frame["harvest_year"].astype(int) >= final_holdout_start
    group_keys = ["lat", "lon_360", "crop", "irrigation"]
    cdd_cutoff = frame.groupby(group_keys, observed=True)["cdd_max_days"].transform(
        "quantile", q=quantile
    )
    rx1_cutoff = frame.groupby(group_keys, observed=True)["rx1day_mm"].transform(
        "quantile", q=quantile
    )
    frame["is_dry_extreme"] = frame["cdd_max_days"] >= cdd_cutoff
    frame["is_wet_extreme"] = frame["rx1day_mm"] >= rx1_cutoff
    frame["is_climate_extreme"] = frame["is_dry_extreme"] | frame["is_wet_extreme"]
    frame["validation_design"] = (
        f"block={block_degrees:g};folds={folds};temporal_last={temporal_years};"
        f"q={quantile:g};seed={seed}"
    )
    if frame["spatial_fold"].nunique() != folds:
        raise ValueError("Not all locked spatial folds are populated")
    if not frame["is_temporal_holdout"].any() or frame["is_temporal_holdout"].all():
        raise ValueError("Locked temporal holdout is empty or exhaustive")
    if not frame["is_climate_extreme"].any() or frame["is_climate_extreme"].all():
        raise ValueError("Locked climate-extreme holdout is empty or exhaustive")
    return frame


def prepare_diagnostic_levels(panel: pd.DataFrame, models: dict[str, list[str]]) -> pd.DataFrame:
    required = set(KEYS + LABELS + ["yield_t_ha", "yield_observed"])
    all_features = [feature for features in models.values() for feature in features]
    required.update(all_features)
    if missing := required - set(panel.columns):
        raise ValueError(f"Diagnostic source missing {sorted(missing)}")
    frame = panel.copy()
    if frame.duplicated(KEYS).any():
        raise ValueError("Diagnostic source contains duplicate outcome keys")
    if set(frame["irrigation"].astype(str)) != {"area_weighted"}:
        raise ValueError("Diagnostic requires one area-weighted outcome row")
    frame["yield_observed"] = frame["yield_observed"].astype(bool)
    yields = pd.to_numeric(frame["yield_t_ha"], errors="coerce")
    if yields.loc[frame["yield_observed"]].isna().any() or (yields.loc[frame["yield_observed"]] <= 0).any():
        raise ValueError("Observed yield must be finite and positive")
    frame["yield_t_ha"] = yields
    unique_features = list(dict.fromkeys(all_features))
    frame[unique_features] = frame[unique_features].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(frame[unique_features].to_numpy(dtype=float)).all():
        raise ValueError("Diagnostic features must be finite")
    return frame


def assert_coefficients_suppressed(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            forbidden_fragment = (
                normalized not in ALLOWED_COEFFICIENT_METADATA_KEYS
                and any(fragment in normalized for fragment in FORBIDDEN_ESTIMATE_KEY_FRAGMENTS)
            )
            if normalized in FORBIDDEN_ESTIMATE_KEYS or forbidden_fragment:
                raise AssertionError(f"Forbidden fitted-parameter field {key!r}")
            assert_coefficients_suppressed(nested)
    elif isinstance(value, list):
        for nested in value:
            assert_coefficients_suppressed(nested)


def evaluate_models(
    frame: pd.DataFrame,
    models: dict[str, list[str]],
    minimum_train_rows: int,
    minimum_test_rows: int,
) -> tuple[list[dict[str, Any]], int]:
    all_features = list(dict.fromkeys(feature for features in models.values() for feature in features))
    pairs = make_first_differences(frame, all_features)
    folds = sorted(int(value) for value in pairs["spatial_fold"].unique())
    results: list[dict[str, Any]] = []
    for model, features in models.items():
        spatial_observed: list[np.ndarray] = []
        spatial_predicted: list[np.ndarray] = []
        fold_audits: list[dict[str, Any]] = []
        for fold in folds:
            test_mask = pairs["spatial_fold"].eq(fold)
            train = pairs.loc[~test_mask]
            test = pairs.loc[test_mask]
            overlap = endpoint_overlap_count(train, test)
            if overlap:
                raise AssertionError("Spatial split retains shared yield endpoints")
            prediction, audit = _fit_predict(
                train, test, features, minimum_train_rows, minimum_test_rows
            )
            spatial_observed.append(test["delta_log_yield"].to_numpy(dtype=float))
            spatial_predicted.append(prediction)
            fold_audits.append({"fold": fold, "endpoint_overlap_count": overlap, **audit})
        observed = np.concatenate(spatial_observed)
        predicted = np.concatenate(spatial_predicted)
        results.append(
            {
                "model": model,
                "holdout": "spatial_block",
                "feature_count": len(features),
                "folds": fold_audits,
                "test_rows": int(len(observed)),
                **_metrics(observed, predicted),
            }
        )

        temporal_train, temporal_test, temporal_purge = purged_temporal_masks(pairs)
        prediction, temporal = _fit_predict(
            pairs.loc[temporal_train],
            pairs.loc[temporal_test],
            features,
            minimum_train_rows,
            minimum_test_rows,
        )
        temporal.update(_metrics(pairs.loc[temporal_test, "delta_log_yield"].to_numpy(dtype=float), prediction))
        temporal.update(temporal_purge)
        results.append(
            {
                "model": model,
                "holdout": "temporal",
                "feature_count": len(features),
                **temporal,
            }
        )

        extreme_train, extreme_test, extreme_purge = purged_extreme_masks(pairs)
        prediction, extreme = _fit_predict(
            pairs.loc[extreme_train],
            pairs.loc[extreme_test],
            features,
            minimum_train_rows,
            minimum_test_rows,
        )
        extreme.update(_metrics(pairs.loc[extreme_test, "delta_log_yield"].to_numpy(dtype=float), prediction))
        extreme.update(extreme_purge)
        results.append(
            {
                "model": model,
                "holdout": "climate_extreme",
                "feature_count": len(features),
                **extreme,
            }
        )
    return results, int(len(pairs))


def run_diagnostic(
    crop: str,
    spec_path: Path = SPEC_DEFAULT,
    lock_path: Path = LOCK_DEFAULT,
    project_root: Path = PROJECT,
) -> dict[str, Any]:
    spec, lock, models, spec_hash, lock_hash = load_contract(spec_path, lock_path)
    source = locked_input(lock, crop)
    panel, _audit, source_summary, panel_path, audit_path = validate_locked_source(
        project_root, source, crop, spec
    )
    labeled = add_outcome_blind_labels(panel, spec["validation"])
    levels = prepare_diagnostic_levels(labeled, models)
    results, pair_count = evaluate_models(
        levels,
        models,
        int(spec["minimum_train_rows"]),
        int(spec["minimum_test_rows"]),
    )
    if sha256_path(panel_path) != source["panel_sha256"] or sha256_path(audit_path) != source["allocation_audit_sha256"]:
        raise AssertionError("A locked source artifact changed during evaluation")
    audit = {
        "status": STATUS,
        "diagnostic_contract_id": DIAGNOSTIC_CONTRACT_ID,
        "specification_id": spec["specification_id"],
        "specification_version": spec["specification_version"],
        "spec_sha256": spec_hash,
        "lock_sha256": lock_hash,
        "crop": crop,
        "source_panel_sha256": source["panel_sha256"],
        "source_allocation_audit_sha256": source["allocation_audit_sha256"],
        "source_basis_contract_id": SOURCE_CONTRACT_ID,
        "source_basis_allocation_order": SOURCE_ALLOCATION_ORDER,
        "source_basis_fit_authorized": False,
        "held_out_predictive_fit_authorized": True,
        "coefficient_export_authorized": False,
        "causal_interpretation_authorized": False,
        "production_model_selection_authorized": False,
        "response_draw_export_authorized": False,
        "scc_use_authorized": False,
        "coefficients_suppressed": True,
        "wet_day_threshold_mm": float(spec["construction"]["wet_day_threshold_mm"]),
        "wet_day_threshold_status": spec["construction"]["wet_day_threshold_status"],
        "stage_fractions": spec["construction"]["stage_fractions"],
        "stage_fraction_status": spec["construction"]["stage_fraction_status"],
        "algebraic_redundancy_rule": spec["construction"]["algebraic_redundancy_rule"],
        "validation_design": str(levels["validation_design"].iloc[0]),
        "nonspatial_split_contract": NONSPATIAL_SPLIT_CONTRACT,
        "models": list(models),
        "model_feature_counts": {name: len(features) for name, features in models.items()},
        "n_level_rows": int(len(levels)),
        "n_observed_level_rows": int(levels["yield_observed"].sum()),
        "n_consecutive_pairs": pair_count,
        "harvest_year_start": int(levels["harvest_year"].min()),
        "harvest_year_end": int(levels["harvest_year"].max()),
        "harvest_years": sorted(int(value) for value in levels["harvest_year"].unique()),
        "source_validation": source_summary,
        "results": results,
        "warning": (
            "These are coefficient-suppressed, first-difference held-out predictions. "
            "They do not identify causal rainfall effects, select a production model, "
            "estimate damages, or authorize an SCC input."
        ),
    }
    assert_coefficients_suppressed(audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop", required=True, choices=["mai", "soy"])
    parser.add_argument("--spec", type=Path, default=SPEC_DEFAULT)
    parser.add_argument("--lock", type=Path, default=LOCK_DEFAULT)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    audit = run_diagnostic(args.crop, args.spec, args.lock)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in audit.items() if key not in {"results", "source_validation"}},
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
