#!/usr/bin/env python3
"""Independently validate the metadata-only soybean execution gate receipts."""
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validator output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tests = json.loads(args.tests.read_text(encoding="utf-8"))
    require(manifest["contract"]["sha256"] == digest(args.config), "manifest/config binding differs")
    require(tests["config"]["sha256"] == digest(args.config), "tests/config binding differs")
    require(tests["gate"]["sha256"] == digest(args.gate), "tests/gate binding differs")
    require(tests["results"]["all_pass"] and all(tests["results"]["tests"].values()), "focused test failure")
    require(tests["results"]["outcome_files_opened"] == 0, "tests report outcome access")
    require(manifest["status"] == "dry_run_complete_metadata_only_authorization_absent", "manifest status differs")
    require(manifest["authorization"]["present"] is False and manifest["authorization"]["validated"] is False, "authorization unexpectedly present")
    require(manifest["execution_audit"] == {"outcome_files_opened": [], "engine_imported": False, "fit_functions_called": []}, "dry-run execution boundary differs")
    require(all(manifest["redactions"].values()), "a redaction is disabled")
    require(not any(manifest["promotion_gates"].values()), "a promotion gate is open")
    require(all(not item["opened"] and not item["hashed_by_dry_run"] for item in manifest["outcome_source_bindings"].values()), "outcome source reports access")
    require(set(manifest["production_declared_path_bindings"]) == {"direct", "heat", "scpdsi", "country_proxy"}, "production declared-path closure differs")
    require(manifest["production_declared_path_bindings"]["country_proxy"]["outcome_bearing"] is False, "country proxy mislabeled as outcome-bearing")
    require("portability_manifest" in manifest["metadata_bindings"] and "portability_validation" in manifest["metadata_bindings"], "portability metadata binding absent")

    source = args.gate.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports, called = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name): called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute): called.add(node.func.attr)
    require(imports <= {"__future__", "argparse", "hashlib", "json", "resource", "sys", "tomllib", "datetime", "pathlib", "typing"}, "gate imports a data or engine module")
    require(not ({"read_parquet", "ParquetFile", "fit_pooled", "wild_cluster_bootstrap_t", "terminal_transport_score", "exec", "eval", "__import__"} & called), "gate contains a forbidden reader, fit, or dynamic import call")
    require("soybean_pooled_response_engine" not in imports, "gate imports the response engine")
    require("authorization token file is required" in source and "synthetic authorization cannot unlock production" in source, "authorization fail-closed source guard absent")

    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "validator memory cap exceeded")
    implementation = Path(__file__).resolve()
    result = {
        "schema": "soybean_pooled_response_execution_gate_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_metadata_only_dry_run_and_fail_closed_authorization_gate",
        "bindings": {
            "config": {"path": str(args.config), "sha256": digest(args.config)},
            "gate": {"path": str(args.gate), "sha256": digest(args.gate)},
            "manifest": {"path": str(args.manifest), "sha256": digest(args.manifest)},
            "tests": {"path": str(args.tests), "sha256": digest(args.tests)},
        },
        "checks": {
            "metadata_only": True, "outcome_files_opened": False, "engine_imported": False,
            "fit_called": False, "authorization_absent": True, "redactions_closed": True,
            "promotion_gates_closed": True, "focused_tests_pass": True,
            "portability_manifest_bound": True, "country_proxy_declared_path_bound": True,
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
        "implementation": {"path": str(implementation.relative_to(args.root.resolve())), "sha256": digest(implementation)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
