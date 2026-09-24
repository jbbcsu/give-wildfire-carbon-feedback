#!/usr/bin/env python3
"""Validate the alternative MIRCA-weighted Hultgren region/grid crosswalk."""

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
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--builder-receipt", type=Path, required=True)
    parser.add_argument("--resource-receipt", type=Path, required=True)
    parser.add_argument("--iroquois-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    builder = json.loads(args.builder_receipt.read_text(encoding="utf-8"))
    resource = json.loads(args.resource_receipt.read_text(encoding="utf-8"))
    iroquois = json.loads(args.iroquois_receipt.read_text(encoding="utf-8"))
    require(builder["status"].startswith("alternative_half_degree"), "builder status failed")
    require(resource["status"] == "completed" and resource["sampled_peak_group_rss_bytes"] <= 512 * 2**20, "resource gate failed")
    require(digest(args.crosswalk) == builder["output"]["sha256"], "crosswalk hash differs")

    frame = pd.read_parquet(args.crosswalk)
    require(len(frame) == builder["output"]["rows"], "crosswalk row count differs")
    require(len(frame) == len(frame.drop_duplicates(["native_lat_index", "native_lon_index", "region_key"])), "duplicate cell-region rows")
    numeric = frame.select_dtypes(include=[np.number])
    require(np.isfinite(numeric.to_numpy()).all(), "crosswalk contains nonfinite numeric values")
    require((frame.cell_overlap_fraction > 0).all() and (frame.cell_overlap_fraction <= 1.0 + 1e-12).all(), "invalid cell overlap fraction")

    maximum_weight_error = 0.0
    for regime in ("rainfed", "irrigated", "combined"):
        proxy = f"{regime}_maize_ha_proxy_within_region" if regime != "combined" else "combined_maize_ha_proxy_within_region"
        weight = f"{regime}_weight_within_region"
        grouped = frame.groupby("region_key")[[proxy, weight]].sum()
        positive = grouped[proxy] > 0
        error = float((grouped.loc[positive, weight] - 1.0).abs().max())
        require(error <= 1e-12, f"{regime} within-region weights do not sum to one")
        require((grouped.loc[~positive, weight] == 0).all(), f"{regime} zero-support weights are nonzero")
        maximum_weight_error = max(maximum_weight_error, error)

    check = frame[frame.region_key.eq("USA.14.630")]
    require(len(check) == 6, "Iroquois crosswalk no longer has six cells")
    rainfed = float(check.rainfed_maize_ha_proxy_within_region.sum())
    irrigated = float(check.irrigated_maize_ha_proxy_within_region.sum())
    combined = rainfed + irrigated
    irrigated_share = irrigated / combined
    prior = iroquois["spatial_audit"]
    area_relative_difference = combined / prior["mirca_within_author_boundary_maize_area_proxy_ha"] - 1.0
    share_difference = irrigated_share - prior["mirca_within_boundary_irrigated_share_proxy"]
    require(abs(area_relative_difference) <= 5e-5, "Iroquois global/equal-area area proxy parity failed")
    require(abs(share_difference) <= 5e-5, "Iroquois global/equal-area irrigation parity failed")

    audit = builder["allocation_audit"]
    require(abs(audit["author_corn_minus_mirca_global_fraction"]) <= 0.01, "author/MIRCA global corn totals differ by more than one percent")
    require(audit["combined_crop_fraction_in_cells_without_region_intersection"] <= 1e-5, "unmapped crop fraction exceeds tolerance")
    require(audit["log1p_region_proxy_author_correlation"] >= 0.8, "regional proxy/author size correlation below diagnostic floor")

    result = {
        "schema": "hultgren_impact_region_grid_crosswalk_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_alternative_within_region_mirca_weight_proxy_not_sage_replication",
        "crosswalk": {"path": str(args.crosswalk), "bytes": args.crosswalk.stat().st_size, "sha256": digest(args.crosswalk), "rows": len(frame)},
        "checks": {
            "unique_cell_region_rows": True,
            "finite_positive_intersections": True,
            "maximum_within_region_weight_sum_error": maximum_weight_error,
            "iroquois_cells": len(check),
            "iroquois_combined_proxy_ha": combined,
            "iroquois_irrigated_share": irrigated_share,
            "iroquois_area_relative_difference_vs_prior_epsg5070_check": area_relative_difference,
            "iroquois_irrigated_share_difference_vs_prior_epsg5070_check": share_difference,
            "global_author_corn_minus_mirca_fraction": audit["author_corn_minus_mirca_global_fraction"],
            "crop_fraction_in_cells_without_region": audit["combined_crop_fraction_in_cells_without_region_intersection"],
            "log1p_region_proxy_author_correlation": audit["log1p_region_proxy_author_correlation"],
        },
        "source_identity": builder["sources"],
        "builder_implementation": builder["implementation"],
        "point_export_implementation": builder["point_export_implementation"],
        "resource": resource,
        "claim_gates": builder["claim_gates"],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, indent=2))


if __name__ == "__main__":
    main()
