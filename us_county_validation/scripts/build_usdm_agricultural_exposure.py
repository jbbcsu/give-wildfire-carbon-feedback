#!/usr/bin/env python3
"""Overlay weekly USDM shapes on sparse CDL agricultural support.

The implementation keeps one weekly geometry in memory, classifies unique
coarse-cell centers once per week, and streams the resulting county-mask-year
exposures to a compact Parquet file.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import tomllib
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import shapefile
from pyproj import Transformer
from shapely import intersects_xy, make_valid, union_all
from shapely.geometry import shape


CATEGORY_NAMES = ("none", "d0", "d1", "d2", "d3", "d4")


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def configured_dates(contract: dict[str, object]) -> list[date]:
    start = date.fromisoformat(str(contract["first_map_date"]))
    end = date.fromisoformat(str(contract["last_map_date"]))
    frequency = int(contract["frequency_days"])
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=frequency)
    if len(dates) != int(contract["expected_archives"]):
        raise ValueError("configured USDM date sequence has unexpected length")
    return dates


def day_allocations(
    map_date: date, analysis_start: date, analysis_end: date
) -> dict[int, int]:
    """Allocate a Tuesday map's seven represented days to harvest years."""
    allocations: dict[int, int] = defaultdict(int)
    for offset in range(7):
        represented = map_date + timedelta(days=offset)
        if represented < analysis_start or represented > analysis_end:
            continue
        harvest_year = represented.year + 1 if represented.month >= 10 else represented.year
        allocations[harvest_year] += 1
    return dict(allocations)


def load_manifest(path: Path) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            name = Path(str(row["file"])).name
            identity = (int(row["bytes"]), str(row["sha512"]).lower())
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid manifest line {line_number}") from error
        if name in records:
            prior = records[name]
            if identity != (int(prior["bytes"]), str(prior["sha512"]).lower()):
                raise ValueError(f"conflicting manifest identities for {name}")
        records[name] = row
    return records


def read_week_geometries(path: Path, map_date: date) -> dict[int, object]:
    base = f"USDM_{map_date:%Y%m%d}"
    with zipfile.ZipFile(path) as archive:
        if bad := archive.testzip():
            raise ValueError(f"ZIP CRC failure in {path.name}: {bad}")
        projection = archive.read(f"{base}.prj").decode("utf-8").upper()
        if "WGS_1984" not in projection and "WGS 84" not in projection:
            raise ValueError(f"unexpected projection in {path.name}")
        reader = shapefile.Reader(
            shp=BytesIO(archive.read(f"{base}.shp")),
            shx=BytesIO(archive.read(f"{base}.shx")),
            dbf=BytesIO(archive.read(f"{base}.dbf")),
        )
        fields = [field[0] for field in reader.fields[1:]]
        if "DM" not in fields:
            raise ValueError(f"DM field absent from {path.name}")
        position = fields.index("DM")
        parts: dict[int, list[object]] = defaultdict(list)
        for record in reader.iterShapeRecords():
            severity = int(record.record[position])
            if severity not in range(5):
                raise ValueError(f"invalid severity {severity} in {path.name}")
            geometry = make_valid(shape(record.shape.__geo_interface__))
            if not geometry.is_empty:
                parts[severity].append(geometry)
    return {severity: union_all(geometries) for severity, geometries in parts.items()}


def classify_points(
    geometries: dict[int, object], longitude: np.ndarray, latitude: np.ndarray
) -> tuple[np.ndarray, dict[str, int]]:
    """Return -1/no drought or the mutually exclusive vector DM class."""
    severity = np.full(longitude.shape, -1, dtype=np.int8)
    overlap_violations: dict[str, int] = {}
    for level in range(5):
        geometry = geometries.get(level)
        inside = (
            np.zeros(longitude.shape, dtype=bool)
            if geometry is None
            else np.asarray(intersects_xy(geometry, longitude, latitude), dtype=bool)
        )
        overlap_violations[str(level)] = int(np.count_nonzero(inside & (severity >= 0)))
        severity[inside] = level
    return severity, overlap_violations


def load_grid(path: Path) -> dict[str, object]:
    columns = [
        "county_geoid", "mask_id", "coarse_row", "coarse_col",
        "cell_center_x_m", "cell_center_y_m", "spatial_weight",
    ]
    table = pq.read_table(path, columns=columns)
    county = np.asarray(
        pc.cast(table["county_geoid"], pa.int32()).to_numpy(zero_copy_only=False),
        dtype=np.int32,
    )
    mask_values = table["mask_id"]
    valid_masks = pc.is_in(
        mask_values,
        value_set=pa.array(["cultivated_agriculture", "broad_agriculture"]),
    )
    if not pc.all(valid_masks).as_py():
        raise ValueError("grid contains an unknown agricultural mask")
    mask = np.asarray(
        pc.equal(mask_values, "broad_agriculture").to_numpy(zero_copy_only=False),
        dtype=np.int8,
    )
    row = np.asarray(table["coarse_row"].to_numpy(zero_copy_only=False), dtype=np.int32)
    col = np.asarray(table["coarse_col"].to_numpy(zero_copy_only=False), dtype=np.int32)
    x = np.asarray(table["cell_center_x_m"].to_numpy(zero_copy_only=False), dtype=np.float64)
    y = np.asarray(table["cell_center_y_m"].to_numpy(zero_copy_only=False), dtype=np.float64)
    weight = np.asarray(table["spatial_weight"].to_numpy(zero_copy_only=False), dtype=np.float64)
    n_rows = len(weight)
    if len(weight) == 0 or not np.all(np.isfinite(weight)) or np.any(weight <= 0):
        raise ValueError("grid contains empty, nonfinite, or nonpositive weights")

    group_raw = county.astype(np.int64) * 2 + mask.astype(np.int64)
    group_keys, group_index_raw = np.unique(group_raw, return_inverse=True)
    group_index = group_index_raw.astype(np.int32)
    del group_index_raw
    column_base = int(col.max()) + 1
    cell_key = row.astype(np.int64) * column_base + col.astype(np.int64)
    cell_base = (int(row.max()) + 1) * column_base
    row_key = group_raw * cell_base + cell_key
    if len(np.unique(row_key)) != len(row_key):
        raise ValueError("duplicate county-mask-cell row in agricultural grid")
    del row_key, group_raw, county, mask, row, col, table, mask_values
    sums = np.bincount(group_index, weights=weight, minlength=len(group_keys))
    if not np.allclose(sums, 1.0, rtol=0, atol=1e-10):
        raise ValueError("agricultural grid weights do not sum to one")

    unique_cells, cell_index_raw = np.unique(cell_key, return_inverse=True)
    cell_index = cell_index_raw.astype(np.int32)
    del cell_index_raw, cell_key
    first = np.full(len(unique_cells), n_rows, dtype=np.int64)
    np.minimum.at(first, cell_index, np.arange(len(cell_index), dtype=np.int64))
    if np.any(first == n_rows):
        raise RuntimeError("failed to map unique grid cells")
    if not np.allclose(x, x[first[cell_index]], rtol=0, atol=1e-7) or not np.allclose(
        y, y[first[cell_index]], rtol=0, atol=1e-7
    ):
        raise ValueError("same coarse-cell key has inconsistent centers")
    unique_x = x[first].copy()
    unique_y = y[first].copy()
    del x, y, first

    group_county = np.asarray(
        [f"{int(value // 2):05d}" for value in group_keys], dtype="U5"
    )
    group_mask = np.asarray([
        "broad_agriculture" if int(value % 2) else "cultivated_agriculture"
        for value in group_keys
    ])
    return {
        "county": group_county,
        "mask": group_mask,
        "group_index": group_index,
        "cell_index": cell_index,
        "weight": weight,
        "x": unique_x,
        "y": unique_y,
        "rows": n_rows,
        "unique_cells": len(unique_cells),
    }


def load_prepared_grid(path: Path, audit_path: Path) -> dict[str, object]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("schema") != "usdm_agricultural_overlay_grid_v1":
        raise ValueError("unexpected prepared-grid audit schema")
    if path.stat().st_size != int(audit["output"]["bytes"]) or sha512_file(path) != audit["output"]["sha512"]:
        raise ValueError("prepared-grid identity differs from audit")
    with np.load(path, allow_pickle=False) as archive:
        required = {
            "county", "mask", "group_index", "cell_index", "weight", "x", "y",
            "rows", "unique_cells",
        }
        if set(archive.files) != required:
            raise ValueError("prepared grid contains unexpected arrays")
        grid = {name: archive[name] for name in required}
    rows = int(grid["rows"][0])
    unique_cells = int(grid["unique_cells"][0])
    for name in ("group_index", "cell_index", "weight"):
        if len(grid[name]) != rows:
            raise ValueError(f"prepared-grid row array length differs for {name}")
    if len(grid["x"]) != unique_cells or len(grid["y"]) != unique_cells:
        raise ValueError("prepared-grid cell coordinate support differs")
    if grid["group_index"].dtype != np.int32 or grid["cell_index"].dtype != np.int32:
        raise ValueError("prepared-grid indices are not int32")
    groups = len(grid["county"])
    if len(grid["mask"]) != groups or grid["group_index"].min() != 0 or grid["group_index"].max() != groups - 1:
        raise ValueError("prepared-grid group support differs")
    if grid["cell_index"].min() != 0 or grid["cell_index"].max() != unique_cells - 1:
        raise ValueError("prepared-grid cell support differs")
    sums = np.bincount(grid["group_index"], weights=grid["weight"], minlength=groups)
    if not np.allclose(sums, 1, rtol=0, atol=1e-10):
        raise ValueError("prepared-grid weights do not sum to one")
    grid["rows"] = rows
    grid["unique_cells"] = unique_cells
    return grid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    grid_group = parser.add_mutually_exclusive_group(required=True)
    grid_group.add_argument("--grid", type=Path)
    grid_group.add_argument("--prepared-grid", type=Path)
    parser.add_argument("--prepared-grid-audit", type=Path)
    parser.add_argument("--shape-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    parser.add_argument("--start-index", type=int, default=0, help="zero-based first configured map")
    parser.add_argument("--limit", type=int, help="bounded map pilot")
    arguments = parser.parse_args()

    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    all_dates = configured_dates(contract)
    if arguments.start_index < 0 or arguments.start_index >= len(all_dates):
        raise ValueError("--start-index is outside the configured map sequence")
    dates = all_dates[arguments.start_index:]
    if arguments.limit is not None:
        if arguments.limit <= 0:
            raise ValueError("--limit must be positive")
        dates = dates[: arguments.limit]
    manifest = load_manifest(arguments.shape_dir / "MANIFEST.jsonl")
    if arguments.prepared_grid is not None:
        if arguments.prepared_grid_audit is None:
            raise ValueError("--prepared-grid requires --prepared-grid-audit")
        grid = load_prepared_grid(arguments.prepared_grid, arguments.prepared_grid_audit)
        grid_source = str(arguments.prepared_grid)
    else:
        if arguments.prepared_grid_audit is not None:
            raise ValueError("--prepared-grid-audit is valid only with --prepared-grid")
        grid = load_grid(arguments.grid)
        grid_source = str(arguments.grid)
    transformer = Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True)
    longitude, latitude = transformer.transform(grid["x"], grid["y"])
    longitude = np.asarray(longitude, dtype=np.float64)
    latitude = np.asarray(latitude, dtype=np.float64)

    start = all_dates[0] + timedelta(days=5)  # 1 October 2000
    end = all_dates[-1] + timedelta(days=6)   # 30 September 2013
    years = sorted({year for value in dates for year in day_allocations(value, start, end)})
    year_position = {year: position for position, year in enumerate(years)}
    groups = len(grid["county"])
    exposure = np.zeros((len(years), groups, len(CATEGORY_NAMES)), dtype=np.float64)
    map_audits = []

    for number, map_date in enumerate(dates, 1):
        name = f"USDM_{map_date:%Y%m%d}_M.zip"
        path = arguments.shape_dir / name
        if not path.is_file():
            raise FileNotFoundError(path)
        record = manifest.get(name)
        if record is None:
            raise ValueError(f"manifest identity absent for {name}")
        if path.stat().st_size != int(record["bytes"]) or sha512_file(path) != str(record["sha512"]):
            raise ValueError(f"archive identity differs from manifest for {name}")
        geometries = read_week_geometries(path, map_date)
        cell_severity, violations = classify_points(geometries, longitude, latitude)
        if sum(violations.values()):
            raise ValueError(f"exclusive vector classes overlap at coarse-cell centers in {name}")
        row_category = cell_severity[grid["cell_index"]].astype(np.int16) + 1
        flat_index = grid["group_index"].astype(np.int64) * len(CATEGORY_NAMES) + row_category
        weekly = np.bincount(
            flat_index,
            weights=grid["weight"],
            minlength=groups * len(CATEGORY_NAMES),
        ).reshape(groups, len(CATEGORY_NAMES))
        if not np.allclose(weekly.sum(axis=1), 1, rtol=0, atol=1e-10):
            raise ValueError(f"category shares fail to sum to one for {name}")
        allocations = day_allocations(map_date, start, end)
        for year, days in allocations.items():
            exposure[year_position[year]] += weekly * (days / 7.0)
        map_audits.append({
            "map_date": map_date.isoformat(),
            "archive": name,
            "archive_sha512": str(record["sha512"]),
            "severity_values": sorted(geometries),
            "exclusive_class_overlap_points": violations,
            "represented_days": allocations,
        })
        print(f"{number}/{len(dates)} {map_date} groups={groups} cells={grid['unique_cells']}")

    rows = []
    for year_index, harvest_year in enumerate(years):
        represented_days = sum(day_allocations(value, start, end).get(harvest_year, 0) for value in dates)
        expected_weeks = represented_days / 7.0
        if not np.allclose(exposure[year_index].sum(axis=1), expected_weeks, rtol=0, atol=1e-9):
            raise ValueError(f"annual exposure accounting failed for {harvest_year}")
        for group in range(groups):
            row = {
                "county_geoid": str(grid["county"][group]),
                "mask_id": str(grid["mask"][group]),
                "harvest_year": int(harvest_year),
                "represented_days": int(represented_days),
                "total_equivalent_weeks": float(exposure[year_index, group].sum()),
                "analysis_role": "historical_agricultural_area_validation_only",
                "scc_authorized": False,
            }
            row.update({
                f"weeks_{name}": float(exposure[year_index, group, category])
                for category, name in enumerate(CATEGORY_NAMES)
            })
            rows.append(row)

    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, arguments.out, compression="zstd", use_dictionary=True)
    output_sha512 = sha512_file(arguments.out)
    full_run = len(dates) == len(all_dates)
    if full_run:
        for harvest_year in years:
            expected = 366 if calendar.isleap(harvest_year) else 365
            actual = sum(day_allocations(value, start, end).get(harvest_year, 0) for value in dates)
            if actual != expected:
                raise ValueError(f"full-run calendar coverage failed for {harvest_year}")
    audit = {
        "schema": "usdm_agricultural_area_exposure_audit_v1",
        "config": str(arguments.config),
        "grid": grid_source,
        "grid_rows": int(grid["rows"]),
        "unique_grid_cells": int(grid["unique_cells"]),
        "county_mask_groups": groups,
        "maps_processed": len(dates),
        "map_index_start": arguments.start_index,
        "map_index_end_inclusive": arguments.start_index + len(dates) - 1,
        "full_configured_run": full_run,
        "harvest_years": years,
        "output": str(arguments.out),
        "output_rows": table.num_rows,
        "output_sha512": output_sha512,
        "map_audits": map_audits,
        "claim_boundary": "historical spatial-fidelity sensitivity only; not future drought, damage, or SCC",
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {table.num_rows} county-mask-year rows")


if __name__ == "__main__":
    main()
