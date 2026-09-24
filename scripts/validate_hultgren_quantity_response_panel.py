#!/usr/bin/env python3
"""Independently validate fixed sentinels from the quantity-response panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_hultgren_precip_basis_climatology import FEATURES
from estimate_hultgren_grid_yield_contrast import design_matrix
from src.hultgren_maize_response import PublishedEstimate

KEYS = ["native_lat_index", "native_lon_index"]
VALUE = "maize_gross_production_value_common_price_2014_2016_usd"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if receipt["schema"] != "hultgren_quantity_response_panel/v1":
        raise AssertionError("unexpected receipt schema")
    if receipt["claim_gates"]["damage"] or receipt["claim_gates"]["scc"]:
        raise AssertionError("claim gate promoted")
    data_path = Path(receipt["output"]["path"])
    if digest(data_path) != receipt["output"]["sha256"]:
        raise AssertionError("output hash differs")
    for source in receipt["sources"].values():
        if digest(Path(source["path"])) != source["sha256"] or digest(Path(source["receipt"])) != source["receipt_sha256"]:
            raise AssertionError(f"source identity differs: {source['path']}")
    for source in receipt["published_response"].values():
        if isinstance(source, dict) and digest(Path(source["path"])) != source["sha256"]:
            raise AssertionError(f"response source identity differs: {source['path']}")
    pwt_path = Path(receipt["country_income"]["path"])
    if digest(pwt_path) != receipt["country_income"]["sha256"]:
        raise AssertionError("PWT source identity differs")

    frame = pd.read_parquet(data_path).sort_values(["iso3", *KEYS]).reset_index(drop=True)
    numeric = [VALUE, "annual_precip_mean_mm", "irrigated_share", "lr_tmax_crop", "lr_prcp_crop", "ln_gdppc", *FEATURES,
               "quantity_first_order_index", "quantity_second_order_index"]
    if len(frame) != receipt["output"]["rows"] or frame.duplicated(["iso3", *KEYS]).any():
        raise AssertionError("output support differs")
    if not np.isfinite(frame[numeric].to_numpy()).all() or not frame[VALUE].gt(0).all() or not frame.annual_precip_mean_mm.gt(0).all():
        raise AssertionError("output numeric support invalid")
    if not math.isclose(float(frame[VALUE].sum()), receipt["support_ledger"]["country_consistent_income_matched"]["maize_value_usd"], rel_tol=1e-14):
        raise AssertionError("retained value differs")

    positions = sorted({0, len(frame) // 4, len(frame) // 2, 3 * len(frame) // 4, len(frame) - 1})
    sentinel = frame.iloc[positions].copy().reset_index(drop=True)
    basis = pd.read_parquet(receipt["sources"]["basis"]["path"])
    annual = pd.read_parquet(receipt["sources"]["annual_precip"]["path"])
    moderators = pd.read_parquet(receipt["sources"]["moderators"]["path"])
    pwt = pd.read_excel(pwt_path, sheet_name="Data", usecols=["countrycode", "year", "pop", "cgdpo"])
    pwt = pwt.loc[pwt["pop"].gt(0) & pwt["cgdpo"].gt(0)].copy()
    target = int(receipt["country_income"]["target_year"])
    pwt["distance"] = (pwt.year - target).abs()
    pwt = pwt.sort_values(["countrycode", "distance", "year"]).drop_duplicates("countrycode").set_index("countrycode")
    estimate = PublishedEstimate.from_exports(
        Path(receipt["published_response"]["coefficients"]["path"]),
        Path(receipt["published_response"]["covariance"]["path"]),
    )
    maximum_source_error = 0.0
    maximum_formula_error = 0.0
    comparisons = 0
    for row in sentinel.itertuples(index=False):
        key_mask = (basis.native_lat_index == row.native_lat_index) & (basis.native_lon_index == row.native_lon_index)
        selected_basis = basis.loc[key_mask]
        if selected_basis.empty:
            raise AssertionError("sentinel basis absent")
        total_area = float(selected_basis.mirca_area_ha.sum())
        for feature in FEATURES:
            reconstructed = float(np.sum(selected_basis[feature] * selected_basis.mirca_area_ha) / total_area)
            maximum_source_error = max(maximum_source_error, abs(reconstructed - getattr(row, feature)))
        key = (annual.native_lat_index == row.native_lat_index) & (annual.native_lon_index == row.native_lon_index)
        maximum_source_error = max(maximum_source_error, abs(float(annual.loc[key, "annual_precip_mean_mm"].iloc[0]) - row.annual_precip_mean_mm))
        key = (moderators.native_lat_index == row.native_lat_index) & (moderators.native_lon_index == row.native_lon_index)
        for field in ("irrigated_share", "lr_tmax_crop", "lr_prcp_crop"):
            maximum_source_error = max(maximum_source_error, abs(float(moderators.loc[key, field].iloc[0]) - getattr(row, field)))
        income = math.log(float(pwt.loc[row.iso3, "cgdpo"] / pwt.loc[row.iso3, "pop"]))
        maximum_source_error = max(maximum_source_error, abs(income - row.ln_gdppc))

        baseline_record = {feature: getattr(row, feature) for feature in FEATURES}
        baseline_record.update({
            "gdd": 1200.0, "kdd": 40.0, "ln_gdppc": row.ln_gdppc,
            "irrigated_share": row.irrigated_share, "lr_tmax_crop": row.lr_tmax_crop,
            "lr_prcp_crop": row.lr_prcp_crop,
        })
        baseline = pd.DataFrame([baseline_record])
        baseline_design = design_matrix(baseline, estimate.terms)
        for change in (-0.20, -0.05, 0.0, 0.03, 0.10):
            comparison = baseline.copy()
            comparison[FEATURES[:3]] *= 1.0 + change
            comparison[FEATURES[3:]] *= (1.0 + change) ** 2
            direct = float(np.sum((design_matrix(comparison, estimate.terms) - baseline_design) * estimate.coefficients[None, :]))
            closed = row.quantity_first_order_index * change + row.quantity_second_order_index * change**2
            maximum_formula_error = max(maximum_formula_error, abs(direct - closed))
            comparisons += 1
    if maximum_source_error > 1e-9 or maximum_formula_error > 1e-11:
        raise AssertionError(f"sentinel validation differs: source={maximum_source_error}, formula={maximum_formula_error}")

    result = {
        "schema": "hultgren_quantity_response_panel_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "validation": {
            "all_source_receipt_and_output_hashes_checked": True,
            "all_output_keys_and_finite_values_checked": True,
            "sentinel_positions": positions,
            "sentinel_country_cells": sentinel[["iso3", *KEYS]].to_dict("records"),
            "direct_design_formula_comparisons": comparisons,
            "maximum_absolute_source_reconstruction_error": maximum_source_error,
            "maximum_absolute_direct_design_formula_error": maximum_formula_error,
            "claim_gates_checked": True,
        },
        "scope": "Full artifact identity/support checks plus independent source and direct 49-term design reconstruction at five fixed key-order country-cell sentinels.",
        "interpretation": "Quantity-response input validation only; no marginal climate response, damage, GIVE replacement, or SCC gate is opened.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
