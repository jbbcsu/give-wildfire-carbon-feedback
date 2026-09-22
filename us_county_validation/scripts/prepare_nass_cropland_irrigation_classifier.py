#!/usr/bin/env python3
"""Prepare the four-vintage all-cropland irrigation classifier.

This implements the data rule described by Kuwayama et al. (2019): divide
irrigated harvested cropland by total harvested cropland in each available
Census year, take the county maximum over 1997/2002/2007/2012, and classify a
county as irrigated when that maximum exceeds 15 percent. Suppressed or absent
numerators are missing, never zero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


YEARS = (1997, 2002, 2007, 2012)
PRACTICES = ("ALL PRODUCTION PRACTICES", "IRRIGATED")
EXPECTED = {
    "source_desc": "CENSUS",
    "sector_desc": "ECONOMICS",
    "group_desc": "FARMS & LAND & ASSETS",
    "commodity_desc": "AG LAND",
    "class_desc": "CROPLAND, HARVESTED",
    "statisticcat_desc": "AREA",
    "agg_level_desc": "COUNTY",
    "freq_desc": "ANNUAL",
    "reference_period_desc": "YEAR",
    "domain_desc": "TOTAL",
    "domaincat_desc": "NOT SPECIFIED",
    "util_practice_desc": "ALL UTILIZATION PRACTICES",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_receipts(manifest: Path, paths: dict[int, Path]) -> list[dict[str, Any]]:
    """Freeze key-free official acquisition metadata into tracked provenance."""
    by_name: dict[str, list[dict[str, Any]]] = {}
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        raw_name = Path(str(record.get("raw_file", ""))).name
        if not raw_name:
            raise ValueError(f"{manifest}: line {number} lacks raw_file")
        by_name.setdefault(raw_name, []).append(record)
    receipts = []
    for year in YEARS:
        path = paths[year]
        matches = by_name.get(path.name, [])
        if len(matches) != 1:
            raise ValueError(
                f"{manifest}: expected exactly one acquisition receipt for {path.name}, "
                f"found {len(matches)}"
            )
        record = matches[0]
        query = dict(record["query_parameters_excluding_key"])
        if "key" in {str(key).lower() for key in query}:
            raise ValueError(f"{manifest}: credential-like key field in receipt for {path.name}")
        if str(query.get("year")) != str(year):
            raise ValueError(f"{manifest}: year mismatch for {path.name}")
        observed = {"bytes": path.stat().st_size, "sha512": sha512(path)}
        expected = {
            "bytes": int(record["raw_bytes"]),
            "sha512": str(record["raw_sha512"]).lower(),
        }
        if observed != expected:
            raise ValueError(f"{manifest}: raw identity mismatch for {path.name}")
        receipts.append({
            "year": year,
            "file": path.name,
            "bytes": observed["bytes"],
            "sha512": observed["sha512"],
            "retrieved_utc": record["retrieved_utc"],
            "source": record["source"],
            "license": record["license"],
            "official_count_endpoint": record["official_count_endpoint"],
            "official_data_endpoint": record["official_data_endpoint"],
            "preflight_count": int(record["preflight_count"]),
            "query_parameters_excluding_key": query,
        })
    return receipts


def _one_value(frame: pd.DataFrame, column: str, expected: str, path: Path) -> None:
    values = set(frame[column].astype("string").str.strip())
    if values != {expected}:
        raise ValueError(f"{path}: {column} differs from {expected!r}: {sorted(values)}")


def read_year(path: Path, expected_year: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if set(payload) != {"data"} or not isinstance(payload["data"], list) or not payload["data"]:
        raise ValueError(f"{path}: expected one nonempty Quick Stats data array")
    frame = pd.DataFrame(payload["data"])
    required = {
        *EXPECTED,
        "prodn_practice_desc", "unit_desc", "year", "state_ansi", "county_ansi",
        "state_alpha", "state_name", "county_name", "Value", "short_desc",
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"{path}: missing fields {sorted(missing)}")
    for column, expected in EXPECTED.items():
        _one_value(frame, column, expected, path)
    years = pd.to_numeric(frame.year, errors="raise").astype(int)
    if set(years) != {expected_year}:
        raise ValueError(f"{path}: expected only {expected_year}, got {sorted(set(years))}")
    frame = frame.loc[frame.unit_desc.astype(str).str.strip().eq("ACRES")].copy()
    practices = set(frame.prodn_practice_desc.astype(str).str.strip())
    if practices != set(PRACTICES):
        raise ValueError(f"{path}: acreage practices differ from {PRACTICES}: {sorted(practices)}")
    state = frame.state_ansi.astype("string").str.strip()
    county = frame.county_ansi.astype("string").str.strip()
    real = state.str.fullmatch(r"\d{2}", na=False) & county.str.fullmatch(r"\d{3}", na=False)
    frame = frame.loc[real].copy()
    frame["county_geoid"] = state.loc[real] + county.loc[real]
    frame["practice"] = frame.prodn_practice_desc.astype(str).str.strip()
    raw = frame.Value.astype("string").str.strip()
    frame["acres"] = pd.to_numeric(raw.str.replace(",", "", regex=False), errors="coerce")
    if (frame.acres.dropna() < 0).any():
        raise ValueError(f"{path}: negative acreage")
    keys = ["county_geoid", "practice"]
    if frame.duplicated(keys).any():
        examples = frame.loc[frame.duplicated(keys, keep=False), keys].head().to_dict("records")
        raise ValueError(f"{path}: duplicate county/practice acreage rows: {examples}")
    metadata = frame.sort_values(keys).drop_duplicates("county_geoid")[
        ["county_geoid", "state_alpha", "state_name", "county_name"]
    ]
    wide = frame.pivot(index="county_geoid", columns="practice", values="acres").reset_index()
    wide = wide.merge(metadata, on="county_geoid", how="left", validate="one_to_one")
    wide = wide.rename(columns={
        "ALL PRODUCTION PRACTICES": "total_harvested_cropland_acres",
        "IRRIGATED": "irrigated_harvested_cropland_acres",
    })
    both = (
        wide.total_harvested_cropland_acres.notna()
        & wide.irrigated_harvested_cropland_acres.notna()
    )
    positive_total = wide.total_harvested_cropland_acres.fillna(0).gt(0)
    eligible = both & positive_total
    wide["share"] = np.nan
    wide.loc[eligible, "share"] = (
        wide.loc[eligible, "irrigated_harvested_cropland_acres"]
        / wide.loc[eligible, "total_harvested_cropland_acres"]
    )
    if not wide.loc[eligible, "share"].between(0, 1.000001).all():
        raise ValueError(f"{path}: eligible irrigation share outside [0,1]")
    wide.loc[eligible, "share"] = wide.loc[eligible, "share"].clip(0, 1)
    wide["share_eligible"] = eligible
    wide["missing_reason"] = ""
    wide.loc[wide.total_harvested_cropland_acres.isna(), "missing_reason"] = (
        "missing_or_suppressed_total_harvested_cropland"
    )
    wide.loc[
        wide.total_harvested_cropland_acres.notna() & ~positive_total, "missing_reason"
    ] = "nonpositive_total_harvested_cropland"
    wide.loc[
        positive_total & wide.irrigated_harvested_cropland_acres.isna(), "missing_reason"
    ] = "missing_or_suppressed_irrigated_harvested_cropland_not_zero"
    audit = {
        "year": expected_year,
        "raw_rows": int(len(payload["data"])),
        "real_county_acreage_rows": int(len(frame)),
        "counties": int(wide.county_geoid.nunique()),
        "eligible_counties": int(eligible.sum()),
        "eligible_states": int(wide.loc[eligible, "state_alpha"].nunique()),
        "total_reported_but_irrigated_missing": int(
            (positive_total & wide.irrigated_harvested_cropland_acres.isna()).sum()
        ),
    }
    return wide, audit


def prepare(
    paths: dict[int, Path], source_manifest: Path | None = None
) -> tuple[pd.DataFrame, dict[str, Any]]:
    yearly: dict[int, pd.DataFrame] = {}
    year_audits = []
    for year in YEARS:
        yearly[year], audit = read_year(paths[year], year)
        audit["path"] = str(paths[year])
        audit["sha256"] = sha256(paths[year])
        year_audits.append(audit)

    combined: pd.DataFrame | None = None
    for year in YEARS:
        part = yearly[year][
            ["county_geoid", "state_alpha", "state_name", "county_name", "share", "share_eligible"]
        ].copy()
        part = part.rename(columns={
            "state_alpha": f"state_alpha_{year}",
            "state_name": f"state_name_{year}",
            "county_name": f"county_name_{year}",
            "share": f"irrigation_share_{year}",
            "share_eligible": f"share_eligible_{year}",
        })
        combined = part if combined is None else combined.merge(
            part, on="county_geoid", how="outer", validate="one_to_one"
        )
    if combined is None or combined.empty:
        raise ValueError("no Census classifier rows")
    state_columns = [f"state_alpha_{year}" for year in YEARS]
    state_counts = combined[state_columns].nunique(axis=1, dropna=True)
    if state_counts.gt(1).any():
        raise ValueError("county GEOID maps to conflicting states across Census vintages")
    combined["state"] = combined[state_columns].bfill(axis=1).iloc[:, 0]
    name_columns = [f"county_name_{year}" for year in YEARS]
    combined["county_name"] = combined[name_columns].bfill(axis=1).iloc[:, 0]
    share_columns = [f"irrigation_share_{year}" for year in YEARS]
    eligible_columns = [f"share_eligible_{year}" for year in YEARS]
    combined[eligible_columns] = combined[eligible_columns].fillna(False).astype(bool)
    combined["eligible_vintage_count"] = combined[eligible_columns].sum(axis=1).astype(int)
    combined["eligible_vintages"] = combined.apply(
        lambda row: ",".join(
            str(year) for year in YEARS if bool(row[f"share_eligible_{year}"])
        ),
        axis=1,
    )
    combined["maximum_irrigation_share"] = combined[share_columns].max(axis=1, skipna=True)
    combined["classifier_eligible"] = combined.eligible_vintage_count.gt(0)
    if combined.loc[combined.classifier_eligible, "maximum_irrigation_share"].isna().any():
        raise ValueError("eligible classifier row lacks a maximum share")
    if combined.loc[~combined.classifier_eligible, "maximum_irrigation_share"].notna().any():
        raise ValueError("ineligible classifier row carries a maximum share")
    combined["irrigation_class"] = "missing"
    combined.loc[
        combined.classifier_eligible & combined.maximum_irrigation_share.gt(0.15),
        "irrigation_class",
    ] = "irrigated"
    combined.loc[
        combined.classifier_eligible & combined.maximum_irrigation_share.le(0.15),
        "irrigation_class",
    ] = "dryland"
    combined["threshold_share"] = 0.15
    combined["published_rule"] = "maximum_available_1997_2002_2007_2012_share"
    columns = [
        "county_geoid", "state", "county_name", *share_columns, *eligible_columns,
        "eligible_vintage_count", "eligible_vintages", "maximum_irrigation_share",
        "classifier_eligible", "irrigation_class", "threshold_share", "published_rule",
    ]
    output = combined[columns].sort_values("county_geoid").reset_index(drop=True)
    eligible = output.loc[output.classifier_eligible]
    audit = {
        "schema": "nass_kuwayama_all_cropland_irrigation_classifier_v1",
        "source_rule": (
            "maximum across available 1997/2002/2007/2012 all-cropland irrigated "
            "harvested-area shares; missing/suppressed numerator never zero"
        ),
        "threshold_rule": "irrigated if maximum share > 0.15; dryland otherwise",
        "exact_equality_count": int(eligible.maximum_irrigation_share.eq(0.15).sum()),
        "year_audits": year_audits,
        "output_rows": int(len(output)),
        "eligible_counties": int(len(eligible)),
        "irrigated_counties": int(eligible.irrigation_class.eq("irrigated").sum()),
        "dryland_counties": int(eligible.irrigation_class.eq("dryland").sum()),
        "eligible_vintage_count_distribution": {
            str(int(key)): int(value)
            for key, value in eligible.eligible_vintage_count.value_counts().sort_index().items()
        },
        "maximum_share_summary": {
            "mean": float(eligible.maximum_irrigation_share.mean()),
            "median": float(eligible.maximum_irrigation_share.median()),
            "minimum": float(eligible.maximum_irrigation_share.min()),
            "maximum": float(eligible.maximum_irrigation_share.max()),
        },
        "role": "historical_support_classifier_only_not_irrigation_effect_damage_or_scc",
    }
    if source_manifest is not None:
        audit["source_manifest"] = {
            "file": source_manifest.name,
            "sha256": sha256(source_manifest),
        }
        audit["source_receipts"] = source_receipts(source_manifest, paths)
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    for year in YEARS:
        parser.add_argument(f"--input-{year}", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path)
    arguments = parser.parse_args()
    paths = {year: getattr(arguments, f"input_{year}") for year in YEARS}
    source_manifest = arguments.source_manifest
    if source_manifest is None:
        candidate = next(iter(paths.values())).parent / "MANIFEST.jsonl"
        source_manifest = candidate if candidate.is_file() else None
    output, audit = prepare(paths, source_manifest)
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(arguments.out, index=False)
    audit["output"] = {
        "path": str(arguments.out), "sha256": sha256(arguments.out), "rows": len(output)
    }
    arguments.audit_out.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {len(output)} counties; eligible={audit['eligible_counties']}; "
        f"irrigated={audit['irrigated_counties']}; dryland={audit['dryland_counties']}"
    )


if __name__ == "__main__":
    main()
