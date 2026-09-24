#!/usr/bin/env python3
"""Combine validated rainfed and irrigated Hultgren region weather bases."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["harvest_year", "region_key"]
FEATURES = [
    "gdd", "kdd",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validated_source(path: Path, receipt_path: Path, expected_regime: str) -> tuple[pd.DataFrame, dict]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt["status"] == "validated_alternative_region_basis_not_response_damage_or_scc", "region validation failed")
    require(receipt["regime"] == expected_regime, "validation regime differs")
    require(digest(path) == receipt["region_basis"]["sha256"], "region basis hash differs")
    frame = pd.read_parquet(path)
    require(frame.regime.eq(expected_regime).all(), "basis regime differs")
    require(len(frame) == len(frame.drop_duplicates(KEYS)), "duplicate region-year rows")
    require(np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy()).all(), "nonfinite region basis")
    return frame, receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rainfed", type=Path, required=True)
    parser.add_argument("--rainfed-validation", type=Path, required=True)
    parser.add_argument("--irrigated", type=Path, required=True)
    parser.add_argument("--irrigated-validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    rainfed, rainfed_receipt = validated_source(args.rainfed, args.rainfed_validation, "rainfed")
    irrigated, irrigated_receipt = validated_source(args.irrigated, args.irrigated_validation, "irrigated")
    require(set(rainfed.harvest_year) == set(irrigated.harvest_year), "regime year support differs")

    keep = [*KEYS, "eligible_regime_proxy_ha", "full_regime_proxy_ha", *FEATURES]
    combined = rainfed[keep].merge(
        irrigated[keep], on=KEYS, how="outer", suffixes=("_rainfed", "_irrigated"), validate="one_to_one"
    )
    for regime in ("rainfed", "irrigated"):
        combined[f"eligible_regime_proxy_ha_{regime}"] = combined[f"eligible_regime_proxy_ha_{regime}"].fillna(0.0)
        combined[f"full_regime_proxy_ha_{regime}"] = combined[f"full_regime_proxy_ha_{regime}"].fillna(0.0)
    combined["eligible_combined_proxy_ha"] = (
        combined.eligible_regime_proxy_ha_rainfed + combined.eligible_regime_proxy_ha_irrigated
    )
    combined["full_combined_proxy_ha"] = (
        combined.full_regime_proxy_ha_rainfed + combined.full_regime_proxy_ha_irrigated
    )
    require((combined.eligible_combined_proxy_ha > 0).all(), "zero combined eligible proxy")
    require((combined.full_combined_proxy_ha > 0).all(), "zero combined full proxy")
    combined["eligible_proxy_fraction"] = combined.eligible_combined_proxy_ha / combined.full_combined_proxy_ha
    combined["fixed_irrigated_proxy_share"] = (
        combined.eligible_regime_proxy_ha_irrigated / combined.eligible_combined_proxy_ha
    )
    for feature in FEATURES:
        numerator = (
            combined[f"{feature}_rainfed"].fillna(0.0) * combined.eligible_regime_proxy_ha_rainfed
            + combined[f"{feature}_irrigated"].fillna(0.0) * combined.eligible_regime_proxy_ha_irrigated
        )
        combined[feature] = numerator / combined.eligible_combined_proxy_ha

    columns = [
        *KEYS,
        "eligible_regime_proxy_ha_rainfed", "eligible_regime_proxy_ha_irrigated",
        "full_regime_proxy_ha_rainfed", "full_regime_proxy_ha_irrigated",
        "eligible_combined_proxy_ha", "full_combined_proxy_ha",
        "eligible_proxy_fraction", "fixed_irrigated_proxy_share", *FEATURES,
    ]
    combined = combined[columns].sort_values(KEYS).reset_index(drop=True)
    require(np.isfinite(combined.select_dtypes(include=[np.number]).to_numpy()).all(), "nonfinite combined basis")
    require(combined.fixed_irrigated_proxy_share.between(0.0, 1.0).all(), "invalid irrigated share")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    try:
        for _, year_frame in combined.groupby("harvest_year", sort=True):
            table = pa.Table.from_pandas(year_frame, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(args.output, table.schema, compression="zstd")
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
    require(writer is not None, "empty combined basis")

    annual = []
    for year, group in combined.groupby("harvest_year", sort=True):
        annual.append({
            "harvest_year": int(year),
            "regions": int(len(group)),
            "weighted_eligible_proxy_fraction": float(
                group.eligible_combined_proxy_ha.sum() / group.full_combined_proxy_ha.sum()
            ),
            "eligible_proxy_weighted_irrigated_share": float(
                group.eligible_regime_proxy_ha_irrigated.sum() / group.eligible_combined_proxy_ha.sum()
            ),
        })
    receipt = {
        "schema": "hultgren_combined_region_weather_basis/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_arithmetic_regime_combination_not_response_damage_or_scc",
        "sources": {
            "rainfed": {"path": str(args.rainfed), "sha256": digest(args.rainfed)},
            "rainfed_validation": {"path": str(args.rainfed_validation), "sha256": digest(args.rainfed_validation)},
            "irrigated": {"path": str(args.irrigated), "sha256": digest(args.irrigated)},
            "irrigated_validation": {"path": str(args.irrigated_validation), "sha256": digest(args.irrigated_validation)},
        },
        "output": {
            "path": str(args.output), "bytes": args.output.stat().st_size,
            "sha256": digest(args.output), "rows": int(len(combined)),
            "regions": int(combined.region_key.nunique()), "years": int(combined.harvest_year.nunique()),
        },
        "annual_audit": annual,
        "method": "average already-nonlinear regime-specific region bases using eligible MIRCA intersection proxy hectares",
        "interpretation": "fixed_irrigated_proxy_share is a weather-basis mixing weight, not an empirical adaptation response or the authors' equipped-irrigation moderator",
        "claim_gates": {
            "source_region_bases_validated": True,
            "regime_combination_validated": True,
            "adaptation_validated": False,
            "response_damage_or_scc_validated": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
        "upstream_claim_gates": {
            "rainfed": rainfed_receipt["claim_gates"], "irrigated": irrigated_receipt["claim_gates"]
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "output": receipt["output"], "annual_audit": annual}, indent=2))


if __name__ == "__main__":
    main()
