#!/usr/bin/env python3
"""Build the fail-closed LKA/VNM Rice2-to-author second-season crosswalk."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import sys
import tomllib
import unicodedata
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
from shapely import Polygon, box, make_valid, union_all
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
ROBINSON = CRS.from_proj4("+proj=robin +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
AREA_CRS = CRS.from_epsg(6933)
MODERATORS = ["ln_gdppc", "irrigated_share", "lr_tmax_crop", "lr_prcp_crop"]
WEATHER = ["gdd", "kdd", "tmin", "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3", "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3"]
GROUPS = ["uid", "adm0_year", "adm1_fact"]
COUNTRIES = ("LKA", "VNM")


def require(value: bool, message: str) -> None:
    if not value:
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


def variants(name: object, alternatives: object) -> set[str]:
    values = {normalized(name)}
    if pd.notna(alternatives):
        values.update(normalized(value) for value in str(alternatives).split("|") if value)
    return values - {"", "nan"}


def load_config(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    require(config["schema_version"] == 1, "config schema changed")
    require(config["contract_id"] == "hultgren_rice2_second_season_parent_crosswalk_v1", "contract id changed")
    for record in config["sources"].values():
        source = resolve(record["path"])
        require(source.is_file(), f"missing source: {source}")
        require(digest(source) == record["sha256"], f"source hash differs: {source}")
    gates = config["claim_gates"]
    require(gates["crosswalk_build_authorized"] is True, "crosswalk build not authorized")
    for key, value in gates.items():
        if key != "crosswalk_build_authorized":
            require(value is False, f"claim gate opened: {key}")
    return config, hashlib.sha256(raw).hexdigest()


def estimation_second_uids(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    columns = [
        "iso", "adm1", "adm2", "uid", "season", "median_plant_month", "median_harvest_month",
        "season_length", "ln_yield", *GROUPS[1:], *MODERATORS, *WEATHER,
    ]
    parts = []
    with pd.read_stata(path, columns=columns, convert_categoricals=False, iterator=True) as reader:
        while True:
            try:
                chunk = reader.read(20000)
            except StopIteration:
                break
            if chunk.empty:
                break
            parts.append(chunk.dropna(subset=["ln_yield", *GROUPS, *MODERATORS, *WEATHER]))
    frame = pd.concat(parts, ignore_index=True)
    require(len(frame) == 166354, "complete-case rows differ")
    while True:
        singleton = np.logical_or.reduce([frame[column].map(frame[column].value_counts()).eq(1).to_numpy() for column in GROUPS])
        if not singleton.any():
            break
        frame = frame.loc[~singleton].copy()
    require(len(frame) == 166174, "estimation rows differ")
    second = frame.loc[frame.season.eq("second") & frame.iso.isin(COUNTRIES)].copy()
    records = []
    for uid, group in second.groupby("uid", sort=True):
        require(group.iso.nunique() == group.adm1.nunique() == 1, f"UID identity varies: {uid}")
        calendars = sorted({
            (int(row.median_plant_month), int(row.median_harvest_month), int(row.season_length))
            for row in group[["median_plant_month", "median_harvest_month", "season_length"]].dropna().itertuples(index=False)
        })
        records.append({
            "uid": int(uid), "iso": str(group.iso.iloc[0]), "adm1": str(group.adm1.iloc[0]),
            "author_calendar_tuples": calendars,
        })
    result = pd.DataFrame(records)
    require(len(result) == 56, "second-season UID count differs")
    require(result.groupby("iso").size().to_dict() == {"LKA": 25, "VNM": 31}, "country UID counts differ")
    return result, {
        "estimation_rows": len(frame), "second_season_rows": len(second), "second_season_uids": len(result),
        "second_season_uids_by_country": {key: int(value) for key, value in result.groupby("iso").size().items()},
        "uids_without_finite_author_calendar": int(result.author_calendar_tuples.map(len).eq(0).sum()),
    }


def hierarchy_mapping(uids: pd.DataFrame, path: Path) -> tuple[pd.DataFrame, dict[int, set[str]], dict[str, Any]]:
    hierarchy = pd.read_csv(path, comment="#", dtype={"region-key": str, "parent-key": str})
    hierarchy["iso"] = hierarchy["region-key"].str.split(".").str[0]
    node_lookup: dict[tuple[str, str], set[str]] = defaultdict(set)
    for _, row in hierarchy.iterrows():
        for label in variants(row["name"], row["alternatives"]):
            node_lookup[(row["iso"], label)].add(row["region-key"])
    records = []
    for row in uids.itertuples(index=False):
        candidates = sorted(node_lookup.get((row.iso, normalized(row.adm1)), set()))
        records.append({"uid": row.uid, "parent_candidate_count": len(candidates), "parent_node": candidates[0] if len(candidates) == 1 else None})
    mapped = uids.merge(pd.DataFrame(records), on="uid", validate="one_to_one")
    require(mapped.parent_candidate_count.value_counts().to_dict() == {1: 43, 0: 10, 2: 3}, "parent match counts differ")

    children: dict[str, list[str]] = defaultdict(list)
    terminal = set(hierarchy.loc[hierarchy.is_terminal.eq(True), "region-key"])
    for _, row in hierarchy.loc[hierarchy["parent-key"].notna()].iterrows():
        children[row["parent-key"]].append(row["region-key"])
    descendants: dict[int, set[str]] = {}
    for row in mapped.loc[mapped.parent_candidate_count.eq(1)].itertuples(index=False):
        found: set[str] = set()
        queue = deque([row.parent_node])
        visited: set[str] = set()
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            if node in terminal:
                found.add(node)
            else:
                queue.extend(children.get(node, []))
        require(found, f"unique parent has no terminal descendants: {row.parent_node}")
        descendants[int(row.uid)] = found
    owners: dict[str, set[int]] = defaultdict(set)
    for uid, keys in descendants.items():
        for key in keys:
            owners[key].add(uid)
    overlaps = {key: sorted(value) for key, value in owners.items() if len(value) > 1}
    require(not overlaps, f"terminal descendants assigned to multiple UIDs: {overlaps}")
    mapped_counts = mapped.loc[mapped.parent_candidate_count.eq(1)].groupby("iso").size().to_dict()
    author_calendar_distributions = {}
    for iso in COUNTRIES:
        counts: Counter[str] = Counter()
        country = mapped.loc[mapped.iso.eq(iso) & mapped.parent_candidate_count.eq(1)]
        for calendars in country.author_calendar_tuples:
            if not calendars:
                counts["missing"] += 1
            for plant, harvest, length in calendars:
                counts[f"{plant}-{harvest}-{length}"] += 1
        author_calendar_distributions[iso] = dict(sorted(counts.items()))
    return mapped, descendants, {
        "parent_candidate_count_distribution": {str(key): int(value) for key, value in sorted(Counter(mapped.parent_candidate_count).items())},
        "unique_parent_uids_by_country": {key: int(value) for key, value in mapped_counts.items()},
        "terminal_descendants": sum(len(value) for value in descendants.values()),
        "terminal_descendants_by_country": {
            iso: sum(len(descendants[int(uid)]) for uid in mapped.loc[mapped.iso.eq(iso) & mapped.parent_candidate_count.eq(1), "uid"])
            for iso in COUNTRIES
        },
        "unique_parent_uid_author_calendar_tuples_by_country": author_calendar_distributions,
        "terminal_descendant_uid_overlap_count": len(overlaps),
    }


def polygonal_valid(geometry: object) -> object:
    candidate = geometry if geometry.is_valid else make_valid(geometry)
    if candidate.geom_type in ("Polygon", "MultiPolygon"):
        return candidate
    return union_all([part for part in candidate.geoms if part.geom_type in ("Polygon", "MultiPolygon")])


def country_terminal_geometries(points_path: Path) -> tuple[list[str], list[object], dict[str, Any]]:
    points = pd.read_csv(points_path, usecols=["long", "lat", "order", "hole", "id", "group"])
    points = points.loc[points.id.astype(str).str.startswith(("LKA.", "VNM."))].copy()
    rings: dict[str, dict[str, list[object]]] = {}
    repaired = 0
    for group, frame in points.groupby("group", sort=False):
        require(frame.id.nunique() == 1 and frame.hole.nunique() == 1, f"mixed ring: {group}")
        ring = Polygon(frame.sort_values("order")[["long", "lat"]].to_numpy(dtype=float))
        if not ring.is_valid:
            repaired += 1
            ring = polygonal_valid(ring)
        entry = rings.setdefault(str(frame.id.iloc[0]), {"outer": [], "holes": []})
        entry["holes" if bool(frame.hole.iloc[0]) else "outer"].append(ring)
    ids = []
    geometries = []
    transformer = Transformer.from_crs(ROBINSON, AREA_CRS, always_xy=True)
    for key, parts in rings.items():
        require(parts["outer"], f"region lacks outer ring: {key}")
        geometry = union_all(parts["outer"])
        if parts["holes"]:
            geometry = geometry.difference(union_all(parts["holes"]))
        if not geometry.is_valid:
            repaired += 1
            geometry = polygonal_valid(geometry)
        ids.append(key)
        geometries.append(transform(transformer.transform, geometry))
    return ids, geometries, {"point_rows": len(points), "regions": len(ids), "repairs": repaired}


def strict_support(noirr_path: Path, firr_path: Path) -> pd.DataFrame:
    columns = ["native_lat_index", "native_lon_index", "latitude", "longitude", "plant_month", "harvest_month", "season_months"]
    left = pd.read_parquet(noirr_path, filters=[[('harvest_year', '==', 1982)]], columns=columns).sort_values(columns[:2]).reset_index(drop=True)
    right = pd.read_parquet(firr_path, filters=[[('harvest_year', '==', 1982)]], columns=columns).sort_values(columns[:2]).reset_index(drop=True)
    require(len(left) == len(right) == 6197 and left.equals(right), "Rice2 branch support/calendar differs")
    return left


def build_ledger(
    support: pd.DataFrame, mapped: pd.DataFrame, descendants: dict[int, set[str]],
    geometry_ids: list[str], geometries: list[object], tolerance: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    terminal_owner = {key: uid for uid, keys in descendants.items() for key in keys}
    uid_record = mapped.set_index("uid").to_dict(orient="index")
    tree = STRtree(geometries)
    cell_transformer = Transformer.from_crs(4326, AREA_CRS, always_xy=True)
    records = []
    for row in support.itertuples(index=False):
        north = float(row.latitude) + 0.25
        south = float(row.latitude) - 0.25
        west = float(row.longitude) - 0.25
        east = float(row.longitude) + 0.25
        cell = transform(cell_transformer.transform, box(west, south, east, north))
        intersections = []
        mapped_parts: dict[int, list[object]] = defaultdict(list)
        competing = 0
        for index in tree.query(cell):
            intersection = cell.intersection(geometries[int(index)])
            if intersection.is_empty or intersection.area <= 0:
                continue
            key = geometry_ids[int(index)]
            intersections.append(key)
            owner = terminal_owner.get(key)
            if owner is None:
                competing += 1
            else:
                mapped_parts[owner].append(intersection)
        candidate_uids = sorted(mapped_parts)
        exact_one = len(candidate_uids) == 1
        uid = candidate_uids[0] if exact_one else None
        union_fraction = 0.0
        if exact_one:
            union_fraction = float(union_all(mapped_parts[uid]).area / cell.area)
        full = bool(exact_one and competing == 0 and union_fraction >= 1.0 - tolerance)
        author = uid_record.get(uid, {}) if uid is not None else {}
        calendar = (int(row.plant_month), int(row.harvest_month), int(row.season_months))
        raw_calendar_match = bool(exact_one and calendar in author.get("author_calendar_tuples", []))
        calendar_match = bool(full and raw_calendar_match)
        records.append({
            "native_lat_index": int(row.native_lat_index), "native_lon_index": int(row.native_lon_index),
            "latitude": float(row.latitude), "longitude": float(row.longitude),
            "plant_month": int(row.plant_month), "harvest_month": int(row.harvest_month), "season_months": int(row.season_months),
            "intersected_lka_vnm_terminal_regions": len(intersections),
            "mapped_second_uid_candidates": len(candidate_uids), "competing_terminal_intersections": competing,
            "mapped_union_overlap_fraction": union_fraction, "exactly_one_second_uid": exact_one,
            "full_spatial_ownership": full, "author_uid": uid,
            "author_iso": author.get("iso"), "author_parent_node": author.get("parent_node"),
            "calendar_concordant_before_spatial_gate": raw_calendar_match,
            "author_calendar_match": calendar_match, "authorized": calendar_match,
        })
    ledger = pd.DataFrame(records)
    attrition = {}
    for iso in COUNTRIES:
        country_uids = set(mapped.loc[mapped.iso.eq(iso) & mapped.parent_candidate_count.eq(1), "uid"].astype(int))
        # Country attribution is intentionally possible only after one UID is identified.
        country = ledger.loc[ledger.author_uid.isin(country_uids)]
        calendar_counts = Counter(
            f"{int(row.plant_month)}-{int(row.harvest_month)}-{int(row.season_months)}"
            for row in country.itertuples(index=False)
        )
        attrition[iso] = {
            "second_season_uids": int(mapped.iso.eq(iso).sum()),
            "unique_parent_uids": len(country_uids),
            "cells_with_exactly_one_uid": int(len(country)),
            "cells_calendar_concordant_before_spatial_gate": int(country.calendar_concordant_before_spatial_gate.sum()),
            "cells_with_full_spatial_ownership": int(country.full_spatial_ownership.sum()),
            "cells_with_exact_author_calendar": int(country.author_calendar_match.sum()),
            "authorized_cells": int(country.authorized.sum()),
            "ggcmi_calendar_tuples_for_exactly_one_uid_cells": dict(sorted(calendar_counts.items())),
        }
    spatial_candidates = ledger.loc[ledger.exactly_one_second_uid & ledger.competing_terminal_intersections.eq(0), "mapped_union_overlap_fraction"]
    return ledger, {
        "strict_support_cells": len(ledger),
        "cells_intersecting_lka_vnm_terminal_regions": int(ledger.intersected_lka_vnm_terminal_regions.gt(0).sum()),
        "cells_with_any_mapped_second_uid": int(ledger.mapped_second_uid_candidates.gt(0).sum()),
        "cells_with_exactly_one_second_uid": int(ledger.exactly_one_second_uid.sum()),
        "cells_calendar_concordant_before_spatial_gate": int(ledger.calendar_concordant_before_spatial_gate.sum()),
        "cells_without_competing_terminal_intersection_after_one_uid": int((ledger.exactly_one_second_uid & ledger.competing_terminal_intersections.eq(0)).sum()),
        "mapped_union_overlap_fraction_for_one_uid_no_competitor": {
            "count": int(len(spatial_candidates)),
            "minimum": float(spatial_candidates.min()) if len(spatial_candidates) else None,
            "median": float(spatial_candidates.median()) if len(spatial_candidates) else None,
            "maximum": float(spatial_candidates.max()) if len(spatial_candidates) else None,
        },
        "cells_with_full_spatial_ownership": int(ledger.full_spatial_ownership.sum()),
        "cells_with_exact_author_calendar": int(ledger.author_calendar_match.sum()),
        "authorized_cells": int(ledger.authorized.sum()),
        "authorized_cell_years_per_branch_1982_2019": int(ledger.authorized.sum()) * 38,
        "by_country": attrition,
        "spatial_full_coverage_tolerance": tolerance,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    config, config_hash = load_config(args.config)
    sources = config["sources"]
    uids, sample_audit = estimation_second_uids(resolve(sources["author_panel"]["path"]))
    mapped, descendants, hierarchy_audit = hierarchy_mapping(uids, resolve(sources["author_hierarchy"]["path"]))
    ids, geometries, geometry_audit = country_terminal_geometries(resolve(sources["author_region_points"]["path"]))
    geometry_set = set(ids)
    missing_geometry = sorted({key for keys in descendants.values() for key in keys} - geometry_set)
    hierarchy_audit["terminal_descendants_without_geometry"] = len(missing_geometry)
    hierarchy_audit["terminal_descendants_without_geometry_examples"] = missing_geometry[:20]
    support = strict_support(resolve(sources["rice2_noirr_basis"]["path"]), resolve(sources["rice2_firr_basis"]["path"]))
    ledger, attrition = build_ledger(support, mapped, descendants, ids, geometries, float(config["spatial"]["full_coverage_tolerance"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output.with_suffix(args.output.suffix + ".partial")
    ledger.to_parquet(partial, index=False, compression="zstd")
    os.replace(partial, args.output)
    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, "builder exceeded 512 MiB RSS cap")
    authorized = int(attrition["authorized_cells"])
    result = {
        "schema": "hultgren_rice2_second_season_parent_crosswalk/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_fail_closed_second_season_parent_crosswalk_not_response_evaluation",
        "contract": {"path": str(args.config), "sha256": config_hash},
        "author_sample": sample_audit, "hierarchy": hierarchy_audit, "geometry": geometry_audit,
        "attrition": attrition,
        "output": {"path": str(args.output), "rows": len(ledger), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "authorized_subset": {
            "nonzero": authorized > 0, "cells_per_branch": authorized,
            "cell_years_per_branch_1982_2019": authorized * 38,
            "rule": "one uniquely matched second-season UID; all positive terminal intersections owned by that UID; mapped descendant union covers full cell within tolerance; exact author/GGCMI plant month, harvest month, and season length",
        },
        "claim_gates": {
            "second_season_crosswalk_audited": True,
            "response_evaluation_authorized": False, "mirca_weights_authorized": False,
            "yield_effects_authorized": False, "damages_authorized": False,
            "scc_authorized": False, "give_integration_authorized": False,
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "hierarchy": hierarchy_audit, "attrition": attrition, "authorized_subset": result["authorized_subset"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
