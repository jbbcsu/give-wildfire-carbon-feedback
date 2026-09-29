#!/usr/bin/env python3
"""Independently validate the strict LKA/VNM Rice2 parent crosswalk."""
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
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
from pyproj import CRS, Transformer
from shapely import Polygon, box, make_valid, union_all
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
ROBINSON = CRS.from_proj4("+proj=robin +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
AREA_CRS = CRS.from_epsg(6933)
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


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def labels(name: object, alternatives: object) -> set[str]:
    result = {norm(name)}
    if pd.notna(alternatives):
        result |= {norm(value) for value in str(alternatives).split("|")}
    return result - {"", "nan"}


def panel_mapping(panel_path: Path, hierarchy_path: Path) -> tuple[dict[str, int], dict[int, set[str]], dict[int, set[tuple[int, int, int]]], dict[int, str]]:
    columns = ["iso", "adm1", "uid", "season", "median_plant_month", "median_harvest_month", "season_length"]
    parts = []
    with pd.read_stata(panel_path, columns=columns, convert_categoricals=False, iterator=True) as reader:
        while True:
            try:
                chunk = reader.read(20000)
            except StopIteration:
                break
            if chunk.empty:
                break
            selected = chunk.loc[chunk.season.eq("second") & chunk.iso.isin(COUNTRIES)]
            if not selected.empty:
                parts.append(selected.copy())
    second = pd.concat(parts, ignore_index=True)
    uid_rows = second.drop_duplicates("uid")[["iso", "adm1", "uid"]]
    require(len(uid_rows) == 56 and uid_rows.groupby("iso").size().to_dict() == {"LKA": 25, "VNM": 31}, "second UID inventory differs")
    calendars: dict[int, set[tuple[int, int, int]]] = defaultdict(set)
    for row in second.dropna(subset=["median_plant_month", "median_harvest_month", "season_length"]).itertuples(index=False):
        calendars[int(row.uid)].add((int(row.median_plant_month), int(row.median_harvest_month), int(row.season_length)))
    uid_iso = {int(row.uid): str(row.iso) for row in uid_rows.itertuples(index=False)}

    hierarchy = pd.read_csv(hierarchy_path, comment="#", dtype={"region-key": str, "parent-key": str})
    hierarchy["iso"] = hierarchy["region-key"].str.split(".").str[0]
    lookup: dict[tuple[str, str], set[str]] = defaultdict(set)
    for _, row in hierarchy.iterrows():
        for label in labels(row["name"], row["alternatives"]):
            lookup[(row["iso"], label)].add(row["region-key"])
    parent_by_uid = {}
    counts = Counter()
    for row in uid_rows.itertuples(index=False):
        candidates = lookup.get((row.iso, norm(row.adm1)), set())
        counts[len(candidates)] += 1
        if len(candidates) == 1:
            parent_by_uid[int(row.uid)] = next(iter(candidates))
    require(dict(counts) == {1: 43, 0: 10, 2: 3}, "parent match counts differ")

    children: dict[str, list[str]] = defaultdict(list)
    terminal = set(hierarchy.loc[hierarchy.is_terminal.eq(True), "region-key"])
    for _, row in hierarchy.loc[hierarchy["parent-key"].notna()].iterrows():
        children[row["parent-key"]].append(row["region-key"])
    descendants = {}
    terminal_owner = {}
    for uid, parent in parent_by_uid.items():
        found = set()
        queue = deque([parent])
        visited = set()
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            if node in terminal:
                found.add(node)
            else:
                queue.extend(children.get(node, []))
        require(found, f"parent has no terminal descendants: {parent}")
        descendants[uid] = found
        for key in found:
            require(key not in terminal_owner, f"competing selected UID terminal: {key}")
            terminal_owner[key] = uid
    require(len(terminal_owner) == 147, "terminal descendant count differs")
    return terminal_owner, descendants, calendars, uid_iso


def valid_polygon(geometry: object) -> object:
    candidate = geometry if geometry.is_valid else make_valid(geometry)
    if candidate.geom_type in ("Polygon", "MultiPolygon"):
        return candidate
    return union_all([part for part in candidate.geoms if part.geom_type in ("Polygon", "MultiPolygon")])


def geometries(points_path: Path) -> tuple[list[str], list[object]]:
    points = pd.read_csv(points_path, usecols=["long", "lat", "order", "hole", "id", "group"])
    points = points.loc[points.id.astype(str).str.startswith(COUNTRIES)]
    rings: dict[str, dict[str, list[object]]] = {}
    for _, frame in points.groupby("group", sort=False):
        polygon = Polygon(frame.sort_values("order")[["long", "lat"]].to_numpy(dtype=float))
        if not polygon.is_valid:
            polygon = valid_polygon(polygon)
        entry = rings.setdefault(str(frame.id.iloc[0]), {"outer": [], "holes": []})
        entry["holes" if bool(frame.hole.iloc[0]) else "outer"].append(polygon)
    del points
    gc.collect()
    transformer = Transformer.from_crs(ROBINSON, AREA_CRS, always_xy=True)
    ids, result = [], []
    for key, parts in rings.items():
        geometry = union_all(parts["outer"])
        if parts["holes"]:
            geometry = geometry.difference(union_all(parts["holes"]))
        if not geometry.is_valid:
            geometry = valid_polygon(geometry)
        ids.append(key)
        result.append(transform(transformer.transform, geometry))
    del rings
    gc.collect()
    return ids, result


def independent_rows(
    support: pd.DataFrame, ids: list[str], shapes: list[object], terminal_owner: dict[str, int],
    calendars: dict[int, set[tuple[int, int, int]]], uid_iso: dict[int, str], tolerance: float,
) -> pd.DataFrame:
    tree = STRtree(shapes)
    transformer = Transformer.from_crs(4326, AREA_CRS, always_xy=True)
    rows = []
    for row in support.itertuples(index=False):
        cell = transform(transformer.transform, box(row.longitude - 0.25, row.latitude - 0.25, row.longitude + 0.25, row.latitude + 0.25))
        parts: dict[int, list[object]] = defaultdict(list)
        region_count = 0
        competitor = 0
        for index in tree.query(cell):
            intersection = cell.intersection(shapes[int(index)])
            if intersection.is_empty or intersection.area <= 0:
                continue
            region_count += 1
            uid = terminal_owner.get(ids[int(index)])
            if uid is None:
                competitor += 1
            else:
                parts[uid].append(intersection)
        candidates = sorted(parts)
        exact = len(candidates) == 1
        uid = candidates[0] if exact else None
        fraction = float(union_all(parts[uid]).area / cell.area) if exact else 0.0
        full = exact and competitor == 0 and fraction >= 1.0 - tolerance
        calendar = (int(row.plant_month), int(row.harvest_month), int(row.season_months))
        raw_match = exact and calendar in calendars.get(uid, set())
        rows.append({
            "native_lat_index": int(row.native_lat_index), "native_lon_index": int(row.native_lon_index),
            "intersected_lka_vnm_terminal_regions": region_count,
            "mapped_second_uid_candidates": len(candidates), "competing_terminal_intersections": competitor,
            "mapped_union_overlap_fraction": fraction, "exactly_one_second_uid": exact,
            "full_spatial_ownership": full, "author_uid": uid,
            "author_iso": uid_iso.get(uid), "calendar_concordant_before_spatial_gate": raw_match,
            "author_calendar_match": bool(full and raw_match), "authorized": bool(full and raw_match),
        })
    return pd.DataFrame(rows).sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    for record in config["sources"].values():
        require(digest(resolve(record["path"])) == record["sha256"], "source hash differs")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    crosswalk_path = resolve(receipt["output"]["path"])
    require(digest(crosswalk_path) == receipt["output"]["sha256"], "crosswalk hash differs")
    ledger = pd.read_parquet(crosswalk_path).sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
    columns = ["native_lat_index", "native_lon_index", "latitude", "longitude", "plant_month", "harvest_month", "season_months"]
    noirr = pd.read_parquet(resolve(config["sources"]["rice2_noirr_basis"]["path"]), filters=[[('harvest_year', '==', 1982)]], columns=columns).sort_values(columns[:2]).reset_index(drop=True)
    firr = pd.read_parquet(resolve(config["sources"]["rice2_firr_basis"]["path"]), filters=[[('harvest_year', '==', 1982)]], columns=columns).sort_values(columns[:2]).reset_index(drop=True)
    require(noirr.equals(firr) and len(noirr) == len(ledger) == 6197, "Rice2 support differs")
    del firr
    gc.collect()
    pa.default_memory_pool().release_unused()
    terminal_owner, descendants, calendars, uid_iso = panel_mapping(resolve(config["sources"]["author_panel"]["path"]), resolve(config["sources"]["author_hierarchy"]["path"]))
    gc.collect()
    pa.default_memory_pool().release_unused()
    ids, shapes = geometries(resolve(config["sources"]["author_region_points"]["path"]))
    require(not (set(terminal_owner) - set(ids)), "selected descendants lack geometry")
    rebuilt = independent_rows(noirr, ids, shapes, terminal_owner, calendars, uid_iso, float(config["spatial"]["full_coverage_tolerance"]))
    compare = [
        "intersected_lka_vnm_terminal_regions", "mapped_second_uid_candidates", "competing_terminal_intersections",
        "exactly_one_second_uid", "full_spatial_ownership", "author_uid", "author_iso",
        "calendar_concordant_before_spatial_gate", "author_calendar_match", "authorized",
    ]
    for column in compare:
        require(ledger[column].fillna("<missing>").equals(rebuilt[column].fillna("<missing>")), f"independent field differs: {column}")
    error = float(np.max(np.abs(ledger.mapped_union_overlap_fraction - rebuilt.mapped_union_overlap_fraction)))
    require(error <= 1e-12, "overlap fraction differs")
    checks = {
        "strict_support_cells": len(ledger), "selected_parent_uids": len(descendants),
        "terminal_descendants": len(terminal_owner),
        "cells_intersecting_lka_vnm_terminal_regions": int(rebuilt.intersected_lka_vnm_terminal_regions.gt(0).sum()),
        "cells_with_any_mapped_second_uid": int(rebuilt.mapped_second_uid_candidates.gt(0).sum()),
        "cells_with_exactly_one_second_uid": int(rebuilt.exactly_one_second_uid.sum()),
        "cells_calendar_concordant_before_spatial_gate": int(rebuilt.calendar_concordant_before_spatial_gate.sum()),
        "cells_without_competing_terminal_intersection_after_one_uid": int((rebuilt.exactly_one_second_uid & rebuilt.competing_terminal_intersections.eq(0)).sum()),
        "cells_with_full_spatial_ownership": int(rebuilt.full_spatial_ownership.sum()),
        "authorized_cells": int(rebuilt.authorized.sum()),
        "maximum_absolute_overlap_fraction_error": error,
    }
    expected = receipt["attrition"]
    for key, value in checks.items():
        if key in expected:
            require(value == expected[key], f"receipt count differs: {key}")
    require(checks["authorized_cells"] == 0 and not receipt["authorized_subset"]["nonzero"], "unauthorized subset opened")
    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"validator exceeded memory cap: {rss} >= {cap}")
    result = {
        "schema": "hultgren_rice2_second_season_parent_crosswalk_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_fail_closed_second_season_parent_crosswalk",
        "config": {"path": str(args.config), "sha256": digest(args.config)},
        "receipt": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "crosswalk": {"path": receipt["output"]["path"], "sha256": receipt["output"]["sha256"]},
        "checks": checks,
        "claim_gates": {"parent_crosswalk_validated": True, "response_or_downstream_calculation_authorized": False},
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks, "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
