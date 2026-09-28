#!/usr/bin/env python3
"""Audit exact MIRCA Rice1/Rice2 alignment to locked rice outcome panels."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["lat", "lon_360"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def collapse_panel(path: Path, crop: str) -> pd.DataFrame:
    columns = KEYS + ["lat", "lon", "crop", "irrigation", "plant_doy", "maturity_doy", "season_days", "yield_observed", "yield_t_ha", "gdhy_path"]
    frame = pd.read_parquet(path, columns=list(dict.fromkeys(columns)))
    require(frame.crop.eq(crop).all(), f"crop differs in {path}")
    require(frame.irrigation.eq("noirr").all(), f"irrigation differs in {path}")
    require(np.allclose(np.mod(frame.lon, 360.0), frame.lon_360, rtol=0, atol=1e-12), "longitude conversion differs")
    require(np.allclose(np.mod(frame.lat + 89.75, 0.5), 0.0, atol=1e-10), "latitude is not a 0.5-degree center")
    require(np.allclose(np.mod(frame.lon_360 - 0.25, 0.5), 0.0, atol=1e-10), "longitude is not a 0.5-degree center")
    calendar = frame.groupby(KEYS, as_index=False, sort=False).agg(
        plant_doy=("plant_doy", "first"),
        plant_doy_nunique=("plant_doy", "nunique"),
        maturity_doy=("maturity_doy", "first"),
        maturity_doy_nunique=("maturity_doy", "nunique"),
        season_days_min=("season_days", "min"),
        season_days_max=("season_days", "max"),
    )
    require(calendar.plant_doy_nunique.eq(1).all(), f"planting day varies within crop cell for {crop}")
    require(calendar.maturity_doy_nunique.eq(1).all(), f"maturity day varies within crop cell for {crop}")
    require((calendar.season_days_max - calendar.season_days_min).le(1).all(), f"season length varies by more than leap-day allowance for {crop}")
    calendar = calendar.drop(columns=["plant_doy_nunique", "maturity_doy_nunique"])
    expected_source = "rice_major" if crop == "ri1" else "rice_second"
    source_ok = frame.gdhy_path.astype(str).str.contains(f"/{expected_source}/", regex=False)
    require(source_ok.all(), f"GDHY source differs for {crop}")
    observed = (
        frame.assign(positive_observed=frame.yield_observed & frame.yield_t_ha.gt(0))
        .groupby(KEYS, as_index=False, sort=False).positive_observed.any()
    )
    cells = calendar.merge(observed, on=KEYS, how="left", validate="one_to_one")
    cells["crop"] = crop
    return cells


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--weights-receipt", type=Path, required=True)
    parser.add_argument("--ri1-panel", type=Path, required=True)
    parser.add_argument("--ri2-panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    upstream = json.loads(args.weights_receipt.read_text(encoding="utf-8"))
    require(upstream["output"]["sha256"] == digest(args.weights), "weight hash differs")
    require(upstream["claim_gates"]["production_weights_authorized"] is False, "upstream gate unexpectedly open")

    weights = pd.read_parquet(args.weights)
    require(set(weights.crop) == {"ri1", "ri2"}, "weight crops differ")
    require(not weights.duplicated(["crop", *KEYS]).any(), "duplicate weight crop-cells")
    require(weights.production_eligible.eq(False).all() and weights.scc_authorized.eq(False).all(), "upstream closed gates differ")
    panels = {
        "ri1": collapse_panel(args.ri1_panel, "ri1"),
        "ri2": collapse_panel(args.ri2_panel, "ri2"),
    }

    output_frames: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    for crop, cells in panels.items():
        crop_weights = weights.loc[weights.crop.eq(crop)].copy()
        merged = cells.merge(crop_weights, on=["crop", *KEYS], how="outer", indicator=True, validate="one_to_one")
        merged["calendar_available"] = merged._merge.ne("right_only")
        merged["weight_available"] = merged._merge.ne("left_only")
        merged["positive_observed"] = merged.positive_observed.eq(True)
        merged["production_eligible"] = False
        merged["scc_authorized"] = False
        output_frames.append(merged.drop(columns="_merge"))
        matched_calendar = merged.calendar_available & merged.weight_available
        matched_observed = matched_calendar & merged.positive_observed
        observed_count = int(merged.positive_observed.sum())
        weight_area = float(crop_weights.total_area_ha.sum())
        summaries.append({
            "crop": crop,
            "calendar_cells": int(merged.calendar_available.sum()),
            "positive_observed_cells": observed_count,
            "weight_cells": int(merged.weight_available.sum()),
            "calendar_cells_with_weight": int(matched_calendar.sum()),
            "positive_observed_cells_with_weight": int(matched_observed.sum()),
            "positive_observed_cells_without_weight": int((merged.positive_observed & ~merged.weight_available).sum()),
            "weight_cells_without_calendar": int((merged.weight_available & ~merged.calendar_available).sum()),
            "calendar_match_fraction": float(matched_calendar.sum() / merged.calendar_available.sum()),
            "positive_observed_match_fraction": float(matched_observed.sum() / observed_count),
            "weight_area_fraction_on_calendar_support": float(merged.loc[matched_calendar, "total_area_ha"].sum() / weight_area),
            "weight_area_fraction_on_positive_observed_support": float(merged.loc[matched_observed, "total_area_ha"].sum() / weight_area),
            "complete_positive_outcome_coverage_gate": bool(observed_count > 0 and matched_observed.sum() == observed_count),
        })

    shared = panels["ri1"].merge(panels["ri2"], on=KEYS, suffixes=("_ri1", "_ri2"), validate="one_to_one")
    separation = np.minimum(
        np.mod(shared.plant_doy_ri2 - shared.plant_doy_ri1, 365),
        np.mod(shared.plant_doy_ri1 - shared.plant_doy_ri2, 365),
    )
    identical = shared.plant_doy_ri1.eq(shared.plant_doy_ri2) & shared.maturity_doy_ri1.eq(shared.maturity_doy_ri2)
    timing = {
        "cells_with_both_calendars": len(shared),
        "identical_plant_and_maturity_calendars": int(identical.sum()),
        "circular_planting_day_separation_quantiles": {
            name: float(np.quantile(separation, q))
            for name, q in (("minimum", 0), ("p01", .01), ("p50", .5), ("p99", .99), ("maximum", 1))
        },
        "interpretation": "descriptive only; numeric rice seasons do not impose a universal calendar-year ordering",
    }
    output = pd.concat(output_frames, ignore_index=True, sort=False).sort_values(["crop", "lat", "lon_360"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    all_complete = all(row["complete_positive_outcome_coverage_gate"] for row in summaries)
    receipt = {
        "schema": "mirca_rice_outcome_crosswalk_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "audited_exact_crosswalk_incomplete_positive_outcome_coverage",
        "protocol_disclosure": "formalized after preliminary support counts; descriptive coverage audit, not preregistered hypothesis test",
        "sources": {
            "weights": {"path": str(args.weights), "sha256": digest(args.weights)},
            "weights_receipt": {"path": str(args.weights_receipt), "sha256": digest(args.weights_receipt)},
            "ri1_panel": {"path": str(args.ri1_panel), "sha256": digest(args.ri1_panel)},
            "ri2_panel": {"path": str(args.ri2_panel), "sha256": digest(args.ri2_panel)},
        },
        "crop_summaries": summaries,
        "timing_separation": timing,
        "output": {"path": str(args.output), "sha256": digest(args.output), "bytes": args.output.stat().st_size, "rows": len(output)},
        "claim_gates": {
            "complete_positive_outcome_coverage": all_complete,
            "candidate_sensitivity_crosswalk_described": True,
            "production_weights_authorized": False,
            "response_damage_or_scc_authorized": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "crop_summaries": summaries, "timing_separation": timing}, indent=2))


if __name__ == "__main__":
    main()
