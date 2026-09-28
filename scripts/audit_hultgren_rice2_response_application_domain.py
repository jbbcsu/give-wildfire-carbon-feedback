#!/usr/bin/env python3
"""Audit fail-closed mapping of Rice2 weather cells to the author rice domain."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
import resource
import sys
import tomllib
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
from shapely import box
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_hultgren_impact_region_grid_crosswalk import ROBINSON, build_regions

MODERATORS = ["ln_gdppc", "irrigated_share", "lr_tmax_crop", "lr_prcp_crop"]
WEATHER = [
    "gdd", "kdd", "tmin",
    "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3",
    "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3",
]
GROUPS = ["uid", "adm0_year", "adm1_fact"]
AREA_CRS = CRS.from_epsg(6933)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def normalized(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def names(name: object, alternatives: object) -> set[str]:
    values = {normalized(name)}
    if pd.notna(alternatives):
        values.update(normalized(value) for value in str(alternatives).split("|") if value)
    return values - {"", "nan"}


def load_config(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    require(config["schema_version"] == 1, "config schema changed")
    require(config["contract_id"] == "hultgren_rice2_response_application_domain_v1", "contract id changed")
    for record in config["sources"].values():
        source = resolve(record["path"])
        require(source.is_file(), f"missing source: {source}")
        require(digest(source) == record["sha256"], f"source hash differs: {source}")
    gates = config["claim_gates"]
    require(gates["application_domain_audit_authorized"] is True, "audit gate closed")
    for key, value in gates.items():
        if key != "application_domain_audit_authorized":
            require(value is False, f"claim gate opened: {key}")
    return config, hashlib.sha256(raw).hexdigest()


def estimation_sample(panel_path: Path, chunk_rows: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    columns = [
        "iso", "adm1", "adm2", "uid", "season", "year",
        "median_plant_month", "median_harvest_month", "season_length",
        "ln_yield", *GROUPS[1:], *MODERATORS, *WEATHER,
    ]
    pieces = []
    source_rows = 0
    with pd.read_stata(panel_path, columns=columns, convert_categoricals=False, iterator=True) as reader:
        while True:
            try:
                chunk = reader.read(chunk_rows)
            except StopIteration:
                break
            if chunk.empty:
                break
            source_rows += len(chunk)
            pieces.append(chunk.dropna(subset=["ln_yield", *GROUPS, *MODERATORS, *WEATHER]))
    frame = pd.concat(pieces, ignore_index=True)
    complete_rows = len(frame)
    removed = []
    while True:
        singleton = np.zeros(len(frame), dtype=bool)
        for column in GROUPS:
            singleton |= frame[column].map(frame[column].value_counts()).eq(1).to_numpy()
        dropped = int(singleton.sum())
        removed.append(dropped)
        if dropped == 0:
            break
        frame = frame.loc[~singleton].copy()
    require(source_rows == 178157, "author panel row count differs")
    require(complete_rows == 166354 and len(frame) == 166174, "published sample count not reproduced")
    require(frame.adm0_year.nunique() == 656 and frame.adm1_fact.nunique() == 581, "published clusters not reproduced")
    variation = frame.groupby("uid")[MODERATORS + ["iso", "adm1", "adm2", "season"]].nunique(dropna=False).max()
    require((variation == 1).all(), f"UID identity or moderators vary: {variation[variation != 1].to_dict()}")
    records = []
    for uid, group in frame.groupby("uid", sort=True):
        calendars = sorted({
            (int(row.median_plant_month), int(row.median_harvest_month), int(row.season_length))
            for row in group[["median_plant_month", "median_harvest_month", "season_length"]].dropna().itertuples(index=False)
        })
        first = group.iloc[0]
        records.append({
            "uid": int(uid), "iso": str(first.iso), "adm1": str(first.adm1), "adm2": str(first.adm2),
            "season": str(first.season), "calendar_tuples": calendars,
            **{column: float(first[column]) for column in MODERATORS},
        })
    uid = pd.DataFrame(records)
    audit = {
        "source_rows": source_rows, "complete_case_rows": complete_rows,
        "estimation_rows": len(frame), "uids": len(uid),
        "countries": int(frame.iso.nunique()), "year_minimum": int(frame.year.min()),
        "year_maximum": int(frame.year.max()), "singleton_iterations": removed,
        "season_rows": {str(key): int(value) for key, value in frame.season.value_counts().items()},
        "season_uids": {str(key): int(value) for key, value in uid.season.value_counts().items()},
        "moderators_constant_within_uid": True,
    }
    return uid, audit


def exact_region_links(uid: pd.DataFrame, hierarchy_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    hierarchy = pd.read_csv(hierarchy_path, comment="#", dtype={"region-key": str, "parent-key": str})
    hierarchy["iso"] = hierarchy["region-key"].str.split(".").str[0]
    node_lookup: dict[tuple[str, str], list[str]] = {}
    for _, row in hierarchy.iterrows():
        for label in names(row["name"], row["alternatives"]):
            node_lookup.setdefault((row["iso"], label), []).append(row["region-key"])
    parent = hierarchy[["region-key", "name", "alternatives"]].rename(
        columns={"region-key": "parent-key", "name": "parent_name", "alternatives": "parent_alternatives"}
    )
    terminal = hierarchy[hierarchy.is_terminal.eq(True)].merge(parent, on="parent-key", how="left", validate="many_to_one")
    terminal = terminal.rename(columns={"region-key": "region_key"})
    terminal["iso"] = terminal.region_key.str.split(".").str[0]
    lookup: dict[tuple[str, str, str], list[str]] = {}
    for row in terminal.itertuples(index=False):
        for adm1_name in names(row.parent_name, row.parent_alternatives):
            for adm2_name in names(row.name, row.alternatives):
                lookup.setdefault((row.iso, adm1_name, adm2_name), []).append(row.region_key)
    records = []
    for row in uid.itertuples(index=False):
        candidates = sorted(set(lookup.get((row.iso, normalized(row.adm1), normalized(row.adm2)), [])))
        records.append({"uid": row.uid, "candidate_count": len(candidates), "region_keys": candidates})
    links = uid.merge(pd.DataFrame(records), on="uid", validate="one_to_one")
    counts = Counter(links.candidate_count.tolist())
    by_season = {}
    for season, group in links.groupby("season", sort=True):
        by_season[str(season)] = {
            "uids": len(group), "unique_region_uids": int(group.candidate_count.eq(1).sum()),
            "unmatched_uids": int(group.candidate_count.eq(0).sum()),
            "ambiguous_uids": int(group.candidate_count.gt(1).sum()),
        }
    second_node_counts: Counter[int] = Counter()
    second_node_country: dict[str, Counter[int]] = defaultdict(Counter)
    for row in links.loc[links.season.eq("second")].itertuples(index=False):
        count = len(set(node_lookup.get((row.iso, normalized(row.adm1)), [])))
        second_node_counts[count] += 1
        second_node_country[row.iso][count] += 1
    return links, {
        "terminal_regions": len(terminal),
        "candidate_count_distribution": {str(key): int(value) for key, value in sorted(counts.items())},
        "unique_region_uids": int(links.candidate_count.eq(1).sum()),
        "by_season": by_season,
        "second_season_any_hierarchy_node_diagnostic": {
            "interpretation": "Exact author ADM1 name/alternative match to any hierarchy node; descendant-terminal expansion and calendar concordance have not been performed.",
            "candidate_count_distribution": {str(key): int(value) for key, value in sorted(second_node_counts.items())},
            "by_country": {
                iso: {str(key): int(value) for key, value in sorted(counts.items())}
                for iso, counts in sorted(second_node_country.items())
            },
        },
    }


def rice2_support(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path, filters=[[('harvest_year', '==', 1982)]])
    require(len(frame) == 6197, "Rice2 strict support changed")
    require(not frame.duplicated(["native_lat_index", "native_lon_index"]).any(), "duplicate Rice2 cell")
    return frame[[
        "native_lat_index", "native_lon_index", "latitude", "longitude",
        "plant_month", "harvest_month", "season_months",
    ]].sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)


def spatial_audit(
    support: pd.DataFrame, links: pd.DataFrame, points_path: Path,
) -> dict[str, Any]:
    reverse: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in links.loc[links.candidate_count.eq(1)].itertuples(index=False):
        reverse[row.region_keys[0]].append({
            "uid": int(row.uid), "season": row.season, "calendar_tuples": row.calendar_tuples,
        })
    ids, geometries, geometry_audit = build_regions(points_path)
    region_transformer = Transformer.from_crs(ROBINSON, AREA_CRS, always_xy=True)
    cell_transformer = Transformer.from_crs(4326, AREA_CRS, always_xy=True)
    geometries = [transform(region_transformer.transform, geometry) for geometry in geometries]
    tree = STRtree(geometries)
    counters: Counter[str] = Counter()
    examples = []
    candidate_uid_frequency: Counter[int] = Counter()
    for row in support.itertuples(index=False):
        north = 90.0 - int(row.native_lat_index) * 0.5
        south = north - 0.5
        west = -180.0 + int(row.native_lon_index) * 0.5
        east = west + 0.5
        cell = transform(cell_transformer.transform, box(west, south, east, north))
        intersections = []
        for index in tree.query(cell):
            area = float(cell.intersection(geometries[int(index)]).area)
            if area > 0:
                intersections.append((ids[int(index)], area / cell.area))
        if intersections:
            counters["any_author_region_intersection"] += 1
        single_full = len(intersections) == 1 and intersections[0][1] >= 1.0 - 1e-6
        if single_full:
            counters["single_full_author_region"] += 1
        candidates: dict[int, dict[str, Any]] = {}
        for region_key, _ in intersections:
            for candidate in reverse.get(region_key, []):
                candidates[candidate["uid"]] = candidate
        if candidates:
            counters["any_exact_name_linked_uid"] += 1
        if len(candidates) == 1:
            counters["one_distinct_exact_name_linked_uid"] += 1
            candidate_uid_frequency[next(iter(candidates))] += 1
        strict_geography = single_full and len(candidates) == 1
        if strict_geography:
            counters["single_full_region_one_exact_uid"] += 1
            candidate = next(iter(candidates.values()))
            if candidate["season"] == "second":
                counters["second_label_after_strict_geography"] += 1
                calendar = (int(row.plant_month), int(row.harvest_month), int(row.season_months))
                if calendar in candidate["calendar_tuples"]:
                    counters["second_label_and_exact_calendar_after_strict_geography"] += 1
            if candidate["season"] == "total":
                counters["total_label_after_strict_geography"] += 1
        if len(examples) < 20 and (strict_geography or len(candidates) > 0):
            examples.append({
                "native_lat_index": int(row.native_lat_index), "native_lon_index": int(row.native_lon_index),
                "plant_month": int(row.plant_month), "harvest_month": int(row.harvest_month),
                "season_months": int(row.season_months), "intersected_regions": len(intersections),
                "single_full_region": single_full, "exact_uid_candidates": sorted(candidates),
                "candidate_seasons": sorted({value["season"] for value in candidates.values()}),
            })
    keys = [
        "any_author_region_intersection", "single_full_author_region", "any_exact_name_linked_uid",
        "one_distinct_exact_name_linked_uid", "single_full_region_one_exact_uid",
        "second_label_after_strict_geography", "second_label_and_exact_calendar_after_strict_geography",
        "total_label_after_strict_geography",
    ]
    counts = {key: int(counters[key]) for key in keys}
    return {
        "strict_support_cells": len(support), "geometry": geometry_audit,
        "cell_counts": counts,
        "cell_fractions": {key: value / len(support) for key, value in counts.items()},
        "cell_year_counts_1982_2019": {key: value * 38 for key, value in counts.items()},
        "distinct_exact_uid_candidates_reached": len(candidate_uid_frequency),
        "examples": examples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunk-rows", type=int, default=20000)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    config, config_hash = load_config(args.config)
    sources = config["sources"]
    uid, sample_audit = estimation_sample(resolve(sources["author_panel"]["path"]), args.chunk_rows)
    links, link_audit = exact_region_links(uid, resolve(sources["author_hierarchy"]["path"]))
    del uid
    gc.collect()
    support = rice2_support(resolve(sources["rice2_basis"]["path"]))
    spatial = spatial_audit(support, links, resolve(sources["author_region_points"]["path"]))
    maximum_rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(maximum_rss < cap, "audit exceeded 512 MiB RSS cap")
    result = {
        "schema": "hultgren_rice2_response_application_domain_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "audited_fail_closed_rice2_response_application_domain_not_response_evaluation",
        "contract": {"path": str(args.config), "sha256": config_hash},
        "author_estimation_sample": sample_audit,
        "exact_name_crosswalk": link_audit,
        "rice2_spatial_coverage": spatial,
        "moderator_inventory": {
            "ln_gdppc": {"author_value_available_by_exact_uid": True, "grid_mapping_complete": False, "substitute_authorized": False},
            "irrigated_share": {"author_value_available_by_exact_uid": True, "grid_mapping_complete": False, "substitute_authorized": False},
            "lr_tmax_crop": {"author_value_available_by_exact_uid": True, "grid_mapping_complete": False, "substitute_authorized": False},
            "lr_prcp_crop": {"author_value_available_by_exact_uid": True, "weather_specific_caps": {"gdd": 200, "kdd": 300, "prcp": 250, "tmin": 175}, "grid_mapping_complete": False, "substitute_authorized": False},
            "season": {"author_labels": sample_audit["season_uids"], "ggcmi_ri2_to_author_second_crosswalk_available": False, "label_equality_claimed": False},
            "fixed_effects": {
                "published_structure": "UID FE; ADM1-specific linear and quadratic time trends; country-year FE; two-way clustering by ADM1 and country-year",
                "needed_for_weather_contrast_at_fixed_moderators": False,
                "authorized_for_transported_level_prediction_or_refit": False,
            },
        },
        "temporal_scope": {
            "author_panel_years": [sample_audit["year_minimum"], sample_audit["year_maximum"]],
            "rice2_weather_years": [1982, 2019], "overlap_years": [1982, sample_audit["year_maximum"]],
            "overlap_year_count": sample_audit["year_maximum"] - 1982 + 1,
            "outside_author_panel_year_count": 2019 - sample_audit["year_maximum"],
            "rows_per_branch_in_overlap": 6197 * (sample_audit["year_maximum"] - 1982 + 1),
            "rows_per_branch_outside_author_panel_years": 6197 * (2019 - sample_audit["year_maximum"]),
        },
        "fail_closed_protocol": {
            "authorized_application_rows": 0,
            "reason": "No pinned author crosswalk maps GGCMI Rice2 season cells to the prepared panel's season-specific UIDs; exact label/calendar concordance is diagnostic, not proof of source identity.",
            "required_before_response_evaluation": [
                "author-supplied or source-reconstructed grid-to-UID membership for the prepared rice panel",
                "authoritative mapping of GGCMI ri2 season identity to the panel's total/first/second/third reporting series",
                "verbatim attachment of all four author moderators from one unambiguous estimation-sample UID",
                "preserve pooled coefficients and evaluate weather contrasts only; do not reconstruct fixed-effect levels or refit",
                "report author-domain bounds separately; never trim, winsorize, or impute without a new protocol",
            ],
        },
        "claim_gates": {
            "application_domain_inventory_validated": True,
            "source_faithful_rice2_uid_mapping_validated": False,
            "published_response_evaluation_authorized": False,
            "mirca_weight_attachment_authorized": False,
            "yield_effects_authorized": False,
            "damages_authorized": False, "scc_authorized": False, "give_integration_authorized": False,
        },
        "resources": {"peak_rss_bytes": maximum_rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "author_estimation_sample": sample_audit,
        "exact_name_crosswalk": link_audit, "rice2_spatial_coverage": spatial["cell_counts"],
        "authorized_application_rows": 0, "resources": result["resources"],
    }, indent=2))


if __name__ == "__main__":
    main()
