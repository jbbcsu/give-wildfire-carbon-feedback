#!/usr/bin/env python3
"""Audit a transparent proportional reconciliation of MIRCA rice seasons."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_mirca_rice_season_shares import (
    COARSE_SHAPE,
    OUTCOME_MAP,
    SEASONS,
    SYSTEMS,
    locate_annual,
    locate_monthly,
    read_annual,
    read_monthly_maximum,
)

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def reconcile_arrays(
    seasonal: dict[int, np.ndarray], annual: np.ndarray
) -> tuple[dict[int, np.ndarray], np.ndarray, dict[str, object]]:
    require(set(seasonal) == set(SEASONS), "all three rice seasons are required")
    require(annual.shape == COARSE_SHAPE, "annual grid shape differs")
    reconstructed = sum((seasonal[s] for s in SEASONS), np.zeros_like(annual))
    annual_positive = annual > 0
    seasonal_positive = reconstructed > 0
    missing = annual_positive & ~seasonal_positive
    excess = ~annual_positive & seasonal_positive
    scale = np.zeros_like(annual)
    common = seasonal_positive
    scale[common] = annual[common] / reconstructed[common]
    repaired = {season: seasonal[season] * scale for season in SEASONS}
    repaired_sum = sum((repaired[s] for s in SEASONS), np.zeros_like(annual))
    relative = np.zeros_like(annual)
    relative[common] = np.abs(scale[common] - 1.0)
    annual_total = float(annual.sum())
    thresholds = (0.001, 0.01, 0.05, 0.10)
    audit = {
        "annual_area_ha": annual_total,
        "reconstructed_area_ha": float(reconstructed.sum()),
        "signed_global_difference_ha": float(reconstructed.sum() - annual_total),
        "maximum_absolute_cell_difference_ha": float(np.abs(reconstructed - annual).max()),
        "annual_positive_seasonal_zero_cells": int(missing.sum()),
        "annual_area_without_seasonal_support_ha": float(annual[missing].sum()),
        "seasonal_positive_annual_zero_cells": int(excess.sum()),
        "seasonal_area_without_annual_support_ha": float(reconstructed[excess].sum()),
        "common_positive_cells": int((annual_positive & seasonal_positive).sum()),
        "scale_quantiles_common_positive": {
            name: float(np.quantile(scale[annual_positive & seasonal_positive], q))
            for name, q in (("minimum", 0), ("p01", .01), ("p50", .5), ("p99", .99), ("maximum", 1))
        },
        "annual_area_fraction_by_absolute_relative_correction": {
            f"above_{threshold:g}": float(annual[relative > threshold].sum() / annual_total)
            for threshold in thresholds
        },
        "postrepair_maximum_absolute_cell_error_ha": float(np.abs(repaired_sum - annual).max()),
        "postrepair_global_error_ha": float(repaired_sum.sum() - annual_total),
        "season_areas": [
            {
                "season": season,
                "original_area_ha": float(seasonal[season].sum()),
                "repaired_area_ha": float(repaired[season].sum()),
                "change_ha": float(repaired[season].sum() - seasonal[season].sum()),
            }
            for season in SEASONS
        ],
    }
    return repaired, scale, audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monthly-root", type=Path, required=True)
    parser.add_argument("--annual-root", type=Path, required=True)
    parser.add_argument("--year", type=int, default=2000, choices=(2000,))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    seasonal_by_system: dict[str, dict[int, np.ndarray]] = {system: {} for system in SYSTEMS}
    sources: list[dict[str, object]] = []
    for season in SEASONS:
        for system in SYSTEMS:
            path = locate_monthly(args.monthly_root, args.year, season, system)
            area, source = read_monthly_maximum(path, args.year, season, system)
            seasonal_by_system[system][season] = area
            sources.append({**source, "season": season, "system": system})

    repaired_by_system: dict[str, dict[int, np.ndarray]] = {}
    scales: dict[str, np.ndarray] = {}
    audits: list[dict[str, object]] = []
    annual_sources: list[dict[str, object]] = []
    for system in SYSTEMS:
        annual_path = locate_annual(args.annual_root, args.year, system)
        annual = read_annual(annual_path)
        repaired, scale, audit = reconcile_arrays(seasonal_by_system[system], annual)
        repaired_by_system[system] = repaired
        scales[system] = scale
        audits.append({"system": system, **audit})
        annual_sources.append({
            "system": system, "path": str(annual_path), "sha256": digest(annual_path),
            "bytes": annual_path.stat().st_size,
        })

    support_complete = all(a["annual_positive_seasonal_zero_cells"] == 0 for a in audits)
    reconciliation_exact = all(
        a["postrepair_maximum_absolute_cell_error_ha"] <= 1e-9 for a in audits
    )
    require(support_complete, "positive annual rice area lacks seasonal support")
    require(reconciliation_exact, "proportional repair does not reconcile exactly")

    lat = 89.75 - 0.5 * np.arange(COARSE_SHAPE[0])
    lon = -179.75 + 0.5 * np.arange(COARSE_SHAPE[1])
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    frames: list[pd.DataFrame] = []
    for season, crop in OUTCOME_MAP.items():
        irrigated = repaired_by_system["ir"][season]
        rainfed = repaired_by_system["rf"][season]
        total = irrigated + rainfed
        keep = total > 0
        frame = pd.DataFrame({
            "lat": lat_grid[keep], "lon": lon_grid[keep],
            "lon_360": np.mod(lon_grid[keep], 360.0), "crop": crop,
            "irrigated_area_ha": irrigated[keep], "rainfed_area_ha": rainfed[keep],
            "total_area_ha": total[keep],
            "irrigated_share": irrigated[keep] / total[keep],
            "rice_season": season,
            "irrigated_repair_scale": scales["ir"][keep],
            "rainfed_repair_scale": scales["rf"][keep],
            "proportional_reconciliation_sensitivity": True,
            "production_eligible": False,
            "scc_authorized": False,
        })
        frames.append(frame)
    output = pd.concat(frames, ignore_index=True).sort_values(["crop", "lat", "lon_360"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    receipt = {
        "schema": "mirca_rice_proportional_reconciliation_sensitivity/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_candidate_sensitivity_not_production_eligible",
        "protocol": {
            "path": "MIRCA_RICE_PROPORTIONAL_RECONCILIATION_PROTOCOL_20260926.md",
            "sha256": digest(ROOT / "MIRCA_RICE_PROPORTIONAL_RECONCILIATION_PROTOCOL_20260926.md"),
        },
        "monthly_sources": sources,
        "annual_sources": annual_sources,
        "system_audits": audits,
        "output": {"path": str(args.output), "sha256": digest(args.output), "bytes": args.output.stat().st_size, "rows": len(output)},
        "claim_gates": {
            "support_complete": support_complete,
            "postrepair_reconciliation_exact": reconciliation_exact,
            "publisher_data_reproduced_without_repair": False,
            "production_weights_authorized": False,
            "response_damage_or_scc_authorized": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "system_audits": audits, "output": receipt["output"]}, indent=2))


if __name__ == "__main__":
    main()
