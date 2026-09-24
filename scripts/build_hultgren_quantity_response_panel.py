#!/usr/bin/env python3
"""Build the cell-country response panel for the annual-rain quantity bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_hultgren_cell_moderators import choose_pwt_snapshot
from build_hultgren_precip_basis_climatology import FEATURES
from src.hultgren_maize_response import PublishedEstimate

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["native_lat_index", "native_lon_index"]
LINEAR = [f"prcp_poly_1_bin{phase}" for phase in (1, 2, 3)]
SQUARED = [f"prcp_poly_2_bin{phase}" for phase in (1, 2, 3)]
VALUE = "maize_gross_production_value_common_price_2014_2016_usd"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def combine_regime_basis(frame: pd.DataFrame) -> pd.DataFrame:
    require(set(frame.regime) == {"rainfed", "irrigated"}, "basis regimes differ")
    parts = []
    for regime in ("rainfed", "irrigated"):
        part = frame.loc[frame.regime.eq(regime), KEYS + ["mirca_area_ha", *FEATURES]].copy()
        require(not part.duplicated(KEYS).any(), f"duplicate {regime} basis cell")
        parts.append(part.rename(columns={column: f"{column}_{regime}" for column in ["mirca_area_ha", *FEATURES]}))
    combined = parts[0].merge(parts[1], on=KEYS, how="outer", validate="one_to_one")
    for regime in ("rainfed", "irrigated"):
        combined[f"mirca_area_ha_{regime}"] = combined[f"mirca_area_ha_{regime}"].fillna(0.0)
    total = combined.mirca_area_ha_rainfed + combined.mirca_area_ha_irrigated
    require(total.gt(0).all(), "zero combined basis area")
    for feature in FEATURES:
        numerator = (
            combined[f"{feature}_rainfed"].fillna(0.0) * combined.mirca_area_ha_rainfed
            + combined[f"{feature}_irrigated"].fillna(0.0) * combined.mirca_area_ha_irrigated
        )
        combined[feature] = numerator / total
    return combined[KEYS + FEATURES].sort_values(KEYS).reset_index(drop=True)


def effective_precip_coefficients(frame: pd.DataFrame, estimate: PublishedEstimate) -> pd.DataFrame:
    primitives = {
        "ln_gdppc": frame.ln_gdppc.to_numpy(dtype=np.float64),
        "irrigated_share": frame.irrigated_share.to_numpy(dtype=np.float64),
        "lr_tmax_crop": frame.lr_tmax_crop.to_numpy(dtype=np.float64),
        "pbarcut_prcp": np.minimum(frame.lr_prcp_crop.to_numpy(dtype=np.float64), 250.0),
    }
    effective = {feature: np.zeros(len(frame), dtype=np.float64) for feature in FEATURES}
    terms_used = 0
    for term, coefficient in zip(estimate.terms, estimate.coefficients, strict=True):
        factors = [factor.removeprefix("c.") for factor in term.split("#")]
        weather = [factor for factor in factors if factor in FEATURES]
        if not weather:
            continue
        require(len(weather) == 1 and factors.count(weather[0]) == 1, f"nonlinear precipitation term unsupported: {term}")
        values = np.full(len(frame), coefficient, dtype=np.float64)
        for factor in factors:
            if factor != weather[0]:
                require(factor in primitives, f"unsupported precipitation interaction: {term}")
                values *= primitives[factor]
        effective[weather[0]] += values
        terms_used += 1
    require(terms_used == 36, f"expected 36 precipitation terms, found {terms_used}")
    result = pd.DataFrame({f"effective_{feature}": values for feature, values in effective.items()})
    require(np.isfinite(result.to_numpy()).all(), "nonfinite effective precipitation coefficient")
    return result


def support_record(frame: pd.DataFrame) -> dict[str, float | int]:
    return {
        "rows": int(len(frame)),
        "countries": int(frame.iso3.nunique()),
        "maize_value_usd": float(frame[VALUE].sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--weights-receipt", type=Path, required=True)
    parser.add_argument("--basis", type=Path, required=True)
    parser.add_argument("--basis-receipt", type=Path, required=True)
    parser.add_argument("--annual-precip", type=Path, required=True)
    parser.add_argument("--annual-precip-receipt", type=Path, required=True)
    parser.add_argument("--moderators", type=Path, required=True)
    parser.add_argument("--moderator-receipt", type=Path, required=True)
    parser.add_argument("--pwt-workbook", type=Path, required=True)
    parser.add_argument("--coefficients", type=Path, required=True)
    parser.add_argument("--covariance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    receipts = {
        "weights": json.loads(args.weights_receipt.read_text(encoding="utf-8")),
        "basis": json.loads(args.basis_receipt.read_text(encoding="utf-8")),
        "annual_precip": json.loads(args.annual_precip_receipt.read_text(encoding="utf-8")),
        "moderators": json.loads(args.moderator_receipt.read_text(encoding="utf-8")),
    }
    require(receipts["weights"]["schema"] == "hultgren_country_cell_maize_value_weights_common_price/v1", "weight receipt differs")
    require(receipts["basis"]["schema"] == "hultgren_precip_basis_climatology/v1", "basis receipt differs")
    require(receipts["annual_precip"]["schema"] == "hultgren_cell_annual_precip_climatology/v1", "annual receipt differs")
    require(receipts["moderators"]["schema"] == "hultgren_cell_moderators/v1", "moderator receipt differs")
    for label, path in (("weights", args.weights), ("basis", args.basis), ("annual_precip", args.annual_precip), ("moderators", args.moderators)):
        require(receipts[label]["output"]["sha256"] == digest(path), f"{label} hash differs")
    pwt_record = receipts["moderators"]["sources"]["pwt"]
    require(pwt_record["sha256"] == digest(args.pwt_workbook), "PWT hash differs")

    weights = pd.read_parquet(args.weights)
    require(not weights.duplicated(["iso3", *KEYS]).any() and weights[VALUE].gt(0).all(), "weight support invalid")
    ledger = {"source_weights": support_record(weights)}
    basis = combine_regime_basis(pd.read_parquet(args.basis))
    frame = weights.merge(basis, on=KEYS, how="inner", validate="many_to_one")
    ledger["crop_calendar_basis_matched"] = support_record(frame)
    annual = pd.read_parquet(args.annual_precip, columns=KEYS + ["annual_precip_mean_mm"])
    frame = frame.merge(annual, on=KEYS, how="inner", validate="many_to_one")
    require(frame.annual_precip_mean_mm.gt(0).all(), "nonpositive annual precipitation baseline")
    ledger["annual_precip_matched"] = support_record(frame)
    moderators = pd.read_parquet(args.moderators, columns=KEYS + ["irrigated_share", "lr_tmax_crop", "lr_prcp_crop"])
    frame = frame.merge(moderators, on=KEYS, how="inner", validate="many_to_one")
    ledger["climate_moderators_matched"] = support_record(frame)

    pwt = pd.read_excel(args.pwt_workbook, sheet_name="Data", usecols=["countrycode", "country", "year", "pop", "cgdpo"])
    income = choose_pwt_snapshot(pwt, int(pwt_record["target_year"]))
    frame = frame.merge(income[["countrycode", "pwt_year", "ln_gdppc"]], left_on="iso3", right_on="countrycode", how="left", validate="many_to_one")
    frame = frame.loc[frame.ln_gdppc.notna()].copy()
    require(not frame.empty and np.isfinite(frame.ln_gdppc).all(), "income-matched support empty or invalid")
    ledger["country_consistent_income_matched"] = support_record(frame)

    estimate = PublishedEstimate.from_exports(args.coefficients, args.covariance)
    effective = effective_precip_coefficients(frame, estimate)
    frame = pd.concat([frame.reset_index(drop=True), effective], axis=1)
    linear_contribution = sum(
        frame[feature].to_numpy(dtype=np.float64) * frame[f"effective_{feature}"].to_numpy(dtype=np.float64)
        for feature in LINEAR
    )
    squared_contribution = sum(
        frame[feature].to_numpy(dtype=np.float64) * frame[f"effective_{feature}"].to_numpy(dtype=np.float64)
        for feature in SQUARED
    )
    frame["baseline_linear_precipitation_index"] = linear_contribution
    frame["baseline_squared_precipitation_index"] = squared_contribution
    frame["quantity_first_order_index"] = linear_contribution + 2.0 * squared_contribution
    frame["quantity_second_order_index"] = squared_contribution
    require(np.isfinite(frame[["quantity_first_order_index", "quantity_second_order_index"]].to_numpy()).all(), "response index invalid")

    output_columns = [
        "iso3", *KEYS, VALUE, "annual_precip_mean_mm", "irrigated_share", "lr_tmax_crop", "lr_prcp_crop",
        "ln_gdppc", "pwt_year", *FEATURES,
        *[f"effective_{feature}" for feature in FEATURES],
        "baseline_linear_precipitation_index", "baseline_squared_precipitation_index",
        "quantity_first_order_index", "quantity_second_order_index",
    ]
    output = frame[output_columns].sort_values(["iso3", *KEYS]).reset_index(drop=True)
    require(not output.duplicated(["iso3", *KEYS]).any(), "duplicate output country-cell")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    require(args.output.stat().st_size < 64 * 2**20, "output exceeds 64 MiB owned-output budget")

    result = {
        "schema": "hultgren_quantity_response_panel/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_quantity_response_input_not_marginal_damage_or_scc",
        "definition": "cell-country coefficients for delta_log_yield = first_order_index*x + second_order_index*x^2, where x is the proportional annual-rainfall change and within-season shares are fixed",
        "support_ledger": ledger,
        "support_loss": {
            "unmatched_value_usd": float(ledger["source_weights"]["maize_value_usd"] - ledger["country_consistent_income_matched"]["maize_value_usd"]),
            "retained_value_fraction": float(ledger["country_consistent_income_matched"]["maize_value_usd"] / ledger["source_weights"]["maize_value_usd"]),
            "no_renormalization": True,
        },
        "sources": {
            label: {"path": str(path), "sha256": digest(path), "receipt": str(receipt_path), "receipt_sha256": digest(receipt_path)}
            for label, path, receipt_path in (
                ("weights", args.weights, args.weights_receipt), ("basis", args.basis, args.basis_receipt),
                ("annual_precip", args.annual_precip, args.annual_precip_receipt),
                ("moderators", args.moderators, args.moderator_receipt),
            )
        },
        "published_response": {
            "coefficients": {"path": str(args.coefficients), "sha256": digest(args.coefficients)},
            "covariance": {"path": str(args.covariance), "sha256": digest(args.covariance)},
            "precipitation_terms_used": 36,
        },
        "country_income": {"path": str(args.pwt_workbook), "sha256": digest(args.pwt_workbook), "join_key": "weight-country ISO3", "target_year": int(pwt_record["target_year"])},
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output), "rows": len(output)},
        "limitations": [
            "Annual quantity is scaled proportionally across fixed baseline months; timing, dry spells, extremes, and drought do not change.",
            "Rows lacking the crop-calendar basis or PWT income are excluded and their value is reported without renormalization.",
            "This is a published-coefficient transport using alternative climate/calendar/area products, not a reproduction of the authors' administrative panel.",
            "No marginal climate path, market damage, discounting, GIVE replacement, or SCC is evaluated here.",
        ],
        "claim_gates": {"quantity_response_input": True, "marginal_response_path": False, "damage": False, "give_replacement": False, "scc": False},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "support_ledger": ledger, "support_loss": result["support_loss"], "output": result["output"]}, indent=2))


if __name__ == "__main__":
    main()
