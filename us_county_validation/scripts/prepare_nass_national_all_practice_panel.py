#!/usr/bin/env python3
"""Build the distinct national all-practice corn/soy outcome panel.

This route does not alter or fill the regional direct-practice panel.  It
attaches the fixed 2017 Census irrigation share where that share is reported,
while preserving an explicit missing-share flag.  It emits outcomes and
pre-outcome sample flags only; no weather relationship, damage, or SCC is
estimated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SOURCE_ID = "nass_quickstats_api_national_all_practice_1981_2019"
KEYS = ["county_geoid", "outcome_crop", "harvest_year"]
INPUT_REQUIRED = {
    "harvest_year", "county_geoid", "state_alpha", "county_name", "commodity",
    "yield_unit", "yield_value", "yield_reported", "prodn_practice_desc",
    "util_practice_desc",
}
SHARE_REQUIRED = {
    "crop", "census_year", "county_geoid", "state_alpha", "irrigation_share",
    "share_eligible", "exclusion_reason",
}
CROP_RULES = {
    "CORN": {"outcome_crop": "corn_grain", "share_crop": "corn", "util": "GRAIN"},
    "SOYBEANS": {
        "outcome_crop": "soybeans",
        "share_crop": "soybeans",
        "util": "ALL UTILIZATION PRACTICES",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _strict_bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing booleans")
        return series.astype(bool)
    text = series.astype("string").str.strip().str.lower()
    if text.isna().any() or (~text.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return text.eq("true")


def _prepare_crop(frame: pd.DataFrame) -> pd.DataFrame:
    if missing := INPUT_REQUIRED - set(frame.columns):
        raise ValueError(f"prepared NASS input lacks fields {sorted(missing)}")
    if frame.empty:
        raise ValueError("prepared NASS input is empty")
    output = frame.copy()
    for column in [
        "county_geoid", "state_alpha", "county_name", "commodity", "yield_unit",
        "prodn_practice_desc", "util_practice_desc",
    ]:
        output[column] = output[column].astype("string").str.strip()
    output["commodity"] = output.commodity.str.upper()
    if output.commodity.nunique() != 1 or output.commodity.iloc[0] not in CROP_RULES:
        raise ValueError("each prepared input must contain one supported commodity")
    rule = CROP_RULES[str(output.commodity.iloc[0])]
    if set(output.yield_unit.str.upper()) != {"BU / ACRE"}:
        raise ValueError("national all-practice yield unit must be BU / ACRE")
    if set(output.prodn_practice_desc.str.upper()) != {"ALL PRODUCTION PRACTICES"}:
        raise ValueError("national outcome must use all production practices")
    if set(output.util_practice_desc.str.upper()) != {str(rule["util"])}:
        raise ValueError("national outcome utilization practice differs from the crop rule")
    if not _strict_bool(output.yield_reported, "yield_reported").all():
        raise ValueError("prepared national panel cannot silently retain nonnumeric yields")
    output["harvest_year"] = pd.to_numeric(output.harvest_year, errors="raise").astype("int64")
    if output.harvest_year.min() != 1981 or output.harvest_year.max() != 2019:
        raise ValueError("national all-practice input must span 1981--2019")
    output["yield_bu_acre"] = pd.to_numeric(output.yield_value, errors="raise")
    if not np.isfinite(output.yield_bu_acre).all() or (output.yield_bu_acre < 0).any():
        raise ValueError("national outcomes must be nonnegative and finite")
    if output.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("national outcome contains malformed county GEOIDs")
    if output.state_alpha.str.fullmatch(r"[A-Z]{2}").ne(True).any():
        raise ValueError("national outcome contains malformed state abbreviations")
    if output.duplicated(["harvest_year", "county_geoid"]).any():
        raise ValueError("prepared crop input duplicates county-year outcomes")
    return pd.DataFrame(
        {
            "county_geoid": output.county_geoid,
            "state": output.state_alpha,
            "county_name": output.county_name,
            "outcome_crop": str(rule["outcome_crop"]),
            "harvest_year": output.harvest_year,
            "yield_bu_acre": output.yield_bu_acre,
            "outcome_value_eligible": output.yield_bu_acre.gt(0),
            "share_crop": str(rule["share_crop"]),
        }
    )


def prepare(crop_frames: list[pd.DataFrame], shares: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if len(crop_frames) != 2:
        raise ValueError("exactly one corn and one soybean prepared input are required")
    crops = pd.concat([_prepare_crop(frame) for frame in crop_frames], ignore_index=True)
    if set(crops.outcome_crop) != {"corn_grain", "soybeans"}:
        raise ValueError("national inputs do not contain exactly corn and soybean")
    if crops.duplicated(KEYS).any():
        raise ValueError("national inputs duplicate crop-county-year outcomes")
    if missing := SHARE_REQUIRED - set(shares.columns):
        raise ValueError(f"2017 irrigation-share input lacks fields {sorted(missing)}")
    fixed = shares.copy()
    fixed["crop"] = fixed.crop.astype("string").str.strip().str.lower()
    fixed["county_geoid"] = fixed.county_geoid.astype("string").str.strip()
    fixed["state_alpha"] = fixed.state_alpha.astype("string").str.strip().str.upper()
    fixed["census_year"] = pd.to_numeric(fixed.census_year, errors="raise").astype("int64")
    if set(fixed.census_year) != {2017}:
        raise ValueError("primary irrigation-share input must be the fixed 2017 vintage")
    fixed = fixed.loc[fixed.crop.isin({"corn", "soybeans"})].copy()
    if set(fixed.crop) != {"corn", "soybeans"} or fixed.duplicated(["crop", "county_geoid"]).any():
        raise ValueError("2017 irrigation-share input lacks unique corn/soy county rows")
    fixed["irrigation_share_eligible"] = _strict_bool(fixed.share_eligible, "share_eligible")
    fixed["irrigation_share"] = pd.to_numeric(fixed.irrigation_share, errors="coerce")
    eligible = fixed.irrigation_share_eligible
    if fixed.loc[eligible, "irrigation_share"].isna().any():
        raise ValueError("share-eligible counties lack numeric irrigation shares")
    if not fixed.loc[eligible, "irrigation_share"].between(0, 1).all():
        raise ValueError("eligible irrigation shares must lie in [0,1]")
    if fixed.loc[~eligible, "irrigation_share"].notna().any():
        raise ValueError("share-ineligible counties cannot carry an irrigation share")
    fixed = fixed.rename(columns={"state_alpha": "share_state"})[
        [
            "crop", "county_geoid", "share_state", "irrigation_share",
            "irrigation_share_eligible", "exclusion_reason",
        ]
    ]
    panel = crops.merge(
        fixed,
        left_on=["share_crop", "county_geoid"],
        right_on=["crop", "county_geoid"],
        how="left",
        validate="many_to_one",
    )
    has_share_row = panel.crop.notna()
    if (has_share_row & panel.share_state.ne(panel.state)).any():
        raise ValueError("NASS outcome and Census irrigation-share states disagree")
    panel["irrigation_share_eligible"] = (
        panel.irrigation_share_eligible.astype("boolean").fillna(False).astype(bool)
    )
    panel["irrigation_share_missing_reason"] = panel.exclusion_reason.astype("string")
    panel.loc[~has_share_row, "irrigation_share_missing_reason"] = "county_absent_from_2017_crop_area_series"
    panel.loc[panel.irrigation_share_eligible, "irrigation_share_missing_reason"] = ""
    for threshold in (10, 20, 30):
        panel[f"rainfed_dominant_{threshold}pct"] = (
            panel.irrigation_share_eligible
            & panel.irrigation_share.le(threshold / 100)
        )
    panel["irrigation_share_vintage"] = 2017
    panel["irrigation_practice"] = "all_practices"
    panel["outcome_source_id"] = SOURCE_ID
    panel["feature_construction_authorized"] = True
    panel["response_estimation_authorized"] = False
    panel["scc_authorized"] = False
    excluded_zero_yield_rows = {
        crop: int((~group.outcome_value_eligible).sum())
        for crop, group in panel.groupby("outcome_crop", observed=True)
    }
    panel = panel.loc[panel.outcome_value_eligible].copy()
    columns = [
        "county_geoid", "state", "county_name", "outcome_crop", "harvest_year",
        "irrigation_practice", "yield_bu_acre", "irrigation_share_vintage",
        "outcome_value_eligible",
        "irrigation_share", "irrigation_share_eligible",
        "irrigation_share_missing_reason", "rainfed_dominant_10pct",
        "rainfed_dominant_20pct", "rainfed_dominant_30pct", "outcome_source_id",
        "feature_construction_authorized", "response_estimation_authorized",
        "scc_authorized",
    ]
    panel = panel[columns].sort_values(KEYS).reset_index(drop=True)
    audit: dict[str, Any] = {
        "role": "national_all_practice_us_validation_outcomes_only_not_response_or_scc",
        "outcome_source_id": SOURCE_ID,
        "year_start": 1981,
        "year_end": 2019,
        "irrigation_share_vintage": 2017,
        "irrigation_rule": (
            "reported 2017 crop-specific Census share only; missing/suppressed numerator "
            "is never assumed zero"
        ),
        "primary_rainfed_dominant_threshold": 0.10,
        "sensitivity_thresholds": [0.20, 0.30],
        "rows": int(len(panel)),
        "counties": int(panel.county_geoid.nunique()),
        "rows_by_crop": {
            str(key): int(value) for key, value in panel.groupby("outcome_crop").size().items()
        },
        "counties_by_crop": {
            str(key): int(value)
            for key, value in panel.groupby("outcome_crop").county_geoid.nunique().items()
        },
        "share_eligible_counties_by_crop": {
            crop: int(group.loc[group.irrigation_share_eligible, "county_geoid"].nunique())
            for crop, group in panel.groupby("outcome_crop", observed=True)
        },
        "rainfed_dominant_counties_by_crop_and_threshold": {
            crop: {
                str(threshold): int(group.loc[group[f"rainfed_dominant_{threshold}pct"], "county_geoid"].nunique())
                for threshold in (10, 20, 30)
            }
            for crop, group in panel.groupby("outcome_crop", observed=True)
        },
        "rows_with_missing_or_unusable_share": int((~panel.irrigation_share_eligible).sum()),
        "excluded_zero_yield_rows_by_crop": excluded_zero_yield_rows,
        "zero_yield_rule": (
            "retain in the commodity-specific prepared source table; exclude explicitly "
            "from this log-yield analysis panel"
        ),
        "all_practice_outcome_not_direct_rainfed_yield": True,
        "relationship_estimated": False,
        "damage_calculated": False,
        "scc_calculated": False,
    }
    return panel, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corn", type=Path, required=True)
    parser.add_argument("--soybeans", type=Path, required=True)
    parser.add_argument("--irrigation-shares", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    inputs = [args.corn, args.soybeans, args.irrigation_shares]
    panel, audit = prepare(
        [pd.read_parquet(args.corn), pd.read_parquet(args.soybeans)],
        pd.read_csv(args.irrigation_shares, dtype={"county_geoid": "string"}),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.out, index=False)
    audit["inputs"] = {
        path.name: {"path": str(path), "sha256": sha256_file(path)} for path in inputs
    }
    audit["output"] = {
        "path": str(args.out), "sha256": sha256_file(args.out), "rows": len(panel)
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {len(panel)} national all-practice corn/soy rows across "
        f"{panel.county_geoid.nunique()} counties; no response estimated"
    )


if __name__ == "__main__":
    main()
