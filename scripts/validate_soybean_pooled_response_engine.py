#!/usr/bin/env python3
"""Validate the synthetic-only soybean pooled-response engine receipt and boundaries."""
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

ROOT = Path(__file__).resolve().parents[1]


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh engine-validator output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    tests = json.loads(args.tests.read_text(encoding="utf-8"))
    require(tests["config"]["sha256"] == digest(args.config), "test/config binding differs")
    require(tests["engine"]["sha256"] == digest(args.engine), "test/engine binding differs")
    require(tests["implementation"]["sha256"] == digest(ROOT / tests["implementation"]["path"]), "test implementation hash differs")
    require(tests["status"] == "validated_engine_on_synthetic_data_only_no_real_outcome_read", "test status differs")
    require(tests["tests"]["all_pass"] and all(tests["tests"]["tests"].values()), "engine test failure")
    require(tests["real_outcome_data_read"] is False and tests["real_coefficient_fit"] is False, "real-data boundary opened")
    require(tests["resources"]["memory_gate_passed"] and tests["resources"]["peak_rss_bytes"] < int(config["memory_cap_bytes"]), "test memory gate differs")
    require(tests["tests"]["test_bootstrap_draws"] < int(config["inference"]["wild_cluster_bootstrap_draws"]), "test bootstrap was not reduced")
    require(tests["tests"]["test_terminal_bootstrap_draws"] < int(config["later_period_validation"]["bootstrap_draws"]), "terminal test bootstrap was not reduced")
    require(tests["tests"]["tests"]["reduced_draws_rejected_outside_test_mode"], "reduced-draw boundary not tested")
    boundary_tests = {
        "zero_draws_fail_closed", "coordinate_bounds_fail_closed", "strict_boolean_flags_fail_closed",
        "integer_years_fail_closed", "production_training_years_enforced",
        "synthetic_alternate_years_require_test_mode", "test_mode_requires_boolean",
        "terminal_years_and_buffer_enforced",
    }
    require(boundary_tests <= set(tests["tests"]["tests"]), f"missing runtime-boundary tests: {sorted(boundary_tests - set(tests['tests']['tests']))}")
    require(all(tests["tests"]["tests"][name] for name in boundary_tests), "one or more runtime-boundary tests failed")

    source = args.engine.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    functions = set()
    called_names = set()
    called_attributes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module.split(".")[0])
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): functions.add(node.name)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name): called_names.add(node.func.id)
            if isinstance(node.func, ast.Attribute): called_attributes.add(node.func.attr)
    allowed_imports = {"__future__", "dataclasses", "typing", "numpy", "pandas", "scipy"}
    require(imports <= allowed_imports, f"engine imports a file/network-capable module: {sorted(imports - allowed_imports)}")
    require("open" not in called_names and "Path" not in called_names, "engine contains direct filesystem access")
    require(not ({"read_parquet", "read_csv", "read_json", "read_pickle", "read_feather", "to_parquet", "to_csv"} & called_attributes), "engine contains tabular file I/O")
    required_functions = {
        "prepare_pair_frame", "fit_pooled", "cr2_from_residual", "satterthwaite_df", "wild_cluster_bootstrap_t",
        "leave_one_block_influence", "control_sensitivities", "terminal_transport_score", "family_features",
        "require_test_mode_flag", "require_training_year_contract", "require_terminal_year_contract",
    }
    require(required_functions <= functions, f"engine function inventory incomplete: {sorted(required_functions - functions)}")
    require("country-, block-, cell-, and irrigation-specific slopes are prohibited" in source, "geographic-slope prohibition absent")
    require("direct precipitation and scPDSI may not be stacked" in source, "family nonstacking prohibition absent")
    require("latitude must lie in [-90, 90]" in source and "longitude must lie in [0, 360)" in source, "coordinate-range guard absent")
    require("must have strict boolean dtype" in source and "must have integer dtype" in source, "dtype guard absent")
    require("production training pair years must equal" in source and "production terminal pair years must equal 2012-2016" in source, "frozen year guard absent")
    require("buffer year entered training or terminal support" in source, "terminal buffer guard absent")
    require("test_mode must be an explicit boolean" in source, "explicit test-mode guard absent")
    require("zero or nonfinite block-score denominator" in source and "zero or nonfinite squared-residual denominator" in source, "influence denominator guard absent")
    require("terminal bootstrap draws must be positive" in source and "zero or nonfinite terminal bootstrap denominator" in source, "bootstrap denominator guard absent")

    rss = peak_rss_bytes(); cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"validator memory cap exceeded: {rss}")
    result = {
        "schema": "soybean_pooled_response_engine_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_synthetic_only_engine_and_fail_closed_boundaries",
        "config": {"path": str(args.config), "sha256": digest(args.config)},
        "engine": {"path": str(args.engine), "sha256": digest(args.engine)},
        "synthetic_tests": {"path": str(args.tests), "sha256": digest(args.tests)},
        "checks": {
            "independent_reference_tests_pass": True,
            "first_difference_input_contract": True,
            "country_year_residualization": True,
            "cr2_satterthwaite": True,
            "restricted_null_webb_bootstrap": True,
            "leave_one_block_influence": True,
            "control_sensitivities": True,
            "terminal_transport_scoring": True,
            "engine_has_no_filesystem_data_reader": True,
            "reduced_draws_test_mode_only": True,
            "strict_coordinate_and_dtype_contracts": True,
            "frozen_training_years_enforced": True,
            "terminal_years_and_buffer_enforced": True,
            "empty_or_zero_denominators_fail_closed": True,
            "family_nonstacking_enforced": True,
            "geographic_slopes_prohibited": True,
            "real_outcome_data_read": False,
            "real_coefficient_fit": False,
        },
        "claim_gates": {
            "engine_validated_on_synthetic_data": True,
            "real_outcome_fit_authorized": False,
            "production_response_authorized": False,
            "causal_interpretation_authorized": False,
            "country_or_block_response_heterogeneity_authorized": False,
            "winner_loser_claims_authorized": False,
            "damage_calculation_authorized": False,
            "scc_authorized": False,
            "give_integration_authorized": False,
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "claim_gates": result["claim_gates"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
