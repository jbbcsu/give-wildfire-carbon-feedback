#!/usr/bin/env python3
"""Acquire and reduce the pinned MapSPAM 2000 production archive.

The official archive contains every crop and both CSV and DBF copies.  This
script verifies the exact Dataverse file identity and streams only the maize
and soybean production columns into ignored project storage.  It never treats
the resulting table as observed production: SPAM is a spatial allocation
model, and its values are candidate baseline welfare weights only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from datetime import UTC, datetime
from pathlib import Path
import shutil
from typing import BinaryIO, Callable
from urllib.request import Request, urlopen
from zipfile import ZipFile


DATASET_DOI = "https://doi.org/10.7910/DVN/A50I2T"
LANDING_PAGE = "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/A50I2T"
METADATA_URL = "https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/A50I2T"
DATAFILE_ID = 3666788
DATA_URL = f"https://dataverse.harvard.edu/api/access/datafile/{DATAFILE_ID}"
ARCHIVE_NAME = "spam2000v3.0.7_global_production.dbf-csv.zip"
ARCHIVE_BYTES = 99_610_984
ARCHIVE_MD5 = "1dff3f23e222b0648ab609ca5a5f05a5"
ARCHIVE_SHA512 = (
    "8d7936b7ba375816d6813415fbfabae864246ad0cd12061cdc4bd39dc0504d6f"
    "b241a04afe24461d3d210b4cd0dafba2d15655335d32e579157658dc9da0ea51"
)
CSV_MEMBER = "spam_r.csv"
CSV_MEMBER_BYTES = 425_079_488

CROPS = {
    "maize": "maiz",
    "soybean": "soyb",
}
SYSTEMS = {
    "rainfed_high": "h",
    "rainfed_low": "l",
    "irrigated": "i",
    "rainfed_subsistence": "s",
}
ID_COLUMNS = (
    "stat_code",
    "prod_level",
    "alloc_key",
    "hc_seq5m",
    "x",
    "y",
    "rec_type",
    "unit",
    "year_data",
    "source",
)


def file_digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def verify_archive(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"Missing MapSPAM archive: {path}")
    if path.stat().st_size != ARCHIVE_BYTES:
        raise ValueError(
            f"MapSPAM archive byte length differs: {path.stat().st_size} != {ARCHIVE_BYTES}"
        )
    md5 = file_digest(path, "md5")
    if md5 != ARCHIVE_MD5:
        raise ValueError(f"MapSPAM archive MD5 differs: {md5} != {ARCHIVE_MD5}")
    sha512 = file_digest(path, "sha512")
    if sha512 != ARCHIVE_SHA512:
        raise ValueError("MapSPAM archive SHA-512 differs from the acquired pinned object")
    with ZipFile(path) as archive:
        try:
            info = archive.getinfo(CSV_MEMBER)
        except KeyError as error:
            raise ValueError(f"MapSPAM archive lacks {CSV_MEMBER}") from error
        if info.file_size != CSV_MEMBER_BYTES:
            raise ValueError(
                f"MapSPAM CSV member byte length differs: {info.file_size} != {CSV_MEMBER_BYTES}"
            )
    return {
        "size_bytes": ARCHIVE_BYTES,
        "md5": md5,
        "sha512": sha512,
        "csv_member": CSV_MEMBER,
        "csv_member_size_bytes": CSV_MEMBER_BYTES,
    }


def validate_dataverse_metadata(payload: dict[str, object]) -> dict[str, object]:
    if payload.get("status") != "OK":
        raise ValueError("Dataverse metadata response status is not OK")
    data = payload.get("data")
    if not isinstance(data, dict) or data.get("identifier") != "DVN/A50I2T":
        raise ValueError("Dataverse dataset identity differs")
    version = data.get("latestVersion")
    if not isinstance(version, dict) or version.get("versionState") != "RELEASED":
        raise ValueError("Dataverse latest version is not a released record")
    files = version.get("files")
    if not isinstance(files, list):
        raise ValueError("Dataverse metadata has no file list")
    target = None
    for candidate in files:
        if isinstance(candidate, dict):
            data_file = candidate.get("dataFile")
            if isinstance(data_file, dict) and data_file.get("id") == DATAFILE_ID:
                target = data_file
                break
    if target is None:
        raise ValueError(f"Dataverse metadata lacks datafile {DATAFILE_ID}")
    expected = {
        "filename": ARCHIVE_NAME,
        "filesize": ARCHIVE_BYTES,
        "contentType": "application/zip",
    }
    for field, value in expected.items():
        if target.get(field) != value:
            raise ValueError(f"Dataverse {field} differs: {target.get(field)!r} != {value!r}")
    checksum = target.get("checksum")
    if not isinstance(checksum, dict) or checksum.get("type") != "MD5" or checksum.get("value") != ARCHIVE_MD5:
        raise ValueError("Dataverse checksum differs from the pinned archive")
    return {
        "dataset_id": data.get("id"),
        "dataset_identifier": data.get("identifier"),
        "version_number": version.get("versionNumber"),
        "version_minor_number": version.get("versionMinorNumber"),
        "release_time": version.get("releaseTime"),
        "datafile_id": DATAFILE_ID,
        "datafile_persistent_id": target.get("persistentId"),
        "filename": target.get("filename"),
        "size_bytes": target.get("filesize"),
        "md5": checksum.get("value"),
    }


def fetch_json(
    url: str,
    opener: Callable[..., BinaryIO] = urlopen,
) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "GIVE-precipitation-SCC/1.0"})
    with opener(request, timeout=120) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    return payload


def download(
    url: str,
    destination: Path,
    opener: Callable[..., BinaryIO] = urlopen,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    partial.unlink(missing_ok=True)
    request = Request(url, headers={"User-Agent": "GIVE-precipitation-SCC/1.0"})
    try:
        with opener(request, timeout=3600) as response, partial.open("wb") as target:
            shutil.copyfileobj(response, target, length=8 * 1024 * 1024)
        verify_archive(partial)
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def parse_nonnegative(value: str, column: str, row_number: int) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"Invalid numeric {column} at source row {row_number}") from error
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError(f"Non-finite or negative {column} at source row {row_number}")
    return parsed


def extract_maize_soy(
    archive_path: Path,
    output_path: Path,
    reconciliation_tolerance_mt: float = 0.51,
) -> dict[str, object]:
    if reconciliation_tolerance_mt < 0:
        raise ValueError("Reconciliation tolerance must be nonnegative")
    output_columns = [
        "stat_code",
        "admin2_fips",
        "alloc_key",
        "hc_seq5m",
        "longitude",
        "latitude",
        "record_type",
        "unit",
        "year_data",
        "source",
    ]
    for crop in CROPS:
        output_columns.append(f"{crop}_total_mt")
        output_columns.extend(f"{crop}_{system}_mt" for system in SYSTEMS)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial = output_path.with_suffix(output_path.suffix + ".partial")
    partial.unlink(missing_ok=True)
    source_rows = 0
    selected_rows = 0
    countries: set[str] = set()
    positive_cells = {crop: 0 for crop in CROPS}
    totals = {crop: 0.0 for crop in CROPS}
    max_system_reconciliation = {crop: 0.0 for crop in CROPS}
    blank_unit_rows = 0
    blank_unit_selected_rows = 0
    blank_unit_selected_production_mt = {crop: 0.0 for crop in CROPS}
    blank_source_rows = 0
    blank_source_selected_rows = 0
    blank_source_selected_production_mt = {crop: 0.0 for crop in CROPS}
    non_iso3_stat_code_rows = 0
    non_iso3_stat_code_selected_rows = 0
    non_iso3_stat_codes: set[str] = set()
    non_iso3_selected_production_mt = {crop: 0.0 for crop in CROPS}
    source_vintage_rows: dict[str, int] = {}
    source_vintage_selected_rows: dict[str, int] = {}
    source_vintage_selected_production_mt: dict[str, dict[str, float]] = {}
    source_field_rows: dict[str, int] = {}
    source_field_selected_rows: dict[str, int] = {}
    source_field_selected_production_mt: dict[str, dict[str, float]] = {}
    selected_cell_ids: set[int] = set()
    selected_coordinates: set[tuple[float, float]] = set()

    try:
        with ZipFile(archive_path) as archive, archive.open(CSV_MEMBER) as binary, partial.open(
            "w", encoding="utf-8", newline=""
        ) as target:
            source = io.TextIOWrapper(binary, encoding="utf-8", newline="")
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise ValueError("MapSPAM CSV has no header")
            value_columns = []
            for crop_code in CROPS.values():
                value_columns.append(crop_code)
                value_columns.extend(f"{crop_code}_{suffix}" for suffix in SYSTEMS.values())
            missing = sorted(set(ID_COLUMNS).union(value_columns) - set(reader.fieldnames))
            if missing:
                raise ValueError(f"MapSPAM CSV lacks required columns: {missing}")
            writer = csv.DictWriter(target, fieldnames=output_columns, lineterminator="\n")
            writer.writeheader()
            for row_number, row in enumerate(reader, start=2):
                source_rows += 1
                if row["rec_type"] != "R" or row["unit"] not in {"mt", ""}:
                    raise ValueError(f"Unexpected record type or unit at source row {row_number}")
                if row["unit"] == "":
                    # The archival production table contains blank unit cells
                    # for some records despite its file-level production/mt
                    # documentation. Preserve and quantify the defect rather
                    # than silently rewriting the source field.
                    blank_unit_rows += 1
                if row["year_data"] == "":
                    raise ValueError(f"Blank source vintage at source row {row_number}")
                source_vintage_rows[row["year_data"]] = source_vintage_rows.get(row["year_data"], 0) + 1
                source_field_rows[row["source"]] = source_field_rows.get(row["source"], 0) + 1
                if row["source"] == "":
                    blank_source_rows += 1
                stat_code = row["stat_code"]
                stat_code_is_iso3_shaped = (
                    len(stat_code) == 3 and stat_code.isalpha() and stat_code.isupper()
                )
                if not stat_code_is_iso3_shaped:
                    non_iso3_stat_code_rows += 1
                    non_iso3_stat_codes.add(stat_code)
                values: dict[str, dict[str, float]] = {}
                for crop, crop_code in CROPS.items():
                    crop_values = {"total": parse_nonnegative(row[crop_code], crop_code, row_number)}
                    for system, suffix in SYSTEMS.items():
                        column = f"{crop_code}_{suffix}"
                        crop_values[system] = parse_nonnegative(row[column], column, row_number)
                    difference = abs(
                        crop_values["total"]
                        - sum(crop_values[system] for system in SYSTEMS)
                    )
                    max_system_reconciliation[crop] = max(
                        max_system_reconciliation[crop], difference
                    )
                    if difference > reconciliation_tolerance_mt:
                        raise ValueError(
                            f"{crop} total does not reconcile with systems at source row {row_number}: "
                            f"{difference} mt"
                        )
                    values[crop] = crop_values
                if not any(values[crop]["total"] > 0 for crop in CROPS):
                    continue
                source_vintage_selected_rows[row["year_data"]] = (
                    source_vintage_selected_rows.get(row["year_data"], 0) + 1
                )
                source_field_selected_rows[row["source"]] = (
                    source_field_selected_rows.get(row["source"], 0) + 1
                )
                vintage_production = source_vintage_selected_production_mt.setdefault(
                    row["year_data"], {crop: 0.0 for crop in CROPS}
                )
                field_source_production = source_field_selected_production_mt.setdefault(
                    row["source"], {crop: 0.0 for crop in CROPS}
                )
                for crop in CROPS:
                    vintage_production[crop] += values[crop]["total"]
                    field_source_production[crop] += values[crop]["total"]
                if row["unit"] == "":
                    blank_unit_selected_rows += 1
                    for crop in CROPS:
                        blank_unit_selected_production_mt[crop] += values[crop]["total"]
                if row["source"] == "":
                    blank_source_selected_rows += 1
                    for crop in CROPS:
                        blank_source_selected_production_mt[crop] += values[crop]["total"]
                if not stat_code_is_iso3_shaped:
                    non_iso3_stat_code_selected_rows += 1
                    for crop in CROPS:
                        non_iso3_selected_production_mt[crop] += values[crop]["total"]
                try:
                    cell_id = int(row["hc_seq5m"])
                    longitude = float(row["x"])
                    latitude = float(row["y"])
                except ValueError as error:
                    raise ValueError(f"Invalid coordinate/index at source row {row_number}") from error
                if cell_id <= 0:
                    raise ValueError(f"Nonpositive hc_seq5m at source row {row_number}")
                if not (-180 < longitude < 180 and -90 < latitude < 90):
                    raise ValueError(f"Coordinate outside Earth bounds at source row {row_number}")
                lon_index = (longitude + 180.0) * 12.0 - 0.5
                lat_index = (latitude + 90.0) * 12.0 - 0.5
                if (
                    abs(lon_index - round(lon_index)) > 1e-6
                    or abs(lat_index - round(lat_index)) > 1e-6
                ):
                    raise ValueError(
                        f"Coordinate is not a five-arc-minute grid centre at source row {row_number}"
                    )
                coordinate = (longitude, latitude)
                if cell_id in selected_cell_ids or coordinate in selected_coordinates:
                    raise ValueError(
                        f"Duplicate selected MapSPAM cell identity at source row {row_number}"
                    )
                selected_cell_ids.add(cell_id)
                selected_coordinates.add(coordinate)
                output = {
                    "stat_code": stat_code,
                    "admin2_fips": row["prod_level"],
                    "alloc_key": row["alloc_key"],
                    "hc_seq5m": row["hc_seq5m"],
                    "longitude": row["x"],
                    "latitude": row["y"],
                    "record_type": row["rec_type"],
                    "unit": row["unit"],
                    "year_data": row["year_data"],
                    "source": row["source"],
                }
                for crop in CROPS:
                    output[f"{crop}_total_mt"] = row[CROPS[crop]]
                    for system, suffix in SYSTEMS.items():
                        output[f"{crop}_{system}_mt"] = row[f"{CROPS[crop]}_{suffix}"]
                    if values[crop]["total"] > 0:
                        positive_cells[crop] += 1
                        totals[crop] += values[crop]["total"]
                writer.writerow(output)
                selected_rows += 1
                countries.add(stat_code)
        partial.replace(output_path)
    except Exception:
        partial.unlink(missing_ok=True)
        raise

    if source_rows == 0 or selected_rows == 0:
        raise ValueError("MapSPAM extraction produced no data")
    return {
        "source_rows": source_rows,
        "selected_union_rows": selected_rows,
        "selected_unique_hc_seq5m": len(selected_cell_ids),
        "selected_unique_coordinates": len(selected_coordinates),
        "coordinate_grid": "global five-arc-minute cell centres",
        "coordinate_alignment_tolerance_index_units": 1e-6,
        "countries_with_selected_rows": len(countries),
        "positive_cells": positive_cells,
        "global_production_mt": totals,
        "max_total_minus_system_sum_abs_mt": max_system_reconciliation,
        "reconciliation_tolerance_mt": reconciliation_tolerance_mt,
        "blank_unit_rows": blank_unit_rows,
        "blank_unit_selected_rows": blank_unit_selected_rows,
        "blank_unit_selected_production_mt": blank_unit_selected_production_mt,
        "blank_unit_policy": "retained as archival production values because the file/member and rec_type identify production; defect is not imputed away",
        "blank_source_rows": blank_source_rows,
        "blank_source_selected_rows": blank_source_selected_rows,
        "blank_source_selected_production_mt": blank_source_selected_production_mt,
        "non_iso3_stat_code_rows": non_iso3_stat_code_rows,
        "non_iso3_stat_code_selected_rows": non_iso3_stat_code_selected_rows,
        "non_iso3_stat_codes": sorted(non_iso3_stat_codes),
        "non_iso3_selected_production_mt": non_iso3_selected_production_mt,
        "country_code_policy": "stat_code is preserved verbatim; ISO3 compatibility must be established by a separate crosswalk audit",
        "source_vintage_rows": dict(sorted(source_vintage_rows.items())),
        "source_vintage_selected_rows": dict(sorted(source_vintage_selected_rows.items())),
        "source_vintage_selected_production_mt": dict(sorted(source_vintage_selected_production_mt.items())),
        "source_vintage_policy": "year_data is preserved verbatim; SPAM 2000 contains national scaling vintages other than avg(99-01)",
        "source_field_rows": dict(sorted(source_field_rows.items())),
        "source_field_selected_rows": dict(sorted(source_field_selected_rows.items())),
        "source_field_selected_production_mt": dict(sorted(source_field_selected_production_mt.items())),
        "source_field_policy": "source is preserved verbatim; archival values include F, N/F, and blanks despite the codebook statement that source is always F",
        "output_path": str(output_path),
        "output_size_bytes": output_path.stat().st_size,
        "output_sha512": file_digest(output_path, "sha512"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="data/raw/mapspam_2000_v3_0_7")
    parser.add_argument(
        "--out",
        default="data/interim/welfare_weights/mapspam2000_maize_soy_production.csv",
    )
    parser.add_argument(
        "--audit",
        default="data/interim/welfare_weights/mapspam2000_maize_soy_production.audit.json",
    )
    parser.add_argument("--skip-metadata", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    archive_path = raw_dir / ARCHIVE_NAME
    metadata = None
    if not args.skip_metadata:
        metadata = validate_dataverse_metadata(fetch_json(METADATA_URL))
    archive_status = "existing"
    if not archive_path.exists():
        download(DATA_URL, archive_path)
        archive_status = "downloaded"
    archive_identity = verify_archive(archive_path)
    if args.download_only:
        print(json.dumps({"status": archive_status, **archive_identity}, indent=2))
        return

    extraction = extract_maize_soy(archive_path, Path(args.out))
    audit = {
        "schema_version": 1,
        "retrieved_or_verified_utc": datetime.now(UTC).isoformat(),
        "dataset_title": "Global Spatially-Disaggregated Crop Production Statistics Data for 2000 Version 3.0.7",
        "dataset_doi": DATASET_DOI,
        "landing_page": LANDING_PAGE,
        "dataverse_metadata": metadata,
        "archive_status": archive_status,
        "archive_path": str(archive_path),
        "archive_identity": archive_identity,
        "license_gate": {
            "dataverse_dataset_terms": "CC-BY-4.0",
            "mapspam_site_terms": "CC-BY-NC-3.0",
            "redistribution_authorized": False,
            "reason": "source-specific official statements differ; the exact Dataverse object is used internally and source/derived data remain ignored pending IFPRI clarification",
        },
        "role": "candidate fixed-circa-2000 production weights; not observed production, response, damage, or SCC",
        "extraction": extraction,
    }
    audit_path = Path(args.audit)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
