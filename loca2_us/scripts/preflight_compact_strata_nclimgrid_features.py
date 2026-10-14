#!/usr/bin/env python3
"""Audit local-only inputs for the compact-strata nClimGrid feature build.

This script performs no network operation and writes no raw data.  It derives
the exact gridded monthly objects required by the preregistered county seasons,
binds their reviewed identities, verifies selected weight hashes, and fails
closed when any local object is absent, partial, the wrong size, or the wrong
SHA-512.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import resource
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PREREGISTRATION = ROOT / "loca2_us/data/provenance/loca2_compact_strata_expansion_preregistration_20261013.json"
DEFAULT_INVENTORY = ROOT / "data/provenance/nclimgrid_daily_1981_2019_http_inventory.csv"
DEFAULT_CONTENT_RECEIPT = ROOT / "data/provenance/nclimgrid_daily_1981_2019_content_receipt.json"
DEFAULT_EVICTION_RECEIPT = ROOT / "data/provenance/nclimgrid_gridded_raw_eviction_20260921.json"
DEFAULT_RAW_DIR = ROOT / "data/raw/us_county/nclimgrid_daily"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def sha512(path: Path) -> str:
    value = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def month_keys_for_season(year: int, start_month_day: str, end_month_day: str) -> list[tuple[int, int]]:
    start_month, start_day = map(int, start_month_day.split("-"))
    end_month, end_day = map(int, end_month_day.split("-"))
    start = date(year, start_month, start_day)
    end_year = year if (end_month, end_day) >= (start_month, start_day) else year + 1
    end = date(end_year, end_month, end_day)
    result = []
    cursor_year, cursor_month = start.year, start.month
    while (cursor_year, cursor_month) <= (end.year, end.month):
        result.append((cursor_year, cursor_month))
        if cursor_month == 12:
            cursor_year, cursor_month = cursor_year + 1, 1
        else:
            cursor_month += 1
    return result


def derive_required_keys(preregistration: dict) -> tuple[list[tuple[int, int]], dict[str, list[tuple[int, int]]]]:
    years = [int(value) for value in preregistration["support"]["years"]]
    require(years == list(range(2001, 2013)), "preregistered years changed")
    selected = preregistration["selected"]
    require([row["county_geoid"] for row in selected] == ["06095", "13131", "18145"], "selected counties changed")
    by_county: dict[str, list[tuple[int, int]]] = {}
    union: set[tuple[int, int]] = set()
    for row in selected:
        keys = sorted({
            key
            for year in years
            for key in month_keys_for_season(year, row["primary_start_month_day"], row["primary_end_month_day"])
        })
        by_county[row["county_geoid"]] = keys
        union.update(keys)
    return sorted(union), by_county


def read_inventory(path: Path) -> dict[tuple[int, int], dict]:
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == 468, "reviewed HTTP inventory is not the exact 1981-2019 monthly scope")
    result = {}
    for row in rows:
        key = (int(row["year"]), int(row["month"]))
        require(key not in result, f"duplicate inventory month: {key}")
        result[key] = {
            "period": f"{key[0]:04d}-{key[1]:02d}",
            "name": row["name"],
            "canonical_url": row["canonical_url"],
            "content_length": int(row["content_length"]),
            "etag": row["etag"],
            "last_modified": row["last_modified"],
            "content_type": row["content_type"],
        }
    return result


def bind_content_identities(inventory: dict[tuple[int, int], dict], content_receipt: dict) -> dict[tuple[int, int], dict]:
    objects = content_receipt.get("objects")
    require(isinstance(objects, list) and len(objects) == 468, "content receipt object scope changed")
    by_period = {str(item["period"]): item for item in objects}
    require(len(by_period) == 468, "content receipt duplicates periods")
    result = {}
    for key, inventory_item in inventory.items():
        item = by_period[inventory_item["period"]]
        http = item["http_identity"]
        require(item["name"] == inventory_item["name"], f"content name differs: {key}")
        require(item["canonical_url"] == inventory_item["canonical_url"], f"content URL differs: {key}")
        require(int(http["content_length"]) == inventory_item["content_length"], f"content length differs: {key}")
        require(http["etag"] == inventory_item["etag"], f"content ETag differs: {key}")
        require(http["last_modified"] == inventory_item["last_modified"], f"content timestamp differs: {key}")
        result[key] = {**inventory_item, "expected_local_sha512": str(item["local_sha512"])}
    return result


def classify_local_objects(required: list[dict], raw_dir: Path) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    valid, missing, partial, invalid = [], [], [], []
    for item in required:
        path = raw_dir / item["name"]
        part = raw_dir / f"{item['name']}.part"
        if part.exists():
            partial.append({"period": item["period"], "path": str(part)})
            continue
        if not path.is_file() or path.is_symlink():
            missing.append({"period": item["period"], "name": item["name"], "content_length": item["content_length"]})
            continue
        actual_bytes = path.stat().st_size
        if actual_bytes != item["content_length"]:
            invalid.append({"period": item["period"], "reason": "size", "expected": item["content_length"], "actual": actual_bytes})
            continue
        actual_sha512 = sha512(path)
        if actual_sha512 != item["expected_local_sha512"]:
            invalid.append({"period": item["period"], "reason": "sha512", "expected": item["expected_local_sha512"], "actual": actual_sha512})
            continue
        valid.append({"period": item["period"], "path": str(path), "bytes": actual_bytes, "sha512": actual_sha512})
    return valid, missing, partial, invalid


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregistration", type=Path, default=DEFAULT_PREREGISTRATION)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--content-receipt", type=Path, default=DEFAULT_CONTENT_RECEIPT)
    parser.add_argument("--eviction-receipt", type=Path, default=DEFAULT_EVICTION_RECEIPT)
    parser.add_argument("--raw-weather-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {name: resolve(value) for name, value in {
        "preregistration": args.preregistration,
        "inventory": args.inventory,
        "content_receipt": args.content_receipt,
        "eviction_receipt": args.eviction_receipt,
        "raw_weather_dir": args.raw_weather_dir,
        "output": args.output,
    }.items()}
    require(not paths["output"].exists(), "fresh output required")

    preregistration = json.loads(paths["preregistration"].read_text())
    require(preregistration["status"] == "compact_outcome_blind_county_design_selected_execution_deferred", "preregistration status changed")
    require(preregistration["input_access_contract"]["yield_magnitudes_read"] is False, "preregistration read yields")
    require(preregistration["input_access_contract"]["nclimgrid_climate_values_read"] is False, "preregistration read climate values")
    config_path = ROOT / preregistration["config"]["path"]
    require(sha256(config_path) == preregistration["config"]["sha256"], "preregistration config changed")
    for geoid, item in preregistration["selected_nclimgrid_weight_readiness"].items():
        require(sha256(ROOT / item["receipt_path"]) == item["receipt_sha256"], f"weight receipt changed: {geoid}")
        require(sha256(ROOT / item["output_path"]) == item["output_sha256"], f"weight output changed: {geoid}")

    eviction = json.loads(paths["eviction_receipt"].read_text())
    require(eviction["status"] == "planned_then_verified_recoverable_raw_eviction", "raw eviction record changed")
    require(eviction["recoverability"]["reacquisition_required_for_full_grid_reanalysis"] is True, "eviction no longer records reacquisition")
    inventory = read_inventory(paths["inventory"])
    content_receipt = json.loads(paths["content_receipt"].read_text())
    identities = bind_content_identities(inventory, content_receipt)
    keys, keys_by_county = derive_required_keys(preregistration)
    require(len(keys) == 84, f"required month scope changed: {len(keys)}")
    required = [identities[key] for key in keys]
    required_bytes = sum(item["content_length"] for item in required)
    require(required_bytes == 4_909_747_416, f"required byte scope changed: {required_bytes}")
    valid, missing, partial, invalid = classify_local_objects(required, paths["raw_weather_dir"])
    ready = len(valid) == len(required) and not missing and not partial and not invalid

    selected_weight_bindings = preregistration["selected_nclimgrid_weight_readiness"]
    result = {
        "schema": "loca2_us_compact_strata_nclimgrid_local_availability/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_outcome_free_feature_construction" if ready else "blocked_missing_resident_gridded_weather",
        "network_operations_performed": False,
        "raw_data_written_or_modified": False,
        "reacquisition_authorized": False,
        "reacquisition_deferred_until_spei_transfer_complete": True,
        "preregistration": {"path": str(paths["preregistration"].relative_to(ROOT)), "sha256": sha256(paths["preregistration"])},
        "config": preregistration["config"],
        "selected_counties": [row["county_geoid"] for row in preregistration["selected"]],
        "selected_weight_bindings": selected_weight_bindings,
        "season_months_by_county": {
            geoid: [f"{year:04d}-{month:02d}" for year, month in county_keys]
            for geoid, county_keys in keys_by_county.items()
        },
        "required_objects": required,
        "required_object_manifest_sha256": canonical_sha256(required),
        "required_object_count": len(required),
        "required_bytes": required_bytes,
        "required_gib": required_bytes / 1024**3,
        "local_availability": {
            "raw_weather_dir": str(paths["raw_weather_dir"].relative_to(ROOT)),
            "valid_object_count": len(valid),
            "missing_object_count": len(missing),
            "partial_object_count": len(partial),
            "invalid_object_count": len(invalid),
            "valid": valid, "missing": missing, "partial": partial, "invalid": invalid,
        },
        "source_bindings": {
            "inventory": {"path": str(paths["inventory"].relative_to(ROOT)), "bytes": paths["inventory"].stat().st_size, "sha256": sha256(paths["inventory"])},
            "content_receipt": {"path": str(paths["content_receipt"].relative_to(ROOT)), "bytes": paths["content_receipt"].stat().st_size, "sha256": sha256(paths["content_receipt"])},
            "eviction_receipt": {"path": str(paths["eviction_receipt"].relative_to(ROOT)), "bytes": paths["eviction_receipt"].stat().st_size, "sha256": sha256(paths["eviction_receipt"])},
        },
        "substitution_gate": {
            "resident_noaa_county_average_csvs_authorized": False,
            "reason": "County-average daily series bypass the selected hash-bound grid-cell weights and change the order of nonlinear CDD/Rx1day/Rx5day construction relative to the registered cell-first basis.",
        },
        "feature_build_gate": {
            "open": ready,
            "require_all_84_objects_validated_before_any_year": True,
            "existing_all_practice_builder_authorized_for_this_task": False,
            "existing_builder_reason": "The existing national builder reads and emits outcome magnitudes; this task requires a dedicated outcome-free support adapter before construction.",
            "next_when_transfer_complete": "Reacquire only the exact 84 manifest-bound objects, validate them against reviewed SHA-512 identities, then run a dedicated outcome-free three-county adapter sequentially by harvest year under 512 MiB.",
        },
        "resources": {"peak_rss_bytes": peak_rss_bytes(), "memory_cap_bytes": 512 * 1024**2, "memory_gate_passed": peak_rss_bytes() <= 512 * 1024**2},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256(Path(__file__).resolve())},
        "claim_gates": {
            "local_input_availability_audited": True,
            "observed_climate_features": False,
            "historical_climate_sentinels": False,
            "representative_multi_county_validation": False,
            "model_skill": False,
            "outcome_response": False,
            "causal_damage": False,
            "SCC": False,
        },
    }
    paths["output"].parent.mkdir(parents=True, exist_ok=True)
    paths["output"].write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["status"], "required_object_count": len(required),
        "required_bytes": required_bytes, "valid": len(valid), "missing": len(missing),
        "partial": len(partial), "invalid": len(invalid), "peak_rss_bytes": result["resources"]["peak_rss_bytes"],
    }, indent=2))


if __name__ == "__main__":
    main()
