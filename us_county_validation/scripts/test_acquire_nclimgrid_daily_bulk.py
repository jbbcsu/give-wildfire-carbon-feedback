#!/usr/bin/env python3
"""Offline integrity, resume, scope, and provenance tests for bulk acquisition."""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import xarray as xr


SCRIPT = Path(__file__).with_name("acquire_nclimgrid_daily_bulk.py")
spec = importlib.util.spec_from_file_location("acquire_nclimgrid_daily_bulk", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class FakeResponse(io.BytesIO):
    def __init__(
        self,
        payload: bytes,
        *,
        url: str,
        headers: dict[str, str],
        status: int = 200,
    ) -> None:
        super().__init__(payload)
        self._url = url
        self.headers = headers
        self.status = status

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def make_netcdf(path: Path, year: int, month: int, *, bad_title: bool = False) -> bytes:
    days = pd.date_range(
        f"{year:04d}-{month:02d}-01",
        periods=pd.Period(f"{year:04d}-{month:02d}").days_in_month,
        freq="D",
    )
    lat = np.array([30.0, 30.5], dtype=np.float64)
    lon = np.array([-100.0, -99.5, -99.0], dtype=np.float64)
    shape = (len(days), len(lat), len(lon))
    dataset = xr.Dataset(
        {
            name: (("time", "lat", "lon"), np.zeros(shape, dtype=np.float32))
            for name in module.smoke.EXPECTED_FIELDS
        },
        coords={"time": days, "lat": lat, "lon": lon},
        attrs={
            "title": "changed title" if bad_title else module.smoke.EXPECTED_TITLE,
            "product_version": module.smoke.EXPECTED_VERSION,
            "license": "no restrictions",
        },
    )
    for name, (standard_name, units) in module.smoke.EXPECTED_FIELDS.items():
        dataset[name].attrs.update(
            {
                "standard_name": standard_name,
                "units": units,
                "comment": "24-hour period ending in the early morning of the specified date",
            }
        )
    dataset.to_netcdf(path, engine="h5netcdf")
    return path.read_bytes()


def make_license_record(path: Path) -> None:
    path.write_text(
        '''source = "NOAA NCEI nClimGrid-Daily v1.0.0"
landing_page_url = "https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily"
dataset_doi = "https://doi.org/10.25921/c4gt-r169"
version = "v1-0-0 20220829 as embedded in the reviewed NetCDF"

[license]
status = "U.S. federal government data with no restrictions stated in the reviewed NetCDF"
spdx_identifier = "NOASSERTION"
url = "https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily"
embedded_statement = "no restrictions"

[stability]
scientific_limitations = ["Synthetic test limitation; not scientific data."]
''',
        encoding="utf-8",
    )


def make_complete_inventory(
    path: Path, lengths: dict[tuple[int, int], int]
) -> dict[tuple[int, int], module.inventory.InventoryRow]:
    rows: dict[tuple[int, int], module.inventory.InventoryRow] = {}
    for expected in module.inventory.expected_objects():
        length = lengths.get(expected.key, 1)
        row = module.inventory.InventoryRow(
            year=expected.year,
            month=expected.month,
            name=expected.name,
            canonical_url=expected.canonical_url,
            content_length=length,
            etag=f'"etag-{expected.year:04d}{expected.month:02d}"',
            last_modified="Sat, 03 Sep 2022 20:48:27 GMT",
            content_type=module.inventory.EXPECTED_CONTENT_TYPE,
        )
        rows[row.key] = row
    module.inventory.write_inventory_atomic(path, rows)
    return rows


def headers_for(row: module.inventory.InventoryRow) -> dict[str, str]:
    return {
        "Content-Length": str(row.content_length),
        "ETag": row.etag,
        "Last-Modified": row.last_modified,
        "Content-Type": row.content_type,
    }


original_shape = module.smoke.EXPECTED_SHAPE
original_inventory_sha512 = module.REVIEWED_INVENTORY_SHA512
original_product_sha512 = module.REVIEWED_PRODUCT_RECORD_SHA512
module.smoke.EXPECTED_SHAPE = {"lat": 2, "lon": 3}
try:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        jan_path = root / "jan.nc"
        feb_path = root / "feb.nc"
        bad_path = root / "bad.nc"
        jan = make_netcdf(jan_path, 1981, 1)
        feb = make_netcdf(feb_path, 1981, 2)
        bad = make_netcdf(bad_path, 1981, 1, bad_title=True)
        inventory_path = root / "inventory.csv"
        rows = make_complete_inventory(
            inventory_path, {(1981, 1): len(jan), (1981, 2): len(feb)}
        )
        license_path = root / "reviewed.toml"
        make_license_record(license_path)
        module.REVIEWED_INVENTORY_SHA512 = module.smoke.sha512_file(inventory_path)
        module.REVIEWED_PRODUCT_RECORD_SHA512 = module.smoke.sha512_file(license_path)
        fixed_now = lambda: datetime(2026, 8, 26, 18, 0, tzinfo=UTC)

        head_calls: list[tuple[int, int]] = []

        def head(row: module.inventory.InventoryRow) -> module.inventory.InventoryRow:
            head_calls.append(row.key)
            return row

        bodies = {(1981, 1): jan, (1981, 2): feb}
        get_calls: list[tuple[int, int]] = []

        def downloader(row: module.inventory.InventoryRow, part: Path) -> None:
            get_calls.append(row.key)

            def opener(request: object, timeout: float) -> FakeResponse:
                assert getattr(request, "method", None) == "GET"
                assert timeout > 0
                return FakeResponse(
                    bodies[row.key],
                    url=row.canonical_url,
                    headers=headers_for(row),
                )

            module.download_to_part(row, part, opener=opener)

        # A stale partial object is discarded; the whole month is restarted,
        # validated, atomically promoted, then recorded once.
        out = root / "raw"
        out.mkdir()
        stale = out / (rows[(1981, 1)].name + ".part")
        stale.write_bytes(b"untrusted interrupted response")
        first = module.run_acquisition(
            inventory_path=inventory_path,
            out_dir=out,
            reviewed_product_record=license_path,
            max_new=1,
            head_fetcher=head,
            downloader=downloader,
            now=fixed_now,
        )
        assert first["expected_objects"] == 468
        assert first["validated_objects"] == 1
        assert first["new_downloaded_objects"] == 1
        assert first["remaining_objects"] == 467
        assert get_calls == [(1981, 1)]
        assert not stale.exists()
        final = out / rows[(1981, 1)].name
        assert final.read_bytes() == jan
        manifest = out / module.MANIFEST_NAME
        records = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert len(records) == 1
        assert records[0]["file_status"] == "downloaded_and_validated"
        assert records[0]["retrieved_utc"] == "2026-08-26T18:00:00+00:00"
        assert records[0]["relationship_estimated"] is False
        assert records[0]["scc_authorized"] is False

        # File-granular resume rechecks HEAD, length, manifest SHA, and schema;
        # max_new=0 cannot issue a GET and does not duplicate the manifest.
        manifest_before = manifest.read_bytes()

        def no_download(row: module.inventory.InventoryRow, part: Path) -> None:
            raise AssertionError("max_new=0 must not download")

        resumed = module.run_acquisition(
            inventory_path=inventory_path,
            out_dir=out,
            reviewed_product_record=license_path,
            max_new=0,
            head_fetcher=head,
            downloader=no_download,
            now=fixed_now,
        )
        assert resumed["reverified_manifested_objects"] == 1
        assert resumed["new_downloaded_objects"] == 0
        assert manifest.read_bytes() == manifest_before

        # Same-length local corruption is caught by the locally pinned SHA-512.
        tampered = bytearray(jan)
        tampered[-1] ^= 1
        final.write_bytes(tampered)
        try:
            module.run_acquisition(
                inventory_path=inventory_path,
                out_dir=out,
                reviewed_product_record=license_path,
                max_new=0,
                head_fetcher=head,
                downloader=no_download,
                now=fixed_now,
            )
        except RuntimeError as error:
            assert "SHA-512" in str(error)
        else:
            raise AssertionError("manifested file corruption should fail")
        final.write_bytes(jan)

        # A validated pre-existing smoke object can be adopted without
        # fabricating its historical retrieval timestamp.
        adopted_out = root / "adopted"
        adopted_out.mkdir()
        (adopted_out / rows[(1981, 1)].name).write_bytes(jan)
        adopted = module.run_acquisition(
            inventory_path=inventory_path,
            out_dir=adopted_out,
            reviewed_product_record=license_path,
            max_new=0,
            head_fetcher=head,
            downloader=no_download,
            now=fixed_now,
        )
        assert adopted["adopted_existing_objects"] == 1
        adopted_record = json.loads(
            (adopted_out / module.MANIFEST_NAME).read_text().strip()
        )
        assert adopted_record["file_status"] == "adopted_existing_and_validated"
        assert adopted_record["retrieved_utc"] is None

        # Upstream identity drift is checked before any GET or manifest update.
        drift_out = root / "drift"
        drift_gets: list[object] = []

        def drift_head(row: module.inventory.InventoryRow) -> module.inventory.InventoryRow:
            return replace(row, etag=row.etag + "-changed")

        def record_get(row: module.inventory.InventoryRow, part: Path) -> None:
            drift_gets.append(row.key)

        try:
            module.run_acquisition(
                inventory_path=inventory_path,
                out_dir=drift_out,
                reviewed_product_record=license_path,
                max_new=1,
                head_fetcher=drift_head,
                downloader=record_get,
                now=fixed_now,
            )
        except RuntimeError as error:
            assert "identity drift" in str(error)
            assert "etag" in str(error)
        else:
            raise AssertionError("upstream drift should fail")
        assert drift_gets == []
        assert not (drift_out / module.MANIFEST_NAME).exists()

        # A truncated response never reaches a final name or manifest.
        trunc_out = root / "truncated"

        def truncated(row: module.inventory.InventoryRow, part: Path) -> None:
            def opener(request: object, timeout: float) -> FakeResponse:
                return FakeResponse(
                    jan[:-1], url=row.canonical_url, headers=headers_for(row)
                )

            module.download_to_part(row, part, opener=opener)

        try:
            module.run_acquisition(
                inventory_path=inventory_path,
                out_dir=trunc_out,
                reviewed_product_record=license_path,
                max_new=1,
                head_fetcher=head,
                downloader=truncated,
                now=fixed_now,
            )
        except RuntimeError as error:
            assert "length" in str(error)
        else:
            raise AssertionError("truncated response should fail")
        assert not (trunc_out / rows[(1981, 1)].name).exists()
        assert not (trunc_out / (rows[(1981, 1)].name + ".part")).exists()
        assert not (trunc_out / module.MANIFEST_NAME).exists()

        # The bounded retry wrapper restarts a transiently truncated month
        # from byte zero; it never appends to or trusts the failed prefix.
        retry_part = root / (rows[(1981, 1)].name + ".part")
        retry_calls: list[int] = []

        def retry_opener(request: object, timeout: float) -> FakeResponse:
            retry_calls.append(len(retry_calls) + 1)
            payload = jan[:-1] if len(retry_calls) == 1 else jan
            return FakeResponse(
                payload,
                url=rows[(1981, 1)].canonical_url,
                headers=headers_for(rows[(1981, 1)]),
            )

        module.download_with_retries(
            rows[(1981, 1)],
            retry_part,
            opener=retry_opener,
            attempts=2,
            sleeper=lambda seconds: None,
        )
        assert retry_calls == [1, 2]
        assert retry_part.read_bytes() == jan
        retry_part.unlink()

        # Response-identity drift is permanent and is not hidden by retrying.
        drift_part = root / (rows[(1981, 1)].name + ".part")
        drift_response_calls: list[int] = []

        def drift_opener(request: object, timeout: float) -> FakeResponse:
            drift_response_calls.append(1)
            headers = headers_for(rows[(1981, 1)])
            headers["ETag"] += "-changed"
            return FakeResponse(
                jan,
                url=rows[(1981, 1)].canonical_url,
                headers=headers,
            )

        try:
            module.download_with_retries(
                rows[(1981, 1)],
                drift_part,
                opener=drift_opener,
                attempts=3,
                sleeper=lambda seconds: None,
            )
        except RuntimeError as error:
            assert "identity drift" in str(error)
        else:
            raise AssertionError("GET identity drift should fail")
        assert drift_response_calls == [1]
        assert not drift_part.exists()

        # Correct byte length and a computed hash are not enough: a changed
        # schema/title must fail before atomic promotion or manifest creation.
        bad_inventory = root / "bad_inventory.csv"
        bad_rows = make_complete_inventory(bad_inventory, {(1981, 1): len(bad)})
        bad_out = root / "bad_schema"

        def bad_download(row: module.inventory.InventoryRow, part: Path) -> None:
            def opener(request: object, timeout: float) -> FakeResponse:
                return FakeResponse(
                    bad, url=row.canonical_url, headers=headers_for(row)
                )

            module.download_to_part(row, part, opener=opener)

        reviewed_test_inventory = module.REVIEWED_INVENTORY_SHA512
        module.REVIEWED_INVENTORY_SHA512 = module.smoke.sha512_file(bad_inventory)
        try:
            try:
                module.run_acquisition(
                    inventory_path=bad_inventory,
                    out_dir=bad_out,
                    reviewed_product_record=license_path,
                    max_new=1,
                    head_fetcher=lambda row: row,
                    downloader=bad_download,
                    now=fixed_now,
                )
            except RuntimeError as error:
                assert "NetCDF validation failed" in str(error)
            else:
                raise AssertionError("changed NetCDF metadata should fail")
        finally:
            module.REVIEWED_INVENTORY_SHA512 = reviewed_test_inventory
        assert not (bad_out / bad_rows[(1981, 1)].name).exists()
        assert not (bad_out / module.MANIFEST_NAME).exists()

        # Incomplete scope is rejected before any output or network callback.
        incomplete = root / "incomplete.csv"
        with inventory_path.open("r", encoding="utf-8", newline="") as source:
            inventory_records = list(csv.DictReader(source))[:-1]
        with incomplete.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=module.inventory.CSV_FIELDS)
            writer.writeheader()
            writer.writerows(inventory_records)
        try:
            module.run_acquisition(
                inventory_path=incomplete,
                out_dir=root / "incomplete_out",
                reviewed_product_record=license_path,
                max_new=0,
                head_fetcher=lambda row: (_ for _ in ()).throw(
                    AssertionError("incomplete inventory must fail before HEAD")
                ),
                downloader=no_download,
                now=fixed_now,
            )
        except RuntimeError as error:
            assert "incomplete" in str(error)
        else:
            raise AssertionError("incomplete 1981--2019 inventory should fail")

        # A modified manifest provenance pin fails before local/network use.
        bad_manifest_out = root / "bad_manifest"
        bad_manifest_out.mkdir()
        bad_record = dict(records[0])
        bad_record["inventory_sha512"] = "0" * 128
        (bad_manifest_out / module.MANIFEST_NAME).write_text(
            json.dumps(bad_record) + "\n", encoding="utf-8"
        )
        try:
            module.run_acquisition(
                inventory_path=inventory_path,
                out_dir=bad_manifest_out,
                reviewed_product_record=license_path,
                max_new=0,
                head_fetcher=lambda row: (_ for _ in ()).throw(
                    AssertionError("bad manifest must fail before HEAD")
                ),
                downloader=no_download,
                now=fixed_now,
            )
        except RuntimeError as error:
            assert "inventory_sha512" in str(error)
        else:
            raise AssertionError("changed manifest inventory pin should fail")
finally:
    module.smoke.EXPECTED_SHAPE = original_shape
    module.REVIEWED_INVENTORY_SHA512 = original_inventory_sha512
    module.REVIEWED_PRODUCT_RECORD_SHA512 = original_product_sha512


# The real reviewed inventory is read-only in this test; assert the exact
# acquisition footprint reported in project documentation.
real_inventory = module.DEFAULT_INVENTORY
if real_inventory.exists():
    real_rows = module.inventory.load_inventory(real_inventory, require_complete=True)
    plan = module.storage_plan(real_rows)
    assert plan["objects"] == 468
    assert plan["content_length_bytes"] == 27_857_685_556

print("nClimGrid-Daily bulk acquisition tests passed")
