#!/usr/bin/env python3
"""Dependency-injected execution adapter for the pooled soybean engine.

Synthetic in-memory tables can exercise the full level-to-pair and fit path.
Production loaders are unreachable until the separate authorization gate
validates a non-synthetic user token.  This module contains no file reader for
outcome tables and does not import the response engine.
"""
from __future__ import annotations

import hashlib
import resource
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_integer_dtype

import soybean_pooled_response_execution_gate as access_gate


class AdapterViolation(ValueError):
    """Raised when an execution request violates the frozen adapter contract."""


def require(value: bool, message: str) -> None:
    if not value:
        raise AdapterViolation(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


@dataclass(frozen=True)
class ExecutionDependencies:
    level_loader: Callable[[str], pd.DataFrame]
    engine: Any
    source_kind: str
    declared_paths: dict[str, str]


def load_contracts(root: Path, adapter_config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    adapter = tomllib.loads(adapter_config_path.read_text(encoding="utf-8"))
    for name, binding in adapter["bindings"].items():
        path = (root / binding["path"]).resolve()
        require(path == root or root in path.parents, f"binding escapes root: {name}")
        require(digest(path) == binding["sha256"], f"adapter binding hash differs: {name}")
    protocol_path = root / adapter["bindings"]["protocol"]["path"]
    protocol = tomllib.loads(protocol_path.read_text(encoding="utf-8"))
    return adapter, protocol


def authorize_before_loader(
    mode: str,
    dependencies: ExecutionDependencies,
    root: Path,
    adapter: dict[str, Any],
    authorization_token: Path | None,
) -> dict[str, Any]:
    synthetic_mode = adapter["execution"]["synthetic_mode_name"]
    production_mode = adapter["execution"]["production_mode_name"]
    require(mode in {synthetic_mode, production_mode}, "undeclared execution mode")
    require(dependencies.source_kind == mode, "dependency source kind differs from execution mode")
    if mode == synthetic_mode:
        require(authorization_token is None, "synthetic execution must not consume a production authorization token")
        require(dependencies.declared_paths == {}, "synthetic dependencies may not declare source paths")
        return {"authorized": True, "synthetic": True, "real_outcome_access_authorized": False}

    gate_config_path = root / adapter["bindings"]["gate_config"]["path"]
    manifest_path = root / adapter["bindings"]["dry_run_manifest"]["path"]
    try:
        verdict = access_gate.validate_authorization_token(
            authorization_token, manifest_path, gate_config_path, root, test_mode=False
        )
    except access_gate.GateViolation as error:
        raise AdapterViolation(f"production authorization failed before loader access: {error}") from error
    require(verdict["authorized"] and verdict["synthetic"] is False, "production token did not authorize real access")
    manifest = access_gate.read_json(manifest_path)
    expected_paths = {name: item["path"] for name, item in manifest["production_declared_path_bindings"].items()}
    require(set(expected_paths) == set(adapter["execution"]["production_declared_path_roles"]), "production declared-path roles differ from adapter contract")
    require(dependencies.declared_paths == expected_paths, "production loader paths differ from the frozen manifest")
    return {**verdict, "real_outcome_access_authorized": True}


def _validate_level_table(frame: pd.DataFrame, features: list[str], label: str) -> pd.DataFrame:
    common = [
        "lat", "lon_360", "harvest_year", "country_label", "country_count",
        "yield_observed", "yield_t_ha",
    ]
    required = set(common + features)
    require(required <= set(frame.columns), f"{label} level schema is incomplete: {sorted(required - set(frame.columns))}")
    require(len(frame) > 0, f"{label} level table is empty")
    require(not frame.duplicated(["lat", "lon_360", "harvest_year"]).any(), f"{label} has duplicate cell-years")
    require(is_bool_dtype(frame["yield_observed"].dtype), f"{label} yield_observed must be Boolean")
    require(is_integer_dtype(frame["harvest_year"].dtype), f"{label} harvest_year must be integer")
    require(is_integer_dtype(frame["country_count"].dtype), f"{label} country_count must be integer")
    numeric = ["lat", "lon_360", "yield_t_ha"] + features
    require(np.isfinite(frame[numeric].to_numpy(float)).all(), f"{label} contains nonfinite values")
    require(frame["lat"].between(-90.0, 90.0, inclusive="both").all(), f"{label} latitude outside [-90,90]")
    require(frame["lon_360"].ge(0.0).all() and frame["lon_360"].lt(360.0).all(), f"{label} longitude outside [0,360)")
    require(frame["country_count"].eq(1).all(), f"{label} contains a non-singleton country proxy")
    require(frame["country_label"].notna().all() and frame["country_label"].astype(str).str.len().gt(0).all(), f"{label} country proxy is missing")
    return frame[common + features].copy()


def construct_pair_frame(
    source_levels: pd.DataFrame,
    heat_levels: pd.DataFrame,
    family: str,
    protocol: dict[str, Any],
) -> pd.DataFrame:
    require(family in {"quantity", "distribution", "scpdsi_season"}, "undeclared or stacked family")
    heat_features = list(protocol["controls"]["heat_columns"])
    moisture_features = list(protocol["families"][family]["moisture_columns"])
    direct_names = {
        "log1p_precip_mm", "stage1_precip_share", "stage2_precip_share", "cdd_max_days",
        "rx5day_mm", "precipitation_concentration_hhi",
    }
    if family == "scpdsi_season":
        require(not any(name in source_levels.columns for name in direct_names), "scPDSI source contains direct moisture features")
    else:
        require(not any("scpdsi" in name for name in source_levels.columns), "direct source contains scPDSI features")
    source = _validate_level_table(source_levels, moisture_features, family)
    heat = _validate_level_table(heat_levels, heat_features, "heat")
    keys = ["lat", "lon_360", "harvest_year"]
    merged = source.merge(heat, on=keys, how="inner", validate="one_to_one", suffixes=("_source", "_heat"))
    require(len(merged) == len(source) == len(heat), "source/heat cell-year support differs")
    for name in ("country_label", "country_count", "yield_observed", "yield_t_ha"):
        left, right = merged[f"{name}_source"], merged[f"{name}_heat"]
        if name == "yield_t_ha":
            require(np.array_equal(left.to_numpy(float), right.to_numpy(float)), "source/heat yield magnitudes differ")
        else:
            require(left.equals(right), f"source/heat {name} differs")
    level = merged[keys].copy()
    level["country_label"] = merged["country_label_source"]
    level["country_count"] = merged["country_count_source"]
    level["yield_observed"] = merged["yield_observed_source"]
    level["yield_t_ha"] = merged["yield_t_ha_source"]
    for name in heat_features + moisture_features:
        level[name] = merged[name]
    level = level.loc[level["yield_observed"] & level["yield_t_ha"].gt(0)].copy()
    require(len(level) > 0, "no positive observed levels")

    level = level.sort_values(keys).reset_index(drop=True)
    prior = level.copy()
    prior["harvest_year"] = prior["harvest_year"] + 1
    prior = prior.rename(columns={
        "harvest_year": "pair_end_year", "yield_observed": "yield_observed_prior",
        "yield_t_ha": "yield_t_ha_prior", "country_label": "country_label_prior",
        "country_count": "country_count_prior", **{name: f"{name}_prior" for name in heat_features + moisture_features},
    })
    current = level.rename(columns={
        "harvest_year": "pair_end_year", "yield_observed": "yield_observed_current",
        "yield_t_ha": "yield_t_ha_current", "country_label": "country_label_current",
        "country_count": "country_count_current", **{name: f"{name}_current" for name in heat_features + moisture_features},
    })
    pairs = current.merge(prior, on=["lat", "lon_360", "pair_end_year"], how="inner", validate="one_to_one")
    require(len(pairs) > 0, "no consecutive positive level pairs")
    require(pairs["country_label_current"].equals(pairs["country_label_prior"]), "country proxy changes within a pair")
    require(pairs["country_count_current"].equals(pairs["country_count_prior"]), "country count changes within a pair")
    out = pairs[["lat", "lon_360", "pair_end_year"]].copy()
    out["cell_id"] = out["lat"].map(lambda value: f"{value:.6f}") + ":" + out["lon_360"].map(lambda value: f"{value:.6f}")
    out["country_label"] = pairs["country_label_current"].astype(str)
    out["country_count"] = pairs["country_count_current"].astype(int)
    out["prior_year"] = out["pair_end_year"].astype(int) - 1
    out["pair_end_year"] = out["pair_end_year"].astype(int)
    out["yield_observed_prior"] = pairs["yield_observed_prior"].astype(bool)
    out["yield_observed_current"] = pairs["yield_observed_current"].astype(bool)
    out["yield_t_ha_prior"] = pairs["yield_t_ha_prior"].astype(float)
    out["yield_t_ha_current"] = pairs["yield_t_ha_current"].astype(float)
    for name in heat_features + moisture_features:
        out[f"d_{name}"] = pairs[f"{name}_current"].to_numpy(float) - pairs[f"{name}_prior"].to_numpy(float)
    return out


def execute_family(
    mode: str,
    family: str,
    dependencies: ExecutionDependencies,
    root: Path,
    adapter_config_path: Path,
    authorization_token: Path | None = None,
) -> dict[str, Any]:
    adapter, protocol = load_contracts(root, adapter_config_path)
    require(family in adapter["supported_families"], "family is not supported by the adapter")
    authorization = authorize_before_loader(mode, dependencies, root.resolve(), adapter, authorization_token)
    source_name = "scpdsi" if family == "scpdsi_season" else "direct"
    source_levels = dependencies.level_loader(source_name)
    heat_levels = dependencies.level_loader("heat")
    pairs = construct_pair_frame(source_levels, heat_levels, family, protocol)
    require(hasattr(dependencies.engine, "fit_pooled"), "injected engine lacks fit_pooled")
    fit = dependencies.engine.fit_pooled(
        pairs, protocol, family, "country_year", test_mode=(mode == adapter["execution"]["synthetic_mode_name"])
    )
    rss = peak_rss_bytes()
    require(rss < int(adapter["memory_cap_bytes"]), "adapter memory cap exceeded")
    redacted_fields = [name.removeprefix("redact_") for name, value in adapter["output"].items() if name.startswith("redact_") and value]
    return {
        "schema": adapter["output"]["schema"],
        "status": "synthetic_execution_complete_redacted" if authorization["synthetic"] else "authorized_production_execution_complete_redacted",
        "mode": mode, "family": family, "synthetic": bool(authorization["synthetic"]),
        "support": {"levels": len(source_levels), "pairs": len(pairs), "pair_end_years": int(pairs["pair_end_year"].nunique()), "cells": int(pairs["cell_id"].nunique())},
        "fit_structure": {"clusters": len(fit.adjustments), "rank": int(np.linalg.matrix_rank(fit.x)), "columns": int(fit.x.shape[1]), "group_mode": fit.group_mode},
        "redaction": {"applied": True, "fields": redacted_fields, "numeric_fit_outputs_emitted": False},
        "execution_audit": {"loader_calls": [source_name, "heat"], "engine_method": "fit_pooled", "real_paths_opened_by_adapter": []},
        "claim_gates": {name: bool(value) for name, value in adapter["claim_gates"].items()},
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(adapter["memory_cap_bytes"]), "memory_gate_passed": True},
    }
