#!/usr/bin/env python3
"""Validate a machine-readable export of the pinned Hultgren maize estimate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def git_blob_digest(path: Path) -> str:
    size = path.stat().st_size
    hasher = hashlib.sha1(b"blob " + str(size).encode() + b"\0")
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_metadata(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        key, separator, value = line.partition("=")
        if not separator or key in result:
            raise ValueError(f"Malformed or duplicate metadata field: {line!r}")
        result[key] = value.strip()
    return result


def finite_number(value: str, context: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite number in {context}: {value}")
    return number


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--coefficients", type=Path, required=True)
    parser.add_argument("--covariance", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = tomllib.loads(config_path.read_text())
    raw_dir = ROOT / config["local_raw_directory"]
    tree_path = ROOT / config["source_tree_snapshot"]
    tree_snapshot = json.loads(tree_path.read_text())
    if tree_snapshot["commit"] != config["source_commit"]:
        raise ValueError("Pinned tree commit differs from source config")
    tree_blobs = {
        entry["path"]: entry["id"]
        for entry in tree_snapshot["all_paths"]
        if entry["type"] == "blob"
    }
    source_records = []
    for expected in config["files"]:
        path = raw_dir / expected["local_filename"]
        actual = {
            "local_filename": expected["local_filename"],
            "repository_path": expected["repository_path"],
            "bytes": path.stat().st_size,
            "sha256": digest(path),
            "git_blob_sha1": git_blob_digest(path),
        }
        for field in ("bytes", "sha256", "git_blob_sha1"):
            if actual[field] != expected[field]:
                raise ValueError(f"Source mismatch for {path}: {field}")
        if tree_blobs.get(expected["repository_path"]) != expected["git_blob_sha1"]:
            raise ValueError(f"Pinned tree path/blob mismatch: {expected['repository_path']}")
        source_records.append(actual)

    with args.coefficients.open(newline="") as stream:
        coefficients = list(csv.DictReader(stream))
    if len(coefficients) != 49:
        raise ValueError(f"Expected 49 coefficients, found {len(coefficients)}")
    terms = [row["term"] for row in coefficients]
    if len(set(terms)) != 49 or terms[-1] != "_cons":
        raise ValueError("Coefficient terms must be unique and end with _cons")
    if [int(row["index"]) for row in coefficients] != list(range(1, 50)):
        raise ValueError("Coefficient indices are not exactly 1..49")
    for row in coefficients:
        finite_number(row["estimate"], f"coefficient {row['term']}")

    with args.covariance.open(newline="") as stream:
        covariance = list(csv.DictReader(stream))
    if len(covariance) != 49 * 49:
        raise ValueError(f"Expected 2401 covariance entries, found {len(covariance)}")
    matrix: dict[tuple[int, int], float] = {}
    for row in covariance:
        i, j = int(row["row_index"]), int(row["column_index"])
        if not (1 <= i <= 49 and 1 <= j <= 49):
            raise ValueError("Covariance index outside 1..49")
        if row["row_term"] != terms[i - 1] or row["column_term"] != terms[j - 1]:
            raise ValueError(f"Covariance term/index mismatch at ({i}, {j})")
        if (i, j) in matrix:
            raise ValueError(f"Duplicate covariance entry ({i}, {j})")
        matrix[i, j] = finite_number(row["covariance"], f"covariance ({i}, {j})")
    max_asymmetry = max(abs(matrix[i, j] - matrix[j, i]) for i in range(1, 50) for j in range(1, 50))
    if max_asymmetry > 1e-12:
        raise ValueError(f"Covariance matrix is not symmetric: max difference {max_asymmetry}")
    minimum_variance = min(matrix[i, i] for i in range(1, 50))
    if minimum_variance < 0:
        raise ValueError(f"Negative covariance diagonal: {minimum_variance}")

    metadata = read_metadata(args.metadata)
    required_metadata = {
        "stata_version", "stata_flavor", "coefficient_count", "N", "N_full",
        "N_clust1", "N_clust2", "r2", "r2_within", "depvar", "cmd", "vce",
        "clustvar", "absvars", "indepvars",
    }
    if set(metadata) != required_metadata:
        raise ValueError(f"Metadata fields differ: {sorted(set(metadata) ^ required_metadata)}")
    if int(metadata["coefficient_count"]) != 49:
        raise ValueError("Metadata coefficient count differs")
    if metadata["indepvars"].split() != terms:
        raise ValueError("Metadata indepvars do not exactly match the exported coefficient terms")
    if metadata["depvar"] != "ln_yield" or metadata["cmd"] != "reghdfe":
        raise ValueError("Unexpected dependent variable or estimator")

    missing_data_path = raw_dir / config["missing_required_impact_data"]
    receipt = {
        "schema_version": 1,
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.relative_to(ROOT)), "sha256": digest(config_path)},
        "source": {
            "repository": config["source_repository"],
            "commit": config["source_commit"],
            "license_status": config["license_status"],
            "tree_snapshot": {"path": config["source_tree_snapshot"], "sha256": digest(tree_path)},
            "files": source_records,
        },
        "estimate_export": {
            "coefficient_csv": {"path": str(args.coefficients), "sha256": digest(args.coefficients), "rows": 49},
            "covariance_csv": {"path": str(args.covariance), "sha256": digest(args.covariance), "rows": 2401},
            "metadata_txt": {"path": str(args.metadata), "sha256": digest(args.metadata), **metadata},
            "max_covariance_asymmetry": max_asymmetry,
            "minimum_covariance_diagonal": minimum_variance,
        },
        "missing_required_impact_data": {
            "repository_relative_path": config["missing_required_impact_data"],
            "present_in_local_source_snapshot": missing_data_path.exists(),
        },
        "claim_gates": {
            "source_identity_validated": True,
            "estimate_export_validated": True,
            "local_response_curve_reproduced": False,
            "future_projection_validated": False,
            "damage_estimate_validated": False,
            "scc_estimate_validated": False,
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt["claim_gates"], sort_keys=True))


if __name__ == "__main__":
    main()
