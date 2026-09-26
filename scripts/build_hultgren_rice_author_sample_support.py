#!/usr/bin/env python3
"""Recover exact published rice estimation-sample primitive support."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WEATHER = [
    "gdd", "kdd", "tmin",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]
MODERATORS = ["ln_gdppc", "irrigated_share", "lr_tmax_crop", "lr_prcp_crop"]
SINGLETON_GROUPS = ["uid", "adm0_year", "adm1_fact"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--history-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunk-rows", type=int, default=20_000)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    metadata = dict(
        line.split("=", 1) for line in args.metadata.read_text(encoding="utf-8").splitlines()
    )
    history = json.loads(args.history_audit.read_text(encoding="utf-8"))
    panel = history["rice_regression_panel"]
    require(history["status"] == "historical_public_rice_regression_panel_recovered", "history audit failed")
    require(panel["sha256"] == digest(args.sample), "rice panel hash differs from history audit")

    columns = ["ln_yield", *SINGLETON_GROUPS, *MODERATORS, *WEATHER]
    require(args.chunk_rows > 0, "chunk rows must be positive")
    pieces = []
    source_rows = 0
    with pd.read_stata(args.sample, columns=columns, convert_categoricals=False, iterator=True) as reader:
        while True:
            try:
                chunk = reader.read(args.chunk_rows)
            except StopIteration:
                break
            if chunk.empty:
                break
            source_rows += len(chunk)
            selected = chunk.dropna()
            if not selected.empty:
                pieces.append(selected.copy())
    complete = pd.concat(pieces, ignore_index=True)
    require(np.isfinite(complete[MODERATORS + WEATHER].to_numpy(dtype=np.float64)).all(), "nonfinite complete rows")
    full_rows = len(complete)
    rounds = []
    while True:
        singleton = np.zeros(len(complete), dtype=bool)
        group_counts = {}
        for column in SINGLETON_GROUPS:
            current = complete[column].map(complete[column].value_counts()).eq(1).to_numpy()
            singleton |= current
            group_counts[column] = int(current.sum())
        removed = int(singleton.sum())
        rounds.append({"rows_removed": removed, "singleton_rows_by_group_before_union": group_counts})
        if removed == 0:
            break
        complete = complete.loc[~singleton].copy()
    estimation_rows = len(complete)
    require(full_rows == int(config["full_observations"]) == int(metadata["N_full"]), "full observation count differs")
    require(estimation_rows == int(config["estimation_observations"]) == int(metadata["N"]), "estimation observation count differs")
    require(complete.adm0_year.nunique() == int(config["country_year_clusters"]) == int(metadata["N_clust1"]), "country-year clusters differ")
    require(complete.adm1_fact.nunique() == int(config["adm1_clusters"]) == int(metadata["N_clust2"]), "ADM1 clusters differ")

    quantiles = {}
    for column in MODERATORS + WEATHER:
        values = complete[column].to_numpy(dtype=np.float64)
        quantiles[column] = {
            "minimum": float(values.min()),
            "p01": float(np.quantile(values, 0.01)),
            "p99": float(np.quantile(values, 0.99)),
            "maximum": float(values.max()),
        }
    result = {
        "schema": "hultgren_rice_author_sample_support/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "published_rice_estimation_sample_support_recovered",
        "source": {
            "path": str(args.sample), "bytes": args.sample.stat().st_size,
            "sha256": digest(args.sample), "git_blob_sha1": panel["git_blob_sha1"],
            "historical_repository_path": panel["path"],
            "reachable_commit": panel["reachable_commit"],
            "repository_license_located": panel["repository_license_located"],
            "raw_source_redistributed": False,
        },
        "counts": {
            "source_rows": source_rows,
            "complete_case_rows_before_singleton_removal": full_rows,
            "estimation_sample_rows": estimation_rows,
            "country_year_clusters": int(complete.adm0_year.nunique()),
            "adm1_clusters": int(complete.adm1_fact.nunique()),
            "singleton_removal_rounds": rounds,
        },
        "complete_case_columns": ["ln_yield", *MODERATORS, *WEATHER],
        "absorbed_effect_singleton_groups": SINGLETON_GROUPS,
        "quantiles": quantiles,
        "method": (
            "drop rows incomplete on outcome, published moderators, or published rice weather primitives; "
            "then iteratively remove singleton uid, country-year, or ADM1 absorbed-effect groups until stable"
        ),
        "claim_gates": {
            "prepared_source_panel_recovered": True,
            "published_estimation_sample_count_reproduced": True,
            "author_primitive_minmax_and_p01_p99_available": True,
            "future_response_damage_or_scc_validated": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "counts": result["counts"]}, indent=2))


if __name__ == "__main__":
    main()
