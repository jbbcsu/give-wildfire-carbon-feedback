#!/usr/bin/env python3
"""Estimate historical weather associations with paired-practice yield gaps."""
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
DEFAULT_CONFIG = PROJECT / "us_county_validation/us_paired_practice_gap_association_v1.toml"
PAIR_KEYS = ["county_geoid", "state", "outcome_crop", "harvest_year"]
WEATHER = [
    "precip_mm", "stage1_precip_share", "stage2_precip_share",
    "stage1_tmean_c", "stage2_tmean_c", "stage3_tmean_c",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("configured paths must be project-relative")
    result = (PROJECT / path).resolve()
    result.relative_to(PROJECT.resolve())
    return result


def load_config(path: Path) -> dict[str, Any]:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if config.get("analysis_id") != "us_paired_practice_gap_association_v1":
        raise ValueError("wrong paired-practice contract")
    if config.get("analysis_role") != "historical_paired_practice_yield_gap_association_only":
        raise ValueError("paired-practice analysis role changed")
    if config.get("association_fit_authorized") is not True:
        raise ValueError("paired-practice association fit is not authorized")
    for gate in ("causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized"):
        if config.get(gate) is not False:
            raise ValueError(f"contract unexpectedly opens {gate}")
    if config["input"]["practices"] != ["non_irrigated", "irrigated"]:
        raise ValueError("paired practices changed")
    if config["models"]["fixed_effects"] != ["county_geoid", "state_by_harvest_year"]:
        raise ValueError("paired-practice fixed effects changed")
    if config["models"]["forms"] != ["quantity", "quantity_timing"]:
        raise ValueError("paired-practice model forms changed")
    return config


def build_paired_frame(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    spec = config["input"]
    selected = frame.loc[
        frame["outcome_crop"].astype(str).isin(map(str, spec["crops"]))
        & frame["irrigation_practice"].astype(str).isin(map(str, spec["practices"]))
        & frame["harvest_year"].between(int(spec["year_min"]), int(spec["year_max"]))
    ].copy()
    keys = PAIR_KEYS + ["irrigation_practice"]
    if selected.empty or selected.duplicated(keys).any():
        raise ValueError("direct-practice input is empty or has duplicate keys")
    if set(selected["irrigation_practice"].astype(str)) != set(spec["practices"]):
        raise ValueError("direct-practice input lacks a declared practice")
    counts = selected.groupby(PAIR_KEYS, observed=True)["irrigation_practice"].agg(
        lambda values: set(map(str, values))
    )
    expected = set(map(str, spec["practices"]))
    if not counts.map(lambda value: value == expected).all():
        raise ValueError("a county-crop-year lacks the exact practice pair")
    if "weather_exposure_shared_across_practices" in selected:
        flag = selected["weather_exposure_shared_across_practices"]
        if flag.isna().any() or not flag.astype(bool).all():
            raise ValueError("input does not certify shared practice weather exposure")
    numeric = selected[["yield_bu_acre", *WEATHER]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("paired-practice inputs must be finite")
    if (numeric["yield_bu_acre"] <= 0).any():
        raise ValueError("paired-practice yields must be positive")
    shared = selected.groupby(PAIR_KEYS, observed=True)[WEATHER].nunique(dropna=False)
    if shared.ne(1).any().any():
        raise ValueError("weather exposure differs within a practice pair")
    weather = selected.groupby(PAIR_KEYS, observed=True, sort=False)[WEATHER].first().reset_index()
    yields = selected.pivot(index=PAIR_KEYS, columns="irrigation_practice", values="yield_bu_acre")
    if yields.isna().any().any() or set(yields.columns.astype(str)) != expected:
        raise ValueError("practice-pair yield pivot is incomplete")
    yields = yields.rename(columns={
        "irrigated": "irrigated_yield_bu_acre",
        "non_irrigated": "non_irrigated_yield_bu_acre",
    }).reset_index()
    result = weather.merge(yields, on=PAIR_KEYS, how="inner", validate="one_to_one")
    result["log_yield_gap"] = np.log(result["irrigated_yield_bu_acre"]) - np.log(
        result["non_irrigated_yield_bu_acre"]
    )
    if len(result) * 2 != len(selected) or not np.isfinite(result["log_yield_gap"]).all():
        raise ValueError("paired-practice output does not conserve the selected input")
    return result.sort_values(PAIR_KEYS).reset_index(drop=True)


def raw_design(frame: pd.DataFrame, form: str, config: dict[str, Any]) -> tuple[np.ndarray, list[str]]:
    models = config["models"]
    columns: list[np.ndarray] = []
    names: list[str] = []
    for feature in models["heat_controls"]:
        values = frame[feature].to_numpy(float)
        columns.extend([values, values**2])
        names.extend([feature, f"{feature}_squared"])
    rain = frame[models["quantity_feature"]].to_numpy(float) / float(models["quantity_scale_mm"])
    columns.extend([rain, rain**2])
    names.extend(["precipitation_per_100mm", "precipitation_per_100mm_squared"])
    if form == "quantity_timing":
        for feature in models["timing_features"]:
            columns.append(frame[feature].to_numpy(float))
            names.append(feature)
    elif form != "quantity":
        raise ValueError(f"unknown paired-practice form: {form}")
    return np.column_stack(columns), names


def fit(frame: pd.DataFrame, crop: str, form: str, config: dict[str, Any]) -> dict[str, object]:
    sample = frame.loc[frame["outcome_crop"] == crop].copy()
    models = config["models"]
    if len(sample) < int(models["minimum_rows"]) or sample["county_geoid"].nunique() < int(models["minimum_counties"]):
        raise ValueError(f"paired-practice sample gate failed for {crop}")
    county, _ = pd.factorize(sample["county_geoid"].astype(str), sort=True)
    state_year, _ = pd.factorize(
        sample["state"].astype(str) + "_" + sample["harvest_year"].astype(str), sort=True
    )
    x_raw, names = raw_design(sample, form, config)
    transformed, iterations, final_change = alternating_residualize(
        np.column_stack([sample["log_yield_gap"].to_numpy(float), x_raw]),
        [county, state_year],
        float(models["demeaning_tolerance"]),
        int(models["demeaning_max_iterations"]),
    )
    y, x = transformed[:, 0], transformed[:, 1:]
    if (x.std(axis=0) <= float(models["minimum_within_standard_deviation"])).any():
        raise ValueError("paired-practice residualized predictor is effectively constant")
    fitted = clustered_ols(y, x, sample["county_geoid"].to_numpy())
    beta = np.asarray(fitted["beta"], dtype=float)
    se = np.asarray(fitted["standard_error_cluster_county"], dtype=float)
    coefficients = [
        {
            "term": name,
            "estimate": float(beta[index]),
            "standard_error_cluster_county": float(se[index]),
            "normal_approx_p_value": float(fitted["normal_approx_p_value"][index]),
        }
        for index, name in enumerate(names)
    ]
    covariance = np.asarray(fitted["covariance_beta_cluster_county"], dtype=float)
    scale = float(models["quantity_scale_mm"])
    reference_mm = float(sample["precip_mm"].quantile(float(config["contrasts"]["quantity_reference_percentile"])))
    reference = reference_mm / scale
    increment = float(config["contrasts"]["quantity_increment_mm"]) / scale
    gradient = np.zeros(len(beta))
    gradient[names.index("precipitation_per_100mm")] = increment
    gradient[names.index("precipitation_per_100mm_squared")] = (reference + increment) ** 2 - reference**2
    delta = float(gradient @ beta)
    delta_se = float(np.sqrt(max(gradient @ covariance @ gradient, 0)))
    contrasts: dict[str, object] = {
        "quantity_increment_at_median": {
            "reference_precipitation_mm": reference_mm,
            "increment_mm": float(config["contrasts"]["quantity_increment_mm"]),
            "fitted_log_yield_gap_difference": delta,
            "standard_error_cluster_county": delta_se,
            "fitted_irrigated_to_non_irrigated_yield_ratio_percent_difference": float(100 * math.expm1(delta)),
        }
    }
    if form == "quantity_timing":
        share = float(config["contrasts"]["timing_shift_share"])
        timing_gradient = np.zeros(len(beta))
        timing_gradient[names.index("stage2_precip_share")] = share
        timing_delta = float(timing_gradient @ beta)
        timing_se = float(np.sqrt(max(timing_gradient @ covariance @ timing_gradient, 0)))
        contrasts["stage3_to_stage2_shift"] = {
            "shift_share": share,
            "fitted_log_yield_gap_difference": timing_delta,
            "standard_error_cluster_county": timing_se,
            "fitted_irrigated_to_non_irrigated_yield_ratio_percent_difference": float(100 * math.expm1(timing_delta)),
        }
    return {
        "crop": crop,
        "form": form,
        "rows": int(len(sample)),
        "counties": int(sample["county_geoid"].nunique()),
        "states": int(sample["state"].nunique()),
        "year_min": int(sample["harvest_year"].min()),
        "year_max": int(sample["harvest_year"].max()),
        "demeaning_iterations": int(iterations),
        "demeaning_final_max_change": float(final_change),
        "within_r_squared": float(fitted["within_r_squared"]),
        "residual_rmse_log_yield_gap": float(fitted["residual_rmse"]),
        "cluster_count": int(fitted["clusters"]),
        "coefficients": coefficients,
        "contrasts": contrasts,
    }


def run(config_path: Path) -> dict[str, object]:
    config = load_config(config_path)
    panel_path = project_path(config["input"]["panel"])
    actual = sha256(panel_path)
    if actual != config["input"]["expected_panel_sha256"]:
        raise ValueError("paired-practice panel hash differs from contract")
    paired = build_paired_frame(pd.read_parquet(panel_path), config)
    estimates = [
        fit(paired, str(crop), str(form), config)
        for crop in config["input"]["crops"] for form in config["models"]["forms"]
    ]
    return {
        "schema": "us_paired_practice_gap_association_result_v1",
        "analysis_id": config["analysis_id"],
        "status": "completed_historical_paired_practice_yield_gap_association_only",
        "input": {"path": config["input"]["panel"], "sha256": actual, "paired_rows": len(paired)},
        "config": {"path": str(config_path.relative_to(PROJECT)), "sha256": sha256(config_path)},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": sha256(Path(__file__))},
        "outcome": config["models"]["outcome"],
        "fixed_effects": config["models"]["fixed_effects"],
        "cluster": config["models"]["cluster"],
        "estimates": estimates,
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
    print(f"wrote {len(result['estimates'])} paired-practice yield-gap associations to {out}")


if __name__ == "__main__":
    main()
