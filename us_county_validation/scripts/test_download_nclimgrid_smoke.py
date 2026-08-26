#!/usr/bin/env python3
"""Synthetic invariants for bounded nClimGrid-Daily smoke acquisition."""
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
from pathlib import Path

import numpy as np
import xarray as xr


SCRIPT = Path(__file__).with_name("download_nclimgrid_smoke.py")
spec = importlib.util.spec_from_file_location("nclimgrid_smoke", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Response:
    def __init__(self):
        self.headers = {
            "Content-Length": "59955310",
            "ETag": '"392d86e-5e7cbf7e65cc0"',
            "Last-Modified": "Sat, 03 Sep 2022 20:48:27 GMT",
            "Content-Type": "application/x-netcdf",
        }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def opener(request, timeout):
    assert request.method == "HEAD"
    assert request.full_url == (
        "https://www.ncei.noaa.gov/data/nclimgrid-daily/access/grids/1981/"
        "ncdd-198101-grd-scaled.nc"
    )
    return Response()


identity = module.head_identity(module.source_url(1981, 1), opener)
assert identity["content_length"] == "59955310"
default_pin = module.load_pinned_record(module.DEFAULT_PROVENANCE_RECORD, 1981, 1)
assert default_pin["size_bytes"] == 59955310
assert default_pin["sha512"].startswith("20ef278e")
module.validate_pinned_remote(identity, default_pin)

growing_season_record = (
    module.PROJECT_ROOT / "data/provenance/nclimgrid_daily_1981_cuming_smoke.toml"
)
may_pin = module.load_pinned_record(growing_season_record, 1981, 5)
assert may_pin["size_bytes"] == 61069446
assert may_pin["sha512"].startswith("b2e52721")

try:
    module.validate_pinned_remote(dict(identity, last_modified="changed"), default_pin)
except RuntimeError as error:
    assert "last_modified differs" in str(error)
else:
    raise AssertionError("changed nClimGrid upstream identity should fail")

for year, month in [(1980, 12), (1981, 2)]:
    try:
        module.load_pinned_record(module.DEFAULT_PROVENANCE_RECORD, year, month)
    except RuntimeError as error:
        assert "differs from reviewed provenance object" in str(error)
    else:
        raise AssertionError("request outside the reviewed nClimGrid object should fail")

try:
    module.object_name(1981, 13)
except ValueError:
    pass
else:
    raise AssertionError("invalid nClimGrid month should fail")

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "daily.nc"
    pinned_bytes = b"reviewed nClimGrid object"
    path.write_bytes(pinned_bytes)
    synthetic_pin = {
        "size_bytes": len(pinned_bytes),
        "sha512": hashlib.sha512(pinned_bytes).hexdigest(),
    }
    module.validate_pinned_file(path, synthetic_pin)
    path.write_bytes(b"tampered nClimGrid object")
    try:
        module.validate_pinned_file(path, synthetic_pin)
    except RuntimeError:
        pass
    else:
        raise AssertionError("tampered nClimGrid file should fail its immutable pin")

    shape = (31, 596, 1385)
    field = np.zeros(shape, dtype=np.int8)
    attrs = {
        "comment": (
            "Values should be rounded. Each daily value applies to the 24-hour period "
            "ending in the early morning of the specified day."
        )
    }
    data_vars = {}
    for name, (standard_name, units) in module.EXPECTED_FIELDS.items():
        data_vars[name] = (
            ("time", "lat", "lon"),
            field,
            {**attrs, "standard_name": standard_name, "units": units},
        )
    data = xr.Dataset(
        data_vars,
        coords={
            "time": np.arange("1981-01-01", "1981-02-01", dtype="datetime64[D]"),
            "lat": np.arange(596, dtype=float),
            "lon": np.arange(1385, dtype=float),
        },
        attrs={
            "title": module.EXPECTED_TITLE,
            "product_version": module.EXPECTED_VERSION,
            "license": "no restrictions",
        },
    )
    data.to_netcdf(path, engine="h5netcdf", mode="w")
    details = module.validate_netcdf(path, 1981, 1)
    assert details["daily_time_steps"] == 31
    assert details["start_date"] == "1981-01-01"
    assert details["end_date"] == "1981-01-31"
    assert details["day_label_semantics"].startswith("24-hour period")

    invalid_cases = [
        (
            data.assign_coords(
                time=np.arange("1981-01-02", "1981-02-02", dtype="datetime64[D]")
            ),
            "exact requested calendar month",
        ),
        (
            data.assign_attrs(product_version="unreviewed-version"),
            "product_version differs",
        ),
        (
            data.assign(prcp=data.prcp.assign_attrs(units="kg m-2")),
            "units changed",
        ),
    ]
    for invalid, expected in invalid_cases:
        invalid.to_netcdf(path, engine="h5netcdf", mode="w")
        try:
            module.validate_netcdf(path, 1981, 1)
        except RuntimeError as error:
            assert expected in str(error), str(error)
        else:
            raise AssertionError(f"invalid nClimGrid case should fail: {expected}")

print("nClimGrid smoke downloader tests passed")
