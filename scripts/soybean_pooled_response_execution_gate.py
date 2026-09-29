#!/usr/bin/env python3
"""Metadata-only dry-run and authorization gate for the pooled soybean engine.

This module deliberately has no outcome reader and never imports or invokes the
estimator.  A caller must obtain an affirmative, hash-bound authorization
verdict before adding any outcome access or engine invocation in a separate
execution layer.
"""
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


class GateViolation(ValueError):
    """Raised when a dry-run or authorization contract fails closed."""


def require(value: bool, message: str) -> None:
    if not value:
        raise GateViolation(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def resolve_inside(root: Path, relative: str) -> Path:
    require(not Path(relative).is_absolute(), "bound paths must be repository-relative")
    resolved = (root / relative).resolve()
    require(resolved == root.resolve() or root.resolve() in resolved.parents, "bound path escapes repository root")
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON metadata is not an object: {path}")
    return value


def expected_schemas(protocol: dict[str, Any]) -> dict[str, Any]:
    heat = list(protocol["controls"]["heat_columns"])
    families = protocol["families"]
    keys = ["lat", "lon_360", "harvest_year"]
    outcome = ["yield_observed", "yield_t_ha"]
    pair_base = [
        "cell_id", "lat", "lon_360", "country_label", "country_count", "prior_year", "pair_end_year",
        "yield_observed_prior", "yield_observed_current", "yield_t_ha_prior", "yield_t_ha_current",
    ]
    result: dict[str, Any] = {
        "level_source_common": {
            "required_columns": keys + ["crop"] + outcome,
            "constraints": {
                "crop": "soy", "level_years": [1982, 2010], "one_row_per_cell_year": True,
                "outcome_use_before_authorization": "forbidden",
            },
        },
        "engine_pair_common": {
            "required_columns": pair_base,
            "constraints": {
                "pair_end_years": [1983, 2010], "strict_boolean_endpoint_flags": True,
                "strictly_positive_yield_endpoints": True, "consecutive_years": True,
                "latitude_range_inclusive": [-90.0, 90.0], "longitude_range_half_open": [0.0, 360.0],
                "singleton_country_proxy": True,
            },
        },
    }
    for family in ("quantity", "distribution", "scpdsi_season"):
        moisture = list(families[family]["moisture_columns"])
        result[f"{family}_level_source"] = {"required_feature_columns": heat + moisture}
        result[f"{family}_engine_pair"] = {"required_differenced_features": [f"d_{name}" for name in heat + moisture]}
    return result


def build_dry_run_manifest(root: Path, gate_config_path: Path) -> dict[str, Any]:
    root = root.resolve()
    gate_config_path = gate_config_path.resolve()
    config = tomllib.loads(gate_config_path.read_text(encoding="utf-8"))
    require(config["allowed_mode"] == "dry-run", "only dry-run mode is authorized")
    require(all(value is False for value in config["dry_run"].values()), "dry-run side-effect boundary changed")
    metadata: dict[str, Any] = {}
    loaded: dict[str, dict[str, Any]] = {}
    for name, binding in config["metadata"].items():
        path = resolve_inside(root, binding["path"])
        actual = digest(path)
        require(actual == binding["sha256"], f"metadata hash differs: {name}")
        metadata[name] = {"path": binding["path"], "sha256": actual, "verified": True}
        if path.suffix == ".json":
            loaded[name] = read_json(path)
        elif path.suffix == ".toml":
            loaded[name] = tomllib.loads(path.read_text(encoding="utf-8"))

    protocol = loaded["protocol"]
    protocol_validation = loaded["protocol_validation"]
    preflight = loaded["design_preflight"]
    readiness = loaded["readiness_audit"]
    engine_validation = loaded["engine_validation"]
    portability = loaded["portability_manifest"]
    portability_validation = loaded["portability_validation"]
    require(protocol_validation["promotion_state"]["protocol_mechanically_validated"] is True, "protocol is not mechanically validated")
    require(protocol_validation["promotion_state"]["real_outcome_slope_fit_authorized"] is False, "unexpected prior fit authorization")
    require(preflight["outcome_blinding"]["production_response_fit_performed"] is False, "preflight reports a response fit")
    require(preflight["resolution"]["finest_support_qualified_geographic_resolution"] == "pooled_global", "pooled-only resolution differs")
    require(engine_validation["claim_gates"]["real_outcome_fit_authorized"] is False, "engine validation reports real-fit authorization")
    require(portability["status"] == "metadata_only_portability_bound_no_real_access_or_fit", "portability manifest status differs")
    require(portability["production_declared_path_roles"] == ["direct", "heat", "scpdsi", "country_proxy"], "production declared-path closure differs")
    require(not any(portability["claim_gates"].values()), "portability manifest opens a claim gate")
    require(portability_validation["status"] == "validated_metadata_only_portability_no_real_access_or_fit", "portability manifest is not independently validated")
    require(all(portability_validation["checks"].values()), "portability validation reports a failed check")

    candidates = readiness["assets"]["continuous_candidate_families"]
    outcome_sources = {}
    for family in ("direct", "heat", "scpdsi"):
        source = candidates[family]
        outcome_sources[family] = {
            "path": source["path"], "pinned_sha256": source["sha256"],
            "rows_from_metadata": int(source["rows"]), "observed_outcomes_from_metadata": int(source["observed_outcomes"]),
            "outcome_bearing": True, "opened": False, "hashed_by_dry_run": False,
            "binding_source": metadata["readiness_audit"],
        }
    proxy = portability["country_proxy_transform"]["input"]
    production_paths = {
        name: {"path": item["path"], "pinned_sha256": item["pinned_sha256"], "bytes": next(record["bytes"] for record in portability["direct_artifacts"] if record["path"] == item["path"])}
        for name, item in outcome_sources.items()
    }
    production_paths["country_proxy"] = {
        "path": proxy["path"], "pinned_sha256": proxy["sha256"], "bytes": proxy["bytes"],
        "outcome_bearing": False, "role": "singleton_country_proxy_preprocessing_input",
    }

    direct = preflight["pair_construction"]["direct_heat_pairs"]
    scpdsi = preflight["pair_construction"]["scpdsi_heat_pairs"]
    terminal = readiness["response_evidence"]["spatial_terminal_prediction"]
    support = {
        "quantity_and_distribution_training": {
            "all_finite_pairs": int(direct["pairs"]), "primary_singleton_country_pairs": int(direct["singleton_country_pairs"]),
            "pair_end_years": int(direct["pair_end_years"]), "cells": int(direct["cells"]),
            "blocks10": int(direct["blocks10"]), "country_proxies": int(direct["countries_singleton"]),
        },
        "scpdsi_training": {
            "all_finite_pairs": int(scpdsi["pairs"]), "primary_singleton_country_pairs": int(scpdsi["singleton_country_pairs"]),
            "pair_end_years": int(scpdsi["pair_end_years"]), "cells": int(scpdsi["cells"]),
            "blocks10": int(scpdsi["blocks10"]), "country_proxies": int(scpdsi["countries_singleton"]),
        },
        "already_inspected_terminal_metadata": {
            "pairs": int(terminal["terminal_pairs"]), "blocks10": int(terminal["terminal_10degree_blocks"]),
            "years": [2012, 2016], "buffer_year_excluded": 2011,
            "status": "metadata_only_not_recomputed_and_not_fresh_confirmation",
        },
    }
    require(support["quantity_and_distribution_training"]["primary_singleton_country_pairs"] == int(protocol["expected_training_support"]["direct_primary"]["pairs"]), "direct primary pair count differs")
    require(support["scpdsi_training"]["primary_singleton_country_pairs"] == int(protocol["expected_training_support"]["scpdsi_common"]["pairs"]), "scPDSI primary pair count differs")

    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "memory cap exceeded")
    return {
        "schema": "soybean_pooled_response_execution_dry_run/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "dry_run_complete_metadata_only_authorization_absent",
        "contract": {"path": str(gate_config_path.relative_to(root)), "sha256": digest(gate_config_path)},
        "metadata_bindings": metadata,
        "outcome_source_bindings": outcome_sources,
        "production_declared_path_bindings": production_paths,
        "expected_schemas": expected_schemas(protocol),
        "expected_support": support,
        "authorization": {
            "required": True, "present": False, "validated": False,
            "scope": config["authorization"]["scope"], "real_outcome_access_authorized": False,
            "engine_import_authorized": False, "fit_invocation_authorized": False,
        },
        "redactions": {name: bool(value) for name, value in config["redaction"].items()},
        "promotion_gates": {name: bool(value) for name, value in config["promotion_gates"].items()},
        "execution_audit": {"outcome_files_opened": [], "engine_imported": False, "fit_functions_called": []},
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
    }


def validate_authorization_token(token_path: Path | None, manifest_path: Path, gate_config_path: Path, root: Path, test_mode: bool = False) -> dict[str, Any]:
    require(type(test_mode) is bool, "test_mode must be an explicit boolean")
    require(token_path is not None, "authorization token file is required")
    require(token_path.is_file(), "authorization token file does not exist")
    config = tomllib.loads(gate_config_path.read_text(encoding="utf-8"))
    manifest = read_json(manifest_path)
    token = read_json(token_path)
    auth = config["authorization"]
    require(manifest["status"] == "dry_run_complete_metadata_only_authorization_absent", "manifest is not a closed dry run")
    require(manifest["execution_audit"] == {"outcome_files_opened": [], "engine_imported": False, "fit_functions_called": []}, "manifest reports forbidden execution")
    require(token.get("schema") == auth["token_schema"], "authorization token schema differs")
    require(token.get("contract_id") == config["contract_id"], "authorization token contract differs")
    require(token.get("authorization_scope") == auth["scope"], "authorization scope differs")
    require(token.get("explicit_user_authorization") is True, "explicit authorization is absent")
    require(token.get("authorization_statement") == auth["required_statement"], "authorization statement differs")
    require(token.get("dry_run_manifest_sha256") == digest(manifest_path), "authorization token does not bind the dry-run manifest")
    require(token.get("protocol_sha256") == config["metadata"]["protocol"]["sha256"], "authorization token does not bind the protocol")
    require(token.get("engine_sha256") == config["metadata"]["engine"]["sha256"], "authorization token does not bind the engine")
    portability_path = resolve_inside(root.resolve(), config["metadata"]["portability_manifest"]["path"])
    portability_sha256 = digest(portability_path)
    require(portability_sha256 == config["metadata"]["portability_manifest"]["sha256"], "configured portability manifest hash differs")
    require(token.get("portability_manifest_sha256") == portability_sha256, "authorization token does not bind the portability manifest")
    require(isinstance(token.get("nonce"), str) and len(token["nonce"]) >= 16, "authorization nonce is absent or too short")
    if test_mode:
        require(token.get("synthetic") is True and token.get("issuer") == "synthetic_test", "test authorization must be explicitly synthetic")
    else:
        require(token.get("synthetic") is False, "synthetic authorization cannot unlock production")
        require(token.get("issuer") == auth["required_issuer"], "authorization issuer differs")
    return {
        "authorized": True, "scope": auth["scope"], "synthetic": bool(token["synthetic"]),
        "manifest_sha256": digest(manifest_path), "protocol_sha256": token["protocol_sha256"], "engine_sha256": token["engine_sha256"],
        "portability_manifest_sha256": portability_sha256,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh dry-run output required")
    manifest = build_dry_run_manifest(args.root, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "authorization": manifest["authorization"], "resources": manifest["resources"]}, indent=2))


if __name__ == "__main__":
    main()
