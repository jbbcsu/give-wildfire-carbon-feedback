#!/usr/bin/env python3
"""Synthetic-only tests for the dependency-injected soybean execution adapter."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import soybean_pooled_response_engine as engine_module
import soybean_pooled_response_execution_adapter as adapter

np.seterr(all="ignore")  # Avoid stale Accelerate floating flags in otherwise finite synthetic linear algebra.


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def expect_violation(function, message: str) -> None:
    try:
        function()
    except adapter.AdapterViolation:
        return
    raise AssertionError(message)


def make_levels(protocol: dict[str, Any], seed: int = 20260929) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    years = list(range(1999, 2011))
    blocks = [(5 + row, column) for row in range(3) for column in range(4)]
    heat_names = list(protocol["controls"]["heat_columns"])
    direct_names = list(protocol["families"]["distribution"]["moisture_columns"])
    rows = []
    for block_id, (lat_bin, lon_bin) in enumerate(blocks):
        country = block_id // 2
        for cell in range(5):
            base = 1.0 + rng.normal(scale=0.08)
            for year in years:
                heat = rng.normal(size=len(heat_names))
                direct = rng.normal(size=len(direct_names))
                scpdsi = 0.4 * direct[0] + rng.normal(scale=0.8)
                country_year = 0.15 * np.sin((year - years[0]) / 2 + country)
                log_yield = base + country_year + 0.025 * heat.sum() - 0.12 * direct[0] + rng.normal(scale=0.05)
                record = {
                    "lat": float(lat_bin * 10 - 85 + cell * 0.1), "lon_360": float(lon_bin * 10 + 5 + cell * 0.1),
                    "harvest_year": year, "country_label": f"K{country:02d}", "country_count": 1,
                    "yield_observed": True, "yield_t_ha": float(np.exp(log_yield)),
                    "heat": dict(zip(heat_names, heat)), "direct": dict(zip(direct_names, direct)), "scpdsi": float(scpdsi),
                }
                rows.append(record)
    common = pd.DataFrame([{key: row[key] for key in ("lat", "lon_360", "harvest_year", "country_label", "country_count", "yield_observed", "yield_t_ha")} for row in rows])
    heat = common.copy()
    direct = common.copy()
    scpdsi = common.copy()
    for name in heat_names: heat[name] = [row["heat"][name] for row in rows]
    for name in direct_names: direct[name] = [row["direct"][name] for row in rows]
    scpdsi["season_scpdsi_mean"] = [row["scpdsi"] for row in rows]
    return {"heat": heat, "direct": direct, "scpdsi": scpdsi}


class LoaderSpy:
    def __init__(self, tables: dict[str, pd.DataFrame]):
        self.tables = tables
        self.calls: list[str] = []

    def __call__(self, name: str) -> pd.DataFrame:
        self.calls.append(name)
        return self.tables[name].copy()


class EngineSpy:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def fit_pooled(self, frame, config, family, group_mode, test_mode=False):
        self.calls.append({"family": family, "group_mode": group_mode, "test_mode": test_mode, "columns": list(frame.columns), "pairs": len(frame)})
        return engine_module.fit_pooled(frame, config, family, group_mode, test_mode=test_mode)


def run(root: Path, config_path: Path) -> dict[str, Any]:
    adapter_config, protocol = adapter.load_contracts(root, config_path)
    tables = make_levels(protocol)
    family_expectations = {
        "quantity": (["direct", "heat"], 7),
        "distribution": (["direct", "heat"], 12),
        "scpdsi_season": (["scpdsi", "heat"], 7),
    }
    results = {}
    for family, (expected_calls, expected_columns) in family_expectations.items():
        loader, engine = LoaderSpy(tables), EngineSpy()
        dependencies = adapter.ExecutionDependencies(loader, engine, "synthetic", {})
        result = adapter.execute_family("synthetic", family, dependencies, root, config_path)
        require(loader.calls == expected_calls, f"{family} loader family separation differs")
        require(len(engine.calls) == 1 and engine.calls[0]["test_mode"] is True, f"{family} did not invoke engine once in test mode")
        require(result["support"] == {"levels": 720, "pairs": 660, "pair_end_years": 11, "cells": 60}, f"{family} support differs")
        require(result["fit_structure"]["columns"] == expected_columns, f"{family} design width differs")
        require(result["redaction"]["applied"] and not result["redaction"]["numeric_fit_outputs_emitted"], f"{family} output not redacted")
        require(not ({"coefficient", "standard_error", "p_value", "confidence_interval", "residual", "predictions"} & set(result)), f"{family} leaked fit output")
        require(not any(result["claim_gates"].values()), f"{family} opened a claim gate")
        results[family] = result

    pairs = adapter.construct_pair_frame(tables["direct"], tables["heat"], "quantity", protocol)
    first = pairs.iloc[0]
    cell = tables["direct"].loc[(tables["direct"].lat == first.lat) & (tables["direct"].lon_360 == first.lon_360)].sort_values("harvest_year")
    current = cell.loc[cell.harvest_year.eq(first.pair_end_year)].iloc[0]
    prior = cell.loc[cell.harvest_year.eq(first.prior_year)].iloc[0]
    require(abs(first.d_log1p_precip_mm - (current.log1p_precip_mm - prior.log1p_precip_mm)) < 1e-14, "feature difference is not current minus prior")
    require(abs(np.log(first.yield_t_ha_current) - np.log(first.yield_t_ha_prior) - (np.log(current.yield_t_ha) - np.log(prior.yield_t_ha))) < 1e-14, "yield endpoints changed during pairing")

    bad_scpdsi = tables["scpdsi"].copy(); bad_scpdsi["log1p_precip_mm"] = 0.0
    expect_violation(lambda: adapter.construct_pair_frame(bad_scpdsi, tables["heat"], "scpdsi_season", protocol), "direct/scPDSI stacking accepted")
    inconsistent_heat = tables["heat"].copy(); inconsistent_heat.loc[0, "yield_t_ha"] *= 2
    expect_violation(lambda: adapter.construct_pair_frame(tables["direct"], inconsistent_heat, "quantity", protocol), "source/heat outcome mismatch accepted")
    duplicate = pd.concat([tables["direct"], tables["direct"].iloc[[0]]], ignore_index=True)
    expect_violation(lambda: adapter.construct_pair_frame(duplicate, tables["heat"], "quantity", protocol), "duplicate cell-year accepted")

    synthetic_loader, synthetic_engine = LoaderSpy(tables), EngineSpy()
    real_path = next(iter(json.loads((root / adapter_config["bindings"]["dry_run_manifest"]["path"]).read_text())["outcome_source_bindings"].values()))["path"]
    path_dependencies = adapter.ExecutionDependencies(synthetic_loader, synthetic_engine, "synthetic", {"direct": real_path})
    expect_violation(lambda: adapter.execute_family("synthetic", "quantity", path_dependencies, root, config_path), "synthetic execution accepted a declared real path")
    require(synthetic_loader.calls == [] and synthetic_engine.calls == [], "synthetic path violation reached loader or engine")

    production_loader, production_engine = LoaderSpy(tables), EngineSpy()
    manifest = json.loads((root / adapter_config["bindings"]["dry_run_manifest"]["path"]).read_text())
    declared = {name: item["path"] for name, item in manifest["outcome_source_bindings"].items()}
    production_dependencies = adapter.ExecutionDependencies(production_loader, production_engine, "production", declared)
    expect_violation(lambda: adapter.execute_family("production", "quantity", production_dependencies, root, config_path), "production execution accepted a missing token")
    require(production_loader.calls == [] and production_engine.calls == [], "missing production token reached loader or engine")
    missing_token = root / "config/authorizations/does_not_exist.json"
    expect_violation(lambda: adapter.execute_family("production", "quantity", production_dependencies, root, config_path, missing_token), "nonexistent production token accepted")
    require(production_loader.calls == [] and production_engine.calls == [], "invalid production token reached loader or engine")

    tests = {
        "exact_current_minus_prior_pair_construction": True,
        "quantity_distribution_scpdsi_family_separation": True,
        "actual_engine_invoked_by_dependency_injection": True,
        "engine_test_mode_only_for_synthetic": True,
        "output_schema_redacts_all_numeric_fit_results": True,
        "direct_scpdsi_stacking_rejected": True,
        "source_heat_outcome_mismatch_rejected": True,
        "duplicate_levels_rejected": True,
        "synthetic_mode_rejects_declared_real_paths_before_loader": True,
        "production_missing_or_invalid_token_rejected_before_loader": True,
        "claim_gates_remain_closed": True,
        "memory_guard_passes": True,
    }
    return {
        "all_pass": all(tests.values()), "tests": tests,
        "synthetic_support": {family: result["support"] for family, result in results.items()},
        "engine_invocations": 3, "real_outcome_files_opened": 0, "production_tokens_created": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh adapter test output required")
    root, config_path = args.root.resolve(), args.config.resolve()
    result = run(root, config_path)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "test memory cap exceeded")
    implementation = Path(__file__).resolve()
    adapter_path = implementation.with_name("soybean_pooled_response_execution_adapter.py")
    payload = {
        "schema": "soybean_pooled_response_execution_adapter_tests/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic_only_adapter_validated_no_real_access_or_token",
        "config": {"path": str(config_path.relative_to(root)), "sha256": digest(config_path)},
        "adapter": {"path": str(adapter_path.relative_to(root)), "sha256": digest(adapter_path)},
        "tests": result,
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
        "implementation": {"path": str(implementation.relative_to(root)), "sha256": digest(implementation)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "tests": result, "resources": payload["resources"]}, indent=2))


if __name__ == "__main__":
    main()
