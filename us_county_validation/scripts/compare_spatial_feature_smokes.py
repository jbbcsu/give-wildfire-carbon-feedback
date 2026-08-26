#!/usr/bin/env python3
"""Compare polygon-primary and fixed-CDL sensitivity feature smokes.

The output measures only how two spatial aggregation routes change already-
constructed weather features. It never compares yields to weather and cannot
be interpreted as a response, damage, or SCC result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = ["county_geoid", "outcome_crop", "harvest_year"]
FEATURES = [
    "precip_mm",
    "stage1_precip_mm",
    "stage2_precip_mm",
    "stage3_precip_mm",
    "stage1_precip_share",
    "stage2_precip_share",
    "stage3_precip_share",
    "precipitation_timing_centroid",
    "precipitation_concentration_hhi",
    "wet_days_n",
    "wet_day_frequency",
    "mean_wet_day_intensity_mm",
    "cdd_max_days",
    "rx1day_mm",
    "rx5day_mm",
    "tmean_c",
    "tmin_mean_c",
    "tmax_mean_c",
]
REQUIRED = set(KEYS + FEATURES + [
    "irrigation_practice",
    "weather_source_id",
    "weather_grid_id",
    "calendar_role",
    "weight_role",
    "crop_pixel_exposure",
    "response_estimation_authorized",
    "scc_authorized",
])


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype={"county_geoid": "string"})


def parse_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        values = series.astype(bool)
    else:
        text = series.astype("string").str.strip().str.lower()
        if text.isna().any() or (~text.isin(["true", "false"])).any():
            raise ValueError(f"{label} must contain only true/false")
        values = text.eq("true")
    if values.isna().any():
        raise ValueError(f"{label} contains missing values")
    return values


def strict_false(series: pd.Series, label: str) -> None:
    values = parse_bool(series, label)
    if values.any():
        raise ValueError(f"{label} must be false")


def one_weather_row(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    if missing := REQUIRED - set(frame.columns):
        raise ValueError(f"{label} lacks columns {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{label} is empty")
    strict_false(frame.response_estimation_authorized, f"{label} response authorization")
    strict_false(frame.scc_authorized, f"{label} SCC authorization")
    numeric = frame[FEATURES].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError(f"{label} contains non-finite weather features")
    frame = frame.copy()
    frame[FEATURES] = numeric
    if frame.duplicated(KEYS + ["irrigation_practice"]).any():
        raise ValueError(f"{label} contains duplicate practice rows")
    for _, group in frame.groupby(KEYS, observed=True):
        if len(group[FEATURES].drop_duplicates()) != 1:
            raise ValueError(f"{label} weather differs across practices")
    return frame.drop_duplicates(KEYS).sort_values(KEYS).reset_index(drop=True)


def compare(primary: pd.DataFrame, sensitivity: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    primary_unique = one_weather_row(primary, "primary")
    sensitivity_unique = one_weather_row(sensitivity, "sensitivity")
    if not primary_unique.weight_role.eq("county_polygon_primary_proxy").all():
        raise ValueError("Primary table does not use county-polygon weights")
    if parse_bool(primary_unique.crop_pixel_exposure, "primary crop_pixel_exposure").any():
        raise ValueError("Primary table is incorrectly labeled crop-pixel exposure")
    if not sensitivity_unique.weight_role.eq("fixed_crop_mask_sensitivity").all():
        raise ValueError("Sensitivity table does not use fixed crop-mask weights")
    if not parse_bool(
        sensitivity_unique.crop_pixel_exposure, "sensitivity crop_pixel_exposure"
    ).all():
        raise ValueError("Sensitivity table is not labeled crop-pixel exposure")
    if "mask_temporal_role" not in sensitivity_unique:
        raise ValueError("Sensitivity table lacks mask_temporal_role")
    allowed_roles = {
        "pre_outcome_fixed_2017_sensitivity",
        "retrospective_2017_mask_sensitivity",
    }
    if not set(sensitivity_unique.mask_temporal_role.astype("string")) <= allowed_roles:
        raise ValueError("Sensitivity table uses an unregistered mask temporal role")
    for column in ["weather_source_id", "weather_grid_id", "calendar_role"]:
        left = primary_unique.set_index(KEYS)[column]
        right = sensitivity_unique.set_index(KEYS)[column]
        if not left.index.equals(right.index) or not left.equals(right):
            raise ValueError(f"Spatial routes differ in key support or {column}")

    primary_long = primary_unique.melt(
        id_vars=KEYS, value_vars=FEATURES, var_name="feature", value_name="primary_value"
    )
    sensitivity_long = sensitivity_unique.melt(
        id_vars=KEYS,
        value_vars=FEATURES,
        var_name="feature",
        value_name="cdl_sensitivity_value",
    )
    result = primary_long.merge(
        sensitivity_long, on=KEYS + ["feature"], how="inner", validate="one_to_one"
    )
    result["absolute_difference"] = result.cdl_sensitivity_value - result.primary_value
    result["absolute_magnitude"] = result.absolute_difference.abs()
    result["relative_difference"] = np.where(
        result.primary_value.abs() > 1e-12,
        result.absolute_difference / result.primary_value,
        np.nan,
    )
    result["comparison_role"] = "spatial_measurement_engineering_smoke_only"
    result["relationship_estimated"] = False
    result["response_estimation_authorized"] = False
    result["scc_authorized"] = False

    key_count = int(len(primary_unique))
    audit = {
        "county_crop_year_keys": key_count,
        "features_compared": len(FEATURES),
        "comparison_rows": int(len(result)),
        "crops": sorted(primary_unique.outcome_crop.unique().tolist()),
        "primary_weight_role": "county_polygon_primary_proxy",
        "sensitivity_weight_role": "fixed_crop_mask_sensitivity",
        "sensitivity_mask_temporal_roles": sorted(
            sensitivity_unique.mask_temporal_role.unique().tolist()
        ),
        "maximum_absolute_relative_difference": float(
            result.relative_difference.abs().max(skipna=True)
        ),
        "interpretation": (
            "weather-feature measurement comparison for one bounded county-year; "
            "not a climate-yield relationship or evidence of general equivalence"
        ),
        "relationship_estimated": False,
        "response_estimation_authorized": False,
        "scc_authorized": False,
    }
    return result.sort_values(KEYS + ["feature"]).reset_index(drop=True), audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", required=True)
    parser.add_argument("--sensitivity", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    result, audit = compare(read_table(Path(args.primary)), read_table(Path(args.sensitivity)))
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination, index=False)
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"compared {audit['features_compared']} weather features across "
        f"{audit['county_crop_year_keys']} crop-year keys; no relationship estimated"
    )


if __name__ == "__main__":
    main()
