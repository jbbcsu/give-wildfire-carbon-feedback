#!/usr/bin/env python3
"""Aggregate cell-level Hultgren weather bases to public impact regions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["native_lat_index", "native_lon_index"]
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", type=Path, required=True)
    parser.add_argument("--basis-validation", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--crosswalk-validation", type=Path, required=True)
    parser.add_argument("--regime", choices=("rainfed", "irrigated"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.output.with_suffix(args.output.suffix + ".result.json")
    partial_path = args.output.with_suffix(args.output.suffix + ".partial")
    require(not args.output.exists() and not result_path.exists() and not partial_path.exists(), "fresh outputs required")

    basis_validation = json.loads(args.basis_validation.read_text(encoding="utf-8"))
    crosswalk_validation = json.loads(args.crosswalk_validation.read_text(encoding="utf-8"))
    require(basis_validation["status"] == "validated_grid_basis_not_response_damage_or_scc", "basis validation failed")
    require(crosswalk_validation["status"].startswith("validated_alternative_within_region"), "crosswalk validation failed")
    require(digest(args.basis) == basis_validation["basis"]["sha256"], "basis hash differs")
    require(digest(args.crosswalk) == crosswalk_validation["crosswalk"]["sha256"], "crosswalk hash differs")

    proxy = f"{args.regime}_maize_ha_proxy_within_region"
    crosswalk = pd.read_parquet(args.crosswalk, columns=[*KEYS, "region_key", proxy])
    crosswalk = crosswalk[crosswalk[proxy] > 0].copy()
    require(len(crosswalk) == len(crosswalk.drop_duplicates([*KEYS, "region_key"])), "duplicate crosswalk keys")
    full_proxy = crosswalk.groupby("region_key", sort=False)[proxy].sum().rename("full_regime_proxy_ha")

    basis_file = pq.ParquetFile(args.basis)
    writer: pq.ParquetWriter | None = None
    rows_written = 0
    annual_audit = []
    try:
        for row_group in range(basis_file.num_row_groups):
            basis = basis_file.read_row_group(
                row_group, columns=["harvest_year", *KEYS, *FEATURES]
            ).to_pandas()
            require(basis.harvest_year.nunique() == 1, "basis row group contains multiple harvest years")
            require(len(basis) == len(basis.drop_duplicates(KEYS)), "duplicate basis cells in year")
            merged = crosswalk.merge(basis, on=KEYS, how="inner", validate="many_to_one")
            require(len(merged) > 0, "no cell/region overlap for basis year")
            for feature in FEATURES:
                merged[f"weighted_{feature}"] = merged[feature] * merged[proxy]
            aggregation = {
                proxy: "sum",
                "native_lat_index": "count",
                **{f"weighted_{feature}": "sum" for feature in FEATURES},
            }
            regional = merged.groupby("region_key", as_index=False, sort=True).agg(aggregation)
            regional = regional.rename(columns={proxy: "eligible_regime_proxy_ha", "native_lat_index": "positive_cell_region_rows"})
            regional = regional.join(full_proxy, on="region_key")
            regional["eligible_proxy_fraction"] = regional.eligible_regime_proxy_ha / regional.full_regime_proxy_ha
            for feature in FEATURES:
                regional[feature] = regional.pop(f"weighted_{feature}") / regional.eligible_regime_proxy_ha
            year = int(basis.harvest_year.iloc[0])
            regional.insert(0, "harvest_year", year)
            regional.insert(1, "regime", args.regime)
            require(np.isfinite(regional.select_dtypes(include=[np.number]).to_numpy()).all(), "nonfinite regional output")
            table = pa.Table.from_pandas(regional, preserve_index=False)
            if writer is None:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                writer = pq.ParquetWriter(partial_path, table.schema, compression="zstd")
            writer.write_table(table)
            rows_written += len(regional)
            annual_audit.append({
                "harvest_year": year,
                "basis_cells": len(basis),
                "cell_region_rows": len(merged),
                "regions": len(regional),
                "eligible_proxy_fraction_weighted": float(regional.eligible_regime_proxy_ha.sum() / regional.full_regime_proxy_ha.sum()),
                "region_coverage_quantiles": {
                    str(q): float(regional.eligible_proxy_fraction.quantile(q)) for q in (0.0, 0.01, 0.5, 0.99, 1.0)
                },
            })
    except Exception:
        if writer is not None:
            writer.close()
        if partial_path.exists():
            partial_path.unlink()
        raise
    require(writer is not None, "no basis row groups")
    writer.close()
    os.replace(partial_path, args.output)
    result = {
        "schema": "hultgren_impact_region_weather_basis/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "alternative_region_basis_not_sage_replication_response_damage_or_scc",
        "regime": args.regime,
        "sources": {
            "basis": {"path": str(args.basis), "bytes": args.basis.stat().st_size, "sha256": digest(args.basis)},
            "basis_validation": {"path": str(args.basis_validation), "sha256": digest(args.basis_validation)},
            "crosswalk": {"path": str(args.crosswalk), "bytes": args.crosswalk.stat().st_size, "sha256": digest(args.crosswalk)},
            "crosswalk_validation": {"path": str(args.crosswalk_validation), "sha256": digest(args.crosswalk_validation)},
        },
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output), "rows": rows_written, "row_groups": basis_file.num_row_groups},
        "annual_audit": annual_audit,
        "method": "cell-level nonlinear weather bases averaged by eligible MIRCA intersection proxy within each mixed-resolution author impact region",
        "claim_gates": {
            "nonlinear_transform_precedes_spatial_aggregation": True,
            "source_sage_pixel_weights_reproduced": False,
            "regime_combination_validated": False,
            "response_damage_or_scc_validated": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": result["output"], "annual_audit": annual_audit}, indent=2))


if __name__ == "__main__":
    main()
