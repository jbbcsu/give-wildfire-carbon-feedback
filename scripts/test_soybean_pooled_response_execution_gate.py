#!/usr/bin/env python3
"""Focused synthetic and boundary tests for the soybean execution gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import soybean_pooled_response_execution_gate as gate


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect_violation(function, message: str) -> None:
    try:
        function()
    except gate.GateViolation:
        return
    raise AssertionError(message)


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def run(root: Path, config_path: Path) -> dict:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    readiness = json.loads((root / config["metadata"]["readiness_audit"]["path"]).read_text(encoding="utf-8"))
    forbidden = {
        (root / readiness["assets"]["continuous_candidate_families"][family]["path"]).resolve()
        for family in ("direct", "heat", "scpdsi")
    }
    original_open = Path.open
    opened: list[str] = []

    def guarded_open(path: Path, *args, **kwargs):
        resolved = path.resolve()
        require(resolved not in forbidden, f"dry run opened outcome source: {resolved}")
        opened.append(str(resolved))
        return original_open(path, *args, **kwargs)

    Path.open = guarded_open
    try:
        manifest = gate.build_dry_run_manifest(root, config_path)
    finally:
        Path.open = original_open

    require(manifest["execution_audit"] == {"outcome_files_opened": [], "engine_imported": False, "fit_functions_called": []}, "execution audit is not empty")
    require(all(not source["opened"] and not source["hashed_by_dry_run"] for source in manifest["outcome_source_bindings"].values()), "outcome binding reports access")
    require("soybean_pooled_response_engine" not in sys.modules, "gate imported pooled-response engine")
    require(manifest["expected_support"]["quantity_and_distribution_training"]["primary_singleton_country_pairs"] == 157868, "direct primary support differs")
    require(manifest["expected_support"]["scpdsi_training"]["primary_singleton_country_pairs"] == 157003, "scPDSI support differs")
    require(manifest["expected_support"]["already_inspected_terminal_metadata"]["pairs"] == 26004, "terminal metadata support differs")
    require(all(manifest["redactions"].values()), "dry-run redaction is open")
    require(not any(manifest["promotion_gates"].values()), "dry-run promotion gate is open")

    with tempfile.TemporaryDirectory(prefix="soy_gate_test_") as temporary:
        directory = Path(temporary)
        manifest_path = directory / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        token = {
            "schema": config["authorization"]["token_schema"],
            "contract_id": config["contract_id"],
            "authorization_scope": config["authorization"]["scope"],
            "explicit_user_authorization": True,
            "authorization_statement": config["authorization"]["required_statement"],
            "dry_run_manifest_sha256": digest(manifest_path),
            "protocol_sha256": config["metadata"]["protocol"]["sha256"],
            "engine_sha256": config["metadata"]["engine"]["sha256"],
            "nonce": "synthetic-test-nonce-20260929",
            "issuer": "synthetic_test",
            "synthetic": True,
        }
        token_path = directory / "token.json"
        token_path.write_text(json.dumps(token, sort_keys=True), encoding="utf-8")
        verdict = gate.validate_authorization_token(token_path, manifest_path, config_path, root, test_mode=True)
        require(verdict["authorized"] and verdict["synthetic"], "valid synthetic token did not pass test mode")
        expect_violation(lambda: gate.validate_authorization_token(None, manifest_path, config_path, root), "missing token accepted")
        expect_violation(lambda: gate.validate_authorization_token(token_path, manifest_path, config_path, root), "synthetic token unlocked production")
        expect_violation(lambda: gate.validate_authorization_token(token_path, manifest_path, config_path, root, test_mode=1), "non-Boolean test_mode accepted")
        for field in ("dry_run_manifest_sha256", "protocol_sha256", "engine_sha256", "authorization_scope", "authorization_statement"):
            mutated = dict(token); mutated[field] = "wrong"
            bad_path = directory / f"bad_{field}.json"
            bad_path.write_text(json.dumps(mutated), encoding="utf-8")
            expect_violation(lambda path=bad_path: gate.validate_authorization_token(path, manifest_path, config_path, root, test_mode=True), f"mutated {field} accepted")
        false_auth = dict(token); false_auth["explicit_user_authorization"] = False
        false_path = directory / "false_auth.json"; false_path.write_text(json.dumps(false_auth), encoding="utf-8")
        expect_violation(lambda: gate.validate_authorization_token(false_path, manifest_path, config_path, root, test_mode=True), "false explicit authorization accepted")

    tests = {
        "outcome_sources_never_opened_or_hashed": True,
        "engine_never_imported_or_invoked": True,
        "metadata_hashes_bound": True,
        "schemas_and_support_materialized": True,
        "redactions_and_promotion_fail_closed": True,
        "missing_token_rejected": True,
        "synthetic_token_rejected_in_production": True,
        "test_mode_requires_boolean": True,
        "manifest_protocol_engine_scope_statement_mutations_rejected": True,
        "explicit_authorization_required": True,
        "valid_synthetic_token_accepted_only_in_test_mode": True,
    }
    return {"all_pass": all(tests.values()), "tests": tests, "metadata_files_opened": len(set(opened)), "outcome_files_opened": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh test output required")
    result = run(args.root.resolve(), args.config.resolve())
    rss = peak_rss_bytes()
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    require(rss < int(config["memory_cap_bytes"]), "memory cap exceeded")
    implementation = Path(__file__).resolve()
    gate_path = implementation.with_name("soybean_pooled_response_execution_gate.py")
    payload = {
        "schema": "soybean_pooled_response_execution_gate_tests/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_metadata_only_fail_closed_authorization_tests",
        "config": {"path": str(args.config.resolve().relative_to(args.root.resolve())), "sha256": digest(args.config)},
        "gate": {"path": str(gate_path.relative_to(args.root.resolve())), "sha256": digest(gate_path)},
        "results": result,
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
        "implementation": {"path": str(implementation.relative_to(args.root.resolve())), "sha256": digest(implementation)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "results": result, "resources": payload["resources"]}, indent=2))


if __name__ == "__main__":
    main()
