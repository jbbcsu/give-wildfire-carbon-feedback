#!/usr/bin/env python3
"""Synthetic invariants for bounded gridMET smoke acquisition."""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

import numpy as np
import xarray as xr

SCRIPT = Path(__file__).with_name("download_gridmet_smoke.py")
spec = importlib.util.spec_from_file_location("gridmet_smoke", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Response:
    def __init__(self):
        self.headers = {
            "Content-Length": "65031749",
            "ETag": "test-etag",
            "Last-Modified": "Wed, 26 May 2021 19:53:53 GMT",
            "Content-Type": "application/x-netcdf",
        }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def opener(request, timeout):
    assert request.method == "HEAD"
    assert request.full_url == "https://www.northwestknowledge.net/metdata/data/pr_2018.nc"
    return Response()


identity = module.head_identity(module.source_url("pr", 2018), opener)
assert identity["content_length"] == "65031749"
try:
    module.source_url("bad", 2018)
except ValueError:
    pass
else:
    raise AssertionError("invalid gridMET variable should fail")

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "daily.nc"
    data = xr.Dataset(
        {"precipitation_amount": (("day", "lat", "lon"), np.ones((365, 2, 2)), {"units": "mm"})},
        coords={
            "day": np.arange("2018-01-01", "2019-01-01", dtype="datetime64[D]"),
            "lat": [42.0, 41.0],
            "lon": [-94.0, -93.0],
        },
    )
    data.to_netcdf(path, engine="h5netcdf")
    details = module.validate_netcdf(path, "pr", 2018)
    assert details["daily_time_steps"] == 365
    assert details["data_variable"] == "precipitation_amount"
    assert details["start_date"] == "2018-01-01"
    assert details["end_date"] == "2018-12-31"

    bad_dates = data.assign_coords(day=np.arange("2018-01-02", "2019-01-02", dtype="datetime64[D]"))
    bad_dates.to_netcdf(path, engine="h5netcdf", mode="w")
    try:
        module.validate_netcdf(path, "pr", 2018)
    except RuntimeError as error:
        assert "exact requested daily year" in str(error)
    else:
        raise AssertionError("shifted gridMET daily chronology should fail")

print("gridMET smoke downloader tests passed")
