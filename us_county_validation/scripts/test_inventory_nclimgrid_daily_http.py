#!/usr/bin/env python3
"""Synthetic fail-closed tests for the nClimGrid-Daily HTTP inventory."""
from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("inventory_nclimgrid_daily_http.py")
spec = importlib.util.spec_from_file_location("nclimgrid_http_inventory", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class Response:
    def __init__(
        self,
        expected,
        *,
        omit: str | None = None,
        redirect: bool = False,
        content_type: str = "application/x-netcdf",
    ):
        self.status = 200
        self._url = expected.canonical_url + ("?redirected=1" if redirect else "")
        self.headers = {
            "Content-Length": str(50_000_000 + expected.year * 100 + expected.month),
            "ETag": f'"etag-{expected.year:04d}-{expected.month:02d}"',
            "Last-Modified": "Sat, 03 Sep 2022 20:48:27 GMT",
            "Content-Type": content_type,
        }
        if omit:
            self.headers.pop(omit)

    def geturl(self):
        return self._url

    def read(self, *_args, **_kwargs):
        raise AssertionError("HEAD inventory must not read a response body")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def make_opener(
    *,
    omit: str | None = None,
    redirect: bool = False,
    content_type: str = "application/x-netcdf",
):
    def opener(request, timeout):
        assert request.method == "HEAD"
        assert request.headers["Accept-encoding"] == "identity"
        assert timeout > 0
        name = Path(request.full_url).name
        year = int(name[5:9])
        month = int(name[9:11])
        expected = module.ExpectedObject(year, month, name, request.full_url)
        return Response(
            expected,
            omit=omit,
            redirect=redirect,
            content_type=content_type,
        )

    return opener


def row_for(expected, *, etag_suffix: str = ""):
    row = module.head_identity(expected, opener=make_opener(), timeout_seconds=1)
    if etag_suffix:
        return module.InventoryRow(
            year=row.year,
            month=row.month,
            name=row.name,
            canonical_url=row.canonical_url,
            content_length=row.content_length,
            etag=row.etag + etag_suffix,
            last_modified=row.last_modified,
            content_type=row.content_type,
        )
    return row


objects = module.expected_objects()
assert len(objects) == 468
assert objects[0].name == "ncdd-198101-grd-scaled.nc"
assert objects[-1].name == "ncdd-201912-grd-scaled.nc"
assert len({item.key for item in objects}) == 468
sample = objects[0]
identity = module.head_identity(sample, opener=make_opener(), timeout_seconds=1)
assert identity.name == sample.name
assert identity.content_type == "application/x-netcdf"

for bad_opener, expected_message in [
    (make_opener(omit="ETag"), "omitted required ETag"),
    (make_opener(redirect=True), "redirected away"),
    (make_opener(content_type="text/html"), "differs from the reviewed NetCDF type"),
]:
    try:
        module.head_identity(sample, opener=bad_opener, timeout_seconds=1)
    except RuntimeError as error:
        assert expected_message in str(error), str(error)
    else:
        raise AssertionError("incomplete or redirected identity should fail")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    output = root / "inventory.csv"
    checkpoint = module.partial_path(output)
    calls: dict[tuple[int, int], int] = {}

    def interrupted_fetch(expected):
        calls[expected.key] = calls.get(expected.key, 0) + 1
        if expected.key == objects[2].key:
            raise RuntimeError("synthetic interruption")
        return row_for(expected)

    # Batch size one proves that completed identities survive an interruption.
    try:
        module.run_inventory(
            output,
            fetcher=interrupted_fetch,
            workers=1,
            batch_size=1,
            max_new=3,
        )
    except RuntimeError as error:
        assert "synthetic interruption" in str(error)
    else:
        raise AssertionError("synthetic interruption should escape")
    assert not output.exists()
    assert checkpoint.exists()
    partial_rows = module.load_inventory(checkpoint, require_complete=False)
    assert set(partial_rows) == {objects[0].key, objects[1].key}

    # Resume must recheck the two pins before adding the next object.
    resumed = module.run_inventory(
        output,
        fetcher=row_for,
        workers=2,
        batch_size=2,
        max_new=1,
    )
    assert resumed["complete"] is False
    assert resumed["recorded_objects"] == 3
    assert resumed["existing_inventory_reverified"] is True
    assert not output.exists()

    complete_output = root / "complete.csv"
    completed = module.run_inventory(
        complete_output,
        fetcher=row_for,
        workers=4,
        batch_size=48,
    )
    assert completed["complete"] is True
    assert completed["recorded_objects"] == 468
    assert complete_output.exists()
    assert not module.partial_path(complete_output).exists()
    assert len(module.load_inventory(complete_output, require_complete=True)) == 468

    before_drift = checkpoint.read_bytes()

    def drifted_fetch(expected):
        if expected.key == objects[0].key:
            return row_for(expected, etag_suffix="-changed")
        return row_for(expected)

    try:
        module.run_inventory(
            output,
            fetcher=drifted_fetch,
            workers=1,
            batch_size=2,
            max_new=1,
        )
    except RuntimeError as error:
        assert "identity drift" in str(error)
        assert "etag" in str(error)
    else:
        raise AssertionError("upstream identity drift should fail")
    assert checkpoint.read_bytes() == before_drift

    # Duplicate and noncanonical inventory rows are rejected before network use.
    good = row_for(objects[0]).as_csv_row()
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=module.CSV_FIELDS)
        writer.writeheader()
        writer.writerow(good)
        writer.writerow(good)
    try:
        module.load_inventory(output, require_complete=False)
    except RuntimeError as error:
        assert "duplicate year/month" in str(error)
    else:
        raise AssertionError("duplicate inventory object should fail")
    output.unlink()

    bad = dict(good, name="unreviewed-name.nc")
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=module.CSV_FIELDS)
        writer.writeheader()
        writer.writerow(bad)
    try:
        module.load_inventory(output, require_complete=False)
    except RuntimeError as error:
        assert "noncanonical nClimGrid object name" in str(error)
    else:
        raise AssertionError("noncanonical inventory name should fail")

print("nClimGrid-Daily HTTP inventory tests passed")
