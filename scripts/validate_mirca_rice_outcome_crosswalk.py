#!/usr/bin/env python3
"""Independently validate compact MIRCA rice outcome-crosswalk statistics."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

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


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require(digest(args.output) == receipt["output"]["sha256"], "output hash differs")
    frame = pd.read_parquet(args.output)
    require(len(frame) == receipt["output"]["rows"], "output rows differ")
    require(not frame.duplicated(["crop", *KEYS]).any(), "duplicate crop-cell")
    require(frame.production_eligible.eq(False).all(), "production gate opened")
    require(frame.scc_authorized.eq(False).all(), "SCC gate opened")

    recomputed = []
    for crop in ("ri1", "ri2"):
        part = frame.loc[frame.crop.eq(crop)].copy()
        calendar = part.calendar_available
        weight = part.weight_available
        positive = part.positive_observed
        matched_calendar = calendar & weight
        matched_positive = positive & weight
        weight_area = float(part.loc[weight, "total_area_ha"].sum())
        row = {
            "crop": crop,
            "calendar_cells": int(calendar.sum()),
            "positive_observed_cells": int(positive.sum()),
            "weight_cells": int(weight.sum()),
            "calendar_cells_with_weight": int(matched_calendar.sum()),
            "positive_observed_cells_with_weight": int(matched_positive.sum()),
            "positive_observed_cells_without_weight": int((positive & ~weight).sum()),
            "weight_cells_without_calendar": int((weight & ~calendar).sum()),
            "calendar_match_fraction": float(matched_calendar.sum() / calendar.sum()),
            "positive_observed_match_fraction": float(matched_positive.sum() / positive.sum()),
            "weight_area_fraction_on_calendar_support": float(part.loc[matched_calendar, "total_area_ha"].sum() / weight_area),
            "weight_area_fraction_on_positive_observed_support": float(part.loc[matched_positive, "total_area_ha"].sum() / weight_area),
            "complete_positive_outcome_coverage_gate": bool(matched_positive.sum() == positive.sum()),
        }
        expected = next(item for item in receipt["crop_summaries"] if item["crop"] == crop)
        for key, value in row.items():
            if isinstance(value, float):
                require(close(value, float(expected[key])), f"{crop} {key} differs")
            else:
                require(value == expected[key], f"{crop} {key} differs")
        recomputed.append(row)

    calendars = {
        crop: frame.loc[frame.crop.eq(crop) & frame.calendar_available, KEYS + ["plant_doy", "maturity_doy"]]
        for crop in ("ri1", "ri2")
    }
    shared = calendars["ri1"].merge(calendars["ri2"], on=KEYS, suffixes=("_ri1", "_ri2"), validate="one_to_one")
    separation = np.minimum(
        np.mod(shared.plant_doy_ri2 - shared.plant_doy_ri1, 365),
        np.mod(shared.plant_doy_ri1 - shared.plant_doy_ri2, 365),
    )
    timing = receipt["timing_separation"]
    require(len(shared) == timing["cells_with_both_calendars"], "shared calendar count differs")
    identical = shared.plant_doy_ri1.eq(shared.plant_doy_ri2) & shared.maturity_doy_ri1.eq(shared.maturity_doy_ri2)
    require(int(identical.sum()) == timing["identical_plant_and_maturity_calendars"], "identical count differs")
    for name, q in (("minimum", 0), ("p01", .01), ("p50", .5), ("p99", .99), ("maximum", 1)):
        require(close(float(np.quantile(separation, q)), timing["circular_planting_day_separation_quantiles"][name]), f"timing {name} differs")

    require(receipt["claim_gates"]["complete_positive_outcome_coverage"] is False, "coverage gate unexpectedly open")
    require(receipt["claim_gates"]["production_weights_authorized"] is False, "production gate differs")
    require(receipt["claim_gates"]["response_damage_or_scc_authorized"] is False, "response gate differs")
    result = {
        "status": "validated_exact_crosswalk_audit_and_closed_claim_gates",
        "receipt_sha256": digest(args.receipt),
        "output_sha256": digest(args.output),
        "rows": len(frame),
        "crop_summaries_recomputed": recomputed,
        "timing_summary_recomputed": True,
        "production_weights_authorized": False,
        "response_damage_or_scc_authorized": False,
    }
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
