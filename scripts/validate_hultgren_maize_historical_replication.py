#!/usr/bin/env python3
"""Validate a bounded historical-data reproduction of Hultgren maize estimates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data/raw/hultgren_response/historical_git/dae5fe8d0d4a260328e4baa45b547368bd6790b3/corn_gmfd_v1_ready.dta"
DEFAULT_PUBLISHED = ROOT / "data/interim/hultgren_maize_response_20260923"
DEFAULT_REPLICATED = ROOT / "data/interim/hultgren_historical_replication"
DEFAULT_OUTPUT = ROOT / "data/provenance/hultgren_maize_historical_replication_validation_20260923.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_numeric_csv(path: Path, value: str) -> tuple[list[dict[str, str]], np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows, np.asarray([float(row[value]) for row in rows], dtype=np.float64)


def read_metadata(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value.strip()
    return result


def audit_phase_sums(path: Path, chunk_size: int = 50_000) -> dict[str, object]:
    columns = ["GMFD_monthly_prcp_poly_1", "GMFD_monthly_prcp_poly_2"] + [
        f"prcp_poly_{power}_bin{phase}" for power in (1, 2) for phase in (1, 2, 3)
    ]
    observations = 0
    results: dict[str, object] = {}
    for power in (1, 2):
        results[str(power)] = {"max_absolute_error": 0.0, "max_scaled_error": 0.0, "nonfinite_rows": 0}

    with pd.read_stata(path, columns=columns, iterator=True, convert_categoricals=False) as reader:
        while True:
            try:
                chunk = reader.read(chunk_size)
            except StopIteration:
                break
            if chunk.empty:
                break
            observations += len(chunk)
            for power in (1, 2):
                total = chunk[f"GMFD_monthly_prcp_poly_{power}"].to_numpy(dtype=np.float64)
                phase_sum = sum(
                    chunk[f"prcp_poly_{power}_bin{phase}"].to_numpy(dtype=np.float64)
                    for phase in (1, 2, 3)
                )
                finite = np.isfinite(total) & np.isfinite(phase_sum)
                error = np.abs(total[finite] - phase_sum[finite])
                scaled = error / np.maximum(np.abs(total[finite]), 1.0)
                entry = results[str(power)]
                entry["nonfinite_rows"] += int((~finite).sum())
                if error.size:
                    entry["max_absolute_error"] = max(entry["max_absolute_error"], float(error.max()))
                    entry["max_scaled_error"] = max(entry["max_scaled_error"], float(scaled.max()))

    return {"observations": observations, "chunk_size": chunk_size, "powers": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--published", type=Path, default=DEFAULT_PUBLISHED)
    parser.add_argument("--replicated", type=Path, default=DEFAULT_REPLICATED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    for path in (args.data, args.published, args.replicated):
        if not path.exists():
            raise FileNotFoundError(path)

    pub_c_rows, pub_c = read_numeric_csv(args.published / "coefficients.csv", "estimate")
    rep_c_rows, rep_c = read_numeric_csv(args.replicated / "coefficients.csv", "estimate")
    pub_v_rows, pub_v = read_numeric_csv(args.published / "covariance.csv", "covariance")
    rep_v_rows, rep_v = read_numeric_csv(args.replicated / "covariance.csv", "covariance")

    coefficient_keys = [(r["index"], r["term"]) for r in pub_c_rows]
    replicated_coefficient_keys = [(r["index"], r["term"]) for r in rep_c_rows]
    covariance_keys = [(r["row_index"], r["column_index"], r["row_term"], r["column_term"]) for r in pub_v_rows]
    replicated_covariance_keys = [(r["row_index"], r["column_index"], r["row_term"], r["column_term"]) for r in rep_v_rows]
    if coefficient_keys != replicated_coefficient_keys or covariance_keys != replicated_covariance_keys:
        raise AssertionError("published and replicated term order differs")

    coefficient_difference = rep_c - pub_c
    covariance_difference = rep_v - pub_v
    coefficient_l2_relative = float(np.linalg.norm(coefficient_difference) / np.linalg.norm(pub_c))
    covariance_l2_relative = float(np.linalg.norm(covariance_difference) / np.linalg.norm(pub_v))
    coefficient_max_absolute = float(np.max(np.abs(coefficient_difference)))
    covariance_max_absolute = float(np.max(np.abs(covariance_difference)))

    pub_meta = read_metadata(args.published / "metadata.txt")
    rep_meta = read_metadata(args.replicated / "metadata.txt")
    exact_metadata_fields = [
        "N", "N_full", "N_clust1", "N_clust2", "coefficient_count", "depvar", "cmd",
        "vce", "clustvar", "absvars", "indepvars",
    ]
    metadata_exact = all(pub_meta.get(field) == rep_meta.get(field) for field in exact_metadata_fields)
    r2_max_absolute = max(abs(float(pub_meta[field]) - float(rep_meta[field])) for field in ("r2", "r2_within"))

    phase_audit = audit_phase_sums(args.data)
    phase_gate = (
        phase_audit["observations"] == 412_282
        and all(v["nonfinite_rows"] == 0 and v["max_scaled_error"] <= 2e-7 for v in phase_audit["powers"].values())
    )
    gates = {
        "sample_and_model_metadata_exact": metadata_exact and r2_max_absolute <= 1e-12,
        "coefficient_vector_numerically_reproduced": coefficient_max_absolute <= 1e-12 and coefficient_l2_relative <= 1e-12,
        "covariance_matrix_numerically_reproduced": covariance_max_absolute <= 1e-6 and covariance_l2_relative <= 1e-5,
        "phase_polynomials_sum_to_full_season_polynomials": phase_gate,
    }
    if not all(gates.values()):
        raise AssertionError(f"historical replication gate failed: {gates}")

    payload = {
        "schema": "hultgren_maize_historical_replication_validation/v1",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "repository": "https://gitlab.com/ClimateImpactLab/cil-ag-replication-package",
            "historical_commit": "dae5fe8d0d4a260328e4baa45b547368bd6790b3",
            "git_blob_sha1": "da2ac691b32db1b98dea95b8f0ff4256659c8a96",
            "dataset_path": str(args.data.relative_to(ROOT)),
            "dataset_bytes": args.data.stat().st_size,
            "dataset_sha256": sha256(args.data),
            "redistribution": "prohibited by project policy because no source-repository license was located",
        },
        "published_estimate": {
            "coefficient_sha256": sha256(args.published / "coefficients.csv"),
            "covariance_sha256": sha256(args.published / "covariance.csv"),
            "metadata_sha256": sha256(args.published / "metadata.txt"),
        },
        "replication": {
            "script": "scripts/hultgren_reproduce_maize_historical.do",
            "coefficient_sha256": sha256(args.replicated / "coefficients.csv"),
            "covariance_sha256": sha256(args.replicated / "covariance.csv"),
            # Stata .ster serialization embeds run-specific metadata; validate its
            # machine-readable coefficient and covariance exports instead.
            "estimate_bytes": (args.replicated / "corn_replicated.ster").stat().st_size,
            "metadata_sha256": sha256(args.replicated / "metadata.txt"),
            "coefficient_max_absolute_difference": coefficient_max_absolute,
            "coefficient_l2_relative_difference": coefficient_l2_relative,
            "covariance_max_absolute_difference": covariance_max_absolute,
            "covariance_l2_relative_difference": covariance_l2_relative,
            "r2_max_absolute_difference": r2_max_absolute,
            "exact_metadata_fields": exact_metadata_fields,
            "published_metadata": pub_meta,
            "replicated_metadata": rep_meta,
        },
        "phase_arithmetic": phase_audit,
        "validation_gates": gates,
        "claim_gates": {
            "historical_response_reproduced": True,
            "primitive_phase_feature_arithmetic_audited": True,
            "future_climate_projection_validated": False,
            "damage_estimate_validated": False,
            "scc_estimate_validated": False,
        },
        "interpretation": (
            "The public historical data blob reproduces the published sample, model metadata, and coefficient vector "
            "to numerical precision; covariance differences are small and consistent with numerical/package-version "
            "variation. This validates the historical response regression, not future impacts, damages, or SCC."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "output": str(args.output), "gates": gates}, indent=2))


if __name__ == "__main__":
    main()
