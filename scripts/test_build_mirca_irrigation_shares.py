#!/usr/bin/env python3
"""Synthetic tests for MIRCA-OS fixed irrigation-share construction."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

import numpy as np
import rasterio


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_mirca_irrigation_shares", PROJECT / "scripts" / "build_mirca_irrigation_shares.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_raster(path: Path, values: np.ndarray, transform=MODULE.EXPECTED_TRANSFORM) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=0.0,
    ) as target:
        target.write(values.astype("float32"), 1)


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    for crop in MODULE.CROP_MAP:
        irrigation = np.zeros(MODULE.EXPECTED_SHAPE, dtype=np.float32)
        rainfed = np.zeros(MODULE.EXPECTED_SHAPE, dtype=np.float32)
        irrigation[0, 0] = 25.0
        rainfed[0, 0] = 75.0
        if crop == "Maize":
            rainfed[1, 1] = 40.0
        for system, values in (("ir", irrigation), ("rf", rainfed)):
            write_raster(
                root / f"MIRCA-OS_{crop}_2000_{system}_30arcmin_v2.tif", values
            )

    weights, audit = MODULE.build_weights(root, 2000)
    assert len(weights) == 14
    assert not weights.duplicated(["lat", "lon_360", "crop", "irrigation"]).any()
    maize = weights.query("crop == 'mai' and lat == 89.75 and lon_360 == 180.25")
    assert len(maize) == 2
    assert np.isclose(maize.loc[maize.irrigation == "firr", "area_share"].iloc[0], 0.25)
    assert np.isclose(maize.loc[maize.irrigation == "noirr", "area_share"].iloc[0], 0.75)
    rainfed_only = weights.query("crop == 'mai' and lat == 89.25 and lon_360 == 180.75")
    assert set(rainfed_only.irrigation) == {"firr", "noirr"}
    assert rainfed_only.loc[rainfed_only.irrigation == "firr", "area_share"].iloc[0] == 0
    assert weights.query("crop in ['mai', 'soy']").production_eligible.all()
    assert not weights.query("crop in ['ri1', 'ri2', 'swh', 'wwh']").production_eligible.any()
    assert audit["production_eligible_outcome_crops"] == ["mai", "soy"]
    assert audit["provisional_outcome_crops"] == ["ri1", "ri2", "swh", "wwh"]
    assert not audit["scc_authorized"]

    bad = np.zeros(MODULE.EXPECTED_SHAPE, dtype=np.float32)
    bad[0, 0] = -1.0
    write_raster(root / "MIRCA-OS_Maize_2000_ir_30arcmin_v2.tif", bad)
    try:
        MODULE.build_weights(root, 2000, ["mai"])
    except ValueError as error:
        assert "nonnegative" in str(error)
    else:
        raise AssertionError("Expected negative harvested area to fail")

print("MIRCA irrigation-share synthetic tests passed")
