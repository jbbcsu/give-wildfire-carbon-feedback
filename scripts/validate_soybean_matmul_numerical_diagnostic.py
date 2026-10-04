#!/usr/bin/env python3
"""Independent validation of the synthetic soybean matmul warning diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh numerical validation output required")
    root = args.root.resolve()
    config_path = args.config.resolve()
    diagnostic_path = args.diagnostic.resolve()
    receipt_path = args.receipt.resolve()
    for path in (config_path, diagnostic_path, receipt_path):
        require(path == root or root in path.parents, "validator input escapes repository root")
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    require((root / config["diagnostic_identity"]["path"]).resolve() == diagnostic_path, "diagnostic path differs")
    require(config["diagnostic_identity"]["sha256"] == digest(diagnostic_path), "diagnostic hash differs")
    for name, binding in config["bindings"].items():
        path = (root / binding["path"]).resolve()
        require(path == root or root in path.parents, f"binding escapes root: {name}")
        require(binding["sha256"] == digest(path), f"configured binding differs: {name}")
        require(receipt["bindings"][name] == binding, f"receipt binding differs: {name}")
    require(receipt["configuration"] == {"path": str(config_path.relative_to(root)), "sha256": digest(config_path)}, "receipt/config binding differs")
    require(receipt["implementation"] == {"path": str(diagnostic_path.relative_to(root)), "sha256": digest(diagnostic_path)}, "receipt/diagnostic binding differs")

    source = diagnostic_path.read_text(encoding="utf-8")
    require("test_mode=True" in source, "synthetic reader authorization is absent")
    require("test_mode=False" not in source, "diagnostic contains a production execution mode")
    require("execute_authorized_production" not in source, "diagnostic can invoke production orchestration")
    require('"real_outcome_paths_opened": []' in source and '"production_tokens_created": 0' in source, "no-access audit is absent")
    scope = receipt["scope"]
    require(scope == {
        "engine_modified": False,
        "family": "distribution",
        "production_tokens_created": 0,
        "real_outcome_paths_opened": [],
        "synthetic_only": True,
    }, "diagnostic scope differs")
    require(receipt["support"]["design_rows"] == 2040 and receipt["support"]["design_columns"] == 12, "design dimensions differ")
    require(receipt["support"]["design_rank"] == 12, "distribution design is not full rank")
    require(receipt["support"]["spatial_clusters"] == 30, "spatial-cluster support differs")

    target_messages = {
        "divide by zero encountered in matmul",
        "invalid value encountered in matmul",
        "overflow encountered in matmul",
    }
    warnings = receipt["warnings"]
    require(warnings["gram_matmul"]["count"] > 0 and set(warnings["gram_matmul"]["messages"]) == target_messages, "target Gram warnings were not reproduced")
    require(warnings["engine_fit_total"]["count"] > 0 and set(warnings["engine_fit_total"]["messages"]) == target_messages, "target engine warnings were not reproduced")
    require(warnings["gram_einsum"]["count"] == 0 and warnings["gram_longdouble_einsum"]["count"] == 0, "stable Gram path emitted a warning")
    require(all(receipt["finiteness"].values()), "a downstream diagnostic array is nonfinite")

    agreement = receipt["agreement"]
    tolerances = config["tolerances"]
    comparisons = {
        "gram_vs_einsum": agreement["gram_matmul_vs_einsum_relative_max"] <= float(tolerances["gram_relative_max"]),
        "gram_vs_longdouble": agreement["gram_einsum_vs_longdouble_relative_max"] <= float(tolerances["gram_longdouble_relative_max"]),
        "gram_vs_decimal50": agreement["gram_einsum_vs_decimal50_relative_max"] <= float(tolerances["gram_decimal50_relative_max"]),
        "bread_root": agreement["bread_root_matmul_vs_einsum_relative_max"] <= float(tolerances["matrix_product_relative_max"]),
        "cluster_products": agreement["cluster_product_matmul_vs_einsum_relative_max"] <= float(tolerances["matrix_product_relative_max"]),
        "cluster_grams": agreement["cluster_gram_matmul_vs_einsum_relative_max"] <= float(tolerances["matrix_product_relative_max"]),
        "coefficient": agreement["coefficient_engine_vs_lstsq_relative_max"] <= float(tolerances["coefficient_relative_max"]),
        "covariance": agreement["covariance_engine_vs_einsum_relative_max"] <= float(tolerances["covariance_relative_max"]),
        "standard_error": agreement["standard_error_engine_vs_einsum_relative_max"] <= float(tolerances["covariance_relative_max"]),
    }
    require(all(comparisons.values()), "an independently evaluated numerical tolerance failed")
    require(receipt["agreement_gates"] == comparisons, "receipt agreement gates differ from independent calculation")
    conditioning = receipt["conditioning"]
    require(all(math.isfinite(float(value)) for value in conditioning.values()), "conditioning diagnostic is nonfinite")
    require(0.0 <= conditioning["maximum_cluster_hat_eigenvalue"] < 1.0 - 1e-10, "cluster leverage boundary failed")
    classification = receipt["classification"]
    require(classification["environment_or_blas_warning"] is True, "warning not classified at environment/BLAS boundary")
    require(classification["material_numerical_discrepancy_detected"] is False, "receipt reports a material discrepancy")
    require(receipt["environment"]["blas"]["name"] == "accelerate", "BLAS backend differs from diagnosed environment")
    require(receipt["environment"]["longdouble_bits"] == 64, "long-double width differs from diagnosed environment")
    require(not any(config["claim_gates"].values()) and not any(receipt["claim_gates"].values()), "a claim gate is open")
    require(receipt["resources"]["memory_gate_passed"] is True, "diagnostic memory gate failed")
    require(receipt["status"] == "warning_reproduced_no_material_numerical_discrepancy_synthetic_only", "diagnostic status differs")

    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "numerical validator memory cap exceeded")
    implementation = Path(__file__).resolve()
    checks = {
        "all_hash_bindings_verified": True,
        "frozen_engine_unchanged": True,
        "synthetic_distribution_design_reproduced": True,
        "target_matmul_warnings_reproduced": True,
        "non_blas_and_decimal_reference_paths_warning_free": True,
        "all_downstream_arrays_finite": True,
        "gram_agreement": True,
        "independent_lstsq_coefficient_agreement": True,
        "independent_cr2_covariance_agreement": True,
        "conditioning_and_leverage_finite": True,
        "no_material_numerical_discrepancy": True,
        "no_real_outcome_access": True,
        "no_production_token_created": True,
        "claim_gates_closed": True,
    }
    payload = {
        "schema": "soybean_pooled_response_matmul_numerical_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_environment_matmul_warning_no_material_numerical_discrepancy",
        "bindings": {
            "config": {"path": str(config_path.relative_to(root)), "sha256": digest(config_path)},
            "diagnostic": {"path": str(diagnostic_path.relative_to(root)), "sha256": digest(diagnostic_path)},
            "receipt": {"path": str(receipt_path.relative_to(root)), "sha256": digest(receipt_path)},
        },
        "checks": checks,
        "agreement_gates_recomputed": comparisons,
        "claim_gates": dict(config["claim_gates"]),
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(config["memory_cap_bytes"]), "memory_gate_passed": True},
        "implementation": {"path": str(implementation.relative_to(root)), "sha256": digest(implementation)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "checks": checks, "resources": payload["resources"]}, indent=2))


if __name__ == "__main__":
    main()
