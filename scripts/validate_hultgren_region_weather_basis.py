#!/usr/bin/env python3
"""Validate selected raw cell-to-region Hultgren basis aggregations."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["native_lat_index", "native_lon_index"]
FEATURES = [
    "gdd", "kdd",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]


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
    parser.add_argument("--region-basis", type=Path, required=True)
    parser.add_argument("--region-result", type=Path, required=True)
    parser.add_argument("--cell-basis", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--regime", choices=("rainfed", "irrigated"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    built = json.loads(args.region_result.read_text(encoding="utf-8"))
    require(built["status"].startswith("alternative_region_basis"), "region builder status failed")
    require(digest(args.region_basis) == built["output"]["sha256"], "region basis hash differs")
    require(digest(args.cell_basis) == built["sources"]["basis"]["sha256"], "cell basis hash differs")
    require(digest(args.crosswalk) == built["sources"]["crosswalk"]["sha256"], "crosswalk hash differs")

    region = pd.read_parquet(args.region_basis)
    require(len(region) == len(region.drop_duplicates(["harvest_year", "region_key"])), "duplicate region-year rows")
    require(region.regime.eq(args.regime).all(), "regime column differs")
    require(np.isfinite(region.select_dtypes(include=[np.number]).to_numpy()).all(), "nonfinite regional basis")
    metadata = pq.read_metadata(args.region_basis)
    require(metadata.num_row_groups == region.harvest_year.nunique(), "expected one row group per harvest year")

    years = sorted(region.harvest_year.unique())
    selected_years = sorted(set((years[0], years[len(years) // 2], years[-1])))
    candidates = region[region.harvest_year.eq(selected_years[0])].sort_values("region_key")
    positions = np.linspace(0, len(candidates) - 1, 4, dtype=int)
    selected_regions = candidates.iloc[positions].region_key.tolist()
    if "USA.14.630" in set(region.region_key):
        selected_regions.append("USA.14.630")
    selected_regions = sorted(set(selected_regions))

    proxy = f"{args.regime}_maize_ha_proxy_within_region"
    crosswalk = pd.read_parquet(
        args.crosswalk, columns=[*KEYS, "region_key", proxy],
        filters=[("region_key", "in", selected_regions)],
    )
    crosswalk = crosswalk[crosswalk[proxy] > 0]
    cells = pd.read_parquet(args.cell_basis, columns=["harvest_year", *KEYS, *FEATURES])
    details = []
    maximum_difference = 0.0
    for region_key in selected_regions:
        spatial = crosswalk[crosswalk.region_key.eq(region_key)]
        for year in selected_years:
            weather = cells[cells.harvest_year.eq(year)]
            joined = spatial.merge(weather, on=KEYS, how="inner", validate="one_to_one")
            require(len(joined) > 0, f"empty selected aggregation: {region_key} {year}")
            expected = {
                feature: float(np.average(joined[feature], weights=joined[proxy]))
                for feature in FEATURES
            }
            actual = region[(region.region_key == region_key) & (region.harvest_year == year)]
            require(len(actual) == 1, "selected output row absent")
            differences = {feature: abs(float(actual.iloc[0][feature]) - value) for feature, value in expected.items()}
            maximum_difference = max(maximum_difference, *differences.values())
            details.append({"region_key": region_key, "harvest_year": int(year), "cell_rows": len(joined), "maximum_absolute_feature_difference": max(differences.values())})
    require(maximum_difference <= 1e-9, "selected cell-to-region recomputation differs")
    result = {
        "schema": "hultgren_impact_region_weather_basis_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_alternative_region_basis_not_response_damage_or_scc",
        "regime": args.regime,
        "region_basis": {"path": str(args.region_basis), "bytes": args.region_basis.stat().st_size, "sha256": digest(args.region_basis), "rows": len(region), "row_groups": metadata.num_row_groups},
        "checks": {"unique_finite_region_years": True, "selected_recomputations": len(details), "maximum_absolute_feature_difference": maximum_difference, "details": details},
        "source_identity": built["sources"],
        "claim_gates": built["claim_gates"],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, indent=2))


if __name__ == "__main__":
    main()
