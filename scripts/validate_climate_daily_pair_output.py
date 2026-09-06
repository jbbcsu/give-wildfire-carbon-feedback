#!/usr/bin/env python3
"""Fail-closed schema checks for future matched daily precipitation outputs.

This module validates structure and exact numerical identities only. It does
not implement a daily generator or establish climate, response, or SCC validity.
"""
from __future__ import annotations

import argparse
import calendar as gregorian_calendar
from collections import defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import tomllib
from typing import Any

from validate_climate_daily_pair_output_schema_contract import (
    MONTHLY_INPUT_FIELDS,
    validate as validate_contract,
)


BUNDLE_SCHEMA = "climate_daily_pair_output_bundle_v1"
TOP_LEVEL_FIELDS = {"schema", "receipt", "records"}
RECEIPT_FIELDS = {
    "contract_sha256", "generator_code_identity", "paper_doi", "parameter_bundle_sha256",
    "monthly_input_sha256", "rng_algorithm", "rng_version", "seed_namespace",
    "daily_output_sha256", "maximum_monthly_mass_error_mm", "peak_resident_memory_bytes",
}
MONTHLY_FIELDS = {
    "climate_draw_id", "esm_id", "member_id", "grid_id", "calendar", "year", "month",
    "pulse_scale_tonnes_c", "path_role", "first_divergence_date_or_model_day",
    "monthly_precipitation_mm", "monthly_temperature_degc", "parameter_bundle_sha256",
    "monthly_innovation_digest", "support_flag", "daily",
}
DAILY_FIELDS = {"date_or_model_day", "precipitation_mm"}
MONTHLY_KEY = [
    "climate_draw_id", "esm_id", "member_id", "grid_id", "calendar", "year", "month",
    "pulse_scale_tonnes_c", "path_role",
]
PAIR_KEY = MONTHLY_KEY[:-1]
CROSS_PULSE_KEY = MONTHLY_KEY[:7]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DAY_KEY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def canonical_records_sha256(records: list[dict[str, Any]]) -> str:
    payload = json.dumps(records, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_monthly_inputs_sha256(records: list[dict[str, Any]]) -> str:
    """Hash monthly identities, targets, parameters, and support without daily outputs."""
    projected = [{field: record[field] for field in MONTHLY_INPUT_FIELDS} for record in records]
    projected.sort(key=lambda record: tuple(record[field] for field in MONTHLY_KEY))
    payload = json.dumps(projected, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _parse_day_key(value: Any, calendar_name: str) -> tuple[int, int, int]:
    require(isinstance(value, str), "date_or_model_day must be a YYYY-MM-DD string")
    match = DAY_KEY.fullmatch(value)
    require(match is not None, "date_or_model_day must be a YYYY-MM-DD string")
    year, month, day_number = (int(part) for part in match.groups())
    require(1 <= month <= 12 and 1 <= day_number <= 31, "date_or_model_day is outside basic bounds")
    if calendar_name in {"gregorian", "proleptic_gregorian", "standard"}:
        try:
            date(year, month, day_number)
        except ValueError as error:
            raise ValueError("date_or_model_day is invalid for Gregorian calendar") from error
    else:
        require(day_number <= _days_in_month(calendar_name, year, month), "date_or_model_day is invalid for model calendar")
    return year, month, day_number


def _days_in_month(calendar_name: str, year: int, month: int) -> int:
    if calendar_name in {"gregorian", "proleptic_gregorian", "standard"}:
        return gregorian_calendar.monthrange(year, month)[1]
    if calendar_name in {"noleap", "365_day"}:
        return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if calendar_name in {"all_leap", "366_day"}:
        return [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if calendar_name == "360_day":
        return 30
    raise ValueError(f"unsupported calendar: {calendar_name}")


def _expected_day_keys(calendar_name: str, year: int, month: int) -> list[str]:
    return [f"{year:04d}-{month:02d}-{day_number:02d}" for day_number in range(1, _days_in_month(calendar_name, year, month) + 1)]


def _nonblank(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _tuple(record: dict[str, Any], fields: list[str]) -> tuple[Any, ...]:
    return tuple(record[field] for field in fields)


def validate_bundle(bundle: dict[str, Any], config_path: Path, root: Path) -> dict[str, Any]:
    validate_contract(config_path, root)
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(isinstance(bundle, dict), "bundle must be an object")
    require(set(bundle) == TOP_LEVEL_FIELDS, "bundle must contain exact top-level fields")
    require(bundle.get("schema") == BUNDLE_SCHEMA, "bundle schema changed")

    receipt = bundle.get("receipt")
    require(isinstance(receipt, dict) and set(receipt) == RECEIPT_FIELDS, "receipt must contain exact required fields")
    for field in RECEIPT_FIELDS:
        require(_nonblank(receipt[field]), f"receipt field is blank: {field}")
    require(receipt["contract_sha256"] == config["parent_interface_sha256"], "receipt contract hash does not match parent interface")
    require(receipt["paper_doi"] == "10.1002/joc.8320", "receipt paper DOI changed")
    for field in ("contract_sha256", "parameter_bundle_sha256", "monthly_input_sha256", "daily_output_sha256"):
        require(isinstance(receipt[field], str) and HEX64.fullmatch(receipt[field]) is not None, f"receipt field is not a SHA-256: {field}")
    peak = receipt["peak_resident_memory_bytes"]
    require(isinstance(peak, int) and not isinstance(peak, bool) and peak > 0, "peak resident memory must be a positive integer")
    require(peak <= config["resources"]["maximum_peak_resident_memory_bytes"], "peak resident memory exceeds interface ceiling")
    recorded_error = receipt["maximum_monthly_mass_error_mm"]
    require(finite_number(recorded_error) and float(recorded_error) >= 0, "maximum monthly mass error is invalid")

    records = bundle.get("records")
    require(isinstance(records, list) and records, "records must be a nonempty list")
    try:
        observed_output_hash = canonical_records_sha256(records)
    except (TypeError, ValueError) as error:
        raise ValueError("records cannot be canonicalized as finite JSON") from error
    require(receipt["daily_output_sha256"] == observed_output_hash, "daily output hash does not match canonical records")

    record_keys: set[tuple[Any, ...]] = set()
    pair_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    cross_pulse_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    maximum_error = 0.0
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == MONTHLY_FIELDS, f"record {index} must contain exact monthly fields")
        for field in ("climate_draw_id", "esm_id", "member_id", "grid_id", "calendar"):
            require(isinstance(record[field], str) and record[field].strip(), f"record {index} has blank identity field: {field}")
        require(isinstance(record["year"], int) and not isinstance(record["year"], bool), f"record {index} year is invalid")
        require(isinstance(record["month"], int) and not isinstance(record["month"], bool) and 1 <= record["month"] <= 12, f"record {index} month is invalid")
        for field in ("pulse_scale_tonnes_c", "monthly_precipitation_mm", "monthly_temperature_degc"):
            require(finite_number(record[field]), f"record {index} has nonfinite numeric field: {field}")
        require(float(record["pulse_scale_tonnes_c"]) >= 0, f"record {index} has negative pulse scale")
        require(float(record["monthly_precipitation_mm"]) >= 0, f"record {index} has negative monthly precipitation")
        require(record["path_role"] in {"baseline", "pulse"}, f"record {index} has invalid path role")
        require(record["support_flag"] in {"within", "below", "above"}, f"record {index} has invalid support flag")
        require(record["parameter_bundle_sha256"] == receipt["parameter_bundle_sha256"], f"record {index} parameter bundle does not match receipt")
        require(isinstance(record["monthly_innovation_digest"], str) and HEX64.fullmatch(record["monthly_innovation_digest"]) is not None, f"record {index} innovation digest is invalid")
        divergence = _parse_day_key(record["first_divergence_date_or_model_day"], record["calendar"])

        key = _tuple(record, MONTHLY_KEY)
        require(key not in record_keys, "duplicate monthly record key")
        record_keys.add(key)
        pair_groups[_tuple(record, PAIR_KEY)].append(record)
        cross_pulse_groups[_tuple(record, CROSS_PULSE_KEY)].append(record)

        daily = record["daily"]
        require(isinstance(daily, list) and daily, f"record {index} daily values must be nonempty")
        expected_days = _expected_day_keys(record["calendar"], record["year"], record["month"])
        observed_days: list[str] = []
        daily_values: list[float] = []
        for day_index, daily_record in enumerate(daily):
            require(isinstance(daily_record, dict) and set(daily_record) == DAILY_FIELDS, f"record {index} day {day_index} must contain exact daily fields")
            day_tuple = _parse_day_key(daily_record["date_or_model_day"], record["calendar"])
            require(day_tuple[:2] == (record["year"], record["month"]), f"record {index} contains a day outside its month")
            require(finite_number(daily_record["precipitation_mm"]), f"record {index} has nonfinite daily precipitation")
            require(float(daily_record["precipitation_mm"]) >= 0, f"record {index} has negative daily precipitation")
            observed_days.append(daily_record["date_or_model_day"])
            daily_values.append(float(daily_record["precipitation_mm"]))
        require(observed_days == expected_days, f"record {index} has missing, duplicate, or unordered calendar days")
        require(tuple(observed_days) == tuple(sorted(observed_days)), f"record {index} daily order is not strictly increasing")
        target = float(record["monthly_precipitation_mm"])
        if target == 0:
            require(all(value == 0 for value in daily_values), f"record {index} zero month contains positive daily precipitation")
        else:
            require(any(value > 0 for value in daily_values), f"record {index} positive month has no positive daily precipitation")
        error = abs(math.fsum(daily_values) - target)
        tolerance = max(config["pair_checks"]["absolute_conservation_tolerance_mm"], config["pair_checks"]["relative_conservation_tolerance"] * target)
        require(error <= tolerance, f"record {index} fails separate monthly conservation")
        maximum_error = max(maximum_error, error)
        require(divergence >= (1, 1, 1), f"record {index} divergence key is invalid")

    for pair_key, pair_records in pair_groups.items():
        require(len(pair_records) == 2, f"pair {pair_key} does not have exactly two path records")
        roles = {record["path_role"]: record for record in pair_records}
        require(set(roles) == {"baseline", "pulse"}, f"pair {pair_key} lacks separate baseline and pulse records")
        baseline, pulse = roles["baseline"], roles["pulse"]
        require(baseline["monthly_innovation_digest"] == pulse["monthly_innovation_digest"], f"pair {pair_key} innovation digests differ")
        require(baseline["first_divergence_date_or_model_day"] == pulse["first_divergence_date_or_model_day"], f"pair {pair_key} divergence keys differ")
        baseline_daily = baseline["daily"]
        pulse_daily = pulse["daily"]
        if float(baseline["pulse_scale_tonnes_c"]) == 0:
            require(baseline_daily == pulse_daily, f"pair {pair_key} violates zero-pulse daily identity")
        divergence_key = _parse_day_key(baseline["first_divergence_date_or_model_day"], baseline["calendar"])
        for baseline_day, pulse_day in zip(baseline_daily, pulse_daily):
            day_key = _parse_day_key(baseline_day["date_or_model_day"], baseline["calendar"])
            if day_key < divergence_key:
                require(baseline_day == pulse_day, f"pair {pair_key} violates pre-divergence daily identity")

    for month_key, month_records in cross_pulse_groups.items():
        scales = {float(record["pulse_scale_tonnes_c"]) for record in month_records}
        require(sum(scale == 0 for scale in scales) == 1, f"month {month_key} must contain exactly one zero pulse scale")
        require(len([scale for scale in scales if scale > 0]) >= 3, f"month {month_key} needs at least three distinct positive pulse scales")
        expected_count = 2 * len(scales)
        require(len(month_records) == expected_count, f"month {month_key} lacks the exact pulse-scale/path product")
        digests = {record["monthly_innovation_digest"] for record in month_records}
        require(len(digests) == 1, f"month {month_key} innovation digest changes across pulse scales")
        divergences = {record["first_divergence_date_or_model_day"] for record in month_records}
        require(len(divergences) == 1, f"month {month_key} divergence key changes across pulse scales")
        baselines = [record for record in month_records if record["path_role"] == "baseline"]
        baseline_daily = baselines[0]["daily"]
        require(all(record["daily"] == baseline_daily for record in baselines[1:]), f"month {month_key} baseline daily path changes across pulse scales")

    observed_monthly_input_hash = canonical_monthly_inputs_sha256(records)
    require(
        receipt["monthly_input_sha256"] == observed_monthly_input_hash,
        "monthly input hash does not match canonical monthly projection",
    )
    require(math.isclose(float(recorded_error), maximum_error, rel_tol=0, abs_tol=1e-15), "receipt maximum monthly mass error does not reconcile")
    return {
        "schema": "climate_daily_pair_output_validation_v1",
        "status": "schema_and_numerical_identity_checks_passed_synthetic_or_future_output_only",
        "record_count": len(records),
        "pair_count": len(pair_groups),
        "cross_pulse_month_count": len(cross_pulse_groups),
        "maximum_monthly_mass_error_mm": maximum_error,
        "monthly_input_sha256": observed_monthly_input_hash,
        "daily_output_sha256": observed_output_hash,
        "peak_resident_memory_bytes": peak,
        "generator_implementation_authorized": False,
        "scientific_validity_established": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/climate_daily_pair_output_schema_v1.toml"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    result = validate_bundle(bundle, args.config.resolve(), args.root.resolve())
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("climate daily-pair output schema gates passed")


if __name__ == "__main__":
    main()
