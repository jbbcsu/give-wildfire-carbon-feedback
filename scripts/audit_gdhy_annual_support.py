#!/usr/bin/env python3
"""Audit annual GDHY source support without imputing or relabeling any value."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import xarray as xr


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_archive(archive: Path, extracted_root: Path) -> dict[str, object]:
    mismatches: list[str] = []
    missing: list[str] = []
    members = 0
    with zipfile.ZipFile(archive) as source:
        corrupt_member = source.testzip()
        if corrupt_member is not None:
            raise ValueError(f"ZIP CRC failure in {corrupt_member}")
        for info in source.infolist():
            if info.is_dir():
                continue
            members += 1
            extracted = extracted_root / info.filename
            if not extracted.is_file():
                missing.append(info.filename)
                continue
            archive_digest = hashlib.sha256(source.read(info)).digest()
            extracted_digest = hashlib.sha256(extracted.read_bytes()).digest()
            if archive_digest != extracted_digest:
                mismatches.append(info.filename)
    return {
        "archive_sha256": sha256(archive),
        "archive_size_bytes": archive.stat().st_size,
        "archive_file_members": members,
        "zip_crc_passed": True,
        "exact_extracted_member_matches": members - len(missing) - len(mismatches),
        "missing_extracted_members": missing,
        "mismatched_extracted_members": mismatches,
    }


def audit_series(root: Path, series: str, years: list[int]) -> dict[str, object]:
    masks: dict[int, np.ndarray] = {}
    positive_masks: dict[int, np.ndarray] = {}
    annual: dict[str, object] = {}
    reference_lat: np.ndarray | None = None
    reference_lon: np.ndarray | None = None
    for year in years:
        path = root / series / f"yield_{year}.nc4"
        if not path.is_file():
            raise FileNotFoundError(path)
        with xr.open_dataset(path, engine="h5netcdf") as dataset:
            if set(dataset.dims) != {"lat", "lon"} or len(dataset.data_vars) != 1:
                raise ValueError(f"Unexpected GDHY schema in {path}")
            variable = next(iter(dataset.data_vars))
            values = dataset[variable].values
            lat = dataset["lat"].values
            lon = dataset["lon"].values
        if reference_lat is None:
            reference_lat = lat
            reference_lon = lon
        elif not np.array_equal(lat, reference_lat) or not np.array_equal(lon, reference_lon):
            raise ValueError(f"Coordinates change within {series}: {path}")
        finite = np.isfinite(values)
        positive = finite & (values > 0)
        zero = finite & (values == 0)
        negative = finite & (values < 0)
        masks[year] = finite
        positive_masks[year] = positive
        annual[str(year)] = {
            "path": str(path),
            "sha256": sha256(path),
            "finite_cells": int(finite.sum()),
            "positive_cells": int(positive.sum()),
            "source_zero_cells": int(zero.sum()),
            "negative_cells": int(negative.sum()),
        }
    assert reference_lat is not None and reference_lon is not None
    transitions: dict[str, object] = {}
    for start, end in zip(years[:-1], years[1:]):
        finite_gained = masks[end] & ~masks[start]
        finite_lost = masks[start] & ~masks[end]
        lost_lat_indices = np.where(finite_lost)[0]
        lost_latitudes = reference_lat[lost_lat_indices]
        positive_union = positive_masks[start] | positive_masks[end]
        transitions[f"{start}-{end}"] = {
            "finite_gained": int(finite_gained.sum()),
            "finite_lost": int(finite_lost.sum()),
            "finite_lost_north": int((lost_latitudes > 0).sum()),
            "finite_lost_south": int((lost_latitudes < 0).sum()),
            "positive_gained": int((positive_masks[end] & ~positive_masks[start]).sum()),
            "positive_lost": int((positive_masks[start] & ~positive_masks[end]).sum()),
            "positive_support_jaccard": (
                None
                if not positive_union.any()
                else float(
                    (positive_masks[start] & positive_masks[end]).sum()
                    / positive_union.sum()
                )
            ),
        }
    return {
        "series": series,
        "grid_shape": list(masks[years[0]].shape),
        "latitude_start": float(reference_lat[0]),
        "latitude_end": float(reference_lat[-1]),
        "longitude_start": float(reference_lon[0]),
        "longitude_end": float(reference_lon[-1]),
        "annual": annual,
        "adjacent_transitions": transitions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--extracted-root", required=True, type=Path)
    parser.add_argument("--series", action="append", required=True)
    parser.add_argument("--year-start", required=True, type=int)
    parser.add_argument("--year-end", required=True, type=int)
    parser.add_argument("--expected-archive-sha256")
    parser.add_argument("--expected-archive-size-bytes", type=int)
    parser.add_argument("--expected-member-count", type=int)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.year_start > args.year_end:
        raise ValueError("year-start must not exceed year-end")
    archive = audit_archive(args.archive, args.extracted_root)
    if archive["missing_extracted_members"] or archive["mismatched_extracted_members"]:
        raise ValueError("Extracted GDHY members do not exactly match the archive")
    expectations = {
        "archive_sha256": args.expected_archive_sha256,
        "archive_size_bytes": args.expected_archive_size_bytes,
        "archive_file_members": args.expected_member_count,
    }
    for field, expected in expectations.items():
        if expected is not None and archive[field] != expected:
            raise ValueError(f"Unexpected {field}: {archive[field]} != {expected}")
    years = list(range(args.year_start, args.year_end + 1))
    result = {
        "schema_version": 1,
        "status": "source_structure_audit_not_missing_value_repair",
        "archive": archive,
        "years": years,
        "series": {
            series: audit_series(args.extracted_root, series, years)
            for series in args.series
        },
        "missing_values_imputed": False,
        "source_files_relabelled": False,
        "causal_interpretation_authorized": False,
        "scc_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
