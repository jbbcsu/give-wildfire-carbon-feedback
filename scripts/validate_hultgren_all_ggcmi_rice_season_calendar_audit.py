#!/usr/bin/env python3
"""Independently validate the preregistered all-GGCMI-rice calendar audit."""
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
import xarray as xr
from pyproj import CRS, Transformer
from shapely import Polygon, box, make_valid, union_all
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
ROBINSON = CRS.from_proj4("+proj=robin +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
AREA_CRS = CRS.from_epsg(6933)
COUNTRIES = ("LKA", "VNM")
MONTH_THRESHOLDS = np.array([32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 336], dtype=float)


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


def aliases(name: object, alternatives: object) -> set[str]:
    values = {norm(name)}
    if pd.notna(alternatives):
        values |= {norm(value) for value in str(alternatives).split("|")}
    return values - {"", "nan"}


def derive_author_map(panel_path: Path, hierarchy_path: Path) -> tuple[dict[str, int], dict[int, set[tuple[int, int, int]]], dict[int, str]]:
    columns = ["iso", "adm1", "uid", "season", "median_plant_month", "median_harvest_month", "season_length"]
    parts = []
    with pd.read_stata(panel_path, columns=columns, convert_categoricals=False, iterator=True) as reader:
        while True:
            try:
                chunk = reader.read(25000)
            except StopIteration:
                break
            if chunk.empty:
                break
            keep = chunk.season.eq("second") & chunk.iso.isin(COUNTRIES)
            if keep.any():
                parts.append(chunk.loc[keep].copy())
    second = pd.concat(parts, ignore_index=True)
    identities = second[["iso", "adm1", "uid"]].drop_duplicates()
    require(len(identities) == identities.uid.nunique() == 56, "author UID inventory differs")
    calendars: dict[int, set[tuple[int, int, int]]] = defaultdict(set)
    for row in second.dropna(subset=["median_plant_month", "median_harvest_month", "season_length"]).itertuples(index=False):
        calendars[int(row.uid)].add((int(row.median_plant_month), int(row.median_harvest_month), int(row.season_length)))
    uid_iso = {int(row.uid): str(row.iso) for row in identities.itertuples(index=False)}

    hierarchy = pd.read_csv(hierarchy_path, comment="#", dtype={"region-key": str, "parent-key": str})
    hierarchy["iso"] = hierarchy["region-key"].str.split(".").str[0]
    name_lookup: dict[tuple[str, str], set[str]] = defaultdict(set)
    for _, row in hierarchy.iterrows():
        for label in aliases(row["name"], row["alternatives"]):
            name_lookup[(row["iso"], label)].add(row["region-key"])
    parent_by_uid, match_counts = {}, Counter()
    for row in identities.itertuples(index=False):
        candidates = name_lookup.get((row.iso, norm(row.adm1)), set())
        match_counts[len(candidates)] += 1
        if len(candidates) == 1:
            parent_by_uid[int(row.uid)] = next(iter(candidates))
    require(dict(match_counts) == {1: 43, 0: 10, 2: 3}, "hierarchy match counts differ")
    terminal = set(hierarchy.loc[hierarchy.is_terminal.eq(True), "region-key"])
    children: dict[str, list[str]] = defaultdict(list)
    for _, row in hierarchy.loc[hierarchy["parent-key"].notna()].iterrows():
        children[row["parent-key"]].append(row["region-key"])
    terminal_owner = {}
    for uid, parent in parent_by_uid.items():
        queue, visited = deque([parent]), set()
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            if node in terminal:
                require(node not in terminal_owner, f"duplicate terminal owner: {node}")
                terminal_owner[node] = uid
            else:
                queue.extend(children.get(node, []))
    require(len(terminal_owner) == 147, "terminal descendant count differs")
    return terminal_owner, calendars, uid_iso


def valid_polygon(geometry: object) -> object:
    fixed = geometry if geometry.is_valid else make_valid(geometry)
    if fixed.geom_type in ("Polygon", "MultiPolygon"):
        return fixed
    return union_all([piece for piece in fixed.geoms if piece.geom_type in ("Polygon", "MultiPolygon")])


def derive_shapes(points_path: Path) -> tuple[list[str], list[object]]:
    points = pd.read_csv(points_path, usecols=["long", "lat", "order", "hole", "id", "group"])
    points = points.loc[points.id.astype(str).str.startswith(COUNTRIES)]
    rings: dict[str, dict[str, list[object]]] = {}
    for _, group in points.groupby("group", sort=False):
        polygon = valid_polygon(Polygon(group.sort_values("order")[["long", "lat"]].to_numpy(dtype=float)))
        holder = rings.setdefault(str(group.id.iloc[0]), {"outer": [], "holes": []})
        holder["holes" if bool(group.hole.iloc[0]) else "outer"].append(polygon)
    del points
    gc.collect()
    project = Transformer.from_crs(ROBINSON, AREA_CRS, always_xy=True)
    ids, shapes = [], []
    for identifier, pieces in rings.items():
        geometry = union_all(pieces["outer"])
        if pieces["holes"]:
            geometry = geometry.difference(union_all(pieces["holes"]))
        ids.append(identifier)
        shapes.append(transform(project.transform, valid_polygon(geometry)))
    return ids, shapes


def raw_support(path: Path, minimum: int, maximum: int) -> pd.DataFrame:
    with xr.open_dataset(path, decode_times=False) as dataset:
        planting = np.asarray(dataset.planting_day.values, dtype=float)
        maturity = np.asarray(dataset.maturity_day.values, dtype=float)
        fraction = np.asarray(dataset.fraction_of_harvested_area.values, dtype=float)
        latitudes = np.asarray(dataset.lat.values, dtype=float)
        longitudes = np.asarray(dataset.lon.values, dtype=float)
    mask = np.isfinite(planting) & np.isfinite(maturity) & np.isfinite(fraction) & (fraction > 0)
    ii, jj = np.nonzero(mask)
    pmonth = np.searchsorted(MONTH_THRESHOLDS, planting[ii, jj], side="right") + 1
    hmonth = np.searchsorted(MONTH_THRESHOLDS, maturity[ii, jj], side="right") + 1
    # Exact source convention: same-month values represent an invalid 13-month loop and fail <=12.
    lengths = np.where(pmonth < hmonth, hmonth - pmonth + 1, 13 - pmonth + hmonth)
    keep = (lengths >= minimum) & (lengths <= maximum)
    return pd.DataFrame({
        "native_lat_index": ii[keep].astype(int), "native_lon_index": jj[keep].astype(int),
        "latitude": latitudes[ii[keep]], "longitude": longitudes[jj[keep]],
        "planting_day": planting[ii[keep], jj[keep]], "maturity_day": maturity[ii[keep], jj[keep]],
        "publisher_fraction": fraction[ii[keep], jj[keep]],
        "plant_month": pmonth[keep].astype(int), "harvest_month": hmonth[keep].astype(int),
        "season_months": lengths[keep].astype(int),
    }).sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)


def independent_spatial(
    support: pd.DataFrame, ids: list[str], shapes: list[object], terminal_owner: dict[str, int],
    calendars: dict[int, set[tuple[int, int, int]]], uid_iso: dict[int, str], tolerance: float,
) -> pd.DataFrame:
    tree = STRtree(shapes)
    project = Transformer.from_crs(4326, AREA_CRS, always_xy=True)
    records = []
    for row in support.itertuples(index=False):
        cell = transform(project.transform, box(row.longitude - 0.25, row.latitude - 0.25, row.longitude + 0.25, row.latitude + 0.25))
        pieces: dict[int, list[object]] = defaultdict(list)
        intersections = competitors = 0
        for index in tree.query(cell):
            overlap = cell.intersection(shapes[int(index)])
            if overlap.is_empty or overlap.area <= 0:
                continue
            intersections += 1
            uid = terminal_owner.get(ids[int(index)])
            if uid is None:
                competitors += 1
            else:
                pieces[uid].append(overlap)
        candidate_uids = sorted(pieces)
        exact = len(candidate_uids) == 1
        uid = candidate_uids[0] if exact else None
        coverage = float(union_all(pieces[uid]).area / cell.area) if exact else 0.0
        full = bool(exact and competitors == 0 and coverage >= 1.0 - tolerance)
        calendar = (int(row.plant_month), int(row.harvest_month), int(row.season_months))
        raw_match = bool(exact and calendar in calendars.get(uid, set()))
        records.append({
            "intersected_lka_vnm_terminal_regions": intersections,
            "mapped_second_uid_candidates": len(candidate_uids), "competing_terminal_intersections": competitors,
            "mapped_union_overlap_fraction": coverage, "exactly_one_second_uid": exact,
            "full_spatial_ownership": full, "author_uid": uid, "author_iso": uid_iso.get(uid),
            "calendar_concordant_before_spatial_gate": raw_match,
            "exact_author_calendar_after_spatial_gate": bool(full and raw_match), "authorized": bool(full and raw_match),
        })
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh validation output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require(digest(args.config) == receipt["contract"]["sha256"], "config hash differs")
    require(digest(args.ledger) == receipt["output"]["sha256"], "ledger hash differs")
    expected_inventory = sorted(Path(record["path"]).name for record in config["calendars"].values())
    actual_inventory = sorted(path.name for path in resolve(config["calendar_inventory"]["directory"]).glob("ggcmi-crop-calendar-phase3_2015soc_ri*_*.nc"))
    require(actual_inventory == expected_inventory, "resident rice calendar inventory differs")
    terminal_owner, calendars, uid_iso = derive_author_map(
        resolve(config["sources"]["author_panel"]["path"]), resolve(config["sources"]["author_hierarchy"]["path"])
    )
    ids, shapes = derive_shapes(resolve(config["sources"]["author_region_points"]["path"]))
    ledger = pd.read_parquet(args.ledger)
    branch_checks = {}
    comparison_fields = [
        "intersected_lka_vnm_terminal_regions", "mapped_second_uid_candidates", "competing_terminal_intersections",
        "exactly_one_second_uid", "full_spatial_ownership", "author_uid", "author_iso",
        "calendar_concordant_before_spatial_gate", "exact_author_calendar_after_spatial_gate", "authorized",
    ]
    maximum_overlap_error = 0.0
    for branch in config["calendar_inventory"]["resident_branches"]:
        source = resolve(config["calendars"][branch]["path"])
        require(digest(source) == config["calendars"][branch]["sha256"], f"calendar hash differs: {branch}")
        support = raw_support(source, int(config["support"]["minimum_inclusive_season_months"]), int(config["support"]["maximum_inclusive_season_months"]))
        recorded = ledger.loc[ledger.branch.eq(branch)].sort_values(["native_lat_index", "native_lon_index"]).reset_index(drop=True)
        require(len(recorded) == len(support), f"support row count differs: {branch}")
        for column in ["native_lat_index", "native_lon_index", "plant_month", "harvest_month", "season_months"]:
            require(recorded[column].equals(support[column]), f"raw calendar-derived field differs: {branch}/{column}")
        for column in ["latitude", "longitude", "planting_day", "maturity_day", "publisher_fraction"]:
            require(np.array_equal(recorded[column].to_numpy(), support[column].to_numpy()), f"raw numeric field differs: {branch}/{column}")
        rebuilt = independent_spatial(support, ids, shapes, terminal_owner, calendars, uid_iso, float(config["spatial"]["full_coverage_tolerance"]))
        for column in comparison_fields:
            require(recorded[column].fillna("<missing>").equals(rebuilt[column].fillna("<missing>")), f"spatial/calendar field differs: {branch}/{column}")
        error = float(np.max(np.abs(recorded.mapped_union_overlap_fraction - rebuilt.mapped_union_overlap_fraction)))
        maximum_overlap_error = max(maximum_overlap_error, error)
        expected = receipt["branch_results"][branch]
        checks = {
            "strict_support_cells": len(recorded),
            "cells_intersecting_lka_vnm_terminal_regions": int(rebuilt.intersected_lka_vnm_terminal_regions.gt(0).sum()),
            "cells_with_any_mapped_second_uid": int(rebuilt.mapped_second_uid_candidates.gt(0).sum()),
            "cells_with_exactly_one_second_uid": int(rebuilt.exactly_one_second_uid.sum()),
            "cells_calendar_concordant_before_spatial_gate": int(rebuilt.calendar_concordant_before_spatial_gate.sum()),
            "cells_with_full_spatial_ownership": int(rebuilt.full_spatial_ownership.sum()),
            "cells_with_exact_author_calendar_after_spatial_gate": int(rebuilt.authorized.sum()),
        }
        for key, value in checks.items():
            require(value == expected[key], f"receipt count differs: {branch}/{key}")
        branch_checks[branch] = checks
        del support, recorded, rebuilt
        gc.collect()
        pa.default_memory_pool().release_unused()
    require(maximum_overlap_error <= 1e-12, "overlap-fraction validation tolerance exceeded")
    require(not ledger.authorized.any(), "audit unexpectedly authorized cells")
    require(receipt["product_results"]["passing_independent_products"] == [], "receipt unexpectedly passed a product")
    require(receipt["path_assessment"]["authoritative_author_to_ggcmi_season_crosswalk_present"] is False, "authoritative claim opened")
    require(receipt["path_assessment"]["preregistered_unique_exact_concordance_path_present"] is False, "concordance path opened")
    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"validator exceeded memory cap: {rss} >= {cap}")
    result = {
        "schema": "hultgren_all_ggcmi_rice_season_calendar_audit_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_diagnostic_all_resident_ggcmi_rice_season_calendar_audit_fail_closed",
        "config": {"path": str(args.config), "sha256": digest(args.config)},
        "receipt": {"path": str(args.receipt), "sha256": digest(args.receipt)},
        "ledger": {"path": str(args.ledger), "sha256": digest(args.ledger), "rows": len(ledger)},
        "inventory": {"resident_files": actual_inventory, "ri3_present": False},
        "checks_by_branch": branch_checks,
        "maximum_absolute_overlap_fraction_error": maximum_overlap_error,
        "fail_closed_checks": {
            "all_authorized_cell_counts_zero": True, "no_independent_product_passed": True,
            "authoritative_crosswalk_absent": True, "weather_or_downstream_authorized": False,
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks_by_branch": branch_checks, "maximum_absolute_overlap_fraction_error": maximum_overlap_error, "fail_closed_checks": result["fail_closed_checks"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
