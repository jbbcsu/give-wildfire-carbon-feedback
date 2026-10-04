#!/usr/bin/env python3
"""Independent static and receipt validation for soybean fit orchestration."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import resource
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def function_source(source: str, tree: ast.AST, name: str) -> str:
    node = next(
        item for item in ast.walk(tree)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name
    )
    lines = source.splitlines()
    return "\n".join(lines[node.lineno - 1:node.end_lineno])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--orchestrator", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh orchestration validation output required")
    root = args.root.resolve()
    config_path = args.config.resolve()
    orchestrator_path = args.orchestrator.resolve()
    tests_path = args.tests.resolve()
    packet_path = args.packet.resolve()
    output_path = args.output.resolve()
    for path in (config_path, orchestrator_path, tests_path, packet_path):
        require(path == root or root in path.parents, "validator path escapes repository root")

    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    tests = json.loads(tests_path.read_text(encoding="utf-8"))
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    require((root / config["orchestrator_identity"]["path"]).resolve() == orchestrator_path, "configured orchestrator path differs")
    require(config["orchestrator_identity"]["sha256"] == digest(orchestrator_path), "config/orchestrator hash differs")
    for name, binding in config["bindings"].items():
        path = (root / binding["path"]).resolve()
        require(path == root or root in path.parents, f"binding escapes root: {name}")
        require(binding["sha256"] == digest(path), f"configured binding differs: {name}")

    require(tests["config"]["sha256"] == digest(config_path), "test/config hash differs")
    require(tests["orchestrator"]["sha256"] == digest(orchestrator_path), "test/orchestrator hash differs")
    result = tests["tests"]
    require(result["all_pass"] is True, "synthetic orchestration test failed")
    negative_evidence = {"real_outcome_paths_opened", "production_token_created"}
    require(all(value is True for name, value in result["tests"].items() if name not in negative_evidence), "a positive test gate failed")
    require(all(result["tests"][name] is False for name in negative_evidence), "forbidden production action reported")
    require(result["real_outcome_files_opened"] == 0 and result["production_tokens_created"] == 0, "production access or token creation reported")
    require(set(result["synthetic_support"]) == set(config["execution"]["allowed_families"]), "synthetic family coverage differs")
    require(tests["resources"]["memory_gate_passed"] is True, "synthetic memory gate failed")

    gate_config_path = root / config["bindings"]["gate_config"]["path"]
    gate = tomllib.loads(gate_config_path.read_text(encoding="utf-8"))
    required = packet["required_token_fields_and_exact_values"]
    require(packet["status"] == "exact_requirements_frozen_authorization_absent", "packet status differs")
    require(packet["authorization_granted"] is False and packet["token_created"] is False, "packet inferred authorization or token creation")
    require(packet["required_user_statement"] == gate["authorization"]["required_statement"], "packet authorization statement differs")
    require(required["production_orchestrator_sha256"] == digest(orchestrator_path), "packet orchestrator hash differs")
    require(required["production_orchestrator_config_sha256"] == digest(config_path), "packet config hash differs")
    require(required["production_reader_sha256"] == config["bindings"]["reader"]["sha256"], "packet reader hash differs")
    reader_config_path = root / config["bindings"]["reader_config"]["path"]
    require(required["production_reader_config_sha256"] == digest(reader_config_path), "packet reader-config hash differs")
    require(required["synthetic"] is False, "packet describes a synthetic token")
    require(packet["execution_audit"] == {"engine_imported": False, "fit_invoked": False, "real_outcome_paths_opened": []}, "packet reports execution")
    require(not any(packet["claim_gates"].values()), "packet opens a claim gate")

    source = orchestrator_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    require(config["execution"]["engine_module"] not in imports, "orchestrator imports engine at module load")
    chain = function_source(source, tree, "validate_production_authorization_chain")
    require("access_gate.validate_authorization_token" in chain, "base production authorization is absent")
    require(chain.index("access_gate.validate_authorization_token") < chain.index("validate_orchestrator_token"), "orchestrator binding is checked before base token validity")
    production = function_source(source, tree, "execute_authorized_production")
    ordered = [
        "validate_production_authorization_chain",
        "production_reader.build_authorized_reader",
        "importlib.import_module",
        "adapter.execute_family",
    ]
    positions = [production.index(item) for item in ordered]
    require(positions == sorted(positions), "authorization/reader/engine/adapter order differs")
    synthetic = function_source(source, tree, "execute_synthetic_path")
    require("importlib.import_module" in synthetic and "adapter.execute_family" in synthetic, "synthetic path does not reach real engine and adapter")
    cli = function_source(source, tree, "main")
    require("execute_synthetic_path" not in cli and "test_mode" not in cli and "--test" not in cli, "production CLI exposes synthetic execution")
    require(cli.count("--family") == 1 and "choices=[\"quantity\", \"distribution\", \"scpdsi_season\"]" in cli, "CLI family boundary differs")
    finalize = function_source(source, tree, "finalize_public_result")
    require("numeric_fit_outputs_emitted" in finalize and "fit_summary_cannot_promote_response" in finalize, "public redaction/promotion boundary is absent")
    require('"executed": False' in finalize and '"passed": False' in finalize, "terminal result can be inferred as run or passed")
    require(config["execution"]["one_family_per_process"] is True, "one-family process contract is open")
    require(config["family_hierarchy"]["direct_and_scpdsi_stacking_allowed"] is False, "moisture-family stacking is allowed")
    require(config["terminal_validation"]["run_in_fit_orchestrator"] is False, "terminal validation is enabled inside fit orchestration")
    require(config["terminal_validation"]["terminal_pass_cannot_be_inferred"] is True, "terminal pass can be inferred")
    require(not any(config["claim_gates"].values()), "orchestrator config opens a claim gate")

    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "orchestrator validator memory cap exceeded")
    implementation = Path(__file__).resolve()
    checks = {
        "all_bound_hashes_verified": True,
        "exact_authorization_packet_hash_bound": True,
        "authorization_absent_and_no_token_created": True,
        "base_and_orchestrator_token_validation_precede_reader_construction": True,
        "reader_construction_precedes_deferred_engine_import": True,
        "engine_import_precedes_adapter_invocation": True,
        "production_cli_has_no_synthetic_mode": True,
        "one_family_per_execution": True,
        "family_nonstacking_preserved": True,
        "real_engine_full_path_exercised_on_synthetic_sources": True,
        "numeric_fit_outputs_redacted": True,
        "terminal_validation_explicitly_not_run": True,
        "fit_summary_nonpromotable": True,
        "no_real_outcome_access": True,
        "no_production_token_created": True,
        "claim_gates_closed": True,
    }
    payload = {
        "schema": "soybean_pooled_response_orchestrator_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_fail_closed_orchestration_synthetic_only_no_real_access_or_token",
        "bindings": {
            "config": {"path": str(config_path.relative_to(root)), "sha256": digest(config_path)},
            "orchestrator": {"path": str(orchestrator_path.relative_to(root)), "sha256": digest(orchestrator_path)},
            "tests": {"path": str(tests_path.relative_to(root)), "sha256": digest(tests_path)},
            "authorization_packet": {"path": str(packet_path.relative_to(root)), "sha256": digest(packet_path)},
        },
        "checks": checks,
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
        "implementation": {"path": str(implementation.relative_to(root)), "sha256": digest(implementation)},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "checks": checks, "resources": payload["resources"]}, indent=2))


if __name__ == "__main__":
    main()
