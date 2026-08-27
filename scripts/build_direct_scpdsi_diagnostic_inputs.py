#!/usr/bin/env python3
"""Build exact-support first-difference inputs for the direct/scPDSI diagnostic.

The three predictor/control views remain structurally separate. This builder
fits nothing and emits no coefficients, predictions, causal quantities,
damages, projections, or SCC values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype

from allocate_outcome_exposures import read_table, write_table
from validate_direct_scpdsi_common_support import validate_bundle as validate_common_bundle


CONTRACT_ID = "global_direct_scpdsi_predictive_diagnostic_v1"
HEAT_CONTRACT_ID = "global_crop_stage_heat_control_basis_v1"
KEYS = ["crop", "episode", "lat", "lon_360", "start_year", "end_year"]
OUTCOME = "delta_log_yield"
LEVEL_KEYS = ["harvest_year", "lat", "lon_360", "crop"]
DIRECT_FEATURES = [
    "direct__log1p_precip_mm",
    "direct__cdd_max_days",
    "direct__rx5day_mm",
]
SCPDSI_FEATURES = [
    "scpdsi__season_scpdsi_mean",
    "scpdsi__season_scpdsi_min",
    "scpdsi__season_scpdsi_fraction_at_or_below_threshold",
    "scpdsi__stage1_scpdsi_mean",
    "scpdsi__stage2_scpdsi_mean",
    "scpdsi__stage3_scpdsi_mean",
]
COMMON_OUTPUT_FEATURES = [
    "common__delta_stage1_tmean_c",
    "common__delta_stage2_tmean_c",
    "common__delta_stage3_tmean_c",
    "common__delta_stage1_heat_degree_days",
    "common__delta_stage2_heat_degree_days",
    "common__delta_stage3_heat_degree_days",
]
DIRECT_OUTPUT_FEATURES = ["direct__delta_log1p_precip_mm"]
SCPDSI_OUTPUT_FEATURES = [
    "scpdsi__delta_season_scpdsi_mean",
    "scpdsi__delta_season_scpdsi_min",
    "scpdsi__delta_season_scpdsi_fraction_at_or_below_threshold",
    "scpdsi__delta_stage1_scpdsi_mean",
    "scpdsi__delta_stage2_scpdsi_mean",
    "scpdsi__delta_stage3_scpdsi_mean",
]
FALSE_GATES = [
    "family_stacking_authorized",
    "coefficient_export_authorized",
    "causal_interpretation_authorized",
    "production_model_selection_authorized",
    "production_fit_authorized",
    "response_draw_authorized",
    "damage_calculation_authorized",
    "future_projection_authorized",
    "scc_authorized",
    "selection_by_scc_authorized",
]
MODEL_IDS = [
    "controls_only",
    "direct_quantity",
    "scpdsi_mean",
    "scpdsi_seasonal_summary",
    "scpdsi_stage_means",
]
HOLDOUT_IDS = [
    *(f"spatial_fold_{fold}" for fold in range(5)),
    "temporal_early_to_later_retrospective",
    "stress_direct_dry",
    "stress_direct_wet",
    "stress_scpdsi_drought",
    "stress_heat",
    "stress_union",
]
FORBIDDEN_HEAT_COLUMNS = re.compile(
    r"(^|_)(precip|rain|scpdsi|pdsi|spei|rx1|rx5|dry_spell|cdd_max)(_|$)",
    re.IGNORECASE,
)
ALLOWED_HEAT_FEATURE = re.compile(
    r"^stage[123]_(?:tmean_c|tmax_(?:29|30)c_(?:days|degree_days))$"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_path(config_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else config_path.resolve().parents[1] / path


def load_config(config_path: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    expected_top = {
        "schema_version", "contract_id", "description", "outcome", "estimator",
        "spatial_block_degrees", "spatial_fold_count", "stress_quantile",
        "scpdsi_drought_threshold", "direct_wet_day_threshold_mm",
        "scpdsi_calibration_period", "scpdsi_temporal_evaluation",
        "temporal_holdout_prospective", "spatial_validation_scope",
        "observation_weighting", "loss_metrics", "model_selection_rule",
        "diagnostic_fit_authorized", *FALSE_GATES,
        "pair_keys", "common_controls", "models", "crops", "episodes", "input_bundles",
    }
    if set(config) != expected_top:
        raise ValueError(
            f"Config schema differs: missing={sorted(expected_top-set(config))}, "
            f"extra={sorted(set(config)-expected_top)}"
        )
    if config["schema_version"] != 1 or config["contract_id"] != CONTRACT_ID:
        raise ValueError("Unexpected diagnostic config contract")
    if config["outcome"] != OUTCOME or config["estimator"] != "ols":
        raise ValueError("Only OLS on delta_log_yield is registered")
    if config["diagnostic_fit_authorized"] is not True:
        raise ValueError("Diagnostic fit authorization must be exactly true")
    for gate in FALSE_GATES:
        if config[gate] is not False:
            raise ValueError(f"Config {gate} must be exactly false")
    if config["pair_keys"] != KEYS or config["common_controls"] != COMMON_OUTPUT_FEATURES:
        raise ValueError("Config keys or common controls differ from the locked contract")
    if config["spatial_block_degrees"] != 5 or config["spatial_fold_count"] != 5:
        raise ValueError("The diagnostic requires five outcome-blind 5-degree folds")
    q = config["stress_quantile"]
    if type(q) not in (int, float) or float(q) != 0.95:
        raise ValueError("stress_quantile must be the locked outcome-blind 0.95 cutoff")
    if config["scpdsi_drought_threshold"] != -2.0:
        raise ValueError("The registered historical scPDSI drought threshold is -2")
    if config["direct_wet_day_threshold_mm"] != 1.0:
        raise ValueError("The registered direct-weather wet-day threshold is 1 mm")
    if config["scpdsi_calibration_period"] != "1901-2025" or config["scpdsi_temporal_evaluation"] != "retrospective_not_prospective_full_record_calibration":
        raise ValueError("The CRU scPDSI calibration and retrospective temporal-evaluation boundary must remain explicit")
    if config["temporal_holdout_prospective"] is not False:
        raise ValueError("The full-record calibrated scPDSI temporal holdout cannot be labeled prospective")
    if config["spatial_validation_scope"] != "hashed_5degree_blocks_unbuffered_adjacent_blocks_may_cross_folds":
        raise ValueError("The unbuffered spatial-validation scope must remain explicit")
    if config["observation_weighting"] != "equal_crop_grid_year_pair_weighting_not_area_production_or_welfare_weighted":
        raise ValueError("The diagnostic must disclose equal pair weighting")
    if config["loss_metrics"] != ["rmse", "mae", "r2"] or config["model_selection_rule"] != "none_nonproduction_diagnostic_reports_all_metrics":
        raise ValueError("The diagnostic reports all registered metrics and performs no production selection")

    models = config["models"]
    expected_models = {
        "controls_only": ("none", []),
        "direct_quantity": ("direct", DIRECT_OUTPUT_FEATURES),
        "scpdsi_mean": ("scpdsi", ["scpdsi__delta_season_scpdsi_mean"]),
        "scpdsi_seasonal_summary": (
            "scpdsi", SCPDSI_OUTPUT_FEATURES[:3],
        ),
        "scpdsi_stage_means": ("scpdsi", SCPDSI_OUTPUT_FEATURES[3:]),
    }
    if [model.get("id") for model in models] != MODEL_IDS:
        raise ValueError("Model registry or order differs from the locked contract")
    for model in models:
        if set(model) != {"id", "family", "candidate_features"}:
            raise ValueError("Model registry contains unknown or missing fields")
        declared_features = model["candidate_features"]
        if any(name.startswith("direct__") for name in declared_features) and any(
            name.startswith("scpdsi__") for name in declared_features
        ):
            raise ValueError("Family stacking is forbidden")
        family, features = expected_models[model["id"]]
        if model["family"] != family or model["candidate_features"] != features:
            raise ValueError(f"Model {model['id']} differs from its registered family/features")

    crops = config["crops"]
    if [crop.get("id") for crop in crops] != ["mai", "soy"]:
        raise ValueError("Crops must be exactly mai and soy")
    expected_heat = {
        "mai": (29, [
            "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c",
            "stage1_tmax_29c_degree_days", "stage2_tmax_29c_degree_days",
            "stage3_tmax_29c_degree_days",
        ]),
        "soy": (30, [
            "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c",
            "stage1_tmax_30c_degree_days", "stage2_tmax_30c_degree_days",
            "stage3_tmax_30c_degree_days",
        ]),
    }
    for crop in crops:
        if set(crop) != {"id", "heat_threshold_c", "heat_source_features"}:
            raise ValueError("Crop registry schema differs")
        if (crop["heat_threshold_c"], crop["heat_source_features"]) != expected_heat[crop["id"]]:
            raise ValueError(f"Crop {crop['id']} heat controls differ from the lock")

    episodes = config["episodes"]
    expected_episodes = [("early", 1982, 1989), ("later", 2012, 2016)]
    if [(e.get("id"), e.get("year_start"), e.get("year_end")) for e in episodes] != expected_episodes:
        raise ValueError("Episode registry differs or attempts cross-period pairing")
    for episode in episodes:
        if set(episode) != {"id", "year_start", "year_end"}:
            raise ValueError("Episode registry schema differs")
    bundles = config["input_bundles"]
    expected_pairs = {(crop, episode) for crop in ("mai", "soy") for episode in ("early", "later")}
    observed_pairs = {(b.get("crop"), b.get("episode")) for b in bundles}
    if len(bundles) != 4 or observed_pairs != expected_pairs:
        raise ValueError("Exactly one bundle per crop and episode is required")
    bundle_fields = {
        "crop", "episode", "direct_view", "scpdsi_view", "common_audit", "common_validation",
        "direct_candidate", "direct_allocation_audit", "direct_validation",
        "scpdsi_candidate", "scpdsi_allocation_audit", "scpdsi_validation",
        "heat_control", "heat_validation",
    }
    for bundle in bundles:
        if set(bundle) != bundle_fields:
            raise ValueError("Input-bundle schema differs")
        if not all(isinstance(bundle[field], str) and bundle[field] for field in bundle_fields):
            raise ValueError("Input-bundle fields must be nonblank strings")
    return config


def _require_exact_false(frame: pd.DataFrame, field: str, label: str) -> None:
    if field not in frame or not is_bool_dtype(frame[field].dtype) or frame[field].isna().any() or not frame[field].eq(False).all():
        raise ValueError(f"{label} {field} must be exactly false")


def _validate_heat(
    heat: pd.DataFrame,
    level: pd.DataFrame,
    direct_candidate: pd.DataFrame,
    crop: dict[str, Any],
    episode: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, int]]:
    label = f"Heat controls {crop['id']} {episode['id']}"
    metadata = ["heat_control_basis_contract_id", "source_role", "diagnostic_fit_authorized", *FALSE_GATES]
    required = LEVEL_KEYS + ["yield_observed", "yield_t_ha"] + crop["heat_source_features"] + metadata
    if missing := set(required) - set(heat.columns):
        raise ValueError(f"{label} missing locked heat-contract columns {sorted(missing)}")
    allowed_metadata = set(LEVEL_KEYS + ["yield_observed", "yield_t_ha"] + metadata)
    if unknown := sorted(
        name for name in heat.columns
        if name not in allowed_metadata and not ALLOWED_HEAT_FEATURE.fullmatch(name)
    ):
        raise ValueError(f"{label} contains unknown non-heat columns {unknown}")
    if heat.empty or heat.duplicated(LEVEL_KEYS).any() or heat[LEVEL_KEYS].isna().any().any():
        raise ValueError(f"{label} must have unique nonmissing crop-grid-year keys")
    if direct_candidate.empty or direct_candidate.duplicated(LEVEL_KEYS).any():
        raise ValueError(f"{label} direct-candidate reference has invalid keys")
    if any(FORBIDDEN_HEAT_COLUMNS.search(column) for column in heat.columns):
        raise ValueError(f"{label} contains moisture-family leakage")
    if set(heat["heat_control_basis_contract_id"].astype(str)) != {HEAT_CONTRACT_ID}:
        raise ValueError(f"{label} contract identity differs")
    if set(heat["source_role"].astype(str)) != {"common_nonmoisture_controls_only"}:
        raise ValueError(f"{label} source role differs")
    if not is_bool_dtype(heat["diagnostic_fit_authorized"].dtype) or not heat["diagnostic_fit_authorized"].eq(True).all():
        raise ValueError(f"{label} diagnostic_fit_authorized must be exactly true")
    for gate in FALSE_GATES:
        _require_exact_false(heat, gate, label)
    for name in crop["heat_source_features"]:
        if is_bool_dtype(heat[name].dtype) or not pd.api.types.is_numeric_dtype(heat[name].dtype):
            raise ValueError(f"{label} feature {name} must have a non-Boolean numeric dtype")
    if not np.isfinite(heat[crop["heat_source_features"]].to_numpy(dtype=float)).all():
        raise ValueError(f"{label} controls must be finite")
    if (heat[crop["heat_source_features"][3:]].to_numpy(dtype=float) < 0).any():
        raise ValueError(f"{label} heat degree days cannot be negative")
    ordered = heat.sort_values(LEVEL_KEYS, kind="mergesort").reset_index(drop=True)
    reference = level.sort_values(LEVEL_KEYS, kind="mergesort").reset_index(drop=True)
    temperature_controls = crop["heat_source_features"][:3]
    direct_reference = direct_candidate[
        LEVEL_KEYS + ["yield_observed", "yield_t_ha", *temperature_controls]
    ].sort_values(LEVEL_KEYS, kind="mergesort").reset_index(drop=True)
    heat_against_direct = ordered.merge(
        direct_reference, on=LEVEL_KEYS, how="left", validate="one_to_one",
        indicator=True, suffixes=("_heat", "_direct"),
    )
    if not heat_against_direct["_merge"].eq("both").all():
        raise ValueError(f"{label} contains keys outside its direct-candidate basis")
    if not np.array_equal(
        heat_against_direct["yield_observed_heat"], heat_against_direct["yield_observed_direct"]
    ) or not np.array_equal(
        heat_against_direct["yield_t_ha_heat"].to_numpy(float),
        heat_against_direct["yield_t_ha_direct"].to_numpy(float), equal_nan=True,
    ):
        raise ValueError(f"{label} outcomes differ from its direct-candidate basis")
    for name in temperature_controls:
        if not np.array_equal(
            heat_against_direct[f"{name}_heat"].to_numpy(dtype=float),
            heat_against_direct[f"{name}_direct"].to_numpy(dtype=float),
        ):
            raise ValueError(f"{label} {name} differs from its direct-candidate basis")
    selected = reference[LEVEL_KEYS].merge(
        ordered, on=LEVEL_KEYS, how="left", validate="one_to_one", indicator=True
    )
    if not selected["_merge"].eq("both").all():
        raise ValueError(f"{label} does not cover every common-bundle level key")
    selected = selected.drop(columns="_merge")
    if not np.array_equal(selected["yield_observed"], reference["yield_observed"]):
        raise ValueError(f"{label} yield_observed differs from the common bundle")
    if not np.array_equal(
        selected["yield_t_ha"].to_numpy(float), reference["yield_t_ha"].to_numpy(float), equal_nan=True
    ):
        raise ValueError(f"{label} yield_t_ha differs from the common bundle")
    if set(ordered["crop"].astype(str)) != {crop["id"]}:
        raise ValueError(f"{label} crop identity differs")
    years = ordered["harvest_year"].astype(int)
    if years.min() < episode["year_start"] or years.max() > episode["year_end"]:
        raise ValueError(f"{label} contains years outside its locked episode")
    return selected, {
        "direct_candidate_rows": int(len(direct_reference)),
        "heat_source_rows": int(len(ordered)),
        "direct_candidate_rows_without_heat": int(len(direct_reference) - len(ordered)),
        "common_support_rows": int(len(selected)),
        "heat_only_rows_excluded": int(len(ordered) - len(selected)),
    }


def _load_receipt(path: Path, label: str) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"{label} is not a readable JSON receipt") from error
    if not isinstance(receipt, dict) or not isinstance(receipt.get("status"), str) or not receipt["status"].startswith("validated"):
        raise ValueError(f"{label} does not carry a validated status")
    for name, value in receipt.items():
        if name.endswith("_authorized") and value is not False and name != "diagnostic_fit_authorized":
            raise ValueError(f"{label} {name} must be exactly false")
    return receipt


def _validate_bound_receipts(
    paths: dict[str, Path], crop: dict[str, Any], episode: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    try:
        direct_audit = json.loads(paths["direct_allocation_audit"].read_text(encoding="utf-8"))
        scpdsi_audit = json.loads(paths["scpdsi_allocation_audit"].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError("A family allocation audit is not readable JSON") from error
    if not isinstance(direct_audit, dict) or not isinstance(scpdsi_audit, dict):
        raise ValueError("Family allocation audits must be JSON objects")

    direct = _load_receipt(paths["direct_validation"], "Direct validation receipt")
    if direct.get("response_basis_contract_id") != "gdhy_aggregate_irrigation_distribution_candidate_v1" or direct.get("crop") != crop["id"]:
        raise ValueError("Direct validation receipt contract or crop differs")
    if direct.get("fit_authorized") is not False or direct.get("scc_authorized") is not False:
        raise ValueError("Direct validation receipt authorization differs")
    direct_candidate_hash = sha256_file(paths["direct_candidate"])
    direct_audit_hash = sha256_file(paths["direct_allocation_audit"])
    if (
        direct.get("candidate_sha256") != direct_candidate_hash
        or direct.get("allocation_audit_sha256") != direct_audit_hash
        or direct_audit.get("candidate_sha256") != direct_candidate_hash
    ):
        raise ValueError("Direct validation receipt or allocation audit is not hash-bound to the candidate")
    if (
        direct.get("wet_day_threshold_mm") != config["direct_wet_day_threshold_mm"]
        or direct_audit.get("wet_day_threshold_mm") != config["direct_wet_day_threshold_mm"]
    ):
        raise ValueError("Direct wet-day threshold differs from the locked 1 mm definition")

    scpdsi = _load_receipt(paths["scpdsi_validation"], "scPDSI validation receipt")
    if scpdsi.get("response_basis_contract_id") != "gdhy_aggregate_irrigation_scpdsi_candidate_v1" or scpdsi.get("crop") != crop["id"]:
        raise ValueError("scPDSI validation receipt contract or crop differs")
    if scpdsi.get("candidate_sha256") != sha256_file(paths["scpdsi_candidate"]):
        raise ValueError("scPDSI validation receipt does not bind the candidate hash")
    if scpdsi.get("allocation_audit_sha256") != sha256_file(paths["scpdsi_allocation_audit"]):
        raise ValueError("scPDSI validation receipt does not bind the allocation-audit hash")
    if (
        scpdsi.get("scpdsi_threshold") != config["scpdsi_drought_threshold"]
        or scpdsi_audit.get("scpdsi_threshold") != config["scpdsi_drought_threshold"]
    ):
        raise ValueError("scPDSI candidate threshold differs from the locked -2 definition")
    if scpdsi.get("raw_source_and_calendar_manifest_chain_passed") is not True or scpdsi.get("full_raw_metric_recomputation_passed") is not False:
        raise ValueError("scPDSI validation receipt overstates or omits its source-chain boundary")

    common = _load_receipt(paths["common_validation"], "Common-support validation receipt")
    if common.get("contract_id") != "global_direct_scpdsi_common_support_v1":
        raise ValueError("Common-support validation receipt contract differs")
    for field in ("input_sha256_verified", "output_sha256_verified", "immediate_input_recomputation_passed"):
        if common.get(field) is not True:
            raise ValueError(f"Common-support validation receipt {field} must be exactly true")

    heat = _load_receipt(paths["heat_validation"], "Heat validation receipt")
    required_heat_fields = {
        "schema_version", "status", "heat_control_basis_contract_id", "crop",
        "harvest_year_start", "harvest_year_end", "heat_control_sha256", "source_role",
        "diagnostic_fit_authorized", "immediate_input_recomputation_passed",
        "raw_source_recomputation_performed", "source_files_sha256", *FALSE_GATES,
    }
    optional_heat_fields = {
        "season_stage_reconciliation_receipt_sha256",
    }
    if not required_heat_fields.issubset(heat) or set(heat) - required_heat_fields - optional_heat_fields:
        raise ValueError("Heat validation receipt schema differs from the locked contract")
    if (
        heat["schema_version"] != 1
        or heat["status"] != "validated_common_nonmoisture_heat_control_basis"
        or heat["heat_control_basis_contract_id"] != HEAT_CONTRACT_ID
        or heat["crop"] != crop["id"]
        or heat["harvest_year_start"] != episode["year_start"]
        or heat["harvest_year_end"] != episode["year_end"]
        or heat["heat_control_sha256"] != sha256_file(paths["heat_control"])
        or heat["source_role"] != "common_nonmoisture_controls_only"
        or heat["diagnostic_fit_authorized"] is not True
    ):
        raise ValueError("Heat validation receipt identity, source role, period, or hash differs")
    for gate in FALSE_GATES:
        if heat[gate] is not False:
            raise ValueError(f"Heat validation receipt {gate} must be exactly false")
    if heat["immediate_input_recomputation_passed"] is not True:
        raise ValueError("Heat validation receipt immediate-input recomputation must be true")
    if heat["raw_source_recomputation_performed"] is not False:
        raise ValueError("Heat validation receipt must not overstate raw-source recomputation")
    if (
        not isinstance(heat["source_files_sha256"], dict)
        or not heat["source_files_sha256"]
        or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in heat["source_files_sha256"].values())
    ):
        raise ValueError("Heat validation receipt source-file hash registry is invalid")
    if "season_stage_reconciliation_receipt_sha256" in heat and not re.fullmatch(
        r"[0-9a-f]{64}", str(heat["season_stage_reconciliation_receipt_sha256"])
    ):
        raise ValueError("Heat validation receipt reconciliation hash is invalid")

    direct_panel_hashes = direct_audit.get("input_panel_sha256")
    scpdsi_panel_hashes = scpdsi.get("input_panel_sha256")
    heat_sources = heat["source_files_sha256"]
    heat_panel_hashes = [
        heat_sources.get("direct_panel_noirr"),
        heat_sources.get("direct_panel_firr"),
    ]
    if (
        direct_audit.get("irrigation_labels") != ["noirr", "firr"]
        or scpdsi_audit.get("irrigation_labels") != ["noirr", "firr"]
        or not isinstance(direct_panel_hashes, list)
        or len(direct_panel_hashes) != 2
        or direct_panel_hashes != scpdsi_panel_hashes
        or direct_panel_hashes != heat_panel_hashes
    ):
        raise ValueError("Direct, scPDSI, and heat families do not share exact panel lineage")
    direct_weight_hash = direct_audit.get("weight_file_sha256")
    if (
        not isinstance(direct_weight_hash, str)
        or direct_weight_hash != scpdsi.get("weight_file_sha256")
        or direct_weight_hash != heat_sources.get("fixed_area_weights")
    ):
        raise ValueError("Direct, scPDSI, and heat families do not share exact fixed-weight lineage")
    return {
        "direct": direct,
        "scpdsi": scpdsi,
        "common_support": common,
        "heat": heat,
        "cross_family_panel_and_weight_lineage_passed": True,
    }


def _pair_episode(
    direct: pd.DataFrame,
    scpdsi: pd.DataFrame,
    heat: pd.DataFrame,
    crop: dict[str, Any],
    episode: dict[str, Any],
) -> pd.DataFrame:
    if not direct[LEVEL_KEYS + ["yield_observed", "yield_t_ha"]].equals(
        scpdsi[LEVEL_KEYS + ["yield_observed", "yield_t_ha"]]
    ):
        raise ValueError("Direct and scPDSI common views have unequal keys/outcomes")
    required_direct = set(DIRECT_FEATURES)
    required_scpdsi = set(SCPDSI_FEATURES)
    if missing := required_direct - set(direct):
        raise ValueError(f"Direct view missing diagnostic features {sorted(missing)}")
    if missing := required_scpdsi - set(scpdsi):
        raise ValueError(f"scPDSI view missing diagnostic features {sorted(missing)}")
    base = direct[LEVEL_KEYS + ["yield_observed", "yield_t_ha"] + DIRECT_FEATURES].merge(
        scpdsi[LEVEL_KEYS + SCPDSI_FEATURES], on=LEVEL_KEYS, validate="one_to_one"
    )
    heat_features = crop["heat_source_features"]
    base = base.merge(heat[LEVEL_KEYS + heat_features], on=LEVEL_KEYS, validate="one_to_one")
    base = base.loc[base["yield_observed"]].copy()
    if base.empty or (base["yield_t_ha"] <= 0).any() or not np.isfinite(base["yield_t_ha"]).all():
        raise ValueError("Observed outcomes must be finite and positive")
    numeric = DIRECT_FEATURES + SCPDSI_FEATURES + heat_features
    if not np.isfinite(base[numeric].to_numpy(dtype=float)).all():
        raise ValueError("All registered diagnostic inputs must be finite on exact support")
    base = base.sort_values(["crop", "lat", "lon_360", "harvest_year"], kind="mergesort")
    groups = base.groupby(["crop", "lat", "lon_360"], observed=True, sort=False)
    end = base.copy()
    for column in ["harvest_year", "yield_t_ha", *numeric]:
        end[f"start__{column}"] = groups[column].shift(1)
    end = end.loc[end["harvest_year"].eq(end["start__harvest_year"] + 1)].copy()
    if end.empty:
        raise ValueError(f"No consecutive observed outcome pairs for {crop['id']} {episode['id']}")
    if end["start__harvest_year"].min() < episode["year_start"] or end["harvest_year"].max() > episode["year_end"]:
        raise ValueError("Cross-period first-difference pairing attempt")
    out = pd.DataFrame({
        "crop": end["crop"].astype(str),
        "episode": episode["id"],
        "lat": end["lat"].astype(float),
        "lon_360": end["lon_360"].astype(float),
        "start_year": end["start__harvest_year"].astype(int),
        "end_year": end["harvest_year"].astype(int),
        OUTCOME: np.log(end["yield_t_ha"].astype(float)) - np.log(end["start__yield_t_ha"].astype(float)),
    })
    out["direct__delta_log1p_precip_mm"] = end["direct__log1p_precip_mm"] - end["start__direct__log1p_precip_mm"]
    for source in SCPDSI_FEATURES:
        name = "scpdsi__delta_" + source.removeprefix("scpdsi__")
        out[name] = end[source] - end[f"start__{source}"]
    for stage in range(1, 4):
        tmean = f"stage{stage}_tmean_c"
        heat_dd = heat_features[stage + 2]
        out[f"common__delta_stage{stage}_tmean_c"] = end[tmean] - end[f"start__{tmean}"]
        out[f"common__delta_stage{stage}_heat_degree_days"] = end[heat_dd] - end[f"start__{heat_dd}"]
    out["_stress_direct_dry_score"] = np.maximum(
        end["direct__cdd_max_days"], end["start__direct__cdd_max_days"]
    )
    out["_stress_direct_wet_score"] = np.maximum(
        end["direct__rx5day_mm"], end["start__direct__rx5day_mm"]
    )
    out["_stress_scpdsi_score"] = np.minimum(
        end["scpdsi__season_scpdsi_mean"], end["start__scpdsi__season_scpdsi_mean"]
    )
    heat_total_end = sum(end[name] for name in heat_features[3:])
    heat_total_start = sum(end[f"start__{name}"] for name in heat_features[3:])
    out["_stress_heat_score"] = np.maximum(heat_total_end, heat_total_start)
    return out.reset_index(drop=True)


def _block_fold(crop: str, lat: float, lon: float) -> tuple[str, int]:
    lat_bin = int(np.floor((lat + 90.0) / 5.0))
    lon_bin = int(np.floor(lon / 5.0))
    block = f"{lat_bin}:{lon_bin}"
    token = f"{crop}|{block}".encode("utf-8")
    return block, int.from_bytes(hashlib.sha256(token).digest()[:8], "big") % 5


def compute_outcome_blind_stress_plan(features: pd.DataFrame, quantile: float, threshold: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create stress flags using keys/exposures only; outcome columns are rejected."""
    if any("yield" in name.lower() or name == OUTCOME for name in features.columns):
        raise ValueError("Outcome-blind stress planning cannot receive an outcome column")
    needed = set(KEYS + [
        "_stress_direct_dry_score", "_stress_direct_wet_score",
        "_stress_scpdsi_score", "_stress_heat_score",
    ])
    if missing := needed - set(features):
        raise ValueError(f"Stress planning missing fields {sorted(missing)}")
    plan = features[KEYS].copy()
    for field in ("stress_direct_dry", "stress_direct_wet", "stress_scpdsi_drought", "stress_heat"):
        plan[field] = False
    cutoff_by_crop: dict[str, dict[str, float]] = {}
    observed_crops = sorted(features["crop"].astype(str).unique())
    if observed_crops != ["mai", "soy"]:
        raise ValueError("Stress planning requires exact maize and soybean support")
    for crop in observed_crops:
        crop_rows = features["crop"].eq(crop)
        early = features.loc[crop_rows & features["episode"].eq("early")]
        if early.empty:
            raise ValueError(f"Stress cutoffs require early-episode feature support for {crop}")
        cutoffs = {
            "direct_dry": float(early["_stress_direct_dry_score"].quantile(quantile)),
            "direct_wet": float(early["_stress_direct_wet_score"].quantile(quantile)),
            "scpdsi_drought": float(threshold),
            "heat": float(early["_stress_heat_score"].quantile(quantile)),
        }
        cutoff_by_crop[crop] = cutoffs
        plan.loc[crop_rows, "stress_direct_dry"] = features.loc[crop_rows, "_stress_direct_dry_score"].ge(cutoffs["direct_dry"])
        plan.loc[crop_rows, "stress_direct_wet"] = features.loc[crop_rows, "_stress_direct_wet_score"].ge(cutoffs["direct_wet"])
        plan.loc[crop_rows, "stress_scpdsi_drought"] = features.loc[crop_rows, "_stress_scpdsi_score"].le(cutoffs["scpdsi_drought"])
        plan.loc[crop_rows, "stress_heat"] = features.loc[crop_rows, "_stress_heat_score"].ge(cutoffs["heat"])
    components = ["stress_direct_dry", "stress_direct_wet", "stress_scpdsi_drought", "stress_heat"]
    plan["stress_union"] = plan[components].any(axis=1)
    return plan, {
        "cutoff_training_episode": "early",
        "cutoff_scope": "crop_specific",
        "quantile": float(quantile),
        "values_by_crop": cutoff_by_crop,
    }


def _endpoint_id(frame: pd.DataFrame, year: str) -> pd.Series:
    return (
        frame["crop"].astype(str) + "|" + frame["lat"].map(lambda v: format(float(v), ".10g"))
        + "|" + frame["lon_360"].map(lambda v: format(float(v), ".10g"))
        + "|" + frame[year].astype(int).astype(str)
    )


def _add_contract_fields(frame: pd.DataFrame, view: str) -> pd.DataFrame:
    result = frame.copy()
    result["diagnostic_contract_id"] = CONTRACT_ID
    result["diagnostic_view"] = view
    result["family_mutually_exclusive"] = True
    result["families_stacked"] = False
    result["coefficients_emitted"] = False
    result["predictions_emitted"] = False
    result["diagnostic_fit_authorized"] = True
    for gate in FALSE_GATES:
        result[gate] = False
    return result


def assemble_diagnostic_inputs(config_path: Path) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    config = load_config(config_path)
    crops = {crop["id"]: crop for crop in config["crops"]}
    episodes = {episode["id"]: episode for episode in config["episodes"]}
    pairs: list[pd.DataFrame] = []
    input_records: list[dict[str, Any]] = []
    for spec in sorted(config["input_bundles"], key=lambda b: (b["crop"], b["episode"])):
        paths = {name: _canonical_path(config_path, spec[name]) for name in (
            "direct_view", "scpdsi_view", "common_audit", "common_validation",
            "direct_candidate", "direct_allocation_audit", "direct_validation",
            "scpdsi_candidate", "scpdsi_allocation_audit", "scpdsi_validation",
            "heat_control", "heat_validation",
        )}
        missing = [str(path) for path in paths.values() if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Required diagnostic inputs are absent: {missing}")
        common_validation = validate_common_bundle(
            paths["direct_view"], paths["scpdsi_view"], paths["common_audit"],
            paths["direct_candidate"], paths["scpdsi_candidate"],
        )
        bound_receipts = _validate_bound_receipts(
            paths, crops[spec["crop"]], episodes[spec["episode"]], config
        )
        direct = read_table(paths["direct_view"])
        scpdsi = read_table(paths["scpdsi_view"])
        heat, heat_support = _validate_heat(
            read_table(paths["heat_control"]), direct,
            read_table(paths["direct_candidate"]),
            crops[spec["crop"]], episodes[spec["episode"]],
        )
        pairs.append(_pair_episode(direct, scpdsi, heat, crops[spec["crop"]], episodes[spec["episode"]]))
        input_records.append({
            "crop": spec["crop"], "episode": spec["episode"],
            "common_bundle_revalidated": True,
            "common_bundle_validation": common_validation,
            "bound_validation_receipts": bound_receipts,
            "heat_common_support_selection": heat_support,
            "files": {name: {"path": str(path), "sha256": sha256_file(path)} for name, path in paths.items()},
        })
    all_pairs = pd.concat(pairs, ignore_index=True).sort_values(KEYS, kind="mergesort").reset_index(drop=True)
    if all_pairs.duplicated(KEYS).any() or not np.isfinite(all_pairs[[OUTCOME, *DIRECT_OUTPUT_FEATURES, *SCPDSI_OUTPUT_FEATURES, *COMMON_OUTPUT_FEATURES]].to_numpy(float)).all():
        raise ValueError("Combined pair support is duplicate or nonfinite")
    if not all_pairs["end_year"].eq(all_pairs["start_year"] + 1).all():
        raise ValueError("Cross-period or nonconsecutive first-difference pairing attempt")

    stress_input = all_pairs[KEYS + [name for name in all_pairs if name.startswith("_stress_")]].copy()
    stress, cutoff_audit = compute_outcome_blind_stress_plan(
        stress_input, float(config["stress_quantile"]), float(config["scpdsi_drought_threshold"])
    )
    split = all_pairs[KEYS + [OUTCOME]].copy()
    block_folds = [_block_fold(crop, lat, lon) for crop, lat, lon in zip(split.crop, split.lat, split.lon_360)]
    split["spatial_block_5deg"] = [value[0] for value in block_folds]
    split["spatial_fold"] = [value[1] for value in block_folds]
    split["temporal_role"] = np.where(split["episode"].eq("early"), "train", "test")
    split = split.merge(stress, on=KEYS, validate="one_to_one")
    split["start_endpoint_id"] = _endpoint_id(split, "start_year")
    split["end_endpoint_id"] = _endpoint_id(split, "end_year")
    for stress_name in ("direct_dry", "direct_wet", "scpdsi_drought", "heat", "union"):
        flag = f"stress_{stress_name}"
        test_endpoints = set(split.loc[split[flag], "start_endpoint_id"]) | set(split.loc[split[flag], "end_endpoint_id"])
        shares = split["start_endpoint_id"].isin(test_endpoints) | split["end_endpoint_id"].isin(test_endpoints)
        split[f"train_eligible_{flag}"] = ~shares
        if (split.loc[split[f"train_eligible_{flag}"], ["start_endpoint_id", "end_endpoint_id"]].isin(test_endpoints)).any().any():
            raise AssertionError("Endpoint purge failed")

    core = all_pairs[KEYS + [OUTCOME]]
    views = {
        "direct": _add_contract_fields(pd.concat([core, all_pairs[DIRECT_OUTPUT_FEATURES]], axis=1), "direct_quantity"),
        "scpdsi": _add_contract_fields(pd.concat([core, all_pairs[SCPDSI_OUTPUT_FEATURES]], axis=1), "historical_scpdsi"),
        "common": _add_contract_fields(pd.concat([core, all_pairs[COMMON_OUTPUT_FEATURES]], axis=1), "common_heat_temperature_controls"),
        "split": _add_contract_fields(split, "outcome_blind_outer_split_plan"),
    }
    prevalence = {
        crop: {
            episode: {
                flag: {
                    "count": int(group[flag].sum()),
                    "prevalence": float(group[flag].mean()),
                }
                for flag in ["stress_direct_dry", "stress_direct_wet", "stress_scpdsi_drought", "stress_heat", "stress_union"]
            }
            for episode, group in crop_group.groupby("episode", observed=True, sort=True)
        }
        for crop, crop_group in split.groupby("crop", observed=True, sort=True)
    }
    audit = {
        "schema_version": 1, "contract_id": CONTRACT_ID,
        "config_file": str(config_path), "config_sha256": sha256_file(config_path),
        "input_bundles": input_records,
        "pair_keys": KEYS, "outcome": OUTCOME, "pair_rows": int(len(all_pairs)),
        "pair_rows_by_crop_episode": {
            f"{crop}:{episode}": int(len(group))
            for (crop, episode), group in all_pairs.groupby(["crop", "episode"], observed=True, sort=True)
        },
        "exact_pair_support_all_models": True,
        "cross_period_pairs_formed": False,
        "first_differences_only": True,
        "common_controls": COMMON_OUTPUT_FEATURES,
        "model_registry": config["models"],
        "holdout_registry": HOLDOUT_IDS,
        "stress_cutoffs": cutoff_audit,
        "stress_prevalence": prevalence,
        "spatial_fold_algorithm": "sha256(crop|5-degree-lat-lon-block) mod 5; outcome blind",
        "centering_scaling_rule": "training_rows_only",
        "observation_weighting": config["observation_weighting"],
        "loss_metrics": config["loss_metrics"],
        "model_selection_rule": config["model_selection_rule"],
        "spatial_validation_scope": config["spatial_validation_scope"],
        "scpdsi_calibration_period": config["scpdsi_calibration_period"],
        "scpdsi_temporal_evaluation": config["scpdsi_temporal_evaluation"],
        "temporal_holdout_prospective": config["temporal_holdout_prospective"],
        "endpoint_purge_required": True,
        "views_emitted_separately": True,
        "validation_receipts_hash_bound": True,
        "raw_source_recomputation_performed": False,
        "family_mutually_exclusive": True,
        "families_stacked": False,
        "coefficients_emitted": False,
        "predictions_emitted": False,
        "diagnostic_fit_authorized": True,
        **{gate: False for gate in FALSE_GATES},
    }
    return views, audit


def build_inputs(config_path: Path, output_dir: Path, audit_path: Path) -> dict[str, Any]:
    paths = {name: output_dir / f"{name}_view.parquet" for name in ("direct", "scpdsi", "common", "split")}
    if len({p.resolve() for p in [config_path, audit_path, *paths.values()]}) != 6:
        raise ValueError("Config, audit, and output paths must be distinct")
    views, audit = assemble_diagnostic_inputs(config_path)
    for name, frame in views.items():
        write_table(frame, paths[name])
    audit["output_files"] = {
        name: {"path": str(path), "sha256": sha256_file(path)} for name, path in paths.items()
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    audit = build_inputs(Path(args.config), Path(args.output_dir), Path(args.audit_out))
    print(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
