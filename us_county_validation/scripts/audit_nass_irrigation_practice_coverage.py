#!/usr/bin/env python3
"""Fail-closed coverage audit for NASS irrigation-practice inputs.

The audit has two distinct outputs:

1. paired SURVEY county yields reported separately for IRRIGATED and
   NON-IRRIGATED production practices; and
2. a Census-year crop-specific irrigated-area share built only where both the
   IRRIGATED numerator and ALL PRODUCTION PRACTICES denominator are numeric.

An absent or suppressed irrigated-area record is never interpreted as zero.
The output is a support diagnostic, not a yield-response estimate or SCC input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


CROP_SERIES = {
    "CORN": {"crop": "corn", "util": "GRAIN", "yield_unit": "BU / ACRE"},
    "SOYBEANS": {
        "crop": "soybeans",
        "util": "ALL UTILIZATION PRACTICES",
        "yield_unit": "BU / ACRE",
    },
    "WHEAT": {
        "crop": "wheat",
        "util": "ALL UTILIZATION PRACTICES",
        "yield_unit": "BU / ACRE",
    },
}
PRACTICES = ("IRRIGATED", "NON-IRRIGATED")
PAIR_KEYS = ["crop", "year", "county_geoid"]
SHARE_COLUMNS = [
    "crop", "census_year", "county_geoid", "state_alpha", "state_name", "county_name",
    "total_harvested_acres", "irrigated_harvested_acres", "irrigation_share",
    "share_eligible", "exclusion_reason",
]


def _text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def _load(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if set(payload) != {"data"} or not isinstance(payload["data"], list) or not payload["data"]:
        raise ValueError(f"{path}: expected one nonempty Quick Stats data array")
    frame = pd.DataFrame(payload["data"])
    required = {
        "source_desc", "sector_desc", "commodity_desc", "class_desc",
        "statisticcat_desc", "agg_level_desc", "freq_desc", "reference_period_desc",
        "domain_desc", "domaincat_desc", "prodn_practice_desc", "util_practice_desc",
        "unit_desc", "year", "state_ansi", "county_ansi", "state_alpha", "state_name",
        "county_name", "Value",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path}: missing Quick Stats fields {missing}")
    return frame


def _require_one(frame: pd.DataFrame, column: str, expected: str, path: Path) -> None:
    observed = set(_text(frame[column]).str.upper())
    if observed != {expected}:
        raise ValueError(f"{path}: {column} differs from {expected!r}: {sorted(observed)}")


def _base_prepare(path: Path) -> pd.DataFrame:
    frame = _load(path)
    common = {
        "sector_desc": "CROPS",
        "class_desc": "ALL CLASSES",
        "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL",
        "domaincat_desc": "NOT SPECIFIED",
    }
    for column, expected in common.items():
        _require_one(frame, column, expected, path)
    commodity = set(_text(frame["commodity_desc"]).str.upper())
    if len(commodity) != 1 or next(iter(commodity)) not in CROP_SERIES:
        raise ValueError(f"{path}: unsupported or mixed commodity_desc {sorted(commodity)}")
    commodity_name = next(iter(commodity))
    specification = CROP_SERIES[commodity_name]
    _require_one(frame, "util_practice_desc", specification["util"], path)
    years = pd.to_numeric(frame["year"], errors="coerce")
    if years.isna().any() or (years % 1 != 0).any():
        raise ValueError(f"{path}: non-integer year")
    state = _text(frame["state_ansi"])
    county = _text(frame["county_ansi"])
    frame["real_county"] = (
        state.str.fullmatch(r"\d{2}", na=False)
        & county.str.fullmatch(r"\d{3}", na=False)
    )
    frame["county_geoid"] = (state.fillna("") + county.fillna("")).where(frame["real_county"])
    frame["year"] = years.astype("int64")
    frame["crop"] = specification["crop"]
    raw = _text(frame["Value"])
    frame["value_raw"] = raw
    frame["value_numeric"] = pd.to_numeric(
        raw.str.replace(",", "", regex=False), errors="coerce"
    ).astype("Float64")
    frame["value_reported"] = frame["value_numeric"].notna()
    for column in ("state_alpha", "state_name", "county_name", "prodn_practice_desc"):
        frame[column] = _text(frame[column])
    return frame


def prepare_yield(path: Path) -> pd.DataFrame:
    frame = _base_prepare(path)
    _require_one(frame, "source_desc", "SURVEY", path)
    _require_one(frame, "statisticcat_desc", "YIELD", path)
    commodity = str(_text(frame["commodity_desc"]).str.upper().iloc[0])
    _require_one(frame, "unit_desc", CROP_SERIES[commodity]["yield_unit"], path)
    practices = set(_text(frame["prodn_practice_desc"]).str.upper())
    if len(practices) != 1 or next(iter(practices)) not in PRACTICES:
        raise ValueError(f"{path}: expected one irrigation production practice, got {sorted(practices)}")
    frame["practice"] = next(iter(practices))
    selected = frame.loc[frame["real_county"]].copy()
    keys = ["crop", "year", "county_geoid", "practice"]
    if selected.duplicated(keys).any():
        examples = selected.loc[selected.duplicated(keys, keep=False), keys].head(5).to_dict("records")
        raise ValueError(f"{path}: duplicate real-county yield keys: {examples}")
    selected["nonpositive_numeric_yield"] = (
        selected["value_reported"] & (selected["value_numeric"] <= 0)
    )
    selected["yield_eligible"] = (
        selected["value_reported"] & (selected["value_numeric"] > 0)
    )
    selected["analysis_value"] = selected["value_numeric"].where(selected["yield_eligible"])
    return selected


def _practice_stats(frame: pd.DataFrame) -> dict[str, Any]:
    usable = frame.loc[frame["yield_eligible"]]
    return {
        "raw_real_county_rows": int(len(frame)),
        "numeric_real_county_rows": int(frame["value_reported"].sum()),
        "usable_positive_yield_rows": int(frame["yield_eligible"].sum()),
        "nonpositive_numeric_real_county_rows": int(frame["nonpositive_numeric_yield"].sum()),
        "suppressed_or_nonnumeric_real_county_rows": int((~frame["value_reported"]).sum()),
        "first_year": int(frame["year"].min()),
        "last_year": int(frame["year"].max()),
        "published_year_count": int(frame["year"].nunique()),
        "usable_state_count": int(usable["state_alpha"].nunique()),
        "usable_county_count": int(usable["county_geoid"].nunique()),
        "states": sorted(str(value) for value in usable["state_alpha"].dropna().unique()),
    }


def audit_yields(paths: list[Path]) -> dict[str, Any]:
    frames = [prepare_yield(path) for path in paths]
    combined = pd.concat(frames, ignore_index=True)
    results: dict[str, Any] = {}
    for crop in sorted(combined["crop"].unique()):
        crop_frame = combined.loc[combined["crop"] == crop].copy()
        present = set(crop_frame["practice"])
        if present != set(PRACTICES):
            raise ValueError(f"{crop}: yield inputs do not contain both practices: {sorted(present)}")
        if crop_frame.duplicated(PAIR_KEYS + ["practice"]).any():
            raise ValueError(f"{crop}: duplicate yield keys across input files")
        practices = {
            practice.lower().replace("-", "_"): _practice_stats(
                crop_frame.loc[crop_frame["practice"] == practice]
            )
            for practice in PRACTICES
        }
        wide = crop_frame.pivot(index=PAIR_KEYS, columns="practice", values="analysis_value")
        paired = wide.dropna(subset=list(PRACTICES)).reset_index()
        row_metadata = (
            crop_frame.sort_values(PAIR_KEYS)
            .drop_duplicates(PAIR_KEYS)
            [PAIR_KEYS + ["state_alpha"]]
        )
        paired = paired.merge(row_metadata, on=PAIR_KEYS, how="left", validate="one_to_one")
        annual = paired.groupby("year", sort=True).size()
        climate_overlap = paired.loc[paired["year"].between(1981, 2019)]
        recent = paired.loc[paired["year"].between(2018, 2022)]
        results[crop] = {
            "practice": practices,
            "reported_paired_county_years": int(len(paired)),
            "reported_paired_counties": int(paired["county_geoid"].nunique()),
            "reported_paired_states": int(paired["state_alpha"].nunique()),
            "paired_first_year": int(paired["year"].min()) if len(paired) else None,
            "paired_last_year": int(paired["year"].max()) if len(paired) else None,
            "paired_year_count": int(paired["year"].nunique()),
            "paired_1981_2019_county_years": int(len(climate_overlap)),
            "paired_1981_2019_counties": int(climate_overlap["county_geoid"].nunique()),
            "paired_1981_2019_states": sorted(
                str(value) for value in climate_overlap["state_alpha"].dropna().unique()
            ),
            "paired_2018_2022_county_years": int(len(recent)),
            "paired_2018_2022_counties": int(recent["county_geoid"].nunique()),
            "paired_2018_2022_states": sorted(
                str(value) for value in recent["state_alpha"].dropna().unique()
            ),
            "reported_pairs_by_year": {str(int(k)): int(v) for k, v in annual.items()},
            "interpretation": (
                "regional_direct-practice validation candidate; not a national county panel"
                if len(paired) else "no direct-practice paired yield support"
            ),
        }
    missing_crops = sorted(set(value["crop"] for value in CROP_SERIES.values()) - set(results))
    if missing_crops:
        raise ValueError(f"yield audit is missing crops: {missing_crops}")
    return results


def prepare_area(path: Path) -> pd.DataFrame:
    frame = _base_prepare(path)
    _require_one(frame, "source_desc", "CENSUS", path)
    _require_one(frame, "statisticcat_desc", "AREA HARVESTED", path)
    _require_one(frame, "unit_desc", "ACRES", path)
    if frame["year"].nunique() != 1:
        raise ValueError(f"{path}: area discovery must contain exactly one Census year")
    practices = set(_text(frame["prodn_practice_desc"]).str.upper())
    expected = {"ALL PRODUCTION PRACTICES", "IRRIGATED"}
    if practices != expected:
        raise ValueError(f"{path}: area practices differ from {sorted(expected)}: {sorted(practices)}")
    selected = frame.loc[frame["real_county"]].copy()
    keys = ["crop", "year", "county_geoid", "prodn_practice_desc"]
    if selected.duplicated(keys).any():
        examples = selected.loc[selected.duplicated(keys, keep=False), keys].head(5).to_dict("records")
        raise ValueError(f"{path}: duplicate real-county area keys: {examples}")
    if (selected.loc[selected["value_reported"], "value_numeric"] < 0).any():
        raise ValueError(f"{path}: reported harvested area is negative")
    return selected


def audit_areas(paths: list[Path]) -> tuple[pd.DataFrame, dict[str, Any]]:
    frames = [prepare_area(path) for path in paths]
    combined = pd.concat(frames, ignore_index=True)
    outputs: list[pd.DataFrame] = []
    results: dict[str, Any] = {}
    for crop in sorted(combined["crop"].unique()):
        crop_frame = combined.loc[combined["crop"] == crop].copy()
        if crop_frame["year"].nunique() != 1:
            raise ValueError(f"{crop}: mixed Census years")
        year = int(crop_frame["year"].iloc[0])
        metadata = (
            crop_frame.sort_values(PAIR_KEYS)
            .drop_duplicates(PAIR_KEYS)
            [PAIR_KEYS + ["state_alpha", "state_name", "county_name"]]
        )
        wide = crop_frame.pivot(
            index=PAIR_KEYS, columns="prodn_practice_desc", values="value_numeric"
        ).reset_index()
        wide = wide.merge(metadata, on=PAIR_KEYS, how="left", validate="one_to_one")
        wide = wide.rename(columns={
            "ALL PRODUCTION PRACTICES": "total_harvested_acres",
            "IRRIGATED": "irrigated_harvested_acres",
            "year": "census_year",
        })
        both = wide["total_harvested_acres"].notna() & wide["irrigated_harvested_acres"].notna()
        positive_total = wide["total_harvested_acres"].fillna(0) > 0
        eligible = both & positive_total
        share = pd.Series(pd.NA, index=wide.index, dtype="Float64")
        share.loc[eligible] = (
            wide.loc[eligible, "irrigated_harvested_acres"]
            / wide.loc[eligible, "total_harvested_acres"]
        )
        if ((share.dropna() < 0) | (share.dropna() > 1.000001)).any():
            examples = wide.loc[
                ((share < 0) | (share > 1.000001)).fillna(False),
                ["crop", "census_year", "county_geoid"],
            ].head(5)
            raise ValueError(f"{crop}: irrigation share outside [0,1] beyond tolerance: {examples.to_dict('records')}")
        share = share.clip(lower=0, upper=1)
        wide["irrigation_share"] = share
        wide["share_eligible"] = eligible
        wide["exclusion_reason"] = ""
        wide.loc[wide["total_harvested_acres"].isna(), "exclusion_reason"] = (
            "missing_or_suppressed_total_area"
        )
        wide.loc[
            wide["total_harvested_acres"].notna() & ~positive_total,
            "exclusion_reason",
        ] = "nonpositive_total_area"
        wide.loc[
            positive_total & wide["irrigated_harvested_acres"].isna(),
            "exclusion_reason",
        ] = "missing_or_suppressed_irrigated_area_not_assumed_zero"
        eligible_frame = wide.loc[eligible]
        thresholds = {
            f"share_le_{int(threshold * 100)}pct": int(
                (eligible_frame["irrigation_share"] <= threshold).sum()
            )
            for threshold in (0.10, 0.20, 0.30)
        }
        results[crop] = {
            "census_year": year,
            "real_county_rows_total_series": int(
                (crop_frame["prodn_practice_desc"] == "ALL PRODUCTION PRACTICES").sum()
            ),
            "reported_total_area_counties": int(
                (
                    (crop_frame["prodn_practice_desc"] == "ALL PRODUCTION PRACTICES")
                    & crop_frame["value_reported"]
                ).sum()
            ),
            "real_county_rows_irrigated_series": int(
                (crop_frame["prodn_practice_desc"] == "IRRIGATED").sum()
            ),
            "reported_irrigated_area_counties": int(
                (
                    (crop_frame["prodn_practice_desc"] == "IRRIGATED")
                    & crop_frame["value_reported"]
                ).sum()
            ),
            "share_eligible_counties": int(eligible.sum()),
            "share_eligible_states": int(eligible_frame["state_alpha"].nunique()),
            "total_reported_but_irrigated_missing_counties": int(
                (positive_total & wide["irrigated_harvested_acres"].isna()).sum()
            ),
            "candidate_high_rainfed_counts": thresholds,
            "interpretation": (
                f"fixed {year} crop-specific selection weight only; missing numerator is excluded, never zero"
            ),
        }
        outputs.append(wide[SHARE_COLUMNS])
    missing_crops = sorted(set(value["crop"] for value in CROP_SERIES.values()) - set(results))
    if missing_crops:
        raise ValueError(f"area audit is missing crops: {missing_crops}")
    shares = pd.concat(outputs, ignore_index=True).sort_values(
        ["crop", "county_geoid"]
    ).reset_index(drop=True)
    return shares, results


def run(yield_paths: list[Path], area_paths: list[Path]) -> tuple[pd.DataFrame, dict[str, Any]]:
    yield_audit = audit_yields(yield_paths)
    shares, area_audit = audit_areas(area_paths)
    area_years = sorted({int(entry["census_year"]) for entry in area_audit.values()})
    if len(area_years) != 1:
        raise ValueError(f"area audit must represent one Census vintage, got {area_years}")
    area_year = area_years[0]
    audit = {
        "role": "US county irrigation identification support audit only; not a response or SCC input",
        "direct_practice_yields": yield_audit,
        "census_irrigation_share_fallback": area_audit,
        "missingness_rule": (
            "suppressed, nonnumeric, or absent irrigated acres are never interpreted as zero"
        ),
        "use_boundary": (
            f"direct practice yields support regional validation where paired; {area_year} Census shares are "
            "fixed sample-selection weights for aggregate county yields, not annual irrigation status"
        ),
    }
    return shares, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yield-input", type=Path, action="append", required=True)
    parser.add_argument("--area-input", type=Path, action="append", required=True)
    parser.add_argument("--shares-out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    shares, audit = run(args.yield_input, args.area_input)
    args.shares_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    shares.to_csv(args.shares_out, index=False)
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {len(shares)} county crop-share rows and audited "
        f"{len(audit['direct_practice_yields'])} direct-practice crops"
    )


if __name__ == "__main__":
    main()
