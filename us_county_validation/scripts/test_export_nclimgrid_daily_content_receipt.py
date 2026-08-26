#!/usr/bin/env python3
"""Offline adversarial checks for the tracked nClimGrid content receipt."""
from __future__ import annotations

import calendar
import copy
import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import export_nclimgrid_daily_content_receipt as module  # noqa: E402


def expect_runtime(action: Callable[[], object], text: str | None = None) -> None:
    try:
        action()
    except RuntimeError as error:
        if text is not None:
            assert text.lower() in str(error).lower(), (text, str(error))
    else:
        raise AssertionError("expected RuntimeError")


def validation_details(year: int, month: int) -> dict[str, object]:
    days = calendar.monthrange(year, month)[1]
    return {
        "data_variables": sorted(module.acquisition.smoke.EXPECTED_FIELDS),
        "time_coordinate": "time",
        "daily_time_steps": days,
        "start_date": f"{year:04d}-{month:02d}-01",
        "end_date": f"{year:04d}-{month:02d}-{days:02d}",
        "dimensions": {
            "time": days,
            **module.acquisition.smoke.EXPECTED_SHAPE,
        },
        "title": module.acquisition.smoke.EXPECTED_TITLE,
        "product_version": module.acquisition.smoke.EXPECTED_VERSION,
        "embedded_license": "no restrictions",
        "day_label_semantics": (
            "24-hour period ending early morning of specified date"
        ),
    }


def write_source_manifest(path: Path) -> None:
    rows = module.inventory.load_inventory(
        module.DEFAULT_INVENTORY, require_complete=True
    )
    product = module.acquisition.load_reviewed_product_record(
        module.DEFAULT_REVIEWED_PRODUCT
    )
    inventory_digest = module.acquisition.smoke.sha512_file(module.DEFAULT_INVENTORY)
    published = json.loads(module.DEFAULT_RECEIPT.read_text(encoding="utf-8"))
    published_hashes = {
        (int(obj["period"][:4]), int(obj["period"][5:])): obj["local_sha512"]
        for obj in published["objects"]
    }
    assert set(published_hashes) == set(rows)
    start = datetime(2026, 8, 26, 18, 0, tzinfo=UTC)
    records: dict[tuple[int, int], dict[str, object]] = {}
    for index, (key, row) in enumerate(rows.items()):
        status = (
            "adopted_existing_and_validated"
            if index < 19
            else "downloaded_and_validated"
        )
        records[key] = module.acquisition._build_record(
            row,
            inventory_name=module.DEFAULT_INVENTORY.name,
            inventory_sha512=inventory_digest,
            product=product,
            digest=published_hashes[key],
            details=validation_details(*key),
            file_status=status,
            event_time=start + timedelta(seconds=index),
        )
    module.acquisition.write_manifest_atomic(path, records)


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def pin_source_manifest(path: Path) -> None:
    payload = path.read_bytes()
    module.REVIEWED_COMPLETE_MANIFEST_SIZE_BYTES = len(payload)
    module.REVIEWED_COMPLETE_MANIFEST_SHA512 = hashlib.sha512(payload).hexdigest()


with TemporaryDirectory() as temporary:
    root = Path(temporary)
    manifest = root / module.acquisition.MANIFEST_NAME
    receipt_path = root / module.DEFAULT_RECEIPT.name
    write_source_manifest(manifest)
    original_manifest_size = module.REVIEWED_COMPLETE_MANIFEST_SIZE_BYTES
    original_manifest_sha512 = module.REVIEWED_COMPLETE_MANIFEST_SHA512
    pin_source_manifest(manifest)

    receipt = module.build_receipt(manifest_path=manifest)
    rows = module.inventory.load_inventory(
        module.DEFAULT_INVENTORY, require_complete=True
    )
    product = module.acquisition.load_reviewed_product_record(
        module.DEFAULT_REVIEWED_PRODUCT
    )
    assert receipt["scope"] == {
        "start_month": "1981-01",
        "end_month": "2019-12",
        "object_count": 468,
        "content_length_bytes": 27_857_685_556,
    }
    assert receipt["acquisition_validation"][
        "adopted_existing_and_validated_objects"
    ] == 19
    assert receipt["acquisition_validation"][
        "downloaded_and_validated_objects"
    ] == 449
    assert all(value is False for value in receipt["scientific_use_gates"].values())
    assert len({obj["local_sha512"] for obj in receipt["objects"]}) == 468

    # Rebuilding the same source is byte-for-byte deterministic, and the
    # tracked serialization contains neither the temporary absolute path nor
    # credential-like fields.
    rebuilt = module.build_receipt(manifest_path=manifest)
    assert module.serialize_receipt(receipt) == module.serialize_receipt(rebuilt)
    serialized = module.serialize_receipt(receipt).decode("utf-8")
    assert str(root) not in serialized
    assert "/Users/" not in serialized
    for forbidden in ("api_key", "access_token", "authorization", "password"):
        assert forbidden not in serialized.lower()

    module.write_receipt_atomic(receipt_path, receipt)
    assert module.load_receipt(receipt_path, rows=rows, product=product) == receipt
    assert module.check_receipt_against_manifest(
        receipt_path, manifest_path=manifest
    ) == receipt
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    expect_runtime(
        lambda: module.load_receipt(receipt_path, rows=rows, product=product),
        "canonical deterministic serialization",
    )
    module.write_receipt_atomic(receipt_path, receipt)

    # A valid-looking substituted content hash is caught by both the object
    # envelope and comparison to the ignored source manifest.
    tampered_receipt = copy.deepcopy(receipt)
    tampered_receipt["objects"][0]["local_sha512"] = "0" * 128
    expect_runtime(
        lambda: module.validate_receipt(tampered_receipt, rows=rows, product=product),
        "object-record hash envelope",
    )
    forged_receipt = copy.deepcopy(receipt)
    forged_receipt["objects"][0]["local_sha512"] = "0" * 128
    forged_receipt["object_records_sha512"] = module._sha512_bytes(
        module._canonical_json_bytes(forged_receipt["objects"])
    )
    forged_receipt.pop("receipt_payload_sha512")
    forged_receipt["receipt_payload_sha512"] = module._sha512_bytes(
        module._canonical_json_bytes(forged_receipt)
    )
    # Recomputing both internal envelopes cannot bless a substituted object:
    # the reviewed chronological object-record envelope is independently
    # hard-pinned.
    expect_runtime(
        lambda: module.validate_receipt(forged_receipt, rows=rows, product=product),
        "reviewed object identities",
    )
    source_records = [json.loads(line) for line in manifest.read_text().splitlines()]
    source_records[0]["local_sha512"] = "1" * 128
    write_jsonl(manifest, source_records)
    expect_runtime(
        lambda: module.check_receipt_against_manifest(
            receipt_path, manifest_path=manifest
        ),
        "differs",
    )
    write_source_manifest(manifest)

    # Incomplete sources and receipts cannot be normalized into an apparently
    # complete snapshot.
    source_records = [json.loads(line) for line in manifest.read_text().splitlines()]
    write_jsonl(manifest, source_records[:-1])
    pin_source_manifest(manifest)
    expect_runtime(
        lambda: module.build_receipt(manifest_path=manifest),
        "complete 468-object scope",
    )
    write_source_manifest(manifest)
    pin_source_manifest(manifest)
    incomplete_receipt = copy.deepcopy(receipt)
    incomplete_receipt["objects"].pop()
    expect_runtime(
        lambda: module.validate_receipt(incomplete_receipt, rows=rows, product=product),
        "objects are incomplete",
    )

    # Chronological order is part of both the ignored-manifest and tracked
    # receipt contracts; swapping otherwise-valid records fails closed.
    source_records = [json.loads(line) for line in manifest.read_text().splitlines()]
    source_records[0], source_records[1] = source_records[1], source_records[0]
    write_jsonl(manifest, source_records)
    pin_source_manifest(manifest)
    expect_runtime(
        lambda: module.build_receipt(manifest_path=manifest),
        "chronological order",
    )
    write_source_manifest(manifest)
    pin_source_manifest(manifest)
    reordered_receipt = copy.deepcopy(receipt)
    reordered_receipt["objects"][0], reordered_receipt["objects"][1] = (
        reordered_receipt["objects"][1],
        reordered_receipt["objects"][0],
    )
    expect_runtime(
        lambda: module.validate_receipt(reordered_receipt, rows=rows, product=product),
        "differs from the frozen inventory/calendar",
    )

    # A source NetCDF-schema alteration is rejected before export; a tracked
    # schema alteration is rejected independently of the payload envelope.
    source_records = [json.loads(line) for line in manifest.read_text().splitlines()]
    source_records[0]["netcdf_validation"]["title"] = "tampered title"
    write_jsonl(manifest, source_records)
    pin_source_manifest(manifest)
    expect_runtime(
        lambda: module.build_receipt(manifest_path=manifest),
        "schema/calendar",
    )
    write_source_manifest(manifest)
    pin_source_manifest(manifest)
    bad_schema_receipt = copy.deepcopy(receipt)
    bad_schema_receipt["netcdf_schema"]["title"] = "tampered title"
    expect_runtime(
        lambda: module.validate_receipt(bad_schema_receipt, rows=rows, product=product),
        "NetCDF schema changed",
    )

    # Structural additions and any attempt to open a scientific-use gate are
    # rejected rather than ignored.
    extra_field_receipt = copy.deepcopy(receipt)
    extra_field_receipt["machine_path"] = "/Users/example/raw"
    expect_runtime(
        lambda: module.validate_receipt(extra_field_receipt, rows=rows, product=product),
        "fields differ",
    )
    open_gate_receipt = copy.deepcopy(receipt)
    open_gate_receipt["scientific_use_gates"]["causal_claim_authorized"] = True
    expect_runtime(
        lambda: module.validate_receipt(open_gate_receipt, rows=rows, product=product),
        "scientific-use gate",
    )

    module.REVIEWED_COMPLETE_MANIFEST_SIZE_BYTES = original_manifest_size
    module.REVIEWED_COMPLETE_MANIFEST_SHA512 = original_manifest_sha512

print("nClimGrid-Daily content receipt tests passed")
