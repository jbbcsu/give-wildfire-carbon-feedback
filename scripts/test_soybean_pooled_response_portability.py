#!/usr/bin/env python3
"""Focused metadata-only tests for the soybean portability validator."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import resource
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import validate_soybean_pooled_response_portability as portability


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def expect_failure(function, message: str) -> None:
    try:
        function()
    except ValueError:
        return
    raise AssertionError(message)


def run(root: Path, manifest_path: Path, builder_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = portability.validate_manifest(manifest, root, verify_files=False)
    require(all(checks.values()), "unmodified portability structure failed")

    wrong_roles = copy.deepcopy(manifest)
    wrong_roles["production_declared_path_roles"].remove("country_proxy")
    expect_failure(lambda: portability.validate_manifest(wrong_roles, root, verify_files=False), "missing country proxy declared path accepted")

    open_license = copy.deepcopy(manifest)
    open_license["composite_license"]["redistribution_authorized"] = True
    expect_failure(lambda: portability.validate_manifest(open_license, root, verify_files=False), "open composite redistribution accepted")

    missing_fallback = copy.deepcopy(manifest)
    middle = next(item for item in missing_fallback["period_components"] if not item["locally_present"])
    middle["fallback"] = None
    expect_failure(lambda: portability.validate_manifest(missing_fallback, root, verify_files=False), "absent middle component without fallback accepted")

    open_gate = copy.deepcopy(manifest)
    open_gate["claim_gates"]["production_fit_authorized"] = True
    expect_failure(lambda: portability.validate_manifest(open_gate, root, verify_files=False), "open claim gate accepted")

    duplicate = copy.deepcopy(manifest)
    duplicate["direct_artifacts"][1]["path"] = duplicate["direct_artifacts"][0]["path"]
    expect_failure(lambda: portability.validate_manifest(duplicate, root, verify_files=False), "duplicate direct path accepted")

    with tempfile.TemporaryDirectory(prefix="soy_portability_test_") as temporary:
        directory = Path(temporary)
        artifact = directory / "artifact.bin"
        artifact.write_bytes(b"metadata-only synthetic portability artifact")
        binding = {"path": "artifact.bin", "bytes": artifact.stat().st_size, "sha256": digest(artifact)}
        portability.verify_binding(directory.resolve(), binding)
        wrong_hash = dict(binding); wrong_hash["sha256"] = "0" * 64
        expect_failure(lambda: portability.verify_binding(directory.resolve(), wrong_hash), "wrong artifact hash accepted")
        wrong_size = dict(binding); wrong_size["bytes"] += 1
        expect_failure(lambda: portability.verify_binding(directory.resolve(), wrong_size), "wrong artifact size accepted")
        escape = dict(binding); escape["path"] = "../artifact.bin"
        expect_failure(lambda: portability.verify_binding(directory.resolve(), escape), "path escape accepted")

    source = builder_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports, called = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name): called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute): called.add(node.func.attr)
    require(not ({"pandas", "pyarrow", "xarray", "numpy"} & imports), "builder imports a table/data module")
    require(not ({"read_parquet", "ParquetFile", "open_dataset", "read_csv", "fit_pooled"} & called), "builder contains a table reader or fit call")

    test_checks = {
        "valid_structure_passes": True,
        "country_proxy_required_in_declared_paths": True,
        "composite_redistribution_fail_closed": True,
        "missing_middle_requires_fallback": True,
        "claim_gates_fail_closed": True,
        "duplicate_direct_paths_rejected": True,
        "synthetic_hash_size_and_path_checks": True,
        "builder_has_no_table_reader_or_fit_import": True,
    }
    return {"all_pass": all(test_checks.values()), "checks": test_checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--builder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-cap-bytes", type=int, default=536870912)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh portability test output required")
    root = args.root.resolve()
    result = run(root, args.manifest.resolve(), args.builder.resolve())
    rss = peak_rss_bytes()
    require(rss < args.memory_cap_bytes, "portability tests exceed memory cap")
    implementation = Path(__file__).resolve()
    payload = {
        "schema": "soybean_pooled_response_production_portability_tests/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_metadata_only_portability_tests_no_real_access_or_fit",
        "manifest": {"path": str(args.manifest), "sha256": digest(args.manifest)},
        "builder": {"path": str(args.builder), "sha256": digest(args.builder)},
        "implementation": {"path": str(implementation.relative_to(root)), "sha256": digest(implementation)},
        "tests": result,
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": args.memory_cap_bytes, "memory_gate_passed": True},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "tests": result, "resources": payload["resources"]}, indent=2))


if __name__ == "__main__":
    main()
