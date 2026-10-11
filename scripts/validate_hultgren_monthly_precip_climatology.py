#!/usr/bin/env python3
"""Validate monthly crop-season climatology against the frozen phase basis."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_hultgren_grid_weather_basis import crop_month_keys
from build_hultgren_monthly_precip_climatology import (
    CALENDAR_COLUMNS,
    MAX_MONTHS,
    RAIN_COLUMNS,
    RAIN_SQUARED_COLUMNS,
)
from build_hultgren_precip_basis_climatology import FEATURES, require

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["regime", "native_lat_index", "native_lon_index"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def reconstructed_basis(frame: pd.DataFrame) -> np.ndarray:
    rain = frame[RAIN_COLUMNS].to_numpy(dtype=np.float64)
    squared = frame[RAIN_SQUARED_COLUMNS].to_numpy(dtype=np.float64)
    phases = (slice(0, 1), slice(1, 4), slice(4, MAX_MONTHS))
    return np.column_stack(
        [rain[:, selected].sum(axis=1) for selected in phases]
        + [squared[:, selected].sum(axis=1) for selected in phases]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monthly", type=Path, required=True)
    parser.add_argument("--monthly-receipt", type=Path, required=True)
    parser.add_argument("--basis", type=Path, required=True)
    parser.add_argument("--basis-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    monthly_receipt = json.loads(args.monthly_receipt.read_text(encoding="utf-8"))
    basis_receipt = json.loads(args.basis_receipt.read_text(encoding="utf-8"))
    require(monthly_receipt["schema"] == "hultgren_monthly_precip_climatology/v1", "monthly receipt differs")
    require(basis_receipt["schema"] == "hultgren_precip_basis_climatology/v1", "basis receipt differs")
    require(monthly_receipt["output"]["sha256"] == digest(args.monthly), "monthly output hash differs")
    require(basis_receipt["output"]["sha256"] == digest(args.basis), "basis output hash differs")
    require(monthly_receipt["source_period"] == basis_receipt["source_period"], "source periods differ")
    require(monthly_receipt["harvest_years"] == basis_receipt["harvest_years"], "harvest years differ")

    monthly = pd.read_parquet(args.monthly)
    basis = pd.read_parquet(args.basis, columns=KEYS + FEATURES)
    require(len(monthly) == monthly_receipt["support"]["output_rows"], "monthly row count differs")
    require(not monthly.duplicated(KEYS).any() and not basis.duplicated(KEYS).any(), "duplicate support keys")
    require(set(monthly.regime) == {"rainfed", "irrigated"}, "monthly regimes differ")
    require(np.isfinite(monthly[RAIN_COLUMNS + RAIN_SQUARED_COLUMNS].to_numpy()).all(), "nonfinite moments")
    require((monthly[RAIN_COLUMNS + RAIN_SQUARED_COLUMNS] >= 0).all().all(), "negative moments")
    require(monthly.season_months.between(4, MAX_MONTHS).all(), "season length outside 4-10 months")

    calendar = monthly[CALENDAR_COLUMNS].to_numpy(dtype=np.int16)
    rain = monthly[RAIN_COLUMNS].to_numpy(dtype=np.float64)
    squared = monthly[RAIN_SQUARED_COLUMNS].to_numpy(dtype=np.float64)
    for index, row in enumerate(monthly.itertuples(index=False)):
        length = int(row.season_months)
        expected = np.asarray([month for _, month in crop_month_keys(2000, int(row.plant_month), int(row.harvest_month))])
        require(len(expected) == length, "stored season length differs from calendar")
        require(np.array_equal(calendar[index, :length], expected), "active calendar sequence differs")
        require(np.all(calendar[index, length:] == 0), "inactive calendar padding differs")
        require(np.all(rain[index, length:] == 0) and np.all(squared[index, length:] == 0), "inactive moment padding differs")
        require(np.all(squared[index, :length] + 1e-12 >= np.square(rain[index, :length])), "second moment below squared mean")

    joined = monthly.merge(basis, on=KEYS, how="outer", validate="one_to_one", indicator=True)
    require(joined._merge.eq("both").all(), "monthly and phase-basis support differ")
    actual = reconstructed_basis(joined)
    expected = joined[FEATURES].to_numpy(dtype=np.float64)
    difference = actual - expected
    require(np.allclose(actual, expected, rtol=1e-11, atol=1e-7), "monthly moments do not reconstruct frozen phase basis")

    result = {
        "schema": "hultgren_monthly_precip_climatology_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_historical_monthly_input_not_response_damage_or_scc",
        "sources": {
            "monthly": {"path": str(args.monthly), "sha256": digest(args.monthly), "receipt": str(args.monthly_receipt), "receipt_sha256": digest(args.monthly_receipt)},
            "basis": {"path": str(args.basis), "sha256": digest(args.basis), "receipt": str(args.basis_receipt), "receipt_sha256": digest(args.basis_receipt)},
        },
        "checks": {
            "rows": int(len(joined)),
            "exact_support_match": True,
            "calendar_and_padding_valid": True,
            "second_moment_inequality_valid": True,
            "phase_basis_reconstructed": True,
            "maximum_absolute_basis_difference": float(np.max(np.abs(difference))),
        },
        "claim_gates": {"monthly_precipitation_input": True, "response": False, "damage": False, "scc": False},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, indent=2))


if __name__ == "__main__":
    main()
