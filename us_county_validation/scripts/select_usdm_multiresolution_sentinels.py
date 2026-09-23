#!/usr/bin/env python3
"""Select outcome-blind counties and weeks for the USDM resolution audit."""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import resource
import tomllib
import zipfile
from collections import defaultdict
from datetime import date
from io import BytesIO
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import shapefile
from pyproj import Transformer
from shapely import intersects_xy, make_valid
from shapely.geometry import shape

from build_usdm_agricultural_exposure import (
    CATEGORY_NAMES,
    classify_points,
    configured_dates,
    load_manifest,
    load_prepared_grid,
    read_week_geometries,
    sha512_file,
)


def classify_raw_features(path: Path, map_date: date, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Classify points without unioning national polygons in memory."""
    base = f"USDM_{map_date:%Y%m%d}"
    severity = np.full(x.shape, -1, dtype=np.int8)
    with zipfile.ZipFile(path) as archive:
        if bad := archive.testzip():
            raise ValueError(f"ZIP CRC failure in {path.name}: {bad}")
        reader = shapefile.Reader(
            shp=BytesIO(archive.read(f"{base}.shp")),
            shx=BytesIO(archive.read(f"{base}.shx")),
            dbf=BytesIO(archive.read(f"{base}.dbf")),
        )
        fields = [field[0] for field in reader.fields[1:]]
        if "DM" not in fields:
            raise ValueError(f"DM field absent from {path.name}")
        position = fields.index("DM")
        for record in reader.iterShapeRecords():
            level = int(record.record[position])
            if level not in range(5):
                raise ValueError(f"invalid severity {level} in {path.name}")
            geometry = make_valid(shape(record.shape.__geo_interface__))
            if geometry.is_empty:
                continue
            inside = np.asarray(intersects_xy(geometry, x, y), dtype=bool)
            if np.any(inside & (severity >= 0)):
                raise ValueError(f"exclusive USDM classes overlap at support points in {path.name}")
            severity[inside] = level
    return severity


def separated_top_dates(values: np.ndarray, dates: list[date], count: int, separation: int) -> list[int]:
    order = sorted(range(len(dates)), key=lambda i: (-float(values[i]), dates[i]))
    selected: list[int] = []
    for index in order:
        if all(abs((dates[index] - dates[prior]).days) >= separation for prior in selected):
            selected.append(index)
            if len(selected) == count:
                return selected
    raise ValueError("insufficient separated map dates for sentinel selection")


def choose_counties(
    counties: np.ndarray,
    states: np.ndarray,
    area: np.ndarray,
    p95: np.ndarray,
    maximum: np.ndarray,
    strata: int,
) -> list[tuple[int, int]]:
    """Return (stratum, county-position), preferring unique represented states."""
    n = len(counties)
    area_order = sorted(range(n), key=lambda i: (float(area[i]), str(counties[i])))
    stratum = np.empty(n, dtype=np.int16)
    for rank, index in enumerate(area_order):
        stratum[index] = min(strata - 1, rank * strata // n)
    used_states: set[str] = set()
    chosen: list[tuple[int, int]] = []
    for group in range(strata):
        candidates = [i for i in range(n) if int(stratum[i]) == group]
        candidates.sort(key=lambda i: (-float(p95[i]), -float(maximum[i]), str(counties[i])))
        pick = next((i for i in candidates if str(states[i]) not in used_states), candidates[0])
        used_states.add(str(states[pick]))
        chosen.append((group, pick))
    return chosen


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--shape-config", type=Path, required=True)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--prepared-grid", type=Path)
    parser.add_argument("--prepared-grid-audit", type=Path)
    parser.add_argument("--grid-audit", type=Path)
    parser.add_argument("--shape-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--inventory-out", type=Path, required=True)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--score-out", type=Path)
    parser.add_argument("--score-audit-out", type=Path)
    arguments = parser.parse_args()

    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    shape_contract = tomllib.loads(arguments.shape_config.read_text(encoding="utf-8"))
    if any(contract[key] for key in ("selection_uses_outcomes", "causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized")):
        raise ValueError("sentinel selection claim boundary changed")
    selection_mask = str(contract["selection_mask"])
    if arguments.prepared_grid is not None:
        if arguments.prepared_grid_audit is None or arguments.grid_audit is None:
            raise ValueError("prepared scoring requires --prepared-grid-audit and --grid-audit")
        prepared = load_prepared_grid(arguments.prepared_grid, arguments.prepared_grid_audit)
        selected_groups = np.asarray(prepared["mask"] == selection_mask, dtype=bool)
        group_positions = np.flatnonzero(selected_groups)
        counties = np.asarray(prepared["county"])[group_positions].astype("U5")
        states = np.asarray([value[:2] for value in counties], dtype="U2")
        remap = np.full(len(selected_groups), -1, dtype=np.int32)
        remap[group_positions] = np.arange(len(group_positions), dtype=np.int32)
        row_keep = selected_groups[prepared["group_index"]]
        group_index = remap[prepared["group_index"][row_keep]]
        weights = np.asarray(prepared["weight"][row_keep], dtype=np.float64)
        old_cells = np.asarray(prepared["cell_index"][row_keep], dtype=np.int32)
        unique_old_cells, compact_cells = np.unique(old_cells, return_inverse=True)
        transformer = Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True)
        unique_longitude, unique_latitude = transformer.transform(
            prepared["x"][unique_old_cells], prepared["y"][unique_old_cells]
        )
        longitude = np.asarray(unique_longitude, dtype=np.float64)[compact_cells]
        latitude = np.asarray(unique_latitude, dtype=np.float64)[compact_cells]
        grid_audit = json.loads(arguments.grid_audit.read_text(encoding="utf-8"))
        area_by_county = {
            str(row["county_geoid"]): float(row["agricultural_area_m2"])
            for row in grid_audit["counties"]
            if row["mask_id"] == selection_mask and int(row["agricultural_pixels"]) > 0
        }
        area = np.asarray([area_by_county[value] for value in counties], dtype=np.float64)
        del prepared, selected_groups, group_positions, remap, row_keep, old_cells
        del unique_old_cells, compact_cells, unique_longitude, unique_latitude, grid_audit
    else:
        columns = [
            "county_geoid", "state_fips", "mask_id", "cell_center_x_m",
            "cell_center_y_m", "spatial_weight", "county_agricultural_area_m2",
        ]
        table = pq.read_table(
            arguments.grid, columns=columns, filters=[("mask_id", "=", selection_mask)]
        )
        if table.num_rows == 0 or not pc.all(pc.equal(table["mask_id"], selection_mask)).as_py():
            raise ValueError("selection grid does not contain only the frozen mask")
        county_raw = np.asarray(table["county_geoid"].to_pylist(), dtype="U5")
        states_raw = np.asarray(table["state_fips"].to_pylist(), dtype="U2")
        counties, group_index = np.unique(county_raw, return_inverse=True)
        group_index = group_index.astype(np.int32)
        first = np.full(len(counties), len(county_raw), dtype=np.int64)
        np.minimum.at(first, group_index, np.arange(len(group_index), dtype=np.int64))
        states = states_raw[first]
        area_raw = np.asarray(table["county_agricultural_area_m2"].to_numpy(), dtype=np.float64)
        area = area_raw[first]
        weights = np.asarray(table["spatial_weight"].to_numpy(), dtype=np.float64)
        transformer = Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True)
        longitude, latitude = transformer.transform(
            np.asarray(table["cell_center_x_m"].to_numpy(), dtype=np.float64),
            np.asarray(table["cell_center_y_m"].to_numpy(), dtype=np.float64),
        )
        longitude = np.asarray(longitude, dtype=np.float64)
        latitude = np.asarray(latitude, dtype=np.float64)
        del table, county_raw, states_raw, area_raw, first
    if not np.allclose(np.bincount(group_index, weights=weights), 1, rtol=0, atol=1e-10):
        raise ValueError("selection-grid weights do not sum to one")
    gc.collect()
    all_dates = configured_dates(shape_contract)
    if arguments.start_index < 0 or arguments.start_index >= len(all_dates):
        raise ValueError("--start-index is outside the configured map sequence")
    dates = all_dates[arguments.start_index:]
    if arguments.limit is not None:
        if arguments.limit <= 0:
            raise ValueError("--limit must be positive")
        dates = dates[:arguments.limit]
    manifest_path = arguments.shape_dir / "MANIFEST.jsonl"
    manifest = load_manifest(manifest_path)
    ambiguity = np.empty((len(dates), len(counties)), dtype=np.float32)

    for position, map_date in enumerate(dates):
        name = f"USDM_{map_date:%Y%m%d}_M.zip"
        path = arguments.shape_dir / name
        identity = manifest.get(name)
        if identity is None or path.stat().st_size != int(identity["bytes"]) or sha512_file(path) != str(identity["sha512"]):
            raise ValueError(f"USDM source identity differs for {name}")
        geometries = read_week_geometries(path, map_date)
        severity, violations = classify_points(geometries, longitude, latitude)
        if sum(violations.values()):
            raise ValueError(f"exclusive USDM classes overlap at support points in {name}")
        category = severity.astype(np.int16) + 1
        flat = group_index.astype(np.int64) * len(CATEGORY_NAMES) + category
        weekly = np.bincount(
            flat, weights=weights, minlength=len(counties) * len(CATEGORY_NAMES)
        ).reshape(len(counties), len(CATEGORY_NAMES))
        if not np.allclose(weekly.sum(axis=1), 1, rtol=0, atol=1e-10):
            raise ValueError(f"weekly shares do not sum to one for {map_date}")
        ambiguity[position] = 1.0 - weekly.max(axis=1)
        print(f"{position + 1}/{len(dates)} {map_date}", flush=True)

    peak_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if peak_rss > int(contract["resource_ceiling_bytes"]):
        raise MemoryError(
            f"sentinel scorer peak {peak_rss} exceeded frozen ceiling {contract['resource_ceiling_bytes']}"
        )
    if arguments.score_out is not None:
        if arguments.score_audit_out is None:
            raise ValueError("--score-out requires --score-audit-out")
        arguments.score_out.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            arguments.score_out,
            dates=np.asarray([value.isoformat() for value in dates], dtype="U10"),
            counties=counties,
            states=states,
            area=area,
            ambiguity=ambiguity,
        )
        score_audit = {
            "schema": "usdm_multiresolution_sentinel_score_batch_v1",
            "config": str(arguments.config),
            "grid": {"path": str(arguments.grid), "sha512": sha512_file(arguments.grid)},
            "vector_manifest": {"path": str(manifest_path), "sha256": file_sha256(manifest_path)},
            "map_index_start": arguments.start_index,
            "map_index_end_inclusive": arguments.start_index + len(dates) - 1,
            "maps_scored": len(dates),
            "counties_scored": len(counties),
            "output": {"path": str(arguments.score_out), "sha256": file_sha256(arguments.score_out)},
            "resource": {"peak_rss_bytes": peak_rss, "ceiling_bytes": int(contract["resource_ceiling_bytes"])},
            "claim_boundary": "outcome-blind spatial measurement scoring only; no crop outcomes used",
        }
        arguments.score_audit_out.parent.mkdir(parents=True, exist_ok=True)
        arguments.score_audit_out.write_text(
            json.dumps(score_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(score_audit, indent=2))
        return
    if arguments.score_audit_out is not None:
        raise ValueError("--score-audit-out requires --score-out")
    if len(dates) != len(all_dates):
        raise ValueError("direct selection requires the full configured date sequence")

    p95 = np.quantile(ambiguity, 0.95, axis=0)
    maximum = ambiguity.max(axis=0)
    chosen = choose_counties(
        counties, states, area, p95, maximum, int(contract["area_strata"])
    )
    sentinels = []
    inventory_rows = []
    for stratum, index in chosen:
        date_indices = separated_top_dates(
            ambiguity[:, index], dates, int(contract["dates_per_county"]),
            int(contract["minimum_date_separation_days"]),
        )
        sentinels.append({
            "area_stratum_zero_based": int(stratum),
            "county_geoid": str(counties[index]),
            "state_fips": str(states[index]),
            "cultivated_area_m2": float(area[index]),
            "weekly_ambiguity_p95": float(p95[index]),
            "weekly_ambiguity_max": float(maximum[index]),
            "selected_weeks": [
                {"map_date": dates[i].isoformat(), "ambiguity": float(ambiguity[i, index])}
                for i in date_indices
            ],
        })
        inventory_rows.append({"county_geoid": str(counties[index]), "classifier_eligible": "true"})

    arguments.inventory_out.parent.mkdir(parents=True, exist_ok=True)
    with arguments.inventory_out.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["county_geoid", "classifier_eligible"])
        writer.writeheader()
        writer.writerows(sorted(inventory_rows, key=lambda row: row["county_geoid"]))
    output = {
        "schema": "usdm_multiresolution_sentinel_selection_v1",
        "config": str(arguments.config),
        "selection_mask": selection_mask,
        "selection_uses_outcomes": False,
        "grid": {"path": str(arguments.grid), "sha512": sha512_file(arguments.grid)},
        "vector_manifest": {"path": str(manifest_path), "sha256": file_sha256(manifest_path)},
        "maps_scored": len(dates),
        "counties_scored": len(counties),
        "sentinels": sentinels,
        "inventory": {
            "path": str(arguments.inventory_out),
            "sha256": file_sha256(arguments.inventory_out),
        },
        "resource": {
            "peak_rss_bytes": peak_rss,
            "ceiling_bytes": int(contract["resource_ceiling_bytes"]),
        },
        "claim_boundary": "outcome-blind spatial measurement audit only; not causal, damage, global-transfer, or SCC evidence",
    }
    if output["resource"]["peak_rss_bytes"] > output["resource"]["ceiling_bytes"]:
        raise MemoryError("sentinel selector exceeded the frozen resource ceiling")
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"sentinels": sentinels, "resource": output["resource"]}, indent=2))


if __name__ == "__main__":
    main()
