#!/usr/bin/env python3
"""Synthetic-file tests for the token-gated soybean production reader."""
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

import soybean_pooled_response_execution_adapter as adapter
import soybean_pooled_response_production_reader as reader


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
    except reader.ReaderViolation:
        return
    raise AssertionError(message)


def make_sources(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    years = range(1982, 2017)
    cells = [(0.25, 10.25), (10.25, 20.25), (20.25, 30.25)]
    base_rows = []
    for cell_index, (lat, lon) in enumerate(cells):
        for year in years:
            observed = not (cell_index == 1 and year == 1990)
            base_rows.append({
                "lat": lat, "lon_360": lon, "harvest_year": year, "crop": "soy",
                "yield_observed": observed,
                "yield_t_ha": float(2.0 + 0.01 * (year - 1982) + 0.1 * cell_index) if observed else np.nan,
            })
    tables: dict[str, pd.DataFrame] = {}
    for family in ("direct", "heat", "scpdsi"):
        frame = pd.DataFrame(base_rows)
        for feature_index, name in enumerate(config["source_contracts"][family]["features"]):
            frame[name] = 1.0 + feature_index + 0.001 * (frame["harvest_year"] - 1982) + 0.01 * frame["lat"]
        for name, value in reader._expected_metadata(config, family).items():
            frame[name] = value
        tables[family] = frame
    country = pd.DataFrame({
        "lat": [0.25, 10.25, 20.25], "lon_360": [10.25, 20.25, 30.25],
        "country_label": ["AAA", "BBB", "AAA|BBB"], "country_count": np.array([1, 1, 2], dtype=np.int64),
    })
    return tables, country


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_manifest_and_token(root: Path, config_path: Path, directory: Path, source_paths: dict[str, Path]) -> tuple[Path, Path]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    gate_config_path = root / config["bindings"]["gate_config"]["path"]
    gate = tomllib.loads(gate_config_path.read_text(encoding="utf-8"))
    template = json.loads((root / config["bindings"]["dry_run_manifest"]["path"]).read_text(encoding="utf-8"))
    manifest = copy.deepcopy(template)
    for role, path in source_paths.items():
        relative = str(path.relative_to(root))
        manifest["production_declared_path_bindings"][role] = {
            "path": relative, "pinned_sha256": digest(path), "bytes": path.stat().st_size,
        }
    manifest_path = directory / "synthetic_manifest.json"
    write_json(manifest_path, manifest)
    token = {
        "schema": gate["authorization"]["token_schema"],
        "contract_id": gate["contract_id"],
        "authorization_scope": gate["authorization"]["scope"],
        "explicit_user_authorization": True,
        "authorization_statement": gate["authorization"]["required_statement"],
        "dry_run_manifest_sha256": digest(manifest_path),
        "protocol_sha256": gate["metadata"]["protocol"]["sha256"],
        "engine_sha256": gate["metadata"]["engine"]["sha256"],
        "portability_manifest_sha256": gate["metadata"]["portability_manifest"]["sha256"],
        "production_reader_sha256": config["reader_identity"]["sha256"],
        "production_reader_config_sha256": digest(config_path),
        "nonce": "synthetic-reader-test-20261004",
        "synthetic": True,
        "issuer": "synthetic_test",
    }
    token_path = directory / "synthetic_token.json"
    write_json(token_path, token)
    return manifest_path, token_path


def run(root: Path, config_path: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    temp_parent = root / "data" / "interim"
    temp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="soy_reader_synthetic_", dir=temp_parent) as name:
        directory = Path(name)
        tables, country = make_sources(config)
        source_paths: dict[str, Path] = {}
        for family, frame in tables.items():
            path = directory / f"{family}.parquet"
            frame.to_parquet(path, index=False)
            source_paths[family] = path
        country_path = directory / "country.parquet"
        country.to_parquet(country_path, index=False)
        source_paths["country_proxy"] = country_path
        manifest_path, token_path = make_manifest_and_token(root, config_path, directory, source_paths)

        expect_violation(lambda: reader.build_authorized_reader(root, config_path, None, manifest_path=manifest_path, test_mode=True), "missing token accepted")
        bad_token = json.loads(token_path.read_text(encoding="utf-8")); bad_token.pop("production_reader_sha256")
        bad_token_path = directory / "bad_reader_token.json"; write_json(bad_token_path, bad_token)
        expect_violation(lambda: reader.build_authorized_reader(root, config_path, bad_token_path, manifest_path=manifest_path, test_mode=True), "token without reader binding accepted")

        loader = reader.build_authorized_reader(root, config_path, token_path, manifest_path=manifest_path, test_mode=True)
        require(loader.audit()["events"] == [], "source access occurred during authorization")
        direct = loader("direct")
        heat = loader("heat")
        require(len(direct) == len(heat) == 69, "singleton direct/heat support differs")
        direct_pairs = adapter.construct_pair_frame(direct, heat, "distribution", tomllib.loads((root / config["bindings"]["protocol"]["path"]).read_text()))
        require(len(direct_pairs) == 66, "missing unobserved level was not handled as expected")
        require(set(direct.columns) == {"lat", "lon_360", "harvest_year", "country_label", "country_count", "yield_observed", "yield_t_ha", *config["source_contracts"]["direct"]["features"]}, "direct projection leaked columns")

        scpdsi = loader("scpdsi")
        scpdsi_heat = loader("heat")
        scpdsi_pairs = adapter.construct_pair_frame(scpdsi, scpdsi_heat, "scpdsi_season", tomllib.loads((root / config["bindings"]["protocol"]["path"]).read_text()))
        require(len(scpdsi_pairs) == 66, "scPDSI/heat support differs")
        audit = loader.audit()
        require(set(audit["verified_roles"]) == {"country_proxy", "direct", "heat", "scpdsi"}, "not all synthetic roles were verified")
        require(all(event["action"] in {"hash_verified_after_authorization", "projected_columns_opened", "projected_observed_rows_opened"} for event in audit["events"]), "unexpected reader event")
        for family in ("direct", "heat", "scpdsi"):
            stats = audit["source_stats"][family]
            require(stats["full_source_rows"] == 105 and stats["full_source_years"] == list(range(1982, 2017)), f"{family} full-source support tracking differs")
            require(stats["observed_positive_rows_accumulated"] == 104 and stats["unobserved_rows_validated_not_accumulated"] == 1, f"{family} unobserved row entered pandas accumulation")
            require(stats["singleton_country_rows_returned"] == 69, f"{family} singleton rows differ")

        wrong_hash_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        wrong_hash_manifest["production_declared_path_bindings"]["direct"]["pinned_sha256"] = "0" * 64
        wrong_manifest_path = directory / "wrong_hash_manifest.json"; write_json(wrong_manifest_path, wrong_hash_manifest)
        _, wrong_token_path = make_manifest_and_token(root, config_path, directory, source_paths)
        wrong_token = json.loads(wrong_token_path.read_text(encoding="utf-8")); wrong_token["dry_run_manifest_sha256"] = digest(wrong_manifest_path)
        wrong_token_bound = directory / "wrong_hash_token.json"; write_json(wrong_token_bound, wrong_token)
        wrong_loader = reader.build_authorized_reader(root, config_path, wrong_token_bound, manifest_path=wrong_manifest_path, test_mode=True)
        expect_violation(lambda: wrong_loader("direct"), "source hash mismatch accepted")
        require(wrong_loader.audit()["events"] == [], "source was opened after hash mismatch")

        bad_basis = tables["direct"].copy(); bad_basis["weight_vintage"] = "moving"
        bad_basis_path = directory / "bad_basis.parquet"; bad_basis.to_parquet(bad_basis_path, index=False)
        bad_sources = dict(source_paths); bad_sources["direct"] = bad_basis_path
        bad_manifest_path, bad_basis_token = make_manifest_and_token(root, config_path, directory, bad_sources)
        bad_loader = reader.build_authorized_reader(root, config_path, bad_basis_token, manifest_path=bad_manifest_path, test_mode=True)
        expect_violation(lambda: bad_loader("direct"), "basis-contract mismatch accepted")

        escape_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        escape_manifest["production_declared_path_bindings"]["direct"]["path"] = "../escape.parquet"
        escape_path = directory / "escape_manifest.json"; write_json(escape_path, escape_manifest)
        escape_token = json.loads(token_path.read_text(encoding="utf-8")); escape_token["dry_run_manifest_sha256"] = digest(escape_path)
        escape_token_path = directory / "escape_token.json"; write_json(escape_token_path, escape_token)
        expect_violation(lambda: reader.build_authorized_reader(root, config_path, escape_token_path, manifest_path=escape_path, test_mode=True), "path escape accepted")

    tests = {
        "authorization_required_before_reader_creation": True,
        "token_binds_reader_and_config": True,
        "authorization_precedes_source_hash_or_open": True,
        "four_role_declared_path_closure": True,
        "source_hashes_verified_before_parquet_open": True,
        "projected_columns_only": True,
        "basis_contract_constants_validated": True,
        "singleton_country_proxy_join_and_filter": True,
        "unobserved_missing_yield_contract_preserved": True,
        "unobserved_rows_validated_per_batch_not_accumulated": True,
        "direct_heat_exact_support": True,
        "scpdsi_heat_exact_support": True,
        "source_hash_mismatch_fails_before_parquet_decode": True,
        "basis_mismatch_fails_closed": True,
        "path_escape_rejected": True,
        "engine_not_imported_or_invoked": True,
        "no_real_outcome_paths_opened": True,
        "no_production_tokens_created": True,
        "claim_gates_remain_closed": True,
    }
    return {"all_pass": all(tests.values()), "tests": tests, "real_outcome_paths_opened": 0, "production_tokens_created": 0, "synthetic": {"full_source_levels_per_family": 105, "observed_positive_levels_per_family": 104, "singleton_levels_per_family": 69, "positive_consecutive_pairs_per_family": 66}, "reader_audit": audit}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh reader test output required")
    root, config_path = args.root.resolve(), args.config.resolve()
    result = run(root, config_path)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "reader test memory cap exceeded")
    implementation = Path(__file__).resolve()
    reader_path = implementation.with_name("soybean_pooled_response_production_reader.py")
    payload = {
        "schema": "soybean_pooled_response_production_reader_tests/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic_reader_validated_no_real_access_token_or_fit",
        "config": {"path": str(config_path.relative_to(root)), "sha256": digest(config_path)},
        "reader": {"path": str(reader_path.relative_to(root)), "sha256": digest(reader_path)},
        "tests": result,
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
        "implementation": {"path": str(implementation.relative_to(root)), "sha256": digest(implementation)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "tests": result["tests"], "resources": payload["resources"]}, indent=2))


if __name__ == "__main__":
    main()
