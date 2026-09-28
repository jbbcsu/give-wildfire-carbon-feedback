#!/usr/bin/env python3
"""Independently validate the fail-closed Rice2 application-domain audit."""
from __future__ import annotations

import argparse
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
WEATHER = ["gdd", "kdd", "tmin", "prcp_poly_1_bin1", "prcp_poly_1_bin2", "prcp_poly_1_bin3", "prcp_poly_2_bin1", "prcp_poly_2_bin2", "prcp_poly_2_bin3"]
GROUPS = ["uid", "adm0_year", "adm1_fact"]
AREA_CRS = CRS.from_epsg(6933)


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def variants(name: object, alternatives: object) -> set[str]:
    values = {norm(name)}
    if pd.notna(alternatives):
        values |= {norm(value) for value in str(alternatives).split("|")}
    return values - {"", "nan"}


def author_uids(panel_path: Path) -> pd.DataFrame:
    columns = ["iso", "adm1", "adm2", "uid", "season", "median_plant_month", "median_harvest_month", "season_length", "ln_yield", *GROUPS[1:], *MODERATORS, *WEATHER]
    parts = []
    with pd.read_stata(panel_path, columns=columns, convert_categoricals=False, iterator=True) as reader:
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
    unique = frame.groupby("uid")[[*MODERATORS, "iso", "adm1", "adm2", "season"]].nunique(dropna=False)
    require((unique == 1).all().all(), "UID fields vary")
    result = frame.groupby("uid", as_index=False).first()[["uid", "iso", "adm1", "adm2", "season"]]
    require(len(result) == 6274, "estimation UID count differs")
    return result


def region_to_uids(uid: pd.DataFrame, hierarchy_path: Path) -> tuple[dict[str, list[tuple[int, str]]], dict[str, int], dict[str, int]]:
    hierarchy = pd.read_csv(hierarchy_path, comment="#", dtype={"region-key": str, "parent-key": str})
    hierarchy["iso"] = hierarchy["region-key"].str.split(".").str[0]
    node_lookup: dict[tuple[str, str], set[str]] = defaultdict(set)
    for _, row in hierarchy.iterrows():
        for label in variants(row["name"], row["alternatives"]):
            node_lookup[(row["iso"], label)].add(row["region-key"])
    parent = hierarchy[["region-key", "name", "alternatives"]].rename(columns={"region-key": "parent-key", "name": "parent_name", "alternatives": "parent_alternatives"})
    terminal = hierarchy[hierarchy.is_terminal.eq(True)].merge(parent, on="parent-key", how="left", validate="many_to_one")
    terminal = terminal.rename(columns={"region-key": "region_key"})
    terminal["iso"] = terminal.region_key.str.split(".").str[0]
    lookup: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in terminal.itertuples(index=False):
        for one in variants(row.parent_name, row.parent_alternatives):
            for two in variants(row.name, row.alternatives):
                lookup[(row.iso, one, two)].add(row.region_key)
    reverse: dict[str, list[tuple[int, str]]] = defaultdict(list)
    candidate_counts = Counter()
    second_node_counts = Counter()
    second_unique = 0
    for row in uid.itertuples(index=False):
        candidates = lookup.get((row.iso, norm(row.adm1), norm(row.adm2)), set())
        candidate_counts[len(candidates)] += 1
        if len(candidates) == 1:
            key = next(iter(candidates))
            reverse[key].append((int(row.uid), str(row.season)))
            second_unique += int(row.season == "second")
        if row.season == "second":
            second_node_counts[len(node_lookup.get((row.iso, norm(row.adm1)), set()))] += 1
    require(second_unique == 0, "second-season UID unexpectedly links uniquely")
    return (
        reverse,
        {str(key): int(value) for key, value in sorted(candidate_counts.items())},
        {str(key): int(value) for key, value in sorted(second_node_counts.items())},
    )


def spatial_counts(basis_path: Path, points_path: Path, reverse: dict[str, list[tuple[int, str]]]) -> dict[str, int]:
    support = pd.read_parquet(basis_path, filters=[[('harvest_year', '==', 1982)]], columns=["native_lat_index", "native_lon_index"])
    require(len(support) == 6197, "Rice2 support count differs")
    ids, geometries, _ = build_regions(points_path)
    region_transformer = Transformer.from_crs(ROBINSON, AREA_CRS, always_xy=True)
    cell_transformer = Transformer.from_crs(4326, AREA_CRS, always_xy=True)
    geometries = [transform(region_transformer.transform, geometry) for geometry in geometries]
    tree = STRtree(geometries)
    counts = Counter()
    for row in support.itertuples(index=False):
        north = 90.0 - int(row.native_lat_index) * 0.5
        west = -180.0 + int(row.native_lon_index) * 0.5
        cell = transform(cell_transformer.transform, box(west, north - 0.5, west + 0.5, north))
        intersections = []
        for index in tree.query(cell):
            area = float(cell.intersection(geometries[int(index)]).area)
            if area > 0:
                intersections.append((ids[int(index)], area / cell.area))
        counts["any_author_region_intersection"] += int(bool(intersections))
        single_full = len(intersections) == 1 and intersections[0][1] >= 1.0 - 1e-6
        counts["single_full_author_region"] += int(single_full)
        candidates = {candidate for key, _ in intersections for candidate in reverse.get(key, [])}
        uids = {uid for uid, _ in candidates}
        counts["any_exact_name_linked_uid"] += int(bool(uids))
        counts["one_distinct_exact_name_linked_uid"] += int(len(uids) == 1)
        strict = single_full and len(uids) == 1
        counts["single_full_region_one_exact_uid"] += int(strict)
        seasons = {season for _, season in candidates}
        counts["second_label_after_strict_geography"] += int(strict and seasons == {"second"})
        counts["total_label_after_strict_geography"] += int(strict and seasons == {"total"})
    return {key: int(value) for key, value in counts.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    for record in config["sources"].values():
        require(digest(resolve(record["path"])) == record["sha256"], "source hash differs")
    uid = author_uids(resolve(config["sources"]["author_panel"]["path"]))
    reverse, link_counts, second_node_counts = region_to_uids(uid, resolve(config["sources"]["author_hierarchy"]["path"]))
    require(link_counts == audit["exact_name_crosswalk"]["candidate_count_distribution"], "link counts differ")
    require(second_node_counts == audit["exact_name_crosswalk"]["second_season_any_hierarchy_node_diagnostic"]["candidate_count_distribution"], "second-season hierarchy-node counts differ")
    observed = spatial_counts(resolve(config["sources"]["rice2_basis"]["path"]), resolve(config["sources"]["author_region_points"]["path"]), reverse)
    expected = audit["rice2_spatial_coverage"]["cell_counts"]
    for key, value in observed.items():
        require(value == expected[key], f"spatial count differs: {key}")
    require(expected["second_label_and_exact_calendar_after_strict_geography"] == 0, "calendar gate opened")
    require(audit["fail_closed_protocol"]["authorized_application_rows"] == 0, "application rows authorized")
    require(not audit["claim_gates"]["published_response_evaluation_authorized"], "response gate opened")
    rss = peak_rss_bytes()
    cap = int(config["memory_cap_bytes"])
    require(rss < cap, "validator exceeded memory cap")
    result = {
        "schema": "hultgren_rice2_response_application_domain_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "validated_fail_closed_rice2_application_domain_audit",
        "config": {"path": str(args.config), "sha256": digest(args.config)},
        "audit": {"path": str(args.audit), "sha256": digest(args.audit)},
        "checks": {"estimation_rows": 166174, "estimation_uids": 6274, "exact_link_candidate_counts": link_counts, "second_season_hierarchy_node_candidate_counts": second_node_counts, "spatial_counts": observed, "authorized_application_rows": 0},
        "claim_gates": {"application_domain_audit_validated": True, "response_or_downstream_calculation_authorized": False},
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": cap, "memory_gate_passed": True},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
