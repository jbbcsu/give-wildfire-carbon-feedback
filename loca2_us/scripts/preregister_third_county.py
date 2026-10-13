#!/usr/bin/env python3
"""Select a third LOCA2 sentinel county without reading outcomes or climate values."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import shapefile


ROOT = Path(__file__).resolve().parents[2]
YEARS = range(2001, 2013)
DIRECT_PRACTICES = {"irrigated", "non_irrigated"}
ANCHORS = ("31039", "31013")  # Cuming, then Box Butte
READ_COLUMNS = (
    "county_geoid", "state", "county_name", "outcome_crop", "harvest_year",
    "irrigation_practice", "season_start", "season_end",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(value))


def load_points(path: Path) -> dict[str, dict]:
    reader = shapefile.Reader(str(path))
    fields = [item[0] for item in reader.fields[1:]]
    required = {"GEOID", "NAME", "STATEFP", "INTPTLAT", "INTPTLON"}
    require(required <= set(fields), "TIGER internal-point fields are incomplete")
    positions = {name: fields.index(name) for name in required}
    result = {}
    for item in reader.iterRecords():
        geoid = str(item[positions["GEOID"]]).zfill(5)
        result[geoid] = {
            "county_geoid": geoid,
            "county_name": str(item[positions["NAME"]]),
            "state_fips": str(item[positions["STATEFP"]]).zfill(2),
            "latitude": float(item[positions["INTPTLAT"]]),
            "longitude": float(item[positions["INTPTLON"]]),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-pattern", default="data/interim/us_county/nclimgrid_features_national_v1/harvest_year={year}/features.parquet")
    parser.add_argument("--shapefile", default="data/raw/us_county/tigerline/tl_2019_us_county/tl_2019_us_county.shp")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-cap-bytes", type=int, default=512 * 1024**2)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    require("yield_bu_acre" not in READ_COLUMNS and "source_value_raw" not in READ_COLUMNS,
            "outcome columns must not be read")

    source_files = []
    frames = []
    for year in YEARS:
        path = ROOT / args.feature_pattern.format(year=year)
        require(path.is_file(), f"missing feature partition: {year}")
        frame = pd.read_parquet(path, columns=list(READ_COLUMNS))
        require(frame["harvest_year"].eq(year).all(), f"partition year differs: {year}")
        frames.append(frame.loc[frame.outcome_crop.eq("corn_grain")].copy())
        source_files.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)})
    support = pd.concat(frames, ignore_index=True)
    support["county_geoid"] = support.county_geoid.astype(str).str.zfill(5)
    support = support.loc[support.irrigation_practice.isin(DIRECT_PRACTICES)].copy()

    eligible = []
    for geoid, county in support.groupby("county_geoid", sort=True):
        keys = county[["harvest_year", "irrigation_practice"]].drop_duplicates()
        if len(keys) != len(YEARS) * len(DIRECT_PRACTICES):
            continue
        if set(keys.harvest_year) != set(YEARS) or set(keys.irrigation_practice) != DIRECT_PRACTICES:
            continue
        require(not county.duplicated(["harvest_year", "irrigation_practice"]).any(), f"duplicate support: {geoid}")
        calendar_counts = county.groupby("harvest_year")[["season_start", "season_end"]].nunique(dropna=False)
        if not (calendar_counts.eq(1).all().all()):
            continue
        eligible.append(geoid)
    require(len(eligible) == 59, f"eligible county count changed: {len(eligible)}")
    require(set(ANCHORS) <= set(eligible), "existing anchors left eligible support")

    shapefile_path = ROOT / args.shapefile
    points = load_points(shapefile_path)
    require(set(eligible) <= set(points), "eligible county missing from TIGER")
    anchor_points = {geoid: (points[geoid]["latitude"], points[geoid]["longitude"]) for geoid in ANCHORS}
    ranked = []
    for geoid in eligible:
        if geoid in ANCHORS:
            continue
        distances = {anchor: haversine_km(
            (points[geoid]["latitude"], points[geoid]["longitude"]), anchor_point,
        ) for anchor, anchor_point in anchor_points.items()}
        ranked.append({
            **points[geoid],
            "distance_to_cuming_km": distances["31039"],
            "distance_to_box_butte_km": distances["31013"],
            "minimum_anchor_distance_km": min(distances.values()),
        })
    ranked.sort(key=lambda row: (-row["minimum_anchor_distance_km"], row["county_geoid"]))
    selected = ranked[0]
    rss = peak_rss_bytes()
    require(rss <= args.memory_cap_bytes, "third-county preregistration exceeded memory cap")

    shapefile_components = []
    for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        path = shapefile_path.with_suffix(suffix)
        if path.is_file():
            shapefile_components.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)})
    result = {
        "schema": "loca2_us_third_county_preregistration/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "third_county_selected_before_loca2_climate_value_access",
        "selection_rule": "Among the unchanged 59 counties with complete 2001-2012 corn calendar/key support in both direct-practice strata, exclude Cuming and Box Butte and select the county maximizing its minimum TIGER-2019 internal-point haversine distance to those two anchors; break exact ties by ascending GEOID.",
        "selection_inputs": {
            "columns_read": list(READ_COLUMNS),
            "outcome_columns_read": False,
            "climate_values_read": False,
            "crop": "corn_grain",
            "years": list(YEARS),
            "direct_practices": sorted(DIRECT_PRACTICES),
            "eligible_counties": len(eligible),
            "anchors": list(ANCHORS),
            "feature_partitions": source_files,
            "tiger_components": shapefile_components,
        },
        "selected": selected,
        "top_five": ranked[:5],
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": args.memory_cap_bytes, "memory_gate_passed": True},
        "next_gate": "build and independently validate TIGER-2019 county-to-LOCA2 weights, then freeze two six-year direct-native-chunk configs for GFDL-ESM4 and IPSL-CM6A-LR without inspecting climate values",
        "claim_gates": {
            "third_county_selected": True,
            "third_county_geometry": False,
            "third_county_climate_sentinel": False,
            "multi_county_validation": False,
            "outcome_response": False,
            "causal_damage": False,
            "SCC": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "selected": selected, "peak_rss_bytes": rss}, indent=2))


if __name__ == "__main__":
    main()
