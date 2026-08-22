#!/usr/bin/env python3
"""Validate a paired crop-response bundle before any GIVE SCC wiring.

The validator checks identities, crop/region coverage, fixed baseline weights,
finite coefficients/features, and baseline/pulse pairing. It does not validate
empirical skill or authorize a bundle for production use by itself.
"""
from __future__ import annotations

import argparse
import csv
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


PAIR_KEYS = ["draw_id", "year", "fund_region", "crop"]
ID_FIELDS = [
    "fair_draw_id", "climate_member_id", "socioeconomic_id", "calendar_id",
    "response_draw_id", "adaptation_scenario", "weight_draw_id", "welfare_draw_id",
]
FEATURE_FIELDS = [
    "mean_temp_anomaly", "seasonal_precip_anomaly", "precip_timing_anomaly",
    "water_stress_anomaly", "wet_extreme_anomaly", "heat_extreme_anomaly",
]
COEFFICIENT_FIELDS = [
    "beta_temp", "beta_precip", "beta_timing", "beta_water_stress",
    "beta_wet_extreme", "beta_heat_extreme", "beta_temp_precip",
]
PAIR_FIXED_FIELDS = ID_FIELDS + COEFFICIENT_FIELDS + [
    "crop_value_share", "adaptation_loss_multiplier", "adaptation_cost_share",
]
WATER_STRESS_FAMILIES = {"direct", "climatic_index", "soil_moisture"}


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError("Bundle must be CSV or Parquet")


def load_contract(contract_path: Path, region_path: Path) -> tuple[list[str], list[str], float]:
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    crops = [str(value) for value in contract["crops"]]
    with region_path.open(newline="", encoding="utf-8") as stream:
        regions = [row["fund_region"] for row in csv.DictReader(stream)]
    tolerance = float(contract.get("weight_tolerance", 1e-8))
    if not crops or len(crops) != len(set(crops)) or not regions or len(regions) != len(set(regions)):
        raise ValueError("Contract crop and region orders must be nonempty and unique")
    return crops, regions, tolerance


def _allclose(left: pd.Series, right: pd.Series, tolerance: float) -> bool:
    if pd.api.types.is_numeric_dtype(left) and pd.api.types.is_numeric_dtype(right):
        return bool(np.allclose(left.to_numpy(dtype=float), right.to_numpy(dtype=float), rtol=0, atol=tolerance))
    return left.astype(str).reset_index(drop=True).equals(right.astype(str).reset_index(drop=True))


def validate_bundle(
    frame: pd.DataFrame,
    crops: list[str],
    regions: list[str],
    water_stress_family: str,
    first_divergence_year: int,
    tolerance: float = 1e-8,
) -> dict[str, object]:
    frame = frame.copy()
    if water_stress_family not in WATER_STRESS_FAMILIES:
        raise ValueError(f"Unknown water-stress family {water_stress_family!r}")
    required = set(PAIR_KEYS + ID_FIELDS + FEATURE_FIELDS + COEFFICIENT_FIELDS) | {
        "scenario", "crop_value_share", "adaptation_loss_multiplier",
        "adaptation_cost_share", "observed_support",
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"Bundle missing required fields {sorted(missing)}")
    frame["scenario"] = frame.scenario.astype(str)
    frame["crop"] = frame.crop.astype(str)
    frame["fund_region"] = frame.fund_region.astype(str)
    years = pd.to_numeric(frame.year, errors="coerce")
    if years.isna().any() or not np.equal(years, np.floor(years)).all():
        raise ValueError("year must be a finite integer")
    frame["year"] = years.astype(int)
    if set(frame.scenario) != {"baseline", "pulse"}:
        raise ValueError("Scenario labels must be exactly baseline and pulse")
    if frame.duplicated(["scenario"] + PAIR_KEYS).any():
        raise ValueError("Bundle has duplicate scenario/draw/year/region/crop keys")
    if set(frame.crop.astype(str)) != set(crops) or set(frame.fund_region.astype(str)) != set(regions):
        raise ValueError("Bundle crop or FUND-region labels differ from the frozen contract")

    numeric = FEATURE_FIELDS + COEFFICIENT_FIELDS + [
        "crop_value_share", "adaptation_loss_multiplier", "adaptation_cost_share",
    ]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    values = frame[numeric].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Bundle contains nonfinite features, coefficients, weights, or adaptation values")
    if (frame.crop_value_share < 0).any():
        raise ValueError("Crop-value shares must be nonnegative")
    if (frame.adaptation_loss_multiplier < 0).any() or (frame.adaptation_cost_share < 0).any():
        raise ValueError("Adaptation multipliers and costs must be nonnegative")
    support_normalized = frame.observed_support.astype(str).str.lower()
    support_values = set(support_normalized.loc[frame.observed_support.notna()])
    if support_values - {"true", "false", "0", "1"}:
        raise ValueError("observed_support must be a nonmissing Boolean flag")
    if frame.observed_support.isna().any():
        raise ValueError("observed_support must be a nonmissing Boolean flag")
    for field in ID_FIELDS:
        if frame[field].isna().any() or (frame[field].astype(str).str.len() == 0).any():
            raise ValueError(f"Identifier {field} must be nonmissing and nonempty")
        if not frame.groupby("draw_id", observed=True)[field].nunique(dropna=False).eq(1).all():
            raise ValueError(f"Identifier {field} is not frozen within draw_id")

    expected_cells = len(crops) * len(regions)
    coverage_counts = frame.groupby(["scenario", "draw_id", "year"], observed=True).size()
    if not coverage_counts.eq(expected_cells).all():
        raise ValueError("Every scenario/draw/year must contain the full crop by FUND-region product")
    group_labels = frame.groupby(["scenario", "draw_id", "year"], observed=True).apply(
        lambda group: set(zip(group.fund_region.astype(str), group.crop.astype(str))),
        include_groups=False,
    )
    expected_labels = {(region, crop) for region in regions for crop in crops}
    if not group_labels.map(lambda labels: labels == expected_labels).all():
        raise ValueError("A scenario/draw/year has duplicated or incomplete region-crop coverage")

    share_sums = frame.groupby(["scenario", "draw_id", "year", "fund_region"], observed=True).crop_value_share.sum()
    if not np.allclose(share_sums.to_numpy(dtype=float), 1.0, rtol=0, atol=tolerance):
        raise ValueError("Production bundle crop-value shares must sum to one in every region")
    share_ranges = frame.groupby(["draw_id", "fund_region", "crop"], observed=True).crop_value_share.agg(
        lambda x: x.max() - x.min()
    )
    if (share_ranges > tolerance).any():
        raise ValueError("Crop-value shares must be fixed across scenarios and years within a draw")

    baseline = frame.loc[frame.scenario.eq("baseline")].sort_values(PAIR_KEYS).reset_index(drop=True)
    pulse = frame.loc[frame.scenario.eq("pulse")].sort_values(PAIR_KEYS).reset_index(drop=True)
    if not baseline[PAIR_KEYS].equals(pulse[PAIR_KEYS]):
        raise ValueError("Baseline and pulse keys are not exactly matched")
    for field in PAIR_FIXED_FIELDS:
        if not _allclose(baseline[field], pulse[field], tolerance):
            raise ValueError(f"Baseline/pulse field {field} is not matched")
    for field in COEFFICIENT_FIELDS:
        ranges = frame.groupby(["scenario", "draw_id", "fund_region", "crop"], observed=True)[field].agg(
            lambda x: x.max() - x.min()
        )
        if (ranges > tolerance).any():
            raise ValueError(f"Coefficient {field} changes over time within a response draw")

    before = baseline.year.astype(int) < first_divergence_year
    for field in FEATURE_FIELDS:
        if not _allclose(baseline.loc[before, field], pulse.loc[before, field], tolerance):
            raise ValueError(f"Feature {field} differs before the declared first-divergence year")

    return {
        "status": "schema_and_pairing_validated_not_empirically_authorized",
        "n_rows": int(len(frame)),
        "n_draws": int(frame.draw_id.nunique()),
        "years": [int(value) for value in sorted(frame.year.unique())],
        "n_regions": len(regions),
        "n_crops": len(crops),
        "water_stress_family": water_stress_family,
        "first_divergence_year": first_divergence_year,
        "observed_support_share": float(support_normalized.isin({"true", "1"}).mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--contract", default="config/crop_response_contract.toml")
    parser.add_argument("--region-order", default="config/fund_region_order.csv")
    parser.add_argument("--water-stress-family", required=True, choices=sorted(WATER_STRESS_FAMILIES))
    parser.add_argument("--first-divergence-year", type=int, required=True)
    parser.add_argument("--audit-out")
    args = parser.parse_args()
    crops, regions, tolerance = load_contract(Path(args.contract), Path(args.region_order))
    audit = validate_bundle(
        read_table(Path(args.bundle)), crops, regions, args.water_stress_family,
        args.first_divergence_year, tolerance,
    )
    if args.audit_out:
        output = Path(args.audit_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
