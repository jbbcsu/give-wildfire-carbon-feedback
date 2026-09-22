#!/usr/bin/env python3
"""Synthetic archive checks for the weekly USDM shapefile downloader."""
from __future__ import annotations

import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import shapefile


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from download_usdm_weekly_shapefiles import build_url, validate_archive  # noqa: E402


def archive_payload() -> bytes:
    shp, shx, dbf = BytesIO(), BytesIO(), BytesIO()
    writer = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    writer.field("DM", "N", 4, 0)
    writer.poly([[[-100, 30], [-99, 30], [-99, 31], [-100, 31], [-100, 30]]])
    writer.record(0)
    writer.poly([[[-99.8, 30.2], [-99.2, 30.2], [-99.2, 30.8], [-99.8, 30.8], [-99.8, 30.2]]])
    writer.record(1)
    writer.close()
    output = BytesIO()
    base = "USDM_20010102"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{base}.shp", shp.getvalue())
        archive.writestr(f"{base}.shx", shx.getvalue())
        archive.writestr(f"{base}.dbf", dbf.getvalue())
        archive.writestr(f"{base}.prj", 'GEOGCS["GCS_WGS_1984"]')
    return output.getvalue()


def main() -> None:
    date = pd.Timestamp("2001-01-02")
    assert build_url(date).endswith("/USDM_20010102_M.zip")
    audit = validate_archive(archive_payload(), date)
    assert audit["records"] == 2
    assert audit["severity_values"] == [0, 1]
    assert audit["bbox"] == [-100.0, 30.0, -99.0, 31.0]
    print("weekly USDM shapefile download tests passed")


if __name__ == "__main__":
    main()
