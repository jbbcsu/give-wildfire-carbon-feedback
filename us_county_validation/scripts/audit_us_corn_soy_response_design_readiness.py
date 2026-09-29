#!/usr/bin/env python3
"""Outcome-blind support and identification audit for U.S. corn/soy designs."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT / "us_county_validation/us_corn_soy_response_design_readiness_v1.toml"
KEYS = ["county_geoid", "outcome_crop", "harvest_year", "irrigation_practice"]
PAIR_KEYS = ["county_geoid", "outcome_crop", "harvest_year"]


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("configured paths must be project-relative")
    resolved = (PROJECT / path).resolve()
    resolved.relative_to(PROJECT.resolve())
    return resolved


def load_config(path: Path) -> dict[str, Any]:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if config.get("protocol_id") != "us_corn_soy_response_design_readiness_v1":
        raise ValueError("wrong readiness protocol")
    if config.get("analysis_role") != "outcome_blind_response_design_readiness_audit_only":
        raise ValueError("readiness role changed")
    for gate in (
        "response_fit_authorized", "coefficient_output_authorized",
        "causal_claim_authorized", "national_claim_authorized",
        "damage_claim_authorized", "scc_claim_authorized",
    ):
        if config.get(gate) is not False:
            raise ValueError(f"protocol unexpectedly opens {gate}")
    if config["design"].get("outcome_values_permitted") is not False:
        raise ValueError("outcome-blind protocol unexpectedly permits outcomes")
    expected_fes = ["county_geoid", "state_by_harvest_year"]
    if config["sample"].get("fixed_effects") != expected_fes:
        raise ValueError("fixed effects changed")
    return config


def validate_receipt(path: Path, expected_family: str, expected_hash: str) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("status") != "validated_us_competing_moisture_source_input":
        raise ValueError(f"{expected_family} source receipt is not validated")
    if receipt.get("family") != expected_family:
        raise ValueError(f"wrong source receipt family for {expected_family}")
    if receipt.get("candidate", {}).get("sha256") != expected_hash:
        raise ValueError(f"{expected_family} receipt does not bind expected input")
    return receipt


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["county_geoid"] = frame.county_geoid.astype("string").str.zfill(5)
    frame["outcome_crop"] = frame.outcome_crop.astype("string")
    frame["irrigation_practice"] = frame.irrigation_practice.astype("string")
    frame["state"] = frame.state.astype("string")
    frame["harvest_year"] = pd.to_numeric(frame.harvest_year, errors="raise").astype(int)
    return frame


def load_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    spec = config["inputs"]
    direct_path = project_path(spec["direct_panel"])
    pdsi_path = project_path(spec["pdsi_panel"])
    direct_hash, pdsi_hash = sha256(direct_path), sha256(pdsi_path)
    if direct_hash != spec["direct_sha256"] or pdsi_hash != spec["pdsi_sha256"]:
        raise ValueError("source panel hash differs from frozen protocol")
    validate_receipt(project_path(spec["direct_receipt"]), "direct_weather", direct_hash)
    validate_receipt(project_path(spec["pdsi_receipt"]), "pdsi", pdsi_hash)

    design = config["design"]
    direct_features = sorted(set(
        design["temperature_controls"] + design["distribution_features"]
    ))
    direct_columns = [*KEYS, "state", "response_estimation_authorized", *direct_features]
    direct = normalize(pd.read_parquet(direct_path, columns=direct_columns))
    sample = config["sample"]
    direct = direct.loc[
        direct.outcome_crop.isin(sample["crops"])
        & direct.irrigation_practice.isin(sample["practices"])
        & direct.harvest_year.between(sample["year_min"], sample["year_max"])
    ].copy()
    if direct.empty or direct.duplicated(KEYS).any():
        raise ValueError("direct input is empty or has duplicate keys")
    if direct.response_estimation_authorized.fillna(True).astype(bool).any():
        raise ValueError("upstream direct artifact unexpectedly authorizes response estimation")
    direct = direct.drop(columns="response_estimation_authorized")
    for column in direct_features:
        direct[column] = pd.to_numeric(direct[column], errors="raise")
    if not np.isfinite(direct[direct_features].to_numpy(float)).all():
        raise ValueError("direct design contains missing/nonfinite features")

    pdsi_columns = [
        *KEYS, "state", "calendar_role", "window_id", "index_day_weighted_mean",
        "response_estimation_authorized_pdsi",
    ]
    pdsi = normalize(pd.read_parquet(pdsi_path, columns=pdsi_columns))
    pdsi = pdsi.loc[
        pdsi.outcome_crop.isin(sample["crops"])
        & pdsi.irrigation_practice.isin(sample["practices"])
        & pdsi.harvest_year.between(sample["year_min"], sample["year_max"])
        & pdsi.calendar_role.astype("string").eq("fixed_primary")
        & pdsi.window_id.astype("string").eq("season")
    ].copy()
    if pdsi.empty or pdsi.duplicated(KEYS).any():
        raise ValueError("season-PDSI input is empty or has duplicate keys")
    if pdsi.response_estimation_authorized_pdsi.fillna(True).astype(bool).any():
        raise ValueError("upstream PDSI artifact unexpectedly authorizes response estimation")
    pdsi["pdsi_season_mean"] = pd.to_numeric(pdsi.index_day_weighted_mean, errors="raise")
    pdsi = pdsi[[*KEYS, "state", "pdsi_season_mean"]]
    if not np.isfinite(pdsi.pdsi_season_mean.to_numpy(float)).all():
        raise ValueError("PDSI design contains missing/nonfinite values")

    direct_keys = direct[KEYS].sort_values(KEYS).reset_index(drop=True)
    pdsi_keys = pdsi[KEYS].sort_values(KEYS).reset_index(drop=True)
    if not direct_keys.equals(pdsi_keys):
        raise ValueError("direct and PDSI level keys are not identical")
    joined = direct.merge(pdsi, on=KEYS, suffixes=("", "_pdsi"), validate="one_to_one")
    if not joined.state.eq(joined.state_pdsi).all():
        raise ValueError("direct/PDSI state labels disagree")
    joined = joined.drop(columns="state_pdsi")

    all_features = direct_features + ["pdsi_season_mean"]
    grouped = joined.groupby(PAIR_KEYS, observed=True, sort=False)
    expected_practices = set(map(str, sample["practices"]))
    if not grouped.irrigation_practice.agg(set).map(lambda x: x == expected_practices).all():
        raise ValueError("practice support is not exactly paired")
    for column in ["state", *all_features]:
        if grouped[column].nunique(dropna=False).ne(1).any():
            raise ValueError(f"paired practices do not share identical {column}")
    return joined, {
        "direct_panel": {"path": spec["direct_panel"], "sha256": direct_hash},
        "pdsi_panel": {"path": spec["pdsi_panel"], "sha256": pdsi_hash},
        "outcome_columns_read": [],
        "level_rows": int(len(joined)),
        "paired_exposure_rows": int(len(joined) // len(expected_practices)),
        "exact_direct_pdsi_keys": True,
        "exact_practice_pairs_and_exposures": True,
    }


def residualize(values: np.ndarray, groups: list[np.ndarray], tolerance: float, maximum: int) -> tuple[np.ndarray, int, float]:
    result = values.astype(float, copy=True)
    final_change = np.inf
    for iteration in range(1, maximum + 1):
        prior = result.copy()
        for group in groups:
            count = np.bincount(group).astype(float)
            for column in range(result.shape[1]):
                totals = np.bincount(group, weights=result[:, column], minlength=len(count))
                result[:, column] -= (totals / count)[group]
        final_change = float(np.max(np.abs(result - prior)))
        if final_change <= tolerance:
            return result, iteration, final_change
    raise ValueError("fixed-effect residualization did not converge")


def raw_design(frame: pd.DataFrame, family: str, config: dict[str, Any]) -> tuple[np.ndarray, list[str]]:
    spec = config["design"]
    columns: list[np.ndarray] = []
    names: list[str] = []
    for feature in spec["temperature_controls"]:
        value = frame[feature].to_numpy(float)
        columns.extend([value, value * value])
        names.extend([feature, f"{feature}_squared"])
    if family in {"quantity", "distribution"}:
        rain = frame["precip_mm"].to_numpy(float) / 100.0
        columns.extend([rain, rain * rain])
        names.extend(["precipitation_per_100mm", "precipitation_per_100mm_squared"])
        if family == "distribution":
            for feature in spec["distribution_features"]:
                if feature == "precip_mm":
                    continue
                columns.append(frame[feature].to_numpy(float))
                names.append(feature)
    elif family == "pdsi":
        value = frame["pdsi_season_mean"].to_numpy(float)
        columns.extend([value, value * value])
        names.extend(["pdsi_season_mean", "pdsi_season_mean_squared"])
    else:
        raise ValueError(f"unknown family {family}")
    return np.column_stack(columns), names


def design_diagnostics(frame: pd.DataFrame, family: str, config: dict[str, Any]) -> dict[str, Any]:
    raw, names = raw_design(frame, family, config)
    county, county_labels = pd.factorize(frame.county_geoid.astype(str), sort=True)
    state_year, state_year_labels = pd.factorize(
        frame.state.astype(str) + "_" + frame.harvest_year.astype(str), sort=True
    )
    spec = config["design"]
    within, iterations, change = residualize(
        raw, [county, state_year], float(spec["demeaning_tolerance"]),
        int(spec["demeaning_max_iterations"]),
    )
    raw_sd = raw.std(axis=0, ddof=0)
    within_sd = within.std(axis=0, ddof=0)
    ratios = within_sd / raw_sd
    standardized = within / within_sd
    u, singular, vh = np.linalg.svd(standardized, full_matrices=False)
    relative = singular / singular[0]
    rank = int(np.sum(relative > float(spec["svd_relative_rank_tolerance"])))
    condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else float("inf")
    # For standardized Z, diag((Z'Z/n)^-1) gives VIF.  The SVD expression
    # avoids optimized BLAS matrix products whose warning behavior can vary by
    # runtime while leaving the numerical definition exact.
    retained = relative > float(spec["svd_relative_rank_tolerance"])
    vif = len(standardized) * np.sum(
        (vh[retained, :] ** 2) / (singular[retained, None] ** 2), axis=0
    )
    leverage = np.sum(u[:, :rank] ** 2, axis=1)
    order = np.sort(leverage)[::-1]
    top_n = max(1, int(np.ceil(0.01 * len(leverage))))
    total_leverage = float(leverage.sum())
    county_h = np.bincount(county, weights=leverage, minlength=len(county_labels))
    state_codes, state_labels = pd.factorize(frame.state.astype(str), sort=True)
    state_h = np.bincount(state_codes, weights=leverage, minlength=len(state_labels))
    county_share = county_h / total_leverage
    state_share = state_h / total_leverage
    row_counts = pd.Series(frame.county_geoid.astype(str)).value_counts().to_numpy(float)
    row_shares = row_counts / row_counts.sum()
    maximum_row = frame.iloc[int(np.argmax(leverage))]
    return {
        "terms": names,
        "columns": len(names),
        "rank": rank,
        "full_rank": rank == len(names),
        "demeaning_iterations": iterations,
        "demeaning_final_max_change": change,
        "raw_sd": {name: float(value) for name, value in zip(names, raw_sd, strict=True)},
        "within_fe_sd": {name: float(value) for name, value in zip(names, within_sd, strict=True)},
        "residual_to_raw_sd_ratio": {name: float(value) for name, value in zip(names, ratios, strict=True)},
        "minimum_residual_to_raw_sd_ratio": float(ratios.min()),
        "standardized_condition_number": condition,
        "smallest_relative_singular_value": float(relative[-1]),
        "maximum_vif": float(vif.max()),
        "maximum_row_leverage": float(leverage.max()),
        "maximum_row_leverage_key": {
            "county_geoid": str(maximum_row.county_geoid),
            "state": str(maximum_row.state),
            "harvest_year": int(maximum_row.harvest_year),
        },
        "p99_row_leverage": float(np.quantile(leverage, 0.99)),
        "top_one_percent_leverage_share": float(order[:top_n].sum() / total_leverage),
        "maximum_county_leverage_share": float(county_share.max()),
        "effective_county_leverage_clusters": float(1.0 / np.sum(county_share**2)),
        "maximum_state_leverage_share": float(state_share.max()),
        "state_with_maximum_leverage_share": str(state_labels[int(np.argmax(state_share))]),
        "effective_counties_by_row_balance": float(1.0 / np.sum(row_shares**2)),
        "state_year_cells": int(len(state_year_labels)),
    }


def audit_stratum(frame: pd.DataFrame, crop: str, practice: str, family: str, config: dict[str, Any]) -> dict[str, Any]:
    subset = frame.loc[
        frame.outcome_crop.eq(crop) & frame.irrigation_practice.eq(practice)
    ].sort_values(["county_geoid", "harvest_year"]).reset_index(drop=True)
    diagnostics = design_diagnostics(subset, family, config)
    gates = config["gates"]
    state_counts = subset.state.value_counts()
    terminal = subset.loc[subset.harvest_year >= int(config["sample"]["terminal_year_min"])]
    leave_state: list[dict[str, Any]] = []
    for state in sorted(subset.state.astype(str).unique()):
        reduced = subset.loc[~subset.state.eq(state)].copy()
        reduced_diag = design_diagnostics(reduced, family, config)
        leave_state.append({
            "omitted_state": state,
            "rows": int(len(reduced)),
            "counties": int(reduced.county_geoid.nunique()),
            "states": int(reduced.state.nunique()),
            "rank": int(reduced_diag["rank"]),
            "full_rank": bool(reduced_diag["full_rank"]),
            "standardized_condition_number": float(reduced_diag["standardized_condition_number"]),
        })
    checks = {
        "rows": len(subset) >= int(gates["minimum_rows"]),
        "counties": subset.county_geoid.nunique() >= int(gates["minimum_counties"]),
        "states": subset.state.nunique() >= int(gates["minimum_states"]),
        "terminal_rows": len(terminal) >= int(gates["minimum_terminal_rows"]),
        "maximum_state_row_share": float(state_counts.max() / len(subset)) <= float(gates["maximum_state_row_share"]),
        "full_rank": bool(diagnostics["full_rank"]),
        "within_variation": diagnostics["minimum_residual_to_raw_sd_ratio"] >= float(gates["minimum_residual_to_raw_sd_ratio"]),
        "condition_number": diagnostics["standardized_condition_number"] <= float(gates["maximum_standardized_condition_number"]),
        "vif": diagnostics["maximum_vif"] <= float(gates["maximum_vif"]),
        "row_leverage": diagnostics["maximum_row_leverage"] <= float(gates["maximum_row_leverage"]),
        "top_one_percent_leverage": diagnostics["top_one_percent_leverage_share"] <= float(gates["maximum_top_one_percent_leverage_share"]),
        "county_leverage": diagnostics["maximum_county_leverage_share"] <= float(gates["maximum_county_leverage_share"]),
        "effective_county_leverage": diagnostics["effective_county_leverage_clusters"] >= float(gates["minimum_effective_county_leverage_clusters"]),
        "state_leverage": diagnostics["maximum_state_leverage_share"] <= float(gates["maximum_state_leverage_share"]),
        "leave_one_state_support": all(
            item["rows"] >= int(gates["minimum_leave_one_state_rows"])
            and item["counties"] >= int(gates["minimum_leave_one_state_counties"])
            for item in leave_state
        ),
        "leave_one_state_rank": all(item["full_rank"] for item in leave_state),
        "leave_one_state_condition": all(
            item["standardized_condition_number"] <= float(gates["maximum_standardized_condition_number"])
            for item in leave_state
        ),
    }
    return {
        "crop": crop,
        "irrigation_practice": practice,
        "family": family,
        "rows": int(len(subset)),
        "counties": int(subset.county_geoid.nunique()),
        "states": int(subset.state.nunique()),
        "year_min": int(subset.harvest_year.min()),
        "year_max": int(subset.harvest_year.max()),
        "terminal_rows": int(len(terminal)),
        "maximum_state_row_share": float(state_counts.max() / len(subset)),
        "state_with_maximum_row_share": str(state_counts.index[0]),
        "diagnostics": diagnostics,
        "leave_one_state": leave_state,
        "gates": checks,
        "all_gates_pass": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    config = load_config(args.config.resolve())
    frame, inputs = load_inputs(config)
    audits = [
        audit_stratum(frame, crop, practice, family, config)
        for crop in config["sample"]["crops"]
        for practice in config["sample"]["practices"]
        for family in ("quantity", "distribution", "pdsi")
    ]
    for crop in config["sample"]["crops"]:
        for family in ("quantity", "distribution", "pdsi"):
            pair = [x for x in audits if x["crop"] == crop and x["family"] == family]
            signatures = [
                (x["rows"], x["counties"], x["states"], x["diagnostics"])
                for x in pair
            ]
            if signatures[0] != signatures[1]:
                raise ValueError(f"practice-specific diagnostics differ for {crop}/{family}")
    readiness = []
    for crop in config["sample"]["crops"]:
        for family in ("quantity", "distribution", "pdsi"):
            pair = [x for x in audits if x["crop"] == crop and x["family"] == family]
            readiness.append({
                "crop": crop,
                "family": family,
                "both_practices_pass": all(x["all_gates_pass"] for x in pair),
                "failed_gates": sorted({
                    gate for x in pair for gate, passed in x["gates"].items() if not passed
                }),
            })
    result = {
        "schema": "us_corn_soy_response_design_readiness_v1",
        "status": "completed_outcome_blind_design_audit",
        "protocol": {
            "path": str(args.config.resolve().relative_to(PROJECT)),
            "sha256": sha256(args.config.resolve()),
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(PROJECT)),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "inputs": inputs,
        "audits": audits,
        "family_readiness": readiness,
        "spei": {
            "status": "blocked_no_validated_direct_practice_county_crop_panel",
            "response_fit_authorized": False,
            "substitution_from_pdsi_or_global_spei_authorized": False,
        },
        "response_fit_authorized": False,
        "coefficient_output_authorized": False,
        "causal_claim_authorized": False,
        "national_claim_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    output = args.out.resolve() if args.out else project_path(config["output"]["result"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(output), "family_readiness": readiness}, indent=2))


if __name__ == "__main__":
    main()
