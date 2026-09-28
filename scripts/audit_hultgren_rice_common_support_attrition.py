#!/usr/bin/env python3
"""Audit attrition from exact MIRCA support in observed rice outcomes."""
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
FEATURES = ["yield_t_ha", "tmean_c", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm"]
LAT_BINS = [-90.0, -30.0, -15.0, 0.0, 15.0, 30.0, 90.0]
LAT_LABELS = ["below_30S", "30S_to_15S", "15S_to_equator", "equator_to_15N", "15N_to_30N", "above_30N"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def standardized_difference(retained: pd.Series, excluded: pd.Series) -> float:
    pooled = np.sqrt((retained.var(ddof=1) + excluded.var(ddof=1)) / 2.0)
    return float((retained.mean() - excluded.mean()) / pooled) if pooled > 0 else 0.0


def summarize_crop(panel_path: Path, crop: str, weights: pd.DataFrame, countries: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame]:
    columns = ["harvest_year", *KEYS, "crop", "yield_observed", *FEATURES]
    frame = pd.read_parquet(panel_path, columns=list(dict.fromkeys(columns)))
    require(frame.crop.eq(crop).all(), f"crop differs for {crop}")
    observed = frame.loc[frame.yield_observed & frame.yield_t_ha.gt(0), ["harvest_year", *KEYS, *FEATURES]].copy()
    require(np.isfinite(observed[FEATURES].to_numpy(dtype=np.float64)).all(), f"nonfinite observed features for {crop}")
    require(not observed.duplicated(["harvest_year", *KEYS]).any(), f"duplicate observed crop-cell-year for {crop}")
    crop_weights = weights.loc[weights.crop.eq(crop), KEYS + ["total_area_ha", "irrigated_share"]].copy()
    observed = observed.merge(crop_weights, on=KEYS, how="left", validate="many_to_one")
    observed["weight_available"] = observed.total_area_ha.notna()
    observed = observed.merge(countries, on=KEYS, how="left", validate="many_to_one")
    observed["country_status"] = np.select(
        [observed.country_count.eq(1) & observed.country_label.notna(), observed.country_count.gt(1)],
        ["unique", "ambiguous"], default="missing",
    )
    observed["country_label_audit"] = observed.country_label.where(observed.country_status.eq("unique"), observed.country_status)
    observed["latitude_band"] = pd.cut(observed.lat, bins=LAT_BINS, labels=LAT_LABELS, right=False, include_lowest=True).astype(str)
    retained = observed.loc[observed.weight_available]
    excluded = observed.loc[~observed.weight_available]
    require(len(retained) > 1 and len(excluded) > 1, f"both attrition groups required for {crop}")

    feature_rows = []
    for feature in FEATURES:
        feature_rows.append({
            "feature": feature,
            "retained_mean": float(retained[feature].mean()),
            "excluded_mean": float(excluded[feature].mean()),
            "retained_minus_excluded_standardized_mean_difference": standardized_difference(retained[feature], excluded[feature]),
        })
    annual = []
    for year, group in observed.groupby("harvest_year", sort=True):
        annual.append({
            "harvest_year": int(year),
            "positive_observed_cell_years": len(group),
            "retained_cell_years": int(group.weight_available.sum()),
            "retention_fraction": float(group.weight_available.mean()),
        })
    cell_support = observed.groupby(KEYS, as_index=False, sort=False).weight_available.any()
    latitude = (
        observed.drop_duplicates(KEYS)
        .groupby(["latitude_band", "weight_available"], observed=True)
        .size().rename("cells").reset_index()
        .sort_values(["latitude_band", "weight_available"])
        .to_dict("records")
    )
    country = (
        observed.drop_duplicates(KEYS)
        .groupby(["country_label_audit", "weight_available"], observed=True)
        .size().rename("cells").reset_index()
    )
    country["crop"] = crop
    excluded_country = country.loc[~country.weight_available].sort_values(["cells", "country_label_audit"], ascending=[False, True]).head(15)
    cell_retention = float(cell_support.weight_available.mean())
    minimum_annual = min(row["retention_fraction"] for row in annual)
    max_abs_smd = max(abs(row["retained_minus_excluded_standardized_mean_difference"]) for row in feature_rows)
    gate = cell_retention >= 0.95 and minimum_annual >= 0.90 and max_abs_smd <= 0.25
    summary = {
        "crop": crop,
        "positive_observed_cells": len(cell_support),
        "retained_cells": int(cell_support.weight_available.sum()),
        "excluded_cells": int((~cell_support.weight_available).sum()),
        "cell_retention_fraction": cell_retention,
        "positive_observed_cell_years": len(observed),
        "retained_cell_years": len(retained),
        "excluded_cell_years": len(excluded),
        "cell_year_retention_fraction": float(len(retained) / len(observed)),
        "minimum_annual_retention_fraction": minimum_annual,
        "maximum_absolute_standardized_mean_difference": max_abs_smd,
        "feature_contrasts": feature_rows,
        "annual_retention": annual,
        "latitude_band_cell_counts": latitude,
        "top_excluded_country_proxy_groups": excluded_country.to_dict("records"),
        "low_attrition_gate": gate,
    }
    compact = observed[["harvest_year", *KEYS, "weight_available", "country_label_audit", "latitude_band", *FEATURES]].copy()
    compact["crop"] = crop
    return summary, compact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--crosswalk-receipt", type=Path, required=True)
    parser.add_argument("--country-proxy", type=Path, required=True)
    parser.add_argument("--ri1-panel", type=Path, required=True)
    parser.add_argument("--ri2-panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    crosswalk = json.loads(args.crosswalk_receipt.read_text(encoding="utf-8"))
    require(crosswalk["sources"]["weights"]["sha256"] == digest(args.weights), "weight hash differs")
    require(crosswalk["claim_gates"]["production_weights_authorized"] is False, "crosswalk gate unexpectedly open")
    weights = pd.read_parquet(args.weights)
    countries = pd.read_parquet(args.country_proxy)
    require(not countries.duplicated(KEYS).any(), "duplicate country proxy cells")
    summaries, compact = [], []
    for crop, path in (("ri1", args.ri1_panel), ("ri2", args.ri2_panel)):
        summary, rows = summarize_crop(path, crop, weights, countries)
        summaries.append(summary)
        compact.append(rows)
    output = pd.concat(compact, ignore_index=True).sort_values(["crop", "harvest_year", "lat", "lon_360"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    all_pass = all(row["low_attrition_gate"] for row in summaries)
    receipt = {
        "schema": "hultgren_rice_common_support_attrition_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "audited_common_support_attrition",
        "thresholds": {"minimum_cell_retention": 0.95, "minimum_each_year_retention": 0.90, "maximum_absolute_standardized_mean_difference": 0.25},
        "sources": {
            "weights": {"path": str(args.weights), "sha256": digest(args.weights)},
            "crosswalk_receipt": {"path": str(args.crosswalk_receipt), "sha256": digest(args.crosswalk_receipt)},
            "country_proxy": {"path": str(args.country_proxy), "sha256": digest(args.country_proxy)},
            "ri1_panel": {"path": str(args.ri1_panel), "sha256": digest(args.ri1_panel)},
            "ri2_panel": {"path": str(args.ri2_panel), "sha256": digest(args.ri2_panel)},
        },
        "crop_summaries": summaries,
        "all_crops_low_attrition_gate": all_pass,
        "output": {"path": str(args.output), "sha256": digest(args.output), "bytes": args.output.stat().st_size, "rows": len(output)},
        "claim_gates": {
            "restricted_common_support_estimand_low_attrition": all_pass,
            "imputation_used": False,
            "causal_or_geographic_winner_interpretation_authorized": False,
            "response_damage_or_scc_authorized": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "all_crops_low_attrition_gate": all_pass, "crop_summaries": summaries}, indent=2))


if __name__ == "__main__":
    main()
