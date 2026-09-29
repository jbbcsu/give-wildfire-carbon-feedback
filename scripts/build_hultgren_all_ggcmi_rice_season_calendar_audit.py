#!/usr/bin/env python3
"""Audit every resident GGCMI rice-season calendar against author second seasons."""
from __future__ import annotations

import argparse
import gc
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
import pyarrow as pa
import xarray as xr
from pyproj import CRS, Transformer
from shapely import Polygon, box, make_valid, union_all
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_crop_calendar import season_months, source_month_from_day

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


def normalized(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def labels(name: object, alternatives: object) -> set[str]:
    result = {normalized(name)}
    if pd.notna(alternatives):
        result |= {normalized(value) for value in str(alternatives).split("|")}
    return result - {"", "nan"}


def load_config(path: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    raw = path.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    require(config["schema_version"] == 1, "config schema changed")
    require(config["contract_id"] == "hultgren_all_ggcmi_rice_season_calendar_audit_v1", "contract id changed")
    for record in config["sources"].values():
        source = resolve(record["path"])
        require(source.is_file(), f"missing source: {source}")
        require(digest(source) == record["sha256"], f"source hash differs: {source}")
    for record in config["calendars"].values():
        source = resolve(record["path"])
        require(source.is_file(), f"missing calendar: {source}")
        require(digest(source) == record["sha256"], f"calendar hash differs: {source}")
    inventory_dir = resolve(config["calendar_inventory"]["directory"])
    rice_files = sorted(path.name for path in inventory_dir.glob("ggcmi-crop-calendar-phase3_2015soc_ri*_*.nc"))
    expected = sorted(Path(record["path"]).name for record in config["calendars"].values())
    require(rice_files == expected, f"resident rice calendar inventory changed: {rice_files}")
    for branch in config["calendar_inventory"]["absent_branches"]:
        require(not list(inventory_dir.glob(f"ggcmi-crop-calendar-phase3_2015soc_{branch}.nc")), f"declared absent branch exists: {branch}")
    gates = config["claim_gates"]
    require(gates["calendar_audit_authorized"] is True, "calendar audit is not authorized")
    require(all(value is False for key, value in gates.items() if key != "calendar_audit_authorized"), "downstream gate opened")
    inventory = {
        "directory": str(inventory_dir.relative_to(ROOT)),
        "resident_rice_calendar_files": rice_files,
        "resident_branches": list(config["calendar_inventory"]["resident_branches"]),
        "resident_independent_season_products": list(config["calendar_inventory"]["resident_independent_season_products"]),
        "absent_branches": list(config["calendar_inventory"]["absent_branches"]),
        "ri3_genuinely_present": False,
    }
    return config, hashlib.sha256(raw).hexdigest(), inventory


def author_mapping(panel_path: Path, hierarchy_path: Path) -> tuple[dict[str, int], dict[int, set[tuple[int, int, int]]], dict[int, str], dict[str, Any]]:
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
            chosen = chunk.loc[chunk.season.eq("second") & chunk.iso.isin(COUNTRIES)]
            if not chosen.empty:
                parts.append(chosen.copy())
    second = pd.concat(parts, ignore_index=True)
    identity = second[["iso", "adm1", "uid"]].drop_duplicates()
    require(identity.uid.nunique() == len(identity) == 56, "author second-season UID identity differs")
    require(identity.groupby("iso").size().to_dict() == {"LKA": 25, "VNM": 31}, "author country UID counts differ")
    calendars: dict[int, set[tuple[int, int, int]]] = defaultdict(set)
    for row in second.dropna(subset=["median_plant_month", "median_harvest_month", "season_length"]).itertuples(index=False):
        calendars[int(row.uid)].add((int(row.median_plant_month), int(row.median_harvest_month), int(row.season_length)))
    require(all(len(calendars[int(uid)]) == 1 for uid in identity.uid), "author UID has missing or varying calendar")
    uid_iso = {int(row.uid): str(row.iso) for row in identity.itertuples(index=False)}

    hierarchy = pd.read_csv(hierarchy_path, comment="#", dtype={"region-key": str, "parent-key": str})
    hierarchy["iso"] = hierarchy["region-key"].str.split(".").str[0]
    lookup: dict[tuple[str, str], set[str]] = defaultdict(set)
    for _, row in hierarchy.iterrows():
        for label in labels(row["name"], row["alternatives"]):
            lookup[(row["iso"], label)].add(row["region-key"])
    parent_by_uid = {}
    match_counts = Counter()
    for row in identity.itertuples(index=False):
        candidates = lookup.get((row.iso, normalized(row.adm1)), set())
        match_counts[len(candidates)] += 1
        if len(candidates) == 1:
            parent_by_uid[int(row.uid)] = next(iter(candidates))
    require(dict(match_counts) == {1: 43, 0: 10, 2: 3}, "frozen hierarchy parent counts differ")

    children: dict[str, list[str]] = defaultdict(list)
    terminal = set(hierarchy.loc[hierarchy.is_terminal.eq(True), "region-key"])
    for _, row in hierarchy.loc[hierarchy["parent-key"].notna()].iterrows():
        children[row["parent-key"]].append(row["region-key"])
    terminal_owner: dict[str, int] = {}
    descendants_by_country = Counter()
    mapped_uids_by_country = Counter()
    for uid, parent in parent_by_uid.items():
        queue = deque([parent])
        visited, found = set(), set()
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            if node in terminal:
                found.add(node)
            else:
                queue.extend(children.get(node, []))
        require(found, f"unique parent has no terminal descendants: {parent}")
        mapped_uids_by_country[uid_iso[uid]] += 1
        descendants_by_country[uid_iso[uid]] += len(found)
        for key in found:
            require(key not in terminal_owner, f"terminal assigned to multiple UIDs: {key}")
            terminal_owner[key] = uid
    require(len(terminal_owner) == 147, "terminal descendant count differs")
    author_tuples = {}
    for iso in COUNTRIES:
        counter = Counter(f"{a}-{b}-{c}" for uid, values in calendars.items() if uid_iso[uid] == iso for a, b, c in values)
        author_tuples[iso] = dict(sorted(counter.items()))
    audit = {
        "second_season_uids": 56,
        "second_season_uids_by_country": {key: int(value) for key, value in identity.groupby("iso").size().items()},
        "parent_candidate_count_distribution": {str(key): int(value) for key, value in sorted(match_counts.items())},
        "unique_parent_uids": len(parent_by_uid),
        "unique_parent_uids_by_country": dict(mapped_uids_by_country),
        "terminal_descendants": len(terminal_owner),
        "terminal_descendants_by_country": dict(descendants_by_country),
        "author_calendar_tuples_by_country_all_56_uids": author_tuples,
    }
    return terminal_owner, calendars, uid_iso, audit


def polygonal_valid(geometry: object) -> object:
    candidate = geometry if geometry.is_valid else make_valid(geometry)
    if candidate.geom_type in ("Polygon", "MultiPolygon"):
        return candidate
    return union_all([part for part in candidate.geoms if part.geom_type in ("Polygon", "MultiPolygon")])


def country_geometries(points_path: Path) -> tuple[list[str], list[object], dict[str, Any]]:
    points = pd.read_csv(points_path, usecols=["long", "lat", "order", "hole", "id", "group"])
    points = points.loc[points.id.astype(str).str.startswith(COUNTRIES)].copy()
    rings: dict[str, dict[str, list[object]]] = {}
    repairs = 0
    for _, frame in points.groupby("group", sort=False):
        require(frame.id.nunique() == 1 and frame.hole.nunique() == 1, "mixed polygon ring")
        polygon = Polygon(frame.sort_values("order")[["long", "lat"]].to_numpy(dtype=float))
        if not polygon.is_valid:
            repairs += 1
            polygon = polygonal_valid(polygon)
        entry = rings.setdefault(str(frame.id.iloc[0]), {"outer": [], "holes": []})
        entry["holes" if bool(frame.hole.iloc[0]) else "outer"].append(polygon)
    point_rows = len(points)
    del points
    gc.collect()
    transformer = Transformer.from_crs(ROBINSON, AREA_CRS, always_xy=True)
    ids, shapes = [], []
    for key, parts in rings.items():
        geometry = union_all(parts["outer"])
        if parts["holes"]:
            geometry = geometry.difference(union_all(parts["holes"]))
        if not geometry.is_valid:
            repairs += 1
            geometry = polygonal_valid(geometry)
        ids.append(key)
        shapes.append(transform(transformer.transform, geometry))
    return ids, shapes, {"point_rows": point_rows, "terminal_regions_lka_vnm": len(ids), "repairs": repairs}


def calendar_support(path: Path, minimum: int, maximum: int) -> tuple[pd.DataFrame, dict[str, Any], str]:
    with xr.open_dataset(path, decode_times=False, mask_and_scale=True) as dataset:
        require(dataset.sizes == {"lon": 720, "lat": 360}, "calendar grid dimensions differ")
        require(dataset.attrs.get("title") == "GGCMI crop calendar for Phase 3", "calendar title differs")
        require(dataset.attrs.get("version") == "1.01", "calendar version differs")
        planting = dataset["planting_day"].to_numpy()
        maturity = dataset["maturity_day"].to_numpy()
        fraction = dataset["fraction_of_harvested_area"].to_numpy()
        latitudes = dataset["lat"].to_numpy()
        longitudes = dataset["lon"].to_numpy()
        metadata = {
            "title": dataset.attrs.get("title"), "version": dataset.attrs.get("version"),
            "planting_day_long_name": dataset["planting_day"].attrs.get("long_name"),
            "maturity_day_long_name": dataset["maturity_day"].attrs.get("long_name"),
            "fraction_long_name": dataset["fraction_of_harvested_area"].attrs.get("long_name"),
        }
    mask = np.isfinite(planting) & np.isfinite(maturity) & np.isfinite(fraction) & (fraction > 0)
    lat_index, lon_index = np.nonzero(mask)
    rows = []
    for i, j in zip(lat_index.tolist(), lon_index.tolist()):
        plant_month = source_month_from_day(float(planting[i, j]))
        harvest_month = source_month_from_day(float(maturity[i, j]))
        length = len(season_months(plant_month, harvest_month))
        if minimum <= length <= maximum:
            rows.append({
                "native_lat_index": i, "native_lon_index": j,
                "latitude": float(latitudes[i]), "longitude": float(longitudes[j]),
                "planting_day": float(planting[i, j]), "maturity_day": float(maturity[i, j]),
                "publisher_fraction": float(fraction[i, j]),
                "plant_month": plant_month, "harvest_month": harvest_month, "season_months": length,
            })
    support = pd.DataFrame(rows)
    signature_columns = ["native_lat_index", "native_lon_index", "plant_month", "harvest_month", "season_months"]
    signature = hashlib.sha256(support[signature_columns].to_records(index=False).tobytes()).hexdigest()
    metadata.update({
        "finite_calendar_positive_fraction_cells_before_length_gate": int(mask.sum()),
        "strict_support_cells": len(support),
        "calendar_support_signature_sha256": signature,
    })
    return support, metadata, signature


def spatial_calendar_rows(
    support: pd.DataFrame, branch: str, product: str, ids: list[str], shapes: list[object],
    terminal_owner: dict[str, int], calendars: dict[int, set[tuple[int, int, int]]],
    uid_iso: dict[int, str], tolerance: float,
) -> pd.DataFrame:
    tree = STRtree(shapes)
    transformer = Transformer.from_crs(4326, AREA_CRS, always_xy=True)
    rows = []
    for row in support.itertuples(index=False):
        cell = transform(transformer.transform, box(row.longitude - 0.25, row.latitude - 0.25, row.longitude + 0.25, row.latitude + 0.25))
        parts: dict[int, list[object]] = defaultdict(list)
        region_count, competitor = 0, 0
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
        full = bool(exact and competitor == 0 and fraction >= 1.0 - tolerance)
        calendar = (int(row.plant_month), int(row.harvest_month), int(row.season_months))
        raw_match = bool(exact and calendar in calendars.get(uid, set()))
        authorized = bool(full and raw_match)
        rows.append({
            "branch": branch, "season_product": product,
            "native_lat_index": int(row.native_lat_index), "native_lon_index": int(row.native_lon_index),
            "latitude": float(row.latitude), "longitude": float(row.longitude),
            "planting_day": float(row.planting_day), "maturity_day": float(row.maturity_day),
            "publisher_fraction": float(row.publisher_fraction),
            "plant_month": int(row.plant_month), "harvest_month": int(row.harvest_month), "season_months": int(row.season_months),
            "intersected_lka_vnm_terminal_regions": region_count,
            "mapped_second_uid_candidates": len(candidates), "competing_terminal_intersections": competitor,
            "mapped_union_overlap_fraction": fraction, "exactly_one_second_uid": exact,
            "full_spatial_ownership": full, "author_uid": uid, "author_iso": uid_iso.get(uid),
            "calendar_concordant_before_spatial_gate": raw_match,
            "exact_author_calendar_after_spatial_gate": authorized, "authorized": authorized,
        })
    return pd.DataFrame(rows)


def summarize_branch(frame: pd.DataFrame) -> dict[str, Any]:
    by_country = {}
    for iso in COUNTRIES:
        country = frame.loc[frame.author_iso.eq(iso)]
        calendar_counts = Counter(f"{int(row.plant_month)}-{int(row.harvest_month)}-{int(row.season_months)}" for row in country.itertuples(index=False))
        by_country[iso] = {
            "cells_with_exactly_one_uid": len(country),
            "cells_calendar_concordant_before_spatial_gate": int(country.calendar_concordant_before_spatial_gate.sum()),
            "cells_with_full_spatial_ownership": int(country.full_spatial_ownership.sum()),
            "cells_with_exact_author_calendar_after_spatial_gate": int(country.authorized.sum()),
            "ggcmi_calendar_tuples_for_exactly_one_uid_cells": dict(sorted(calendar_counts.items())),
        }
    candidates = frame.loc[frame.exactly_one_second_uid & frame.competing_terminal_intersections.eq(0), "mapped_union_overlap_fraction"]
    return {
        "strict_support_cells": len(frame),
        "cells_intersecting_lka_vnm_terminal_regions": int(frame.intersected_lka_vnm_terminal_regions.gt(0).sum()),
        "cells_with_any_mapped_second_uid": int(frame.mapped_second_uid_candidates.gt(0).sum()),
        "cells_with_exactly_one_second_uid": int(frame.exactly_one_second_uid.sum()),
        "cells_calendar_concordant_before_spatial_gate": int(frame.calendar_concordant_before_spatial_gate.sum()),
        "cells_without_competing_terminal_after_one_uid": int((frame.exactly_one_second_uid & frame.competing_terminal_intersections.eq(0)).sum()),
        "cells_with_full_spatial_ownership": int(frame.full_spatial_ownership.sum()),
        "cells_with_exact_author_calendar_after_spatial_gate": int(frame.authorized.sum()),
        "mapped_union_overlap_fraction_one_uid_no_competitor": {
            "count": len(candidates), "minimum": float(candidates.min()) if len(candidates) else None,
            "median": float(candidates.median()) if len(candidates) else None,
            "maximum": float(candidates.max()) if len(candidates) else None,
        },
        "by_country": by_country,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    config, config_hash, inventory = load_config(args.config)
    terminal_owner, calendars, uid_iso, author_audit = author_mapping(
        resolve(config["sources"]["author_panel"]["path"]), resolve(config["sources"]["author_hierarchy"]["path"])
    )
    ids, shapes, geometry_audit = country_geometries(resolve(config["sources"]["author_region_points"]["path"]))
    require(not (set(terminal_owner) - set(ids)), "selected descendants lack polygon geometry")
    all_frames, branch_summaries, metadata, signatures = [], {}, {}, {}
    for branch in config["calendar_inventory"]["resident_branches"]:
        record = config["calendars"][branch]
        support, metadata[branch], signatures[branch] = calendar_support(
            resolve(record["path"]), int(config["support"]["minimum_inclusive_season_months"]),
            int(config["support"]["maximum_inclusive_season_months"]),
        )
        frame = spatial_calendar_rows(
            support, branch, record["season_product"], ids, shapes, terminal_owner, calendars, uid_iso,
            float(config["spatial"]["full_coverage_tolerance"]),
        )
        branch_summaries[branch] = summarize_branch(frame)
        all_frames.append(frame)
        del support, frame
        gc.collect()
        pa.default_memory_pool().release_unused()
    ledger = pd.concat(all_frames, ignore_index=True)
    product_counts = {
        product: int(ledger.loc[ledger.season_product.eq(product), "authorized"].sum())
        for product in config["calendar_inventory"]["resident_independent_season_products"]
    }
    passing_products = sorted(product for product, count in product_counts.items() if count > 0)
    branch_pairs = {}
    for product in config["calendar_inventory"]["resident_independent_season_products"]:
        branches = [branch for branch, record in config["calendars"].items() if record["season_product"] == product]
        branch_pairs[product] = {
            "branches": branches,
            "calendar_support_signatures_equal": len({signatures[branch] for branch in branches}) == 1,
            "calendar_support_signature_sha256_by_branch": {branch: signatures[branch] for branch in branches},
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output.with_suffix(args.output.suffix + ".partial")
    ledger.to_parquet(partial, index=False, compression="zstd")
    os.replace(partial, args.output)
    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, f"builder exceeded memory cap: {rss} >= {cap}")
    unique = len(passing_products) == 1
    result = {
        "schema": "hultgren_all_ggcmi_rice_season_calendar_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_diagnostic_all_resident_ggcmi_rice_season_calendar_audit_fail_closed",
        "contract": {"path": str(args.config), "sha256": config_hash},
        "inventory": inventory, "author_domain": author_audit, "geometry": geometry_audit,
        "calendar_metadata": metadata, "branch_concordance": branch_pairs,
        "branch_results": branch_summaries,
        "product_results": {
            "authorized_cells_by_independent_product_across_reported_branches": product_counts,
            "passing_independent_products": passing_products,
            "unique_exact_product_passed": unique,
        },
        "path_assessment": {
            "authoritative_author_to_ggcmi_season_crosswalk_present": False,
            "preregistered_unique_exact_concordance_path_present": unique,
            "weather_build_authorized": False,
            "reason": "diagnostic-only audit; no author-supplied product crosswalk, and downstream gates remain closed",
        },
        "output": {"path": str(args.output), "rows": len(ledger), "bytes": args.output.stat().st_size, "sha256": digest(args.output)},
        "claim_gates": {
            "calendar_audit_complete": True, "calendar_product_selected": False,
            "weather_build_authorized": False, "response_evaluation_authorized": False,
            "mirca_weights_authorized": False, "yield_effects_authorized": False,
            "damages_authorized": False, "scc_authorized": False, "give_integration_authorized": False,
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "inventory": inventory, "branch_results": branch_summaries, "product_results": result["product_results"], "path_assessment": result["path_assessment"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
