#!/usr/bin/env python3
"""Validate and hash named parameters for future daily climate pairs.

Only synthetic or future parameter metadata is accepted. This module does not
fit parameters, implement a generator, or establish scientific validity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

from validate_climate_daily_parameter_bundle_contract import (
    PARAMETER_FIELDS,
    PARAMETER_KEY,
    POSITIVE_FIELDS,
    PROBABILITY_FIELDS,
    SHA256_FIELDS,
    TOP_LEVEL_FIELDS,
    validate as validate_contract,
)


BUNDLE_SCHEMA = "climate_daily_parameter_bundle_v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def parameter_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(record[field] for field in PARAMETER_KEY)


def canonical_parameter_bundle_sha256(bundle: dict[str, Any]) -> str:
    """Hash every field after sorting parameter records by their exact key."""
    canonical = {field: bundle[field] for field in TOP_LEVEL_FIELDS if field != "records"}
    canonical["records"] = sorted(bundle["records"], key=parameter_key)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_parameter_bundle(
    parameter_bundle: dict[str, Any],
    output_bundle: dict[str, Any],
    config_path: Path,
    root: Path,
) -> dict[str, Any]:
    validate_contract(config_path, root)
    require(isinstance(parameter_bundle, dict), "parameter bundle must be an object")
    require(set(parameter_bundle) == set(TOP_LEVEL_FIELDS), "parameter bundle must contain exact top-level fields")
    require(parameter_bundle["schema"] == BUNDLE_SCHEMA, "parameter bundle schema changed")
    require(parameter_bundle["generator_id"] == "kemsley_markov_gamma", "parameter bundle generator changed")
    require(parameter_bundle["paper_doi"] == "10.1002/joc.8320", "parameter bundle paper DOI changed")
    for field in ("generator_code_identity", "parameterization_id"):
        require(isinstance(parameter_bundle[field], str) and parameter_bundle[field].strip(), f"blank parameter bundle field: {field}")

    records = parameter_bundle["records"]
    require(isinstance(records, list) and records, "parameter records must be a nonempty list")
    keys: set[tuple[Any, ...]] = set()
    records_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == set(PARAMETER_FIELDS), f"parameter record {index} must contain exact fields")
        for field in ("climate_draw_id", "esm_id", "member_id", "grid_id", "calendar"):
            require(isinstance(record[field], str) and record[field].strip(), f"parameter record {index} has blank identity: {field}")
        require(isinstance(record["year"], int) and not isinstance(record["year"], bool), f"parameter record {index} year is invalid")
        require(isinstance(record["month"], int) and not isinstance(record["month"], bool) and 1 <= record["month"] <= 12, f"parameter record {index} month is invalid")
        require(finite_number(record["pulse_scale_tonnes_c"]) and float(record["pulse_scale_tonnes_c"]) >= 0, f"parameter record {index} pulse scale is invalid")
        require(record["path_role"] in {"baseline", "pulse"}, f"parameter record {index} path role is invalid")
        require(record["support_flag"] in {"within", "below", "above"}, f"parameter record {index} support flag is invalid")
        for field in PROBABILITY_FIELDS:
            require(finite_number(record[field]) and 0 <= float(record[field]) <= 1, f"parameter record {index} probability is invalid: {field}")
        for field in POSITIVE_FIELDS:
            require(finite_number(record[field]) and float(record[field]) > 0, f"parameter record {index} positive value is invalid: {field}")
        for field in SHA256_FIELDS:
            require(isinstance(record[field], str) and HEX64.fullmatch(record[field]) is not None, f"parameter record {index} SHA-256 is invalid: {field}")
        key = parameter_key(record)
        require(key not in keys, "duplicate parameter record key")
        keys.add(key)
        records_by_key[key] = record

    require(isinstance(output_bundle, dict), "output bundle must be an object")
    receipt = output_bundle.get("receipt")
    output_records = output_bundle.get("records")
    require(isinstance(receipt, dict), "output receipt must be an object")
    require(isinstance(output_records, list) and output_records, "output records must be a nonempty list")
    output_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, record in enumerate(output_records):
        require(isinstance(record, dict), f"output record {index} must be an object")
        try:
            key = parameter_key(record)
        except KeyError as error:
            raise ValueError(f"output record {index} lacks parameter-linkage key") from error
        require(key not in output_by_key, "duplicate output record key during parameter linkage")
        output_by_key[key] = record
    require(set(records_by_key) == set(output_by_key), "parameter and output record keys do not match exactly")

    try:
        observed_hash = canonical_parameter_bundle_sha256(parameter_bundle)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("parameter bundle cannot be canonicalized as finite JSON") from error
    require(receipt.get("parameter_bundle_sha256") == observed_hash, "output receipt parameter bundle hash does not match canonical bundle")
    require(receipt.get("generator_code_identity") == parameter_bundle["generator_code_identity"], "generator code identity differs between parameter and output bundles")
    for key, output_record in output_by_key.items():
        parameter_record = records_by_key[key]
        require(output_record.get("parameter_bundle_sha256") == observed_hash, "output monthly record parameter bundle hash does not match canonical bundle")
        require(output_record.get("support_flag") == parameter_record["support_flag"], "parameter and output support flags differ")

    return {
        "schema": "climate_daily_parameter_bundle_validation_v1",
        "status": "canonical_named_parameter_bundle_checks_passed_synthetic_or_future_only",
        "parameter_record_count": len(records),
        "parameter_bundle_sha256": observed_hash,
        "generator_implementation_authorized": False,
        "scientific_validity_established": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parameter_bundle", type=Path)
    parser.add_argument("output_bundle", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/climate_daily_parameter_bundle_v1.toml"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    parameter_bundle = json.loads(args.parameter_bundle.read_text(encoding="utf-8"))
    output_bundle = json.loads(args.output_bundle.read_text(encoding="utf-8"))
    result = validate_parameter_bundle(parameter_bundle, output_bundle, args.config.resolve(), args.root.resolve())
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
