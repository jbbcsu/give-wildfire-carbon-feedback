#!/usr/bin/env python3
"""Acquire pinned FAOSTAT maize/soy gross-production-value query results.

The FAO catalog exposes a parameterized BigQuery-backed CSV endpoint.  This
script downloads only item 56 (maize) and item 236 (soya beans), verifies the
exact responses acquired for this project, validates schema and key integrity,
and writes a deterministic combined table plus an ignored audit.  It does not
spatially allocate national values or authorize welfare/SCC aggregation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
import shutil
from typing import BinaryIO, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


LANDING_PAGE = "https://data.fao.org/catalog/dataset/b1a04191-c86f-4972-a9d7-28b23568deba"
SQL_URL = (
    "https://data.apps.fao.org/catalog/dataset/"
    "bba7a5e2-1c92-4ba2-809f-e28cc7417abe/resource/"
    "63b1963d-d65c-4867-87c2-b4f513083cba/download/"
    "agricultural-production-value-qv-query.sql"
)
API_URL = "https://api.data.apps.fao.org/api/v2/bigquery"
CATALOG_REVISION = "2025-01-31"
CATALOG_TEMPORAL_END = "2024-12-31"
BASELINE_YEARS = (1999, 2000, 2001)

ITEMS = {
    56: {
        "slug": "maize",
        "label": "Maize (corn)",
        "filename": "qv_56_maize_retrieved_2026-08-26.csv",
        "size_bytes": 1_212_971,
        "sha512": (
            "82cde2ffb0e6063f729a7c962d873c2990c20d16f96e9ca2db3a47a3da043112"
            "d11ecec02f509f17ea2be4c3e55e2e3ad0afb8e0a25f7caf8b6227d0a2a2955c"
        ),
    },
    236: {
        "slug": "soybeans",
        "label": "Soya beans",
        "filename": "qv_236_soybeans_retrieved_2026-08-26.csv",
        "size_bytes": 630_134,
        "sha512": (
            "452d348b62233095fb8b0de1f65c9778440be1b0c315f3dd2ab44a5da6e35db8"
            "e71e9bc1d423d83a6d8d25d32404311ecc65d1e0445943b76e356d86eb53d1a8"
        ),
    },
}

REQUIRED_COLUMNS = (
    "faostat",
    "m49_code",
    "country_name_en",
    "item_code",
    "item",
    "year",
    "gross_production_value_constant_20142016_1000_slc_slc",
    "gross_production_value_constant_20142016_1000_slc_slc_flag",
    "gross_production_value_current_1000_slc_slc",
    "gross_production_value_current_1000_slc_slc_flag",
    "gross_production_value_current_1000_us_usd",
    "gross_production_value_current_1000_us_usd_flag",
    "gross_production_value_constant_20142016_1000_us_usd",
    "gross_production_value_constant_20142016_1000_us_usd_flag",
    "gross_production_value_constant_20142016_1000_i_index",
    "gross_production_value_constant_20142016_1000_i_index_flag",
)
CONSTANT_USD = "gross_production_value_constant_20142016_1000_us_usd"
CONSTANT_USD_FLAG = CONSTANT_USD + "_flag"
CURRENT_USD = "gross_production_value_current_1000_us_usd"
CURRENT_USD_FLAG = CURRENT_USD + "_flag"


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def query_url(item_code: int) -> str:
    return API_URL + "?" + urlencode({"sql_url": SQL_URL, "item_code": str(item_code)})


def verify_file(path: Path, definition: dict[str, object]) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"Missing FAOSTAT response: {path}")
    expected_size = int(definition["size_bytes"])
    if path.stat().st_size != expected_size:
        raise ValueError(
            f"FAOSTAT response byte length differs for {path.name}: "
            f"{path.stat().st_size} != {expected_size}"
        )
    digest = sha512(path)
    if digest != definition["sha512"]:
        raise ValueError(f"FAOSTAT response SHA-512 differs for {path.name}")
    return {"size_bytes": expected_size, "sha512": digest}


def download(
    url: str,
    destination: Path,
    definition: dict[str, object],
    opener: Callable[..., BinaryIO] = urlopen,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    partial.unlink(missing_ok=True)
    request = Request(url, headers={"User-Agent": "GIVE-precipitation-SCC/1.0"})
    try:
        with opener(request, timeout=600) as response, partial.open("wb") as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
        verify_file(partial, definition)
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def parse_optional_nonnegative(value: str, field: str, row_number: int) -> float | None:
    if value == "":
        return None
    try:
        result = float(value)
    except ValueError as error:
        raise ValueError(f"Invalid {field} at row {row_number}") from error
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"Non-finite or negative {field} at row {row_number}")
    return result


def validate_response(path: Path, item_code: int) -> tuple[list[dict[str, str]], dict[str, object]]:
    definition = ITEMS[item_code]
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(REQUIRED_COLUMNS):
            raise ValueError(f"FAOSTAT schema differs for item {item_code}: {reader.fieldnames}")
        rows: list[dict[str, str]] = []
        keys: set[tuple[str, str, str]] = set()
        flags = {CONSTANT_USD_FLAG: {}, CURRENT_USD_FLAG: {}}
        for row_number, row in enumerate(reader, start=2):
            if row["item_code"] != str(item_code) or row["item"] != definition["label"]:
                raise ValueError(f"FAOSTAT item identity differs at row {row_number}")
            try:
                m49 = int(row["m49_code"])
                year = int(row["year"])
                int(row["faostat"])
            except ValueError as error:
                raise ValueError(f"Invalid FAOSTAT identifier/year at row {row_number}") from error
            if not (0 <= m49 <= 999) or not (1961 <= year <= 2024):
                raise ValueError(f"FAOSTAT identifier/year outside pinned range at row {row_number}")
            key = (row["m49_code"], row["item_code"], row["year"])
            if key in keys:
                raise ValueError(f"Duplicate FAOSTAT M49-item-year key: {key}")
            keys.add(key)
            for field in (
                CONSTANT_USD,
                CURRENT_USD,
                "gross_production_value_constant_20142016_1000_slc_slc",
                "gross_production_value_current_1000_slc_slc",
                "gross_production_value_constant_20142016_1000_i_index",
            ):
                parse_optional_nonnegative(row[field], field, row_number)
            for field in flags:
                label = row[field] or "<blank>"
                flags[field][label] = flags[field].get(label, 0) + 1
            rows.append(row)
    if not rows:
        raise ValueError(f"FAOSTAT response for item {item_code} is empty")
    years = [int(row["year"]) for row in rows]
    if min(years) != 1961 or max(years) != 2024:
        raise ValueError(f"FAOSTAT temporal coverage differs for item {item_code}")
    baseline = [row for row in rows if int(row["year"]) in BASELINE_YEARS]
    baseline_constant = [row for row in baseline if row[CONSTANT_USD] != ""]
    baseline_current = [row for row in baseline if row[CURRENT_USD] != ""]
    summary = {
        "rows": len(rows),
        "countries": len({row["m49_code"] for row in rows}),
        "year_min": min(years),
        "year_max": max(years),
        "constant_usd_nonmissing_rows": sum(row[CONSTANT_USD] != "" for row in rows),
        "current_usd_nonmissing_rows": sum(row[CURRENT_USD] != "" for row in rows),
        "baseline_1999_2001_rows": len(baseline),
        "baseline_1999_2001_constant_usd_nonmissing_rows": len(baseline_constant),
        "baseline_1999_2001_constant_usd_countries": len(
            {row["m49_code"] for row in baseline_constant}
        ),
        "baseline_1999_2001_current_usd_nonmissing_rows": len(baseline_current),
        "baseline_1999_2001_current_usd_countries": len(
            {row["m49_code"] for row in baseline_current}
        ),
        "flags": flags,
    }
    return rows, summary


def write_canonical(rows: list[dict[str, str]], output_path: Path) -> dict[str, object]:
    rows = sorted(
        rows,
        key=lambda row: (
            int(row["item_code"]),
            int(row["m49_code"]),
            int(row["year"]),
            int(row["faostat"]),
        ),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial = output_path.with_suffix(output_path.suffix + ".partial")
    partial.unlink(missing_ok=True)
    try:
        with partial.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=REQUIRED_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        partial.replace(output_path)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return {
        "rows": len(rows),
        "path": str(output_path),
        "size_bytes": output_path.stat().st_size,
        "sha512": sha512(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="data/raw/faostat_qv")
    parser.add_argument(
        "--out", default="data/interim/welfare_weights/faostat_qv_maize_soy.csv"
    )
    parser.add_argument(
        "--audit",
        default="data/interim/welfare_weights/faostat_qv_maize_soy.audit.json",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, str]] = []
    item_audits: dict[str, object] = {}
    for item_code, definition in ITEMS.items():
        path = raw_dir / str(definition["filename"])
        status = "existing"
        if not path.exists():
            download(query_url(item_code), path, definition)
            status = "downloaded"
        identity = verify_file(path, definition)
        rows, validation = validate_response(path, item_code)
        all_rows.extend(rows)
        item_audits[str(item_code)] = {
            "item": definition["label"],
            "query_url": query_url(item_code),
            "raw_path": str(path),
            "status": status,
            **identity,
            **validation,
        }
    combined = write_canonical(all_rows, Path(args.out))
    audit = {
        "schema_version": 1,
        "retrieved_or_verified_utc": datetime.now(UTC).isoformat(),
        "dataset": "FAOSTAT Value of agricultural production (Global, National - Annual)",
        "landing_page": LANDING_PAGE,
        "catalog_revision": CATALOG_REVISION,
        "catalog_temporal_end": CATALOG_TEMPORAL_END,
        "license": "CC-BY-4.0",
        "items": item_audits,
        "combined": combined,
        "baseline_weight_candidate": "country-crop mean of 1999-2001 constant-2014-2016 thousand USD, with flags retained",
        "unresolved_crosswalk": "FAOSTAT M49 to MapSPAM stat_code/ISO3; no national value is allocated until audited",
        "role": "candidate national crop-value totals; not spatial weights, response, damage, or SCC",
    }
    audit_path = Path(args.audit)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
