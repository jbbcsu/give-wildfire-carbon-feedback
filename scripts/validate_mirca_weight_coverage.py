#!/usr/bin/env python3
"""Audit fixed irrigation-weight coverage of observed GDHY panel cells.

This is a support/eligibility check only. It does not drop observations,
estimate a response, or authorize SCC use.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


CELL_KEYS = ["lat", "lon_360", "crop"]
PANEL_REQUIRED = set(CELL_KEYS + ["harvest_year", "yield_observed"])
WEIGHT_REQUIRED = set(
    CELL_KEYS
    + [
        "irrigation", "area_share", "share_year", "production_eligible",
        "weight_source_id", "source_role",
    ]
)


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported table {path}; use CSV or Parquet")


def require(frame: pd.DataFrame, fields: set[str], label: str) -> None:
    if missing := fields - set(frame.columns):
        raise ValueError(f"{label} missing fields {sorted(missing)}")


def audit_coverage(weights: pd.DataFrame, panels: list[pd.DataFrame]) -> dict[str, object]:
    require(weights, WEIGHT_REQUIRED, "Weights")
    if not panels:
        raise ValueError("Supply at least one panel")
    if weights.duplicated(CELL_KEYS + ["irrigation"]).any():
        raise ValueError("Weights contain duplicate crop-grid-irrigation keys")
    share_years = sorted(int(value) for value in weights["share_year"].dropna().astype(int).unique())
    source_ids = sorted(weights["weight_source_id"].dropna().astype(str).unique())
    if len(share_years) != 1 or len(source_ids) != 1:
        raise ValueError("Coverage audit requires one fixed share vintage and source")
    eligible = weights.loc[weights["production_eligible"].eq(True)].copy()
    supported = eligible[CELL_KEYS].drop_duplicates()
    summaries: list[dict[str, object]] = []
    seen_crops: set[str] = set()
    for panel in panels:
        require(panel, PANEL_REQUIRED, "Panel")
        if not panel["yield_observed"].isin([True, False]).all():
            raise ValueError("yield_observed must be Boolean")
        for crop, crop_panel in panel.groupby("crop", observed=True):
            crop = str(crop)
            if crop in seen_crops:
                raise ValueError(f"Crop {crop} occurs in more than one supplied panel")
            seen_crops.add(crop)
            if crop not in set(eligible.crop.astype(str)):
                raise ValueError(f"No production-eligible weights for crop {crop}")
            observed = crop_panel.loc[crop_panel.yield_observed].copy()
            if observed.duplicated(CELL_KEYS + ["harvest_year"]).any():
                raise ValueError(f"Panel has duplicate observed crop-grid-year keys for {crop}")
            observed_cells = observed[CELL_KEYS].drop_duplicates()
            merged_cells = observed_cells.merge(
                supported, on=CELL_KEYS, how="left", indicator=True, validate="one_to_one"
            )
            matched_cells = int(merged_cells["_merge"].eq("both").sum())
            observed_years = observed[CELL_KEYS + ["harvest_year"]]
            merged_years = observed_years.merge(
                supported, on=CELL_KEYS, how="left", indicator=True, validate="many_to_one"
            )
            matched_years = int(merged_years["_merge"].eq("both").sum())
            summaries.append(
                {
                    "crop": crop,
                    "observed_cells": int(len(observed_cells)),
                    "matched_cells": matched_cells,
                    "unmatched_cells": int(len(observed_cells) - matched_cells),
                    "cell_coverage_fraction": matched_cells / len(observed_cells),
                    "observed_crop_grid_years": int(len(observed_years)),
                    "matched_crop_grid_years": matched_years,
                    "crop_grid_year_coverage_fraction": matched_years / len(observed_years),
                }
            )
    return {
        "schema_version": 1,
        "role": "fixed_irrigation_weight_support_audit_not_response_or_scc",
        "share_year": share_years[0],
        "weight_source_id": source_ids[0],
        "crop_summaries": sorted(summaries, key=lambda item: str(item["crop"])),
        "missing_weight_rule": "disclose and exclude before estimation; do not infill or renormalize",
        "scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--panel", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    audit = audit_coverage(
        read_table(Path(args.weights)), [read_table(Path(path)) for path in args.panel]
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
