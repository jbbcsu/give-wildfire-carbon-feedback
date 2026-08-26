#!/usr/bin/env python3
"""Estimate locked direct-practice precipitation fixed-effects associations."""
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

from estimate_us_national_all_practice_pdsi_association import (
    alternating_residualize,
    clustered_ols,
)


PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT / "us_county_validation/us_direct_practice_precipitation_association_v1.toml"
ESTIMATION_PRIMITIVES = Path(__file__).with_name("estimate_us_national_all_practice_pdsi_association.py")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("configured paths must be project-relative")
    resolved = (PROJECT / path).resolve()
    resolved.relative_to(PROJECT.resolve())
    return resolved


def load_config(path: Path) -> dict[str, Any]:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if config.get("analysis_id") != "us_direct_practice_precipitation_association_v1":
        raise ValueError("wrong precipitation-association contract")
    if config.get("analysis_role") != "historical_fixed_effects_association_only":
        raise ValueError("analysis role changed")
    if config.get("association_fit_authorized") is not True:
        raise ValueError("association fit is not authorized")
    for gate in ("causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized"):
        if config.get(gate) is not False:
            raise ValueError(f"contract unexpectedly opens {gate}")
    models = config["models"]
    if models["fixed_effects"] != ["county_geoid", "state_by_harvest_year"]:
        raise ValueError("fixed effects changed")
    if models["forms"] != ["quantity", "quantity_timing"]:
        raise ValueError("model family changed")
    if models["timing_features"] != ["stage1_precip_share", "stage2_precip_share"]:
        raise ValueError("timing parameterization changed")
    return config


def validate_panel(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, object]]:
    spec = config["input"]
    path = project_path(spec["panel"])
    receipt_path = project_path(spec["source_receipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    actual_hash = sha256(path)
    if actual_hash != spec["expected_panel_sha256"]:
        raise ValueError("direct-weather panel hash differs from contract")
    if receipt.get("candidate", {}).get("sha256") != actual_hash:
        raise ValueError("direct-weather source receipt does not bind panel")
    if receipt.get("status") != "validated_us_competing_moisture_source_input":
        raise ValueError("direct-weather source receipt status changed")
    frame = pd.read_parquet(path)
    frame = frame.loc[
        frame.outcome_crop.astype(str).isin(map(str, spec["crops"]))
        & frame.irrigation_practice.astype(str).isin(map(str, spec["practices"]))
        & frame.harvest_year.between(int(spec["year_min"]), int(spec["year_max"]))
    ].copy()
    keys = ["county_geoid", "outcome_crop", "irrigation_practice", "harvest_year"]
    if frame.empty or frame.duplicated(keys).any():
        raise ValueError("direct-practice analysis panel is empty or has duplicate keys")
    if set(frame.outcome_source_id.astype(str)) != {str(spec["outcome_source_id"])}:
        raise ValueError("outcome source changed")
    if set(frame.weather_source_id.astype(str)) != {str(spec["weather_source_id"])}:
        raise ValueError("weather source changed")
    if set(frame.calendar_role.astype(str)) != {str(spec["calendar_role"])}:
        raise ValueError("calendar role changed")
    for gate in ("response_estimation_authorized", "scc_authorized"):
        if frame[gate].fillna(True).astype(bool).any():
            raise ValueError(f"upstream construction artifact unexpectedly opens {gate}")
    numeric = [
        "yield_bu_acre", "precip_mm", "stage1_precip_share", "stage2_precip_share",
        "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c",
    ]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="raise")
    if (frame.yield_bu_acre <= 0).any() or not np.isfinite(frame[numeric]).all().all():
        raise ValueError("analysis variables are nonpositive or nonfinite")
    if ((frame.stage1_precip_share < 0) | (frame.stage2_precip_share < 0)).any():
        raise ValueError("precipitation shares are negative")
    if (frame.stage1_precip_share + frame.stage2_precip_share > 1 + 1e-8).any():
        raise ValueError("precipitation shares exceed the simplex")
    frame["log_yield"] = np.log(frame.yield_bu_acre)
    return frame, {"path": spec["panel"], "sha256": actual_hash, "rows": int(len(frame))}


def raw_design(frame: pd.DataFrame, form: str, config: dict[str, Any]) -> tuple[np.ndarray, list[str]]:
    models = config["models"]
    columns: list[np.ndarray] = []
    names: list[str] = []
    for feature in models["heat_controls"]:
        value = frame[feature].to_numpy(dtype=float)
        columns.extend([value, np.square(value)])
        names.extend([feature, f"{feature}_squared"])
    scale = float(models["quantity_scale_mm"])
    precipitation = frame[models["quantity_feature"]].to_numpy(dtype=float) / scale
    columns.extend([precipitation, np.square(precipitation)])
    names.extend(["precipitation_per_100mm", "precipitation_per_100mm_squared"])
    if form == "quantity_timing":
        for feature in models["timing_features"]:
            columns.append(frame[feature].to_numpy(dtype=float))
            names.append(feature)
    elif form != "quantity":
        raise ValueError(f"unknown model form: {form}")
    return np.column_stack(columns), names


def contrast_summary(
    frame: pd.DataFrame,
    form: str,
    names: list[str],
    beta: np.ndarray,
    covariance: np.ndarray,
    config: dict[str, Any],
) -> dict[str, object]:
    contrasts = config["contrasts"]
    scale = float(config["models"]["quantity_scale_mm"])
    increment = float(contrasts["quantity_increment_mm"]) / scale
    p_index = names.index("precipitation_per_100mm")
    p2_index = names.index("precipitation_per_100mm_squared")
    quantiles = frame.precip_mm.quantile(contrasts["quantity_reference_percentiles"])
    quantity = []
    for percentile, reference_mm in quantiles.items():
        reference = float(reference_mm) / scale
        gradient = np.zeros(len(beta))
        gradient[p_index] = increment
        gradient[p2_index] = (reference + increment) ** 2 - reference**2
        delta_log = float(gradient @ beta)
        standard_error = float(np.sqrt(max(gradient @ covariance @ gradient, 0.0)))
        low_log, high_log = delta_log - 1.96 * standard_error, delta_log + 1.96 * standard_error
        quantity.append({
            "reference_percentile": float(percentile),
            "reference_precipitation_mm": float(reference_mm),
            "increment_mm": float(contrasts["quantity_increment_mm"]),
            "fitted_log_yield_difference": float(delta_log),
            "standard_error_cluster_county_log_difference": standard_error,
            "ci95_normal_log_difference": [low_log, high_log],
            "fitted_percent_yield_difference": float(100 * math.expm1(delta_log)),
            "ci95_normal_percent_yield_difference": [
                float(100 * math.expm1(low_log)), float(100 * math.expm1(high_log))
            ],
        })
    result: dict[str, object] = {"quantity_increment_contrasts": quantity}
    if form == "quantity_timing":
        share = float(contrasts["timing_shift_share"])
        delta_log = beta[names.index("stage2_precip_share")] * share
        gradient = np.zeros(len(beta))
        gradient[names.index("stage2_precip_share")] = share
        standard_error = float(np.sqrt(max(gradient @ covariance @ gradient, 0.0)))
        low_log, high_log = delta_log - 1.96 * standard_error, delta_log + 1.96 * standard_error
        result["stage3_to_stage2_shift"] = {
            "shift_share": share,
            "fitted_log_yield_difference": float(delta_log),
            "standard_error_cluster_county_log_difference": standard_error,
            "ci95_normal_log_difference": [low_log, high_log],
            "fitted_percent_yield_difference": float(100 * math.expm1(delta_log)),
            "ci95_normal_percent_yield_difference": [
                float(100 * math.expm1(low_log)), float(100 * math.expm1(high_log))
            ],
            "partial_contrast_warning": "holds total rain, stage1 share, heat, and registered regressors fixed; does not update correlated dry-spell or heavy-rain metrics",
        }
    return result


def estimate(frame: pd.DataFrame, crop: str, practice: str, form: str, config: dict[str, Any]) -> dict[str, object]:
    subset = frame.loc[
        frame.outcome_crop.eq(crop) & frame.irrigation_practice.eq(practice)
    ].copy()
    models = config["models"]
    if len(subset) < int(models["minimum_rows"]) or subset.county_geoid.nunique() < int(models["minimum_counties"]):
        raise ValueError(f"sample gate failed for {crop}/{practice}")
    county_codes, _ = pd.factorize(subset.county_geoid.astype(str), sort=True)
    state_year_codes, _ = pd.factorize(
        subset.state.astype(str) + "_" + subset.harvest_year.astype(str), sort=True
    )
    x_raw, names = raw_design(subset, form, config)
    stacked = np.column_stack([subset.log_yield.to_numpy(dtype=float), x_raw])
    residualized, iterations, final_change = alternating_residualize(
        stacked,
        [county_codes, state_year_codes],
        float(models["demeaning_tolerance"]),
        int(models["demeaning_max_iterations"]),
    )
    y, x = residualized[:, 0], residualized[:, 1:]
    if np.any(x.std(axis=0, ddof=0) <= float(models["minimum_within_standard_deviation"])):
        raise ValueError("residualized predictor is effectively constant")
    fit = clustered_ols(y, x, subset.county_geoid.to_numpy())
    coefficients = []
    for index, name in enumerate(names):
        estimate_value = float(fit["beta"][index])
        standard_error = float(fit["standard_error_cluster_county"][index])
        coefficients.append({
            "term": name,
            "estimate": estimate_value,
            "standard_error_cluster_county": standard_error,
            "ci95_normal": [estimate_value - 1.96 * standard_error, estimate_value + 1.96 * standard_error],
            "normal_approx_p_value": float(fit["normal_approx_p_value"][index]),
        })
    beta = np.asarray(fit["beta"], dtype=float)
    return {
        "crop": crop,
        "irrigation_practice": practice,
        "form": form,
        "is_registered_primary_form_for_crop": form == models["primary_form_by_crop"][crop],
        "rows": int(len(subset)),
        "counties": int(subset.county_geoid.nunique()),
        "states": int(subset.state.nunique()),
        "year_min": int(subset.harvest_year.min()),
        "year_max": int(subset.harvest_year.max()),
        "demeaning_iterations": int(iterations),
        "demeaning_final_max_change": float(final_change),
        "within_r_squared": float(fit["within_r_squared"]),
        "residual_rmse_log_yield": float(fit["residual_rmse"]),
        "cluster_count": int(fit["clusters"]),
        "coefficients": coefficients,
        "contrasts": contrast_summary(
            subset,
            form,
            names,
            beta,
            np.asarray(fit["covariance_beta_cluster_county"], dtype=float),
            config,
        ),
    }


def run(config_path: Path) -> dict[str, object]:
    config = load_config(config_path)
    frame, input_record = validate_panel(config)
    estimates = [
        estimate(frame, crop, practice, form, config)
        for crop in map(str, config["input"]["crops"])
        for practice in map(str, config["input"]["practices"])
        for form in map(str, config["models"]["forms"])
    ]
    return {
        "schema": "us_direct_practice_precipitation_association_result_v1",
        "analysis_id": config["analysis_id"],
        "status": "completed_historical_fixed_effects_association_only",
        "input": input_record,
        "config": {"path": str(config_path.relative_to(PROJECT)), "sha256": sha256(config_path)},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": sha256(Path(__file__))},
        "estimation_primitives": {
            "path": str(ESTIMATION_PRIMITIVES.relative_to(PROJECT)),
            "sha256": sha256(ESTIMATION_PRIMITIVES),
        },
        "fixed_effects": config["models"]["fixed_effects"],
        "cluster": config["models"]["cluster"],
        "selection_lineage": config["models"]["primary_form_reason"],
        "estimates": estimates,
        "coefficients_emitted": True,
        "row_predictions_emitted": False,
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
        "disclaimer": config["output"]["required_disclaimer"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    result = run(config_path)
    out = args.out or project_path(load_config(config_path)["output"]["result"])
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix(out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(out)
    print(f"wrote {len(result['estimates'])} direct-practice precipitation associations to {out}")


if __name__ == "__main__":
    main()
