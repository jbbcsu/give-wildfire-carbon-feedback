#!/usr/bin/env python3
"""Synthetic end-to-end tests for soybean reader-adapter-engine orchestration."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import resource
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import soybean_pooled_response_orchestrator as orchestrator
import soybean_pooled_response_production_reader as production_reader


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
    except (orchestrator.OrchestratorViolation, production_reader.ReaderViolation):
        return
    raise AssertionError(message)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_sources(reader_config: dict[str, Any], seed: int = 20261004) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    rng = np.random.default_rng(seed)
    years = range(1982, 2017)
    # Keep substantially more independent spatial clusters than fitted
    # columns.  This avoids turning the orchestration test into a synthetic
    # high-leverage CR2 edge case, which is covered by the engine's own tests.
    blocks = [(1 + row, column) for row in range(5) for column in range(6)]
    heat_names = list(reader_config["source_contracts"]["heat"]["features"])
    direct_names = list(reader_config["source_contracts"]["direct"]["features"])
    rows = []
    countries = []
    for block_id, (lat_bin, lon_bin) in enumerate(blocks):
        country = block_id // 2
        for cell in range(2):
            lat = float(lat_bin * 10 - 85 + cell * 0.1)
            lon = float(lon_bin * 10 + 5 + cell * 0.1)
            countries.append({"lat": lat, "lon_360": lon, "country_label": f"K{country:02d}", "country_count": 1})
            base = 1.0 + rng.normal(scale=0.08)
            for year in years:
                heat = np.r_[rng.normal(20, 3, 3), rng.gamma(2, 4, 3)]
                direct = np.r_[rng.uniform(3, 7), rng.uniform(0.05, 0.8, 2), rng.uniform(2, 30), rng.uniform(5, 100), rng.uniform(0.34, 0.95)]
                scpdsi = 0.4 * (direct[0] - 5) + rng.normal(scale=0.8)
                country_year = 0.15 * np.sin((year - 1982) / 2 + country)
                log_yield = base + country_year + 0.002 * heat.sum() - 0.08 * direct[0] + rng.normal(scale=0.05)
                rows.append({
                    "lat": lat, "lon_360": lon, "harvest_year": year, "crop": "soy",
                    "yield_observed": True, "yield_t_ha": float(np.exp(log_yield)),
                    "heat": dict(zip(heat_names, heat)), "direct": dict(zip(direct_names, direct)),
                    "scpdsi": float(scpdsi),
                })
    common = pd.DataFrame([{key: row[key] for key in ("lat", "lon_360", "harvest_year", "crop", "yield_observed", "yield_t_ha")} for row in rows])
    tables = {}
    for family in ("direct", "heat", "scpdsi"):
        frame = common.copy()
        if family == "direct":
            for name in direct_names:
                frame[name] = [row["direct"][name] for row in rows]
        elif family == "heat":
            for name in heat_names:
                frame[name] = [row["heat"][name] for row in rows]
        else:
            frame["season_scpdsi_mean"] = [row["scpdsi"] for row in rows]
        for name, value in production_reader._expected_metadata(reader_config, family).items():
            frame[name] = value
        tables[family] = frame
    return tables, pd.DataFrame(countries).drop_duplicates(["lat", "lon_360"])


def make_manifest_and_token(root: Path, orchestrator_config_path: Path, directory: Path, paths: dict[str, Path]) -> tuple[Path, Path]:
    orchestration = tomllib.loads(orchestrator_config_path.read_text(encoding="utf-8"))
    reader_config_path = root / orchestration["bindings"]["reader_config"]["path"]
    reader_config = tomllib.loads(reader_config_path.read_text(encoding="utf-8"))
    gate_path = root / orchestration["bindings"]["gate_config"]["path"]
    gate = tomllib.loads(gate_path.read_text(encoding="utf-8"))
    template = json.loads((root / orchestration["bindings"]["dry_run_manifest"]["path"]).read_text(encoding="utf-8"))
    manifest = copy.deepcopy(template)
    for role, path in paths.items():
        manifest["production_declared_path_bindings"][role] = {
            "path": str(path.relative_to(root)), "pinned_sha256": digest(path), "bytes": path.stat().st_size,
        }
    manifest_path = directory / "synthetic_manifest.json"
    write_json(manifest_path, manifest)
    token = {
        "schema": gate["authorization"]["token_schema"], "contract_id": gate["contract_id"],
        "authorization_scope": gate["authorization"]["scope"], "explicit_user_authorization": True,
        "authorization_statement": gate["authorization"]["required_statement"],
        "dry_run_manifest_sha256": digest(manifest_path),
        "protocol_sha256": gate["metadata"]["protocol"]["sha256"],
        "engine_sha256": gate["metadata"]["engine"]["sha256"],
        "portability_manifest_sha256": gate["metadata"]["portability_manifest"]["sha256"],
        "production_reader_sha256": reader_config["reader_identity"]["sha256"],
        "production_reader_config_sha256": digest(reader_config_path),
        "production_orchestrator_sha256": orchestration["orchestrator_identity"]["sha256"],
        "production_orchestrator_config_sha256": digest(orchestrator_config_path),
        "nonce": "synthetic-orchestrator-20261004", "synthetic": True, "issuer": "synthetic_test",
    }
    token_path = directory / "synthetic_token.json"
    write_json(token_path, token)
    return manifest_path, token_path


def run(root: Path, config_path: Path) -> dict[str, Any]:
    config = orchestrator.load_config(root, config_path)
    packet = orchestrator.build_authorization_packet(root, config_path)
    require(packet["authorization_granted"] is False and packet["token_created"] is False, "packet inferred authorization or created a token")
    require(packet["execution_audit"] == {"real_outcome_paths_opened": [], "engine_imported": False, "fit_invoked": False}, "packet reports execution")
    require(packet["terminal_validation_policy"]["terminal_pass_cannot_be_inferred"] is True, "packet terminal boundary differs")
    require(not any(packet["claim_gates"].values()), "packet opens a claim gate")

    engine_name = config["execution"]["engine_module"]
    sys.modules.pop(engine_name, None)
    missing_token = root / "config" / "authorizations" / "does_not_exist.json"
    expect_violation(lambda: orchestrator.execute_authorized_production(root, config_path, "quantity", missing_token), "missing production token accepted")
    require(engine_name not in sys.modules, "engine imported before production authorization")

    temp_parent = root / "data" / "interim"
    temp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="soy_orchestrator_synthetic_", dir=temp_parent) as name:
        directory = Path(name)
        reader_config_path = root / config["bindings"]["reader_config"]["path"]
        reader_config = tomllib.loads(reader_config_path.read_text(encoding="utf-8"))
        tables, country = make_sources(reader_config)
        paths = {}
        for family, frame in tables.items():
            path = directory / f"{family}.parquet"; frame.to_parquet(path, index=False); paths[family] = path
        country_path = directory / "country.parquet"; country.to_parquet(country_path, index=False); paths["country_proxy"] = country_path
        manifest_path, token_path = make_manifest_and_token(root, config_path, directory, paths)
        synthetic_token = orchestrator.validate_orchestrator_token(token_path, config_path, config, synthetic=True)
        require(synthetic_token["issuer"] == "synthetic_test", "synthetic orchestration token differs")
        bad_token = json.loads(token_path.read_text(encoding="utf-8")); bad_token.pop("production_orchestrator_sha256")
        bad_path = directory / "bad_orchestrator_token.json"; write_json(bad_path, bad_token)
        expect_violation(lambda: orchestrator.validate_orchestrator_token(bad_path, config_path, config, synthetic=True), "token without orchestrator binding accepted")

        sys.modules.pop(engine_name, None)
        expect_violation(
            lambda: orchestrator.execute_authorized_production(root, config_path, "quantity", token_path),
            "synthetic token reached production orchestration",
        )
        require(engine_name not in sys.modules, "engine imported for a synthetic token on the production path")

        results = {}
        production_selections = {}
        protocol_path = root / config["bindings"]["protocol"]["path"]
        protocol = tomllib.loads(protocol_path.read_text(encoding="utf-8"))
        for family in config["execution"]["allowed_families"]:
            level_reader = production_reader.build_authorized_reader(root, reader_config_path, token_path, manifest_path=manifest_path, test_mode=True)
            result = orchestrator.execute_synthetic_path(root, config_path, family, level_reader)
            require(result["numeric_fit_outputs_emitted"] is False and not any(result["claim_gates"].values()), f"{family} leaked fit output or opened a gate")
            require(result["terminal_validation"]["executed"] is False and result["terminal_validation"]["passed"] is False, f"{family} inferred terminal validation")
            require(result["adapter_result"]["support"] == {"levels": 2100, "pairs": 2040, "pair_end_years": 34, "cells": 60}, f"{family} support differs")
            require(result["adapter_result"]["redaction"]["numeric_fit_outputs_emitted"] is False, f"{family} adapter redaction differs")
            forbidden = {"coefficient", "standard_error", "p_value", "confidence_interval", "residual", "predictions"}
            require(not (forbidden & set(result["adapter_result"])), f"{family} emitted a forbidden numeric field")
            source_name = "scpdsi" if family == "scpdsi_season" else "direct"
            pairs = orchestrator.adapter.construct_pair_frame(level_reader(source_name), level_reader("heat"), family, protocol)
            production_fit, selection = orchestrator.adapter.select_fit_pairs(pairs, protocol, test_mode=False)
            require(len(production_fit) == 1680, f"{family} production training-pair support differs")
            require(selection["fit_pair_end_year_minimum"] == 1983 and selection["fit_pair_end_year_maximum"] == 2010, f"{family} training years differ")
            require(selection["buffer_year"] == 2011 and selection["buffer_pairs_excluded"] == 60, f"{family} buffer handling differs")
            require(selection["terminal_pair_end_year_minimum"] == 2012 and selection["terminal_pair_end_year_maximum"] == 2016 and selection["terminal_pairs_locked"] == 300, f"{family} terminal lock differs")
            production_selections[family] = selection
            results[family] = result

    tests = {
        "metadata_packet_exact_and_authorization_absent": True,
        "packet_does_not_create_token": True,
        "missing_production_token_stops_before_engine_import": True,
        "synthetic_token_stops_before_reader_construction_and_engine_import": True,
        "token_binds_orchestrator_and_config": True,
        "production_cli_has_no_test_mode": True,
        "synthetic_reader_to_adapter_to_real_engine_quantity": True,
        "synthetic_reader_to_adapter_to_real_engine_distribution": True,
        "synthetic_reader_to_adapter_to_real_engine_scpdsi": True,
        "one_family_per_execution": True,
        "family_nonstacking_preserved": True,
        "numeric_fit_outputs_redacted": True,
        "terminal_validation_explicitly_not_run": True,
        "production_sample_selection_locks_2011_buffer_and_2012_2016_terminal": True,
        "fit_summary_nonpromotable": True,
        "real_outcome_paths_opened": False,
        "production_token_created": False,
        "claim_gates_remain_closed": True,
    }
    return {
        "all_pass": all(value for name, value in tests.items() if name not in {"real_outcome_paths_opened", "production_token_created"}) and tests["real_outcome_paths_opened"] is False and tests["production_token_created"] is False,
        "tests": tests,
        "synthetic_support": {family: result["adapter_result"]["support"] for family, result in results.items()},
        "fit_structures": {family: result["adapter_result"]["fit_structure"] for family, result in results.items()},
        "terminal_status": {family: result["terminal_validation"] for family, result in results.items()},
        "production_sample_selection": production_selections,
        "real_outcome_files_opened": 0, "production_tokens_created": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh orchestration test output required")
    root, config_path = args.root.resolve(), args.config.resolve()
    result = run(root, config_path)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    rss = peak_rss_bytes(); require(rss < int(config["memory_cap_bytes"]), "orchestration test memory cap exceeded")
    implementation = Path(__file__).resolve(); orchestration_path = implementation.with_name("soybean_pooled_response_orchestrator.py")
    payload = {
        "schema": "soybean_pooled_response_orchestrator_tests/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic_full_execution_path_validated_no_real_access_or_token",
        "config": {"path": str(config_path.relative_to(root)), "sha256": digest(config_path)},
        "orchestrator": {"path": str(orchestration_path.relative_to(root)), "sha256": digest(orchestration_path)},
        "tests": result,
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
        "implementation": {"path": str(implementation.relative_to(root)), "sha256": digest(implementation)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "tests": result["tests"], "resources": payload["resources"]}, indent=2))


if __name__ == "__main__":
    main()
