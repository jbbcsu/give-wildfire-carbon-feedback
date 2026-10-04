#!/usr/bin/env python3
"""Fail-closed orchestration for one-family pooled soybean execution.

The production CLI validates the exact authorization, reader, orchestrator,
and configuration bindings before importing the response engine. A separate
internal synthetic function is exercised by tests but is not exposed by the
CLI. Public results remain numerically redacted and explicitly do not claim
that locked terminal validation ran.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import resource
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import soybean_pooled_response_execution_adapter as adapter
import soybean_pooled_response_execution_gate as access_gate
import soybean_pooled_response_production_reader as production_reader


class OrchestratorViolation(ValueError):
    """Raised when orchestration or redaction contracts fail closed."""


def require(value: bool, message: str) -> None:
    if not value:
        raise OrchestratorViolation(message)


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
    require(not Path(relative).is_absolute(), "bound path must be repository-relative")
    path = (root / relative).resolve()
    require(path == root or root in path.parents, "bound path escapes repository root")
    return path


def load_config(root: Path, config_path: Path) -> dict[str, Any]:
    root, config_path = root.resolve(), config_path.resolve()
    require(config_path == root or root in config_path.parents, "orchestrator config escapes repository root")
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    for name, binding in config["bindings"].items():
        path = resolve_inside(root, binding["path"])
        require(digest(path) == binding["sha256"], f"orchestrator binding hash differs: {name}")
    identity_path = resolve_inside(root, config["orchestrator_identity"]["path"])
    require(identity_path == Path(__file__).resolve(), "orchestrator identity path differs from running implementation")
    require(digest(identity_path) == config["orchestrator_identity"]["sha256"], "orchestrator implementation hash differs")
    require(not any(config["claim_gates"].values()), "orchestrator config opens a claim gate")
    return config


def build_authorization_packet(root: Path, config_path: Path) -> dict[str, Any]:
    root, config_path = root.resolve(), config_path.resolve()
    config = load_config(root, config_path)
    gate_path = resolve_inside(root, config["bindings"]["gate_config"]["path"])
    gate = tomllib.loads(gate_path.read_text(encoding="utf-8"))
    reader_config_path = resolve_inside(root, config["bindings"]["reader_config"]["path"])
    manifest_path = resolve_inside(root, config["bindings"]["dry_run_manifest"]["path"])
    return {
        "schema": "soybean_pooled_response_authorization_packet/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "exact_requirements_frozen_authorization_absent",
        "authorization_granted": False,
        "token_created": False,
        "required_user_statement": gate["authorization"]["required_statement"],
        "required_token_fields_and_exact_values": {
            "schema": gate["authorization"]["token_schema"],
            "contract_id": gate["contract_id"],
            "authorization_scope": gate["authorization"]["scope"],
            "explicit_user_authorization": True,
            "authorization_statement": gate["authorization"]["required_statement"],
            "dry_run_manifest_sha256": digest(manifest_path),
            "protocol_sha256": gate["metadata"]["protocol"]["sha256"],
            "engine_sha256": gate["metadata"]["engine"]["sha256"],
            "portability_manifest_sha256": gate["metadata"]["portability_manifest"]["sha256"],
            "production_reader_sha256": config["bindings"]["reader"]["sha256"],
            "production_reader_config_sha256": digest(reader_config_path),
            "production_orchestrator_sha256": config["orchestrator_identity"]["sha256"],
            "production_orchestrator_config_sha256": digest(config_path),
            "synthetic": False,
            "issuer": gate["authorization"]["required_issuer"],
        },
        "required_nonce_rule": "string with at least 16 characters; value must be supplied only after explicit authorization",
        "allowed_families_one_at_a_time": list(config["execution"]["allowed_families"]),
        "family_hierarchy": dict(config["family_hierarchy"]),
        "public_output_policy": dict(config["public_output"]),
        "terminal_validation_policy": dict(config["terminal_validation"]),
        "execution_audit": {"real_outcome_paths_opened": [], "engine_imported": False, "fit_invoked": False},
        "claim_gates": dict(config["claim_gates"]),
        "resources": {"peak_rss_bytes": peak_rss_bytes(), "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": peak_rss_bytes() < int(config["memory_cap_bytes"])},
    }


def validate_orchestrator_token(token_path: Path, config_path: Path, config: dict[str, Any], *, synthetic: bool) -> dict[str, Any]:
    require(type(synthetic) is bool, "synthetic must be an explicit boolean")
    token = access_gate.read_json(token_path)
    require(token.get("production_orchestrator_sha256") == config["orchestrator_identity"]["sha256"], "token does not bind the production orchestrator")
    require(token.get("production_orchestrator_config_sha256") == digest(config_path), "token does not bind the production orchestrator config")
    require(token.get("synthetic") is synthetic, "token synthetic status differs from orchestration mode")
    return token


def validate_production_authorization_chain(root: Path, token_path: Path, config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Validate every token binding before constructing a production reader."""
    gate_config = resolve_inside(root, config["bindings"]["gate_config"]["path"])
    manifest = resolve_inside(root, config["bindings"]["dry_run_manifest"]["path"])
    try:
        verdict = access_gate.validate_authorization_token(token_path, manifest, gate_config, root, test_mode=False)
    except access_gate.GateViolation as error:
        raise OrchestratorViolation(f"production authorization failed before reader construction: {error}") from error
    require(verdict["authorized"] is True and verdict["synthetic"] is False, "production authorization verdict differs")
    validate_orchestrator_token(token_path, config_path, config, synthetic=False)
    return verdict


def finalize_public_result(result: dict[str, Any], config: dict[str, Any], reader_audit: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema", "status", "mode", "family", "synthetic", "support", "sample_selection",
        "fit_structure", "redaction", "execution_audit", "claim_gates", "resources",
    }
    require(set(result) == allowed, "adapter public result schema differs")
    require(result["redaction"]["applied"] is True and result["redaction"]["numeric_fit_outputs_emitted"] is False, "numeric fit output is not redacted")
    require(not any(result["claim_gates"].values()), "adapter opened a claim gate")
    require(not any(config["claim_gates"].values()), "orchestrator opened a claim gate")
    terminal = {
        "status": config["terminal_validation"]["public_status"],
        "executed": False,
        "passed": False,
        "buffer_year": int(config["terminal_validation"]["buffer_year"]),
        "terminal_years": [int(config["terminal_validation"]["year_minimum"]), int(config["terminal_validation"]["year_maximum"])],
        "fit_summary_cannot_promote_response": True,
        "required_next_operation": config["terminal_validation"]["required_next_operation"],
    }
    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "orchestrator memory cap exceeded")
    return {
        "schema": config["public_output"]["schema"],
        "status": "synthetic_path_complete_redacted" if result["synthetic"] else "authorized_fit_path_complete_redacted_terminal_not_run",
        "family": result["family"],
        "synthetic": result["synthetic"],
        "adapter_result": result,
        "reader_audit": {
            "authorization_validated_before_source_access": reader_audit["authorization_validated_before_source_access"],
            "synthetic_authorization": reader_audit["synthetic_authorization"],
            "verified_roles": reader_audit["verified_roles"],
            "source_stats": reader_audit["source_stats"],
            "memory_gate_passed": reader_audit["memory_gate_passed"],
        },
        "terminal_validation": terminal,
        "numeric_fit_outputs_emitted": False,
        "claim_gates": dict(config["claim_gates"]),
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
    }


def execute_synthetic_path(root: Path, config_path: Path, family: str, level_reader: Any) -> dict[str, Any]:
    """Test-only full path; intentionally not reachable from the CLI."""
    root, config_path = root.resolve(), config_path.resolve()
    config = load_config(root, config_path)
    require(family in config["execution"]["allowed_families"], "undeclared family")
    engine = importlib.import_module(config["execution"]["engine_module"])
    adapter_config = resolve_inside(root, config["bindings"]["adapter_config"]["path"])
    dependencies = adapter.ExecutionDependencies(level_reader, engine, "synthetic", {})
    result = adapter.execute_family("synthetic", family, dependencies, root, adapter_config)
    return finalize_public_result(result, config, level_reader.audit())


def execute_authorized_production(root: Path, config_path: Path, family: str, token_path: Path) -> dict[str, Any]:
    root, config_path, token_path = root.resolve(), config_path.resolve(), token_path.resolve()
    config = load_config(root, config_path)
    require(family in config["execution"]["allowed_families"], "undeclared family")
    validate_production_authorization_chain(root, token_path, config_path, config)
    reader_config = resolve_inside(root, config["bindings"]["reader_config"]["path"])
    level_reader = production_reader.build_authorized_reader(root, reader_config, token_path, test_mode=False)
    engine = importlib.import_module(config["execution"]["engine_module"])
    adapter_config = resolve_inside(root, config["bindings"]["adapter_config"]["path"])
    dependencies = adapter.ExecutionDependencies(level_reader, engine, "production", level_reader.declared_paths)
    result = adapter.execute_family("production", family, dependencies, root, adapter_config, token_path)
    return finalize_public_result(result, config, level_reader.audit())


def write_fresh(path: Path, value: dict[str, Any]) -> None:
    require(not path.exists(), "fresh output path required")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    packet = subparsers.add_parser("packet", help="write exact metadata-only authorization requirements")
    packet.add_argument("--root", type=Path, required=True)
    packet.add_argument("--config", type=Path, required=True)
    packet.add_argument("--output", type=Path, required=True)
    run = subparsers.add_parser("run", help="run one explicitly authorized family")
    run.add_argument("--root", type=Path, required=True)
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--family", choices=["quantity", "distribution", "scpdsi_season"], required=True)
    run.add_argument("--token", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "packet":
        value = build_authorization_packet(args.root, args.config)
    else:
        value = execute_authorized_production(args.root, args.config, args.family, args.token)
    write_fresh(args.output.resolve(), value)
    print(json.dumps({"status": value["status"], "family": value.get("family"), "claim_gates": value["claim_gates"]}, indent=2))


if __name__ == "__main__":
    main()
