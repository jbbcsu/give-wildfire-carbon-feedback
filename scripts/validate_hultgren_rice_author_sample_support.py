#!/usr/bin/env python3
"""Independently validate recovered Hultgren rice source-domain summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


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
    parser.add_argument("--support", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--chunk-rows", type=int, default=20_000)
    args = parser.parse_args()
    require(not args.out.exists(), "fresh output required")
    support = json.loads(args.support.read_text(encoding="utf-8"))
    require(support["status"] == "published_rice_estimation_sample_support_recovered", "support build failed")
    source = Path(support["source"]["path"])
    require(digest(source) == support["source"]["sha256"], "source hash differs")
    variables = list(support["quantiles"])
    groups = support["absorbed_effect_singleton_groups"]
    require(args.chunk_rows > 0, "chunk rows must be positive")
    pieces = []
    with pd.read_stata(
        source, columns=["ln_yield", *groups, *variables], convert_categoricals=False, iterator=True
    ) as reader:
        while True:
            try:
                chunk = reader.read(args.chunk_rows)
            except StopIteration:
                break
            if chunk.empty:
                break
            selected = chunk.dropna()
            if not selected.empty:
                pieces.append(selected.copy())
    frame = pd.concat(pieces, ignore_index=True)
    initial_rows = len(frame)
    removed = []
    while True:
        counts = {column: frame.groupby(column)[column].transform("size") for column in groups}
        keep = np.logical_and.reduce([values.gt(1).to_numpy() for values in counts.values()])
        dropped = int((~keep).sum())
        removed.append(dropped)
        if dropped == 0:
            break
        frame = frame.loc[keep].copy()
    maximum_error = 0.0
    for column in variables:
        values = frame[column].to_numpy(dtype=np.float64)
        observed = {
            "minimum": float(np.min(values)), "p01": float(np.quantile(values, 0.01)),
            "p99": float(np.quantile(values, 0.99)), "maximum": float(np.max(values)),
        }
        for name, value in observed.items():
            maximum_error = max(maximum_error, abs(value - support["quantiles"][column][name]))
    require(initial_rows == support["counts"]["complete_case_rows_before_singleton_removal"], "complete rows differ")
    require(len(frame) == support["counts"]["estimation_sample_rows"], "estimation rows differ")
    require(maximum_error == 0.0, "support quantiles differ")
    result = {
        "schema": "hultgren_rice_author_sample_support_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_published_rice_estimation_sample_support",
        "support": {"path": str(args.support), "sha256": digest(args.support)},
        "checks": {
            "complete_case_rows": initial_rows,
            "singleton_rows_removed_by_iteration": removed,
            "estimation_sample_rows": len(frame),
            "country_year_clusters": int(frame.adm0_year.nunique()),
            "adm1_clusters": int(frame.adm1_fact.nunique()),
            "maximum_absolute_summary_error": maximum_error,
        },
        "claim_gates": {
            "author_primitive_domain_validated": True,
            "transport_application_domain_not_yet_applied": True,
            "response_damage_or_scc_validated": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, indent=2))


if __name__ == "__main__":
    main()
