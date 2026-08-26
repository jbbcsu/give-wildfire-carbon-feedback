#!/usr/bin/env python3
"""Synthetic fail-closed tests for MapSPAM production acquisition."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "acquire_mapspam2000_production",
    PROJECT / "scripts" / "acquire_mapspam2000_production.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


metadata = {
    "status": "OK",
    "data": {
        "id": 3357438,
        "identifier": "DVN/A50I2T",
        "latestVersion": {
            "versionState": "RELEASED",
            "versionNumber": 2,
            "versionMinorNumber": 2,
            "releaseTime": "2025-02-04T20:48:09Z",
            "files": [
                {
                    "dataFile": {
                        "id": MODULE.DATAFILE_ID,
                        "persistentId": "doi:10.7910/DVN/A50I2T/R9POPJ",
                        "filename": MODULE.ARCHIVE_NAME,
                        "filesize": MODULE.ARCHIVE_BYTES,
                        "contentType": "application/zip",
                        "checksum": {"type": "MD5", "value": MODULE.ARCHIVE_MD5},
                    }
                }
            ],
        },
    },
}
assert MODULE.validate_dataverse_metadata(metadata)["datafile_id"] == MODULE.DATAFILE_ID
bad_metadata = json.loads(json.dumps(metadata))
bad_metadata["data"]["latestVersion"]["files"][0]["dataFile"]["filesize"] += 1
try:
    MODULE.validate_dataverse_metadata(bad_metadata)
except ValueError as error:
    assert "filesize differs" in str(error)
else:
    raise AssertionError("Metadata identity drift was accepted")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    archive_path = root / "fixture.zip"
    output_path = root / "selected.csv"
    columns = list(MODULE.ID_COLUMNS)
    for crop_code in MODULE.CROPS.values():
        columns.append(crop_code)
        columns.extend(f"{crop_code}_{suffix}" for suffix in MODULE.SYSTEMS.values())
    rows = [
        {
            "stat_code": "USA",
            "prod_level": "US00001",
            "alloc_key": "10002000",
            "hc_seq5m": "123",
            "x": "-99.9583333333333",
            "y": "40.0416666666667",
            "rec_type": "R",
            "unit": "",
            "year_data": "avg(99-01)",
            "source": "F",
            "maiz": "10.0",
            "maiz_h": "4.0",
            "maiz_l": "1.0",
            "maiz_i": "5.0",
            "maiz_s": "0.0",
            "soyb": "0.0",
            "soyb_h": "0.0",
            "soyb_l": "0.0",
            "soyb_i": "0.0",
            "soyb_s": "0.0",
        },
        {
            "stat_code": "BRA",
            "prod_level": "BR00001",
            "alloc_key": "20003000",
            "hc_seq5m": "456",
            "x": "-49.9583333333333",
            "y": "-9.9583333333333",
            "rec_type": "R",
            "unit": "mt",
            "year_data": "avg(99-01)",
            "source": "F",
            "maiz": "0.0",
            "maiz_h": "0.0",
            "maiz_l": "0.0",
            "maiz_i": "0.0",
            "maiz_s": "0.0",
            "soyb": "20.0",
            "soyb_h": "12.0",
            "soyb_l": "4.0",
            "soyb_i": "4.0",
            "soyb_s": "0.0",
        },
    ]
    csv_path = root / MODULE.CSV_MEMBER
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.write(csv_path, MODULE.CSV_MEMBER)
    original_member_bytes = MODULE.CSV_MEMBER_BYTES
    MODULE.CSV_MEMBER_BYTES = csv_path.stat().st_size
    summary = MODULE.extract_maize_soy(archive_path, output_path)
    assert summary["source_rows"] == 2
    assert summary["selected_union_rows"] == 2
    assert summary["selected_unique_hc_seq5m"] == 2
    assert summary["selected_unique_coordinates"] == 2
    assert summary["positive_cells"] == {"maize": 1, "soybean": 1}
    assert summary["global_production_mt"] == {"maize": 10.0, "soybean": 20.0}
    assert summary["blank_unit_rows"] == 1
    assert summary["blank_unit_selected_rows"] == 1
    assert summary["blank_unit_selected_production_mt"] == {"maize": 10.0, "soybean": 0.0}
    assert hashlib.sha512(output_path.read_bytes()).hexdigest() == summary["output_sha512"]

    rows[0]["maiz_i"] = "4.0"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.write(csv_path, MODULE.CSV_MEMBER)
    try:
        MODULE.extract_maize_soy(archive_path, output_path)
    except ValueError as error:
        assert "does not reconcile" in str(error)
    else:
        raise AssertionError("Non-reconciling crop systems were accepted")

    rows[0]["maiz_i"] = "5.0"
    rows[1]["hc_seq5m"] = rows[0]["hc_seq5m"]
    rows[1]["x"] = rows[0]["x"]
    rows[1]["y"] = rows[0]["y"]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
        archive.write(csv_path, MODULE.CSV_MEMBER)
    try:
        MODULE.extract_maize_soy(archive_path, output_path)
    except ValueError as error:
        assert "Duplicate selected MapSPAM cell identity" in str(error)
    else:
        raise AssertionError("Duplicate MapSPAM cell identity was accepted")
    MODULE.CSV_MEMBER_BYTES = original_member_bytes

print("MapSPAM production acquisition tests passed")
