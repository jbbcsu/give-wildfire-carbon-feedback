#!/usr/bin/env python3
"""Audit MIRCA rice-season file inventory and metadata without loading rasters."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import xarray as xr


YEARS = (2000, 2005, 2010, 2015, 2020)
SEASONS = (1, 2, 3)
SYSTEMS = ("ir", "rf")
SYSTEM_LABEL = {"ir": "irrigated", "rf": "rainfed"}
FINE_SHAPE = (2160, 4320)
FINE_RESOLUTION = 1.0 / 12.0


def expected_path(root: Path, year: int, season: int, system: str) -> Path:
    return root / str(year) / f"MIRCA-OS_Rice{season}_{year}_{system}.nc"


def inspect_file(
    path: Path,
    year: int,
    season: int,
    system: str,
    *,
    shape: tuple[int, int] = FINE_SHAPE,
) -> dict[str, object]:
    errors: list[str] = []
    record: dict[str, object] = {
        "file_name": path.name,
        "expected_year": year,
        "season": season,
        "system": system,
    }
    if not path.is_file():
        record.update({"passed": False, "errors": ["missing_file"]})
        return record
    try:
        with xr.open_dataset(path, engine="h5netcdf", decode_timedelta=False) as dataset:
            record["source_year_attribute"] = dataset.attrs.get("year")
            record["source_crop_name_attribute"] = dataset.attrs.get("crop_name")
            record["source_irrigation_attribute"] = dataset.attrs.get("irrigation_type")
            if dataset.sizes.get("month") != 12:
                errors.append("month_dimension_not_12")
            if dataset.sizes.get("latitude") != shape[0] or dataset.sizes.get("longitude") != shape[1]:
                errors.append("unexpected_spatial_shape")
            if "harvested_area" not in dataset:
                errors.append("missing_harvested_area")
            elif dataset["harvested_area"].dims != ("month", "latitude", "longitude"):
                errors.append("unexpected_harvested_area_dimensions")
            if "month" not in dataset or not np.array_equal(dataset.month.values, np.arange(1, 13)):
                errors.append("months_not_1_through_12")
            expected_lat = 90.0 - FINE_RESOLUTION / 2 - FINE_RESOLUTION * np.arange(shape[0])
            expected_lon = -180.0 + FINE_RESOLUTION / 2 + FINE_RESOLUTION * np.arange(shape[1])
            if "latitude" not in dataset or not np.allclose(
                dataset.latitude.values, expected_lat, rtol=0.0, atol=2e-10
            ):
                errors.append("unexpected_latitude_coordinates")
            if "longitude" not in dataset or not np.allclose(
                dataset.longitude.values, expected_lon, rtol=0.0, atol=2e-10
            ):
                errors.append("unexpected_longitude_coordinates")
            if str(dataset.attrs.get("crop_name")) != f"Rice{season}":
                errors.append("crop_name_attribute_mismatch")
            try:
                source_year = int(dataset.attrs.get("year"))
            except (TypeError, ValueError):
                source_year = None
            if source_year != year:
                errors.append("year_attribute_mismatch")
            if str(dataset.attrs.get("irrigation_type")).strip().lower() != SYSTEM_LABEL[system]:
                errors.append("irrigation_attribute_mismatch")
    except Exception as error:  # preserve the exact failed-file audit
        errors.append(f"open_error:{type(error).__name__}:{error}")
    record.update({"passed": not errors, "errors": errors})
    return record


def audit_inventory(
    root: Path,
    *,
    years: tuple[int, ...] = YEARS,
    shape: tuple[int, int] = FINE_SHAPE,
) -> dict[str, object]:
    records = [
        inspect_file(expected_path(root, year, season, system), year, season, system, shape=shape)
        for year in years
        for season in SEASONS
        for system in SYSTEMS
    ]
    failed = [record for record in records if not record["passed"]]
    return {
        "schema_version": 1,
        "role": "source_inventory_and_metadata_gate_not_response_damage_or_scc",
        "expected_files": len(records),
        "passed_files": len(records) - len(failed),
        "failed_files": len(failed),
        "all_passed": not failed,
        "records": records,
        "production_rule": "Any metadata mismatch blocks that vintage; filenames never override source attributes.",
        "scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="data/raw/mirca_os_v2/monthly_rice")
    parser.add_argument(
        "--audit-out",
        default="data/interim/mirca_os_v2/rice_season_inventory_metadata_audit.json",
    )
    args = parser.parse_args()
    audit = audit_inventory(Path(args.root))
    output = Path(args.audit_out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "records"}, indent=2))
    if not audit["all_passed"]:
        raise SystemExit("MIRCA rice inventory metadata gate failed; see audit JSON")


if __name__ == "__main__":
    main()
