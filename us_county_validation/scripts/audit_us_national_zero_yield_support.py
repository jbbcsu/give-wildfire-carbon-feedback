#!/usr/bin/env python3
"""Describe reported national all-practice zero yields without fitting a model."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CONFIG_SCHEMA = "us_national_zero_yield_support_config_v1"
CONFIG_ROLE = "descriptive_zero_yield_support_audit_not_response_damage_or_scc"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_bool(series: pd.Series, name: str) -> pd.Series:
    if series.dtype == bool:
        return series
    values = series.astype("string").str.lower()
    if not values.isin(["true", "false"]).all():
        raise ValueError(f"{name} is not strict boolean")
    return values.eq("true")


def audit(corn: pd.DataFrame, positive: pd.DataFrame, geography: pd.DataFrame, config: dict) -> dict:
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("zero-yield audit config identity changed")
    required = {"harvest_year", "county_geoid", "state_alpha", "commodity", "yield_value", "yield_reported"}
    if required - set(corn):
        raise ValueError("corn source lacks required fields")
    source = corn.copy()
    source["county_geoid"] = source.county_geoid.astype("string").str.zfill(5)
    source["harvest_year"] = pd.to_numeric(source.harvest_year, errors="raise").astype(int)
    source["yield_value"] = pd.to_numeric(source.yield_value, errors="coerce")
    source["yield_reported"] = strict_bool(source.yield_reported, "yield_reported")
    start = int(config["inputs"]["year_start"])
    end = int(config["inputs"]["year_end"])
    if source.duplicated(["county_geoid", "harvest_year"]).any() or not source.harvest_year.between(start, end).all():
        raise ValueError("corn source keys or year range changed")
    if set(source.harvest_year) != set(range(start, end + 1)):
        raise ValueError("corn source lacks at least one declared harvest year")
    if set(source.commodity.astype(str).str.upper()) != {"CORN"}:
        raise ValueError("corn source includes another commodity")
    if source.loc[source.yield_reported, "yield_value"].isna().any() or (source.yield_value.dropna() < 0).any():
        raise ValueError("reported corn values are missing or negative")
    zeros = source.loc[source.yield_reported & source.yield_value.eq(0)].copy()
    if len(zeros) != int(config["inputs"]["expected_reported_zero_rows"]):
        raise ValueError("reported zero-yield count changed")
    if (pd.to_numeric(positive["yield_bu_acre"], errors="raise") <= 0).any():
        raise ValueError("positive panel contains a nonpositive yield")
    if positive.duplicated(["outcome_crop", "county_geoid", "harvest_year"]).any():
        raise ValueError("positive panel contains duplicate keys")

    geography = geography.copy()
    geography["county_geoid"] = geography.county_geoid.astype("string").str.zfill(5)
    if geography.duplicated("county_geoid").any():
        raise ValueError("geography gate contains duplicate counties")
    eligible = strict_bool(geography.feature_construction_eligible, "feature_construction_eligible")
    geo_map = dict(zip(geography.county_geoid, eligible, strict=True))
    zeros["geography_eligible"] = zeros.county_geoid.map(geo_map).eq(True)

    share_cols = ["county_geoid", "irrigation_share_eligible", "irrigation_share", "rainfed_dominant_10pct", "rainfed_dominant_20pct", "rainfed_dominant_30pct"]
    shares = positive.loc[positive.outcome_crop.eq("corn_grain"), share_cols].drop_duplicates()
    if shares.duplicated("county_geoid").any():
        raise ValueError("fixed irrigation-share flags vary within county")
    zeros = zeros.merge(shares, on="county_geoid", how="left", validate="many_to_one")
    zeros["irrigation_share_eligible"] = zeros.irrigation_share_eligible.eq(True)
    for threshold in (10, 20, 30):
        name = f"rainfed_dominant_{threshold}pct"
        zeros[name] = zeros[name].eq(True)

    values = source.set_index(["county_geoid", "harvest_year"])["yield_value"]
    adjacent_positive_keys: set[tuple[str, int]] = set()
    run_lengths = []
    for county, group in zeros.sort_values(["county_geoid", "harvest_year"]).groupby("county_geoid", sort=True):
        years = list(map(int, group.harvest_year))
        run = 1
        for previous, current in zip(years, years[1:]):
            if current == previous + 1:
                run += 1
            else:
                run_lengths.append(run)
                run = 1
        run_lengths.append(run)
        for year in years:
            neighbors = [values.get((county, year - 1)), values.get((county, year + 1))]
            if any(pd.notna(value) and float(value) > 0 for value in neighbors):
                adjacent_positive_keys.add((str(county), int(year)))

    zeros["adjacent_positive_observation"] = [
        (str(county), int(year)) in adjacent_positive_keys
        for county, year in zip(zeros.county_geoid, zeros.harvest_year, strict=True)
    ]

    def counts(series: pd.Series) -> dict[str, int]:
        return {str(key): int(value) for key, value in series.value_counts().sort_index().items()}

    state_counts = zeros.state_alpha.value_counts().sort_values(ascending=False)
    top_states = {str(key): int(value) for key, value in state_counts.head(5).items()}
    first_zero_year, last_zero_year = int(zeros.harvest_year.min()), int(zeros.harvest_year.max())
    result = {
        "schema": "us_national_zero_yield_support_audit_v1",
        "role": config["role"],
        "registered_utc_date": config["registered_utc_date"],
        "result": "passed_descriptive_support_only",
        "reported_zero_rows": int(len(zeros)),
        "zero_yield_counties": int(zeros.county_geoid.nunique()),
        "zero_yield_states": int(zeros.state_alpha.nunique()),
        "rows_by_year": counts(zeros.harvest_year),
        "rows_by_state": counts(zeros.state_alpha),
        "top_five_states_by_zero_rows": top_states,
        "top_five_state_row_share": float(sum(top_states.values()) / len(zeros)),
        "state_row_concentration_hhi": float(((state_counts / len(zeros)) ** 2).sum()),
        "first_reported_zero_year": first_zero_year,
        "last_reported_zero_year": last_zero_year,
        "declared_years_before_first_zero": first_zero_year - start,
        "declared_years_after_last_zero": end - last_zero_year,
        "geography_eligible_rows": int(zeros.geography_eligible.sum()),
        "geography_eligible_counties": int(zeros.loc[zeros.geography_eligible, "county_geoid"].nunique()),
        "irrigation_share_eligible_rows": int(zeros.irrigation_share_eligible.sum()),
        "rainfed_dominant_rows": {str(t): int(zeros[f"rainfed_dominant_{t}pct"].sum()) for t in (10, 20, 30)},
        "zero_spell_count": int(len(run_lengths)),
        "zero_spell_max_years": int(max(run_lengths)),
        "zero_spell_length_counts": counts(pd.Series(run_lengths)),
        "rows_with_adjacent_positive_observation": int(zeros.adjacent_positive_observation.sum()),
        "geography_eligible_rows_with_adjacent_positive": int(
            (zeros.geography_eligible & zeros.adjacent_positive_observation).sum()
        ),
        "irrigation_share_eligible_rows_with_adjacent_positive": int(
            (zeros.irrigation_share_eligible & zeros.adjacent_positive_observation).sum()
        ),
        "rainfed_dominant_rows_with_adjacent_positive": {
            str(t): int((zeros[f"rainfed_dominant_{t}pct"] & zeros.adjacent_positive_observation).sum())
            for t in (10, 20, 30)
        },
        "all_practice_outcome_not_direct_rainfed_yield": True,
        "zero_outcome_model_selected": False,
        "relationship_estimated": False,
        "damage_or_scc_authorized": False,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="us_county_validation/us_national_zero_yield_support_v1.toml")
    parser.add_argument("--output", default="data/provenance/us_national_zero_yield_support_20260827.json")
    args = parser.parse_args()
    config_path = ROOT / args.config
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    inputs = config["inputs"]
    paths = {name: ROOT / inputs[name] for name in ("corn_source", "positive_panel", "geography_gate")}
    result = audit(
        pd.read_parquet(paths["corn_source"]),
        pd.read_parquet(paths["positive_panel"]),
        pd.read_csv(paths["geography_gate"], dtype={"county_geoid": "string"}),
        config,
    )
    result["inputs"] = {name: {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "size_bytes": path.stat().st_size} for name, path in paths.items()}
    result["config"] = {"path": str(config_path.relative_to(ROOT)), "sha256": sha256(config_path)}
    result["implementation"] = {
        "path": str(Path(__file__).resolve().relative_to(ROOT)),
        "sha256": sha256(Path(__file__).resolve()),
    }
    output = ROOT / args.output
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Zero-yield support audit passed: {result['reported_zero_rows']} rows, {result['zero_spell_count']} spells")


if __name__ == "__main__":
    main()
