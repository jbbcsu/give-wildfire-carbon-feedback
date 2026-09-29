#!/usr/bin/env python3
"""Static and receipt validation for the synthetic-only soybean adapter."""
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
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh adapter validation output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    tests = json.loads(args.tests.read_text(encoding="utf-8"))
    require(tests["config"]["sha256"] == digest(args.config), "test/config hash differs")
    require(tests["adapter"]["sha256"] == digest(args.adapter), "test/adapter hash differs")
    require(tests["tests"]["all_pass"] and all(tests["tests"]["tests"].values()), "synthetic adapter test failed")
    require(tests["tests"]["real_outcome_files_opened"] == 0 and tests["tests"]["production_tokens_created"] == 0, "real access or token reported")

    source = args.adapter.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports, called = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name): called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute): called.add(node.func.attr)
    require("soybean_pooled_response_engine" not in imports, "adapter directly imports the engine")
    require(not ({"read_parquet", "read_csv", "ParquetFile", "read_feather", "read_pickle"} & called), "adapter contains a real table reader")
    require("authorization = authorize_before_loader" in source, "authorization call absent")
    require(source.index("authorization = authorize_before_loader") < source.index("dependencies.level_loader(source_name)"), "loader is reachable before authorization")
    require("fit = dependencies.engine.fit_pooled" in source, "dependency-injected engine invocation absent")
    require("test_mode=(mode == adapter" in source, "synthetic-only engine test-mode boundary absent")
    require(set(config["execution"]["production_declared_path_roles"]) == {"direct", "heat", "scpdsi", "country_proxy"}, "country proxy absent from production declared paths")
    require("portability_manifest" in config["bindings"], "portability manifest binding absent")
    require(all(config["output"][key] for key in config["output"] if key.startswith("redact_")), "an output redaction is disabled")
    require(not any(config["claim_gates"].values()), "a claim gate is open")

    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "adapter validator memory cap exceeded")
    implementation = Path(__file__).resolve()
    result = {
        "schema": "soybean_pooled_response_execution_adapter_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_synthetic_only_adapter_no_real_access_or_token",
        "bindings": {
            "config": {"path": str(args.config), "sha256": digest(args.config)},
            "adapter": {"path": str(args.adapter), "sha256": digest(args.adapter)},
            "tests": {"path": str(args.tests), "sha256": digest(args.tests)},
        },
        "checks": {
            "dependency_injected_engine": True, "adapter_has_no_outcome_table_reader": True,
            "production_authorization_precedes_loader": True, "synthetic_family_fits_pass": True,
            "output_redaction_closed": True, "claim_gates_closed": True,
            "real_outcome_files_opened": False, "production_token_created": False,
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
