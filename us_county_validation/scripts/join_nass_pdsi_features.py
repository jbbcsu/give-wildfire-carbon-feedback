#!/usr/bin/env python3
"""Join paired-practice NASS outcomes to data-only county PDSI features.

Corn and soybean outcomes map one-to-one to their named NASS calendar.  The
all-classes wheat outcome is deliberately duplicated across every published
wheat calendar candidate available in its state.  Those candidate rows are
not interchangeable observations and must not be pooled or fitted until a
class-selection/weighting rule is frozen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PAIR_KEYS = ["outcome_crop", "county_geoid", "harvest_year"]
PRACTICES = {"irrigated", "non_irrigated"}
DIRECT_CALENDAR = {"corn_grain": "corn_grain", "soybeans": "soybeans"}
WHEAT_CALENDARS = {"winter_wheat", "spring_wheat", "durum_wheat"}
FEATURE_KEYS = [
    "county_geoid", "calendar_crop", "harvest_year", "calendar_role", "window_id",
]
INDEX_FEATURES = [
    "index_day_weighted_mean", "index_monthly_minimum",
    "index_day_equivalents_at_or_below_moderate",
    "index_day_equivalents_at_or_below_severe", "monthly_index_days_covered",
]


def read_table(path: Path) -> pd.DataFrame:
    return (
        pd.read_parquet(path)
        if path.suffix.lower() in {".parquet", ".pq"}
        else pd.read_csv(path, dtype={"county_geoid": "string"})
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _bool(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        if series.isna().any():
            raise ValueError(f"{label} contains missing values")
        return series.astype(bool)
    text = series.astype("string").str.strip().str.lower()
    if text.isna().any() or (~text.isin(["true", "false"])).any():
        raise ValueError(f"{label} must contain only true/false")
    return text.eq("true")


def validate_panel(panel: pd.DataFrame) -> pd.DataFrame:
    required = {
        *PAIR_KEYS, "state", "irrigation_practice", "yield_bu_acre",
        "outcome_source_id", "feature_construction_eligible",
        "response_estimation_authorized", "scc_authorized",
    }
    if missing := required - set(panel.columns):
        raise ValueError(f"NASS panel lacks {sorted(missing)}")
    result = panel.copy()
    result["county_geoid"] = result.county_geoid.astype("string").str.strip()
    result["state"] = result.state.astype("string").str.strip().str.upper()
    result["outcome_crop"] = result.outcome_crop.astype("string").str.strip()
    result["irrigation_practice"] = result.irrigation_practice.astype("string").str.strip()
    result["harvest_year"] = pd.to_numeric(result.harvest_year, errors="raise").astype("int64")
    result["yield_bu_acre"] = pd.to_numeric(result.yield_bu_acre, errors="raise")
    if result.county_geoid.str.fullmatch(r"\d{5}").ne(True).any():
        raise ValueError("NASS panel has malformed GEOIDs")
    if set(result.outcome_crop) != {*DIRECT_CALENDAR, "wheat_all_classes"}:
        raise ValueError("NASS panel must contain exactly corn, soybeans, and all-classes wheat")
    if set(result.irrigation_practice) != PRACTICES:
        raise ValueError("NASS panel must contain exactly both named practices")
    if not np.isfinite(result.yield_bu_acre).all() or (result.yield_bu_acre <= 0).any():
        raise ValueError("NASS panel contains nonpositive or nonfinite outcomes")
    for column in ["feature_construction_eligible", "response_estimation_authorized", "scc_authorized"]:
        result[column] = _bool(result[column], column)
    if result.response_estimation_authorized.any() or result.scc_authorized.any():
        raise ValueError("NASS panel unexpectedly authorizes estimation or SCC use")
    if result.duplicated(PAIR_KEYS + ["irrigation_practice"]).any():
        raise ValueError("NASS panel contains duplicate outcome keys")
    practices = result.groupby(PAIR_KEYS, observed=True).irrigation_practice.agg(set)
    if not practices.map(lambda value: value == PRACTICES).all():
        raise ValueError("NASS panel does not preserve exact practice pairs")
    return result


def validate_geography(geography: pd.DataFrame) -> pd.DataFrame:
    required = {
        "county_geoid", "state", "geography_gate_status",
        "feature_construction_eligible", "response_estimation_authorized", "scc_authorized",
    }
    if missing := required - set(geography.columns):
        raise ValueError(f"geography gate lacks {sorted(missing)}")
    result = geography.copy()
    result["county_geoid"] = result.county_geoid.astype("string").str.strip()
    if result.duplicated("county_geoid").any():
        raise ValueError("geography gate contains duplicate counties")
    for column in ["feature_construction_eligible", "response_estimation_authorized", "scc_authorized"]:
        result[column] = _bool(result[column], f"geography {column}")
    if result.response_estimation_authorized.any() or result.scc_authorized.any():
        raise ValueError("geography gate unexpectedly authorizes estimation or SCC use")
    return result


def validate_features(features: pd.DataFrame) -> pd.DataFrame:
    required = {
        *FEATURE_KEYS, *INDEX_FEATURES, "state", "drought_family", "index_name",
        "index_source_id", "index_scale_months", "index_distribution",
        "calendar_source_id", "window_days", "monthly_value_day_weighted_not_daily_observation",
        "response_estimation_authorized", "scc_authorized",
    }
    if missing := required - set(features.columns):
        raise ValueError(f"PDSI features lack {sorted(missing)}")
    result = features.copy()
    if result.empty or result.duplicated(FEATURE_KEYS).any():
        raise ValueError("PDSI features are empty or duplicate their keys")
    if set(result.drought_family.astype(str)) != {"pdsi"}:
        raise ValueError("one PDSI-only join cannot contain another moisture family")
    if result.index_name.astype(str).nunique() != 1 or result.index_source_id.astype(str).nunique() != 1:
        raise ValueError("PDSI source identity varies within the feature input")
    if not result.index_scale_months.eq(0).all() or set(result.index_distribution.astype(str)) != {"palmer_water_balance"}:
        raise ValueError("PDSI scale/distribution metadata are invalid")
    for column in ["monthly_value_day_weighted_not_daily_observation", "response_estimation_authorized", "scc_authorized"]:
        result[column] = _bool(result[column], f"PDSI feature {column}")
    if not result.monthly_value_day_weighted_not_daily_observation.all():
        raise ValueError("PDSI features are not marked as monthly-index day-weighted")
    if result.response_estimation_authorized.any() or result.scc_authorized.any():
        raise ValueError("PDSI features unexpectedly authorize estimation or SCC use")
    for column in INDEX_FEATURES:
        values = pd.to_numeric(result[column], errors="raise")
        if not np.isfinite(values).all():
            raise ValueError(f"PDSI feature {column} contains nonfinite values")
        result[column] = values
    if not result.monthly_index_days_covered.eq(result.window_days).all():
        raise ValueError("PDSI features do not fully cover their calendar windows")
    return result


def join_panel(
    panel: pd.DataFrame, geography: pd.DataFrame, features: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    panel = validate_panel(panel)
    geography = validate_geography(geography)
    features = validate_features(features)
    geo = geography[["county_geoid", "geography_gate_status", "feature_construction_eligible"]].rename(
        columns={"feature_construction_eligible": "geography_eligible"}
    )
    support = panel.merge(geo, on="county_geoid", how="left", validate="many_to_one")
    if support.geography_eligible.isna().any():
        raise ValueError("a NASS county is absent from the geography gate")
    eligible = support.loc[support.geography_eligible].copy()
    blocked = support.loc[~support.geography_eligible].copy()

    direct = eligible.loc[eligible.outcome_crop.isin(DIRECT_CALENDAR)].copy()
    direct["calendar_crop"] = direct.outcome_crop.map(DIRECT_CALENDAR)
    wheat = eligible.loc[eligible.outcome_crop.eq("wheat_all_classes")].copy()
    wheat_features = features.loc[features.calendar_crop.isin(WHEAT_CALENDARS)]
    available = wheat_features[["state", "calendar_crop"]].drop_duplicates()
    wheat = wheat.merge(available, on="state", how="left", validate="many_to_many")
    if wheat.calendar_crop.isna().any():
        raise ValueError("an eligible all-wheat outcome state lacks every wheat calendar candidate")
    routed = pd.concat([direct, wheat], ignore_index=True)
    routed["calendar_mapping_role"] = np.where(
        routed.outcome_crop.eq("wheat_all_classes"),
        "unresolved_all_classes_wheat_candidate_not_poolable",
        "direct_named_crop_calendar",
    )
    joined = routed.merge(
        features, on=["county_geoid", "state", "calendar_crop", "harvest_year"],
        how="left", validate="many_to_many", suffixes=("", "_pdsi"),
    )
    missing = joined.index_source_id.isna()
    if missing.any():
        examples = joined.loc[missing, PAIR_KEYS + ["state", "calendar_crop"]].head(10)
        raise ValueError(f"eligible NASS rows lack PDSI calendar features: {examples.to_dict('records')}")
    expected_windows = features[["calendar_role", "window_id"]].drop_duplicates().shape[0]
    routed_keys = PAIR_KEYS + ["irrigation_practice", "calendar_crop"]
    counts = joined.groupby(routed_keys, observed=True).size()
    if not counts.eq(expected_windows).all():
        raise ValueError("joined NASS routes do not have the complete PDSI window set")
    joined["feature_family"] = "pdsi"
    joined["moisture_family_rule"] = "mutually_exclusive_not_stacked_with_direct_weather_or_spei"
    joined["analysis_role"] = "joined_outcome_exposure_support_not_predictor_matrix"
    joined["feature_construction_eligible"] = True
    joined["response_estimation_authorized"] = False
    joined["scc_authorized"] = False
    joined = joined.sort_values(routed_keys + ["calendar_role", "window_id"]).reset_index(drop=True)

    eligible_pairs = eligible.drop_duplicates(PAIR_KEYS)
    blocked_pairs = blocked.drop_duplicates(PAIR_KEYS)
    direct_pairs = eligible_pairs.loc[eligible_pairs.outcome_crop.isin(DIRECT_CALENDAR)]
    wheat_pairs = eligible_pairs.loc[eligible_pairs.outcome_crop.eq("wheat_all_classes")]
    wheat_candidate_counts = (
        wheat.drop_duplicates(PAIR_KEYS + ["calendar_crop"])
        .groupby("calendar_crop", observed=True).size().sort_index().to_dict()
    )
    audit = {
        "role": "data-only paired-practice NASS/PDSI join; not a fitted climate-yield result",
        "input_paired_crop_county_years": int(panel.drop_duplicates(PAIR_KEYS).shape[0]),
        "input_long_practice_rows": int(len(panel)),
        "geography_eligible_paired_crop_county_years": int(len(eligible_pairs)),
        "geography_eligible_long_practice_rows": int(len(eligible)),
        "geography_blocked_paired_crop_county_years": int(len(blocked_pairs)),
        "geography_blocked_long_practice_rows": int(len(blocked)),
        "direct_calendar_paired_crop_county_years": int(len(direct_pairs)),
        "all_wheat_paired_crop_county_years": int(len(wheat_pairs)),
        "all_wheat_calendar_candidate_pair_counts": {str(k): int(v) for k, v in wheat_candidate_counts.items()},
        "joined_long_window_rows": int(len(joined)),
        "joined_unique_outcome_practice_rows": int(joined.drop_duplicates(PAIR_KEYS + ["irrigation_practice"]).shape[0]),
        "pdsi_window_variants_per_calendar_candidate": int(expected_windows),
        "irrigation_practices": sorted(PRACTICES),
        "suppressed_outcome_rule": "only positive numeric exact pairs from the upstream NASS panel enter; absent/suppressed practices are never imputed",
        "wheat_gate": "all-classes wheat calendar candidates remain separate and non-poolable until class weights or a class-selection rule are frozen",
        "pdsi_role": "mutually exclusive moisture predictor family; not additive with direct weather or SPEI",
        "monthly_index_interpretation": "threshold counts are monthly-index day-equivalents, not daily drought observations",
        "contains_outcome_values": True,
        "predictor_matrix_constructed": False,
        "immediate_input_hashes_only": True,
        "upstream_raw_metric_recomputation_in_this_join": False,
        "response_estimated": False,
        "causal_effect_estimated": False,
        "damage_calculated": False,
        "scc_calculated": False,
    }
    return joined, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--geography-gate", required=True)
    parser.add_argument("--pdsi-features", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit-out", required=True)
    args = parser.parse_args()
    panel_path = Path(args.panel)
    geography_path = Path(args.geography_gate)
    feature_path = Path(args.pdsi_features)
    joined, audit = join_panel(
        read_table(panel_path), read_table(geography_path), read_table(feature_path),
    )
    audit["inputs"] = {
        "nass_panel": {"path": str(panel_path), "sha256": sha256(panel_path)},
        "geography_gate": {"path": str(geography_path), "sha256": sha256(geography_path)},
        "pdsi_features": {"path": str(feature_path), "sha256": sha256(feature_path)},
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    joined.to_parquet(output, index=False)
    audit["output"] = {"path": str(output), "sha256": sha256(output)}
    audit_path = Path(args.audit_out)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {len(joined)} data-only PDSI join rows; "
        "response_estimation_authorized=false; scc_authorized=false"
    )


if __name__ == "__main__":
    main()
