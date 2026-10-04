#!/usr/bin/env python3
"""Independent static and receipt validation for the soybean production reader."""
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
    node = next(item for item in ast.walk(tree) if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name)
    lines = source.splitlines()
    return "\n".join(lines[node.lineno - 1:node.end_lineno])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reader", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh reader validation output required")
    root = args.root.resolve()
    args.config = args.config.resolve()
    args.reader = args.reader.resolve()
    args.tests = args.tests.resolve()
    args.output = args.output.resolve()
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    tests = json.loads(args.tests.read_text(encoding="utf-8"))
    require(config["reader_identity"]["sha256"] == digest(args.reader), "config/reader hash differs")
    for name, binding in config["bindings"].items():
        path = root / binding["path"]
        require(binding["sha256"] == digest(path), f"configured binding differs: {name}")
    require(tests["config"]["sha256"] == digest(args.config), "test/config hash differs")
    require(tests["reader"]["sha256"] == digest(args.reader), "test/reader hash differs")
    require(tests["tests"]["all_pass"] and all(tests["tests"]["tests"].values()), "reader synthetic test failed")
    require(tests["tests"]["real_outcome_paths_opened"] == 0, "real outcome access reported")
    require(tests["tests"]["production_tokens_created"] == 0, "production token creation reported")

    source = args.reader.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    require("soybean_pooled_response_engine" not in imports, "reader imports the response engine")
    factory = function_source(source, tree, "build_authorized_reader")
    require("access_gate.validate_authorization_token" in factory, "authorization validation is absent")
    require(factory.index("access_gate.validate_authorization_token") < factory.index("return AuthorizedLevelReader"), "reader can be returned before authorization")
    require(factory.index("production_reader_sha256") < factory.index("return AuthorizedLevelReader"), "reader hash is not token-bound before return")
    require(factory.index("production_reader_config_sha256") < factory.index("return AuthorizedLevelReader"), "reader config is not token-bound before return")
    family_reader = function_source(source, tree, "_read_family")
    require(family_reader.index("self._verified_path(role)") < family_reader.index("pq.ParquetFile(path)"), "family source can open before hash verification")
    country_reader = function_source(source, tree, "_load_country")
    require(country_reader.index('self._verified_path("country_proxy")') < country_reader.index("pq.ParquetFile(path)"), "country source can open before hash verification")
    require("iter_batches" in family_reader and "use_threads=False" in family_reader, "projected sequential batching is absent")
    require("observed_batch = batch.filter" in family_reader and "observed_batch.select(retained_columns).to_pandas()" in family_reader, "unobserved rows can enter pandas accumulation")
    require(family_reader.index("yield flag and finite magnitude differ") < family_reader.index("observed_batch = batch.filter"), "batch missingness validation does not precede filtering")
    require(family_reader.index("observed_batch = batch.filter") < family_reader.index("observed_batch.select(retained_columns).to_pandas()"), "pandas conversion precedes observed-row filtering")
    require("full_source_years" in source and "unobserved_rows_validated_not_accumulated" in source, "full-source support accounting is absent")
    require("basis contract differs" in family_reader, "basis constant validation is absent")
    require("yield flag and finite magnitude differ" in family_reader, "outcome missingness contract is absent")
    require(not any(config["claim_gates"].values()), "reader config opens a claim gate")
    require(config["reader"]["engine_import_allowed"] is False and config["reader"]["fit_invocation_allowed"] is False, "reader config permits fitting")

    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "reader validator memory cap exceeded")
    implementation = Path(__file__).resolve()
    result = {
        "schema": "soybean_pooled_response_production_reader_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_token_gated_reader_synthetic_only_no_real_access_or_fit",
        "bindings": {
            "config": {"path": str(args.config.relative_to(root)), "sha256": digest(args.config)},
            "reader": {"path": str(args.reader.relative_to(root)), "sha256": digest(args.reader)},
            "tests": {"path": str(args.tests.relative_to(root)), "sha256": digest(args.tests)},
        },
        "checks": {
            "all_config_bindings_verified": True,
            "reader_and_config_token_bound": True,
            "authorization_precedes_reader_creation": True,
            "hash_verification_precedes_parquet_decode": True,
            "projected_sequential_batches": True,
            "batch_validation_precedes_observed_row_filter": True,
            "unobserved_rows_not_accumulated_in_pandas": True,
            "full_source_year_support_tracked_separately": True,
            "basis_contract_validation": True,
            "outcome_missingness_contract_validation": True,
            "family_support_alignment_synthetic": True,
            "reader_does_not_import_engine": True,
            "no_real_outcome_access": True,
            "no_production_token_created": True,
            "claim_gates_closed": True,
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
        "implementation": {"path": str(implementation.relative_to(root)), "sha256": digest(implementation)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
