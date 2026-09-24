#!/usr/bin/env python3
"""Independently validate selected rainfed/irrigated region combinations."""

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
KEYS = ["harvest_year", "region_key"]
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


def read_year(path: Path, year: int) -> pd.DataFrame:
    parquet = pq.ParquetFile(path)
    for row_group in range(parquet.num_row_groups):
        table = parquet.read_row_group(row_group)
        frame = table.to_pandas()
        if int(frame.harvest_year.iloc[0]) == year:
            require(frame.harvest_year.eq(year).all(), "row group mixes years")
            return frame
    raise ValueError(f"year absent: {year}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--combined-receipt", type=Path, required=True)
    parser.add_argument("--rainfed", type=Path, required=True)
    parser.add_argument("--irrigated", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    receipt = json.loads(args.combined_receipt.read_text(encoding="utf-8"))
    require(receipt["status"] == "validated_arithmetic_regime_combination_not_response_damage_or_scc", "combination receipt failed")
    require(digest(args.combined) == receipt["output"]["sha256"], "combined hash differs")
    require(digest(args.rainfed) == receipt["sources"]["rainfed"]["sha256"], "rainfed hash differs")
    require(digest(args.irrigated) == receipt["sources"]["irrigated"]["sha256"], "irrigated hash differs")

    metadata = pq.read_metadata(args.combined)
    years = [int(item["harvest_year"]) for item in receipt["annual_audit"]]
    selected_years = sorted(set((years[0], years[len(years) // 2], years[-1])))
    details = []
    maximum_difference = 0.0
    for year in selected_years:
        combined = read_year(args.combined, year).set_index("region_key")
        rainfed = read_year(args.rainfed, year).set_index("region_key")
        irrigated = read_year(args.irrigated, year).set_index("region_key")
        positions = np.linspace(0, len(combined) - 1, 7, dtype=int)
        regions = combined.sort_index().iloc[positions].index.tolist()
        for region in regions:
            actual = combined.loc[region]
            rf_area = float(rainfed.loc[region, "eligible_regime_proxy_ha"]) if region in rainfed.index else 0.0
            ir_area = float(irrigated.loc[region, "eligible_regime_proxy_ha"]) if region in irrigated.index else 0.0
            require(rf_area + ir_area > 0, "selected region has zero eligible proxy")
            differences = {}
            for feature in FEATURES:
                rf_value = float(rainfed.loc[region, feature]) if rf_area else 0.0
                ir_value = float(irrigated.loc[region, feature]) if ir_area else 0.0
                expected = (rf_value * rf_area + ir_value * ir_area) / (rf_area + ir_area)
                differences[feature] = abs(float(actual[feature]) - expected)
            share_expected = ir_area / (rf_area + ir_area)
            differences["fixed_irrigated_proxy_share"] = abs(float(actual.fixed_irrigated_proxy_share) - share_expected)
            local_max = max(differences.values())
            maximum_difference = max(maximum_difference, local_max)
            details.append({
                "harvest_year": year, "region_key": region,
                "rainfed_eligible_proxy_ha": rf_area, "irrigated_eligible_proxy_ha": ir_area,
                "maximum_absolute_difference": local_max,
            })
    require(maximum_difference <= 1e-9, "selected independent combinations differ")
    result = {
        "schema": "hultgren_combined_region_weather_basis_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "independently_validated_regime_combination_not_response_damage_or_scc",
        "combined": {"path": str(args.combined), "bytes": args.combined.stat().st_size, "sha256": digest(args.combined), "row_groups": metadata.num_row_groups},
        "checks": {"selected_recomputations": len(details), "maximum_absolute_difference": maximum_difference, "details": details},
        "claim_gates": receipt["claim_gates"],
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, indent=2))


if __name__ == "__main__":
    main()
