#!/usr/bin/env python3
"""Synthetic-only numerical audit of soybean orchestration matmul warnings."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import resource
import sys
import tempfile
import tomllib
import warnings
from decimal import Decimal, localcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import pyarrow
import scipy

import soybean_pooled_response_engine as engine
import soybean_pooled_response_execution_adapter as adapter
import soybean_pooled_response_production_reader as production_reader
import test_soybean_pooled_response_orchestrator as fixture


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def capture_runtime_warnings(function: Callable[[], Any]) -> tuple[Any, list[dict[str, str]]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        value = function()
    records = [
        {"category": item.category.__name__, "message": str(item.message)}
        for item in caught
        if issubclass(item.category, RuntimeWarning)
    ]
    return value, records


def relative_max(left: np.ndarray, right: np.ndarray) -> float:
    left_ld = np.asarray(left, dtype=np.longdouble)
    right_ld = np.asarray(right, dtype=np.longdouble)
    numerator = np.max(np.abs(left_ld - right_ld))
    denominator = max(np.longdouble(1.0), np.max(np.abs(right_ld)))
    return float(numerator / denominator)


def warning_summary(records: list[dict[str, str]]) -> dict[str, Any]:
    messages = sorted({item["message"] for item in records})
    return {"count": len(records), "messages": messages}


def decimal_gram(matrix: np.ndarray, precision: int = 50) -> np.ndarray:
    """Accumulate X'X with decimal arithmetic independent of BLAS/NumPy sums."""
    columns = matrix.shape[1]
    result = np.empty((columns, columns), dtype=float)
    values = [[Decimal.from_float(float(value)) for value in matrix[:, column]] for column in range(columns)]
    with localcontext() as context:
        context.prec = precision
        for left in range(columns):
            for right in range(left, columns):
                total = sum((a * b for a, b in zip(values[left], values[right])), Decimal(0))
                result[left, right] = result[right, left] = float(total)
    return result


def stable_cr2(fit: engine.FitResult) -> tuple[np.ndarray, dict[str, Any]]:
    eigen_bread, vectors_bread = np.linalg.eigh(fit.bread)
    require(np.all(eigen_bread > 0), "stable reconstruction found non-positive bread")
    bread_root = np.einsum(
        "ik,k,jk->ij", vectors_bread, np.sqrt(eigen_bread), vectors_bread,
        optimize=False,
    )
    scores = []
    maximum_hat_eigenvalue = 0.0
    for label in np.unique(fit.blocks):
        index = np.flatnonzero(fit.blocks == label)
        xg = fit.x[index]
        w = np.einsum("ni,ij->nj", xg, bread_root, optimize=False)
        hat = np.einsum("ni,nj->ij", w, w, optimize=False)
        eigen, vectors = np.linalg.eigh(hat)
        keep = eigen > 1e-12
        eigen = eigen[keep]
        vectors = vectors[:, keep]
        if len(eigen):
            maximum_hat_eigenvalue = max(maximum_hat_eigenvalue, float(eigen.max()))
        require(np.all(eigen < 1.0 - 1e-10), f"stable cluster hat eigenvalue reaches one: {label}")
        if len(eigen):
            u = np.einsum("ni,ij->nj", w, vectors, optimize=False) / np.sqrt(eigen)[None, :]
            delta = 1.0 / np.sqrt(1.0 - eigen) - 1.0
            projection = np.einsum("nk,n->k", u, fit.residual[index], optimize=False)
            adjusted = fit.residual[index] + np.einsum("nk,k->n", u, delta * projection, optimize=False)
        else:
            adjusted = fit.residual[index].copy()
        scores.append(np.einsum("np,n->p", xg, adjusted, optimize=False))
    score_matrix = np.asarray(scores)
    meat = np.einsum("gi,gj->ij", score_matrix, score_matrix, optimize=False)
    covariance = np.einsum("ij,jk,kl->il", fit.bread, meat, fit.bread, optimize=False)
    return covariance, {
        "bread_root": bread_root,
        "score_matrix": score_matrix,
        "maximum_cluster_hat_eigenvalue": maximum_hat_eigenvalue,
    }


def run(root: Path, config_path: Path) -> dict[str, Any]:
    root, config_path = root.resolve(), config_path.resolve()
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(digest(Path(__file__).resolve()) == config["diagnostic_identity"]["sha256"], "diagnostic implementation hash differs")
    for name, binding in config["bindings"].items():
        path = (root / binding["path"]).resolve()
        require(path == root or root in path.parents, f"binding escapes root: {name}")
        require(digest(path) == binding["sha256"], f"diagnostic binding hash differs: {name}")
    require(not any(config["claim_gates"].values()), "diagnostic config opens a claim gate")

    orchestrator_config_path = root / config["bindings"]["orchestrator_config"]["path"]
    orchestration = tomllib.loads(orchestrator_config_path.read_text(encoding="utf-8"))
    reader_config_path = root / orchestration["bindings"]["reader_config"]["path"]
    reader_config = tomllib.loads(reader_config_path.read_text(encoding="utf-8"))
    protocol_path = root / orchestration["bindings"]["protocol"]["path"]
    protocol = tomllib.loads(protocol_path.read_text(encoding="utf-8"))

    temp_parent = root / "data" / "interim"
    temp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="soy_matmul_diagnostic_synthetic_", dir=temp_parent) as name:
        directory = Path(name)
        tables, country = fixture.make_sources(reader_config)
        paths: dict[str, Path] = {}
        for family_name, frame in tables.items():
            path = directory / f"{family_name}.parquet"
            frame.to_parquet(path, index=False)
            paths[family_name] = path
        country_path = directory / "country.parquet"
        country.to_parquet(country_path, index=False)
        paths["country_proxy"] = country_path
        manifest_path, token_path = fixture.make_manifest_and_token(root, orchestrator_config_path, directory, paths)
        level_reader = production_reader.build_authorized_reader(
            root, reader_config_path, token_path, manifest_path=manifest_path, test_mode=True
        )
        distribution_levels = level_reader("direct")
        heat_levels = level_reader("heat")
        pairs = adapter.construct_pair_frame(distribution_levels, heat_levels, "distribution", protocol)
        fit_pairs, selection = adapter.select_fit_pairs(pairs, protocol, test_mode=True)

        features = engine.family_features(protocol, "distribution", "pooled_global")
        prepared = engine.prepare_pair_frame(fit_pairs, features)
        groups = engine.group_codes(prepared, "country_year")
        y = engine.residualize(prepared["d_log_yield"].to_numpy(float), groups)
        x = engine.residualize(prepared[features].to_numpy(float), groups)
        require(x.shape == (2040, 12), "synthetic distribution design shape differs")
        require(np.linalg.matrix_rank(x) == x.shape[1], "synthetic distribution design is rank deficient")

        gram_matmul, gram_warnings = capture_runtime_warnings(lambda: x.T @ x)
        gram_einsum, stable_gram_warnings = capture_runtime_warnings(
            lambda: np.einsum("ni,nj->ij", x, x, optimize=False)
        )
        x_longdouble = x.astype(np.longdouble)
        gram_longdouble, longdouble_warnings = capture_runtime_warnings(
            lambda: np.einsum("ni,nj->ij", x_longdouble, x_longdouble, optimize=False)
        )
        gram_decimal50 = decimal_gram(x, precision=50)
        fit, engine_warnings = capture_runtime_warnings(
            lambda: engine.fit_pooled(fit_pairs, protocol, "distribution", "country_year", test_mode=True)
        )

        eigen_bread, vectors_bread = np.linalg.eigh(fit.bread)
        bread_root_matmul, bread_root_warnings = capture_runtime_warnings(
            lambda: (vectors_bread * np.sqrt(eigen_bread)) @ vectors_bread.T
        )
        bread_root_einsum = np.einsum(
            "ik,k,jk->ij", vectors_bread, np.sqrt(eigen_bread), vectors_bread,
            optimize=False,
        )
        cluster_product_warnings: list[dict[str, str]] = []
        maximum_cluster_product_difference = 0.0
        maximum_cluster_gram_difference = 0.0
        for label in np.unique(fit.blocks):
            index = np.flatnonzero(fit.blocks == label)
            xg = fit.x[index]
            w_matmul, records = capture_runtime_warnings(lambda xg=xg: xg @ bread_root_matmul)
            cluster_product_warnings.extend(records)
            w_einsum = np.einsum("ni,ij->nj", xg, bread_root_einsum, optimize=False)
            maximum_cluster_product_difference = max(maximum_cluster_product_difference, relative_max(w_matmul, w_einsum))
            hat_matmul, records = capture_runtime_warnings(lambda w=w_matmul: w.T @ w)
            cluster_product_warnings.extend(records)
            hat_einsum = np.einsum("ni,nj->ij", w_einsum, w_einsum, optimize=False)
            maximum_cluster_gram_difference = max(maximum_cluster_gram_difference, relative_max(hat_matmul, hat_einsum))

        covariance_einsum, stable_details = stable_cr2(fit)
        coefficient_lstsq = np.linalg.lstsq(fit.x, fit.y, rcond=None)[0]
        standard_error_einsum = np.sqrt(np.maximum(np.diag(covariance_einsum), 0.0))
        finite_arrays = {
            "design": x,
            "outcome": y,
            "gram_matmul": gram_matmul,
            "gram_einsum": gram_einsum,
            "gram_longdouble": gram_longdouble,
            "gram_decimal50": gram_decimal50,
            "engine_coefficient": fit.coefficient,
            "lstsq_coefficient": coefficient_lstsq,
            "engine_covariance": fit.covariance,
            "einsum_covariance": covariance_einsum,
            "engine_standard_error": fit.standard_error,
            "einsum_standard_error": standard_error_einsum,
            "engine_degrees_of_freedom": fit.degrees_of_freedom,
            "engine_p_value": fit.p_value,
            "engine_confidence_interval": fit.confidence_interval,
        }
        finite = {key: bool(np.isfinite(value).all()) for key, value in finite_arrays.items()}
        agreements = {
            "gram_matmul_vs_einsum_relative_max": relative_max(gram_matmul, gram_einsum),
            "gram_einsum_vs_longdouble_relative_max": relative_max(gram_einsum, gram_longdouble),
            "gram_einsum_vs_decimal50_relative_max": relative_max(gram_einsum, gram_decimal50),
            "bread_root_matmul_vs_einsum_relative_max": relative_max(bread_root_matmul, bread_root_einsum),
            "cluster_product_matmul_vs_einsum_relative_max": maximum_cluster_product_difference,
            "cluster_gram_matmul_vs_einsum_relative_max": maximum_cluster_gram_difference,
            "coefficient_engine_vs_lstsq_relative_max": relative_max(fit.coefficient, coefficient_lstsq),
            "covariance_engine_vs_einsum_relative_max": relative_max(fit.covariance, covariance_einsum),
            "standard_error_engine_vs_einsum_relative_max": relative_max(fit.standard_error, standard_error_einsum),
        }
        tolerances = config["tolerances"]
        agreement_gates = {
            "gram_vs_einsum": agreements["gram_matmul_vs_einsum_relative_max"] <= float(tolerances["gram_relative_max"]),
            "gram_vs_longdouble": agreements["gram_einsum_vs_longdouble_relative_max"] <= float(tolerances["gram_longdouble_relative_max"]),
            "gram_vs_decimal50": agreements["gram_einsum_vs_decimal50_relative_max"] <= float(tolerances["gram_decimal50_relative_max"]),
            "bread_root": agreements["bread_root_matmul_vs_einsum_relative_max"] <= float(tolerances["matrix_product_relative_max"]),
            "cluster_products": agreements["cluster_product_matmul_vs_einsum_relative_max"] <= float(tolerances["matrix_product_relative_max"]),
            "cluster_grams": agreements["cluster_gram_matmul_vs_einsum_relative_max"] <= float(tolerances["matrix_product_relative_max"]),
            "coefficient": agreements["coefficient_engine_vs_lstsq_relative_max"] <= float(tolerances["coefficient_relative_max"]),
            "covariance": agreements["covariance_engine_vs_einsum_relative_max"] <= float(tolerances["covariance_relative_max"]),
            "standard_error": agreements["standard_error_engine_vs_einsum_relative_max"] <= float(tolerances["covariance_relative_max"]),
        }
        warnings_by_product = {
            "gram_matmul": warning_summary(gram_warnings),
            "engine_fit_total": warning_summary(engine_warnings),
            "bread_root_matmul": warning_summary(bread_root_warnings),
            "cluster_matmul_products": warning_summary(cluster_product_warnings),
            "gram_einsum": warning_summary(stable_gram_warnings),
            "gram_longdouble_einsum": warning_summary(longdouble_warnings),
        }
        require(warnings_by_product["engine_fit_total"]["count"] > 0, "target engine warning was not reproduced")
        require(warnings_by_product["gram_einsum"]["count"] == 0, "stable Gram calculation warned")
        require(warnings_by_product["gram_longdouble_einsum"]["count"] == 0, "long-double Gram calculation warned")
        require(all(finite.values()), "a diagnostic array is nonfinite")
        require(all(agreement_gates.values()), "a stable numerical agreement gate failed")
        reader_audit = level_reader.audit()

    rss = peak_rss_bytes()
    require(rss < int(config["memory_cap_bytes"]), "numerical diagnostic memory cap exceeded")
    return {
        "schema": "soybean_pooled_response_matmul_numerical_diagnostic/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "warning_reproduced_no_material_numerical_discrepancy_synthetic_only",
        "scope": {
            "family": "distribution",
            "synthetic_only": True,
            "engine_modified": False,
            "real_outcome_paths_opened": [],
            "production_tokens_created": 0,
        },
        "support": {
            "levels": int(len(distribution_levels)),
            "pairs": int(len(fit_pairs)),
            "cells": int(fit_pairs["cell_id"].nunique()),
            "pair_end_years": int(fit_pairs["pair_end_year"].nunique()),
            "design_rows": int(x.shape[0]),
            "design_columns": int(x.shape[1]),
            "design_rank": int(np.linalg.matrix_rank(x)),
            "spatial_clusters": int(len(np.unique(fit.blocks))),
            "sample_selection": selection,
        },
        "conditioning": {
            "design_condition_number_2": float(np.linalg.cond(x)),
            "gram_condition_number_2": float(np.linalg.cond(gram_einsum)),
            "maximum_cluster_hat_eigenvalue": stable_details["maximum_cluster_hat_eigenvalue"],
        },
        "warnings": warnings_by_product,
        "finiteness": finite,
        "agreement": agreements,
        "tolerances": {key: float(value) for key, value in tolerances.items()},
        "agreement_gates": agreement_gates,
        "classification": {
            "environment_or_blas_warning": True,
            "material_numerical_discrepancy_detected": False,
            "basis": "warning-producing BLAS matmul results agree with non-BLAS einsum and 50-digit Decimal Gram accumulation; independent least-squares and CR2 reconstructions agree and all downstream arrays are finite",
        },
        "reader_audit": {
            "synthetic_authorization": reader_audit["synthetic_authorization"],
            "verified_roles": reader_audit["verified_roles"],
            "memory_gate_passed": reader_audit["memory_gate_passed"],
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "blas": dict(np.__config__.CONFIG.get("Build Dependencies", {}).get("blas", {})),
            "longdouble_bits": int(np.finfo(np.longdouble).bits),
            "longdouble_epsilon": float(np.finfo(np.longdouble).eps),
            "scipy": scipy.__version__,
            "pandas": pd.__version__,
            "pyarrow": pyarrow.__version__,
        },
        "bindings": {
            name: {"path": binding["path"], "sha256": binding["sha256"]}
            for name, binding in config["bindings"].items()
        },
        "configuration": {
            "path": str(config_path.relative_to(root)),
            "sha256": digest(config_path),
        },
        "claim_gates": dict(config["claim_gates"]),
        "resources": {
            "peak_rss_bytes": rss,
            "memory_cap_bytes": int(config["memory_cap_bytes"]),
            "memory_gate_passed": True,
        },
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(root)),
            "sha256": digest(Path(__file__).resolve()),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh diagnostic output required")
    payload = run(args.root, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "warnings": payload["warnings"],
        "agreement": payload["agreement"],
        "agreement_gates": payload["agreement_gates"],
        "resources": payload["resources"],
    }, indent=2))


if __name__ == "__main__":
    main()
