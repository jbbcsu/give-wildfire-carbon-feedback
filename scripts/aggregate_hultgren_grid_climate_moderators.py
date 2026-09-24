#!/usr/bin/env python3
"""Aggregate validated cell-year climate inputs to fixed cell climatologies."""

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
SUPPORT = ["latitude", "longitude", "plant_month", "harvest_month", "season_months", "cross_year", "mirca_area_ha"]
SOURCE_FEATURES = ["season_mean_monthly_tmax_c", "season_mean_monthly_precip_mm"]


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
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--regime", choices=("rainfed", "irrigated"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(len(args.input) >= 2, "at least two source blocks required")
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    baseline: pd.DataFrame | None = None
    tmax_sum: np.ndarray | None = None
    precip_sum: np.ndarray | None = None
    count: np.ndarray | None = None
    source_records = []
    years: list[int] = []
    for source_path in args.input:
        source_receipt_path = source_path.with_suffix(source_path.suffix + ".result.json")
        receipt = json.loads(source_receipt_path.read_text(encoding="utf-8"))
        require(receipt["status"] == "alternative_product_cell_year_moderators_not_author_30yr_triangular_average", "source status failed")
        require(receipt["regime"] == args.regime, "source regime differs")
        require(digest(source_path) == receipt["output"]["sha256"], "source hash differs")
        parquet = pq.ParquetFile(source_path)
        for row_group in range(parquet.num_row_groups):
            frame = parquet.read_row_group(row_group, columns=["harvest_year", *KEYS, *SUPPORT, *SOURCE_FEATURES]).to_pandas()
            require(frame.harvest_year.nunique() == 1, "source row group mixes years")
            year = int(frame.harvest_year.iloc[0])
            require(year not in years, "duplicate harvest year")
            years.append(year)
            frame = frame.sort_values(KEYS).reset_index(drop=True)
            if baseline is None:
                baseline = frame[KEYS + SUPPORT].copy()
                tmax_sum = np.zeros(len(frame), dtype=np.float64)
                precip_sum = np.zeros(len(frame), dtype=np.float64)
                count = np.zeros(len(frame), dtype=np.int16)
            else:
                require(frame[KEYS].equals(baseline[KEYS]), "cell keys differ across years")
                for column in SUPPORT:
                    require(np.allclose(frame[column], baseline[column], rtol=0.0, atol=0.0), f"support differs: {column}")
            values = frame[SOURCE_FEATURES].to_numpy(dtype=np.float64)
            complete = np.isfinite(values).all(axis=1)
            require(complete.all(), "nonfinite source moderators")
            assert tmax_sum is not None and precip_sum is not None and count is not None
            tmax_sum += values[:, 0]
            precip_sum += values[:, 1]
            count += complete.astype(np.int16)
        source_records.append({
            "path": str(source_path), "bytes": source_path.stat().st_size, "sha256": digest(source_path),
            "receipt": str(source_receipt_path), "receipt_sha256": digest(source_receipt_path),
        })
    require(baseline is not None and tmax_sum is not None and precip_sum is not None and count is not None, "no source rows")
    require((count == len(years)).all(), "cell year counts differ")
    result_frame = baseline.copy()
    result_frame["moderator_years"] = count
    result_frame["lr_tmax_crop"] = tmax_sum / count
    result_frame["lr_prcp_crop"] = precip_sum / count
    require(np.isfinite(result_frame[["lr_tmax_crop", "lr_prcp_crop"]].to_numpy()).all(), "nonfinite climatology")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result_frame.to_parquet(args.output, index=False, compression="zstd")
    receipt = {
        "schema": "hultgren_grid_climate_moderator_climatology/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "alternative_27yr_fixed_climatology_not_author_30yr_triangular_average",
        "regime": args.regime,
        "harvest_years": sorted(years),
        "excluded_boundary_harvest_years": [1991, 2001],
        "sources": source_records,
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output), "rows": len(result_frame)},
        "definitions": {
            "lr_tmax_crop": "simple mean across 27 retained cell-year crop-season mean monthly Tmax values",
            "lr_prcp_crop": "simple mean across 27 retained cell-year crop-season mean monthly precipitation values",
        },
        "interpretation": "fixed observational alternative-product moderator benchmark; not the authors' time-varying 30-year triangular GMFD/SAGE moderator",
        "claim_gates": {"arithmetic_climatology_complete": True, "author_moderator_reproduction": False, "response_damage_or_scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "output": receipt["output"], "years": len(years)}, indent=2))


if __name__ == "__main__":
    main()
