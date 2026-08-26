#!/usr/bin/env python3
"""Synthetic MIRCA rice inventory metadata test."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

import numpy as np
import xarray as xr


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_mirca_rice_inventory", PROJECT / "scripts" / "audit_mirca_rice_inventory.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

shape = (2, 3)
latitude = 90.0 - MODULE.FINE_RESOLUTION / 2 - MODULE.FINE_RESOLUTION * np.arange(shape[0])
longitude = -180.0 + MODULE.FINE_RESOLUTION / 2 + MODULE.FINE_RESOLUTION * np.arange(shape[1])
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    year = 2005
    for season in MODULE.SEASONS:
        for system in MODULE.SYSTEMS:
            path = MODULE.expected_path(root, year, season, system)
            path.parent.mkdir(parents=True, exist_ok=True)
            source_year = 2020 if (season, system) == (2, "rf") else year
            xr.Dataset(
                {
                    "harvested_area": (
                        ("month", "latitude", "longitude"),
                        np.zeros((12, *shape), dtype=np.float32),
                    )
                },
                coords={"month": np.arange(1, 13), "latitude": latitude, "longitude": longitude},
                attrs={
                    "crop_name": f"Rice{season}",
                    "year": source_year,
                    "irrigation_type": MODULE.SYSTEM_LABEL[system],
                },
            ).to_netcdf(path, engine="h5netcdf")
    audit = MODULE.audit_inventory(root, years=(year,), shape=shape)
    assert audit["expected_files"] == 6
    assert audit["passed_files"] == 5 and audit["failed_files"] == 1
    failed = [record for record in audit["records"] if not record["passed"]]
    assert failed[0]["errors"] == ["year_attribute_mismatch"]

print("MIRCA rice inventory metadata tests passed")
