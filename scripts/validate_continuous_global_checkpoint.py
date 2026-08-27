#!/usr/bin/env python3
"""Verify the tracked checkpoint against ignored continuous-panel artifacts.

This validator checks file hashes and observed-outcome counts only. It does not
fit a response model or authorize causal, damage, projection, or SCC use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


PROJECT = Path(__file__).resolve().parents[1]
BASE = PROJECT / "data/interim/continuous_global_panel_1982_2016_v1"
OUTPUTS = PROJECT / "outputs/continuous_global_panel_1982_2016_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parquet_counts(path: Path) -> tuple[int, int]:
    parquet = pq.ParquetFile(path)
    rows = parquet.metadata.num_rows
    observed = pq.read_table(path, columns=["yield_observed"]).column(0)
    observed_count = sum(bool(value.as_py()) for chunk in observed.chunks for value in chunk)
    return rows, observed_count


def require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, found {actual!r}")


def validate(checkpoint_path: Path) -> dict[str, object]:
    checkpoint = json.loads(checkpoint_path.read_text())
    require_equal(checkpoint["families_stacked"], False, "families_stacked")
    for gate in (
        "fit_performed", "causal_interpretation_authorized",
        "damage_calculation_authorized", "future_projection_authorized",
        "scc_authorized",
    ):
        require_equal(checkpoint[gate], False, gate)

    assembly = checkpoint["middle_feature_assembly"]
    assembly_path = PROJECT / assembly["receipt"]
    require_equal(sha256(assembly_path), assembly["receipt_sha256"], "middle assembly receipt hash")

    verified: dict[str, object] = {}
    for name, expected in checkpoint["continuous_candidates"].items():
        crop, family = name.split("_", 1)
        candidate_path = BASE / "continuous_candidates" / f"{crop}_1982_2016_{family}.parquet"
        receipt_path = OUTPUTS / f"{crop}_1982_2016_{family}_assembly_receipt.json"
        require_equal(sha256(candidate_path), expected["candidate_sha256"], f"{name} candidate hash")
        require_equal(sha256(receipt_path), expected["receipt_sha256"], f"{name} receipt hash")
        rows, observed = parquet_counts(candidate_path)
        require_equal(rows, expected["rows"], f"{name} rows")
        require_equal(observed, expected["observed_outcomes"], f"{name} observed outcomes")
        verified[name] = {"rows": rows, "observed_outcomes": observed}

    common_verified: dict[str, object] = {}
    for crop, expected in checkpoint["direct_scpdsi_common_support"].items():
        direct_path = BASE / "common_support" / f"{crop}_1982_2016_direct_view.parquet"
        scpdsi_path = BASE / "common_support" / f"{crop}_1982_2016_scpdsi_view.parquet"
        validation_path = OUTPUTS / f"{crop}_1982_2016_common_support_validation.json"
        require_equal(sha256(validation_path), expected["validation_receipt_sha256"], f"{crop} common validation hash")
        direct_counts = parquet_counts(direct_path)
        scpdsi_counts = parquet_counts(scpdsi_path)
        require_equal(direct_counts, scpdsi_counts, f"{crop} common-view counts")
        require_equal(direct_counts[0], expected["rows"], f"{crop} common rows")
        require_equal(direct_counts[1], expected["observed_outcomes"], f"{crop} common observed outcomes")
        common_verified[crop] = {"rows": direct_counts[0], "observed_outcomes": direct_counts[1]}

    return {
        "schema_version": 1,
        "status": "checkpoint_verified_against_local_ignored_artifacts",
        "checkpoint": str(checkpoint_path.resolve().relative_to(PROJECT)),
        "continuous_candidates": verified,
        "common_support": common_verified,
        "families_stacked": False,
        "fit_performed": False,
        "causal_interpretation_authorized": False,
        "damage_calculation_authorized": False,
        "future_projection_authorized": False,
        "scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=PROJECT / "data/provenance/continuous_global_panel_checkpoint_20260827.json",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = validate(args.checkpoint)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
