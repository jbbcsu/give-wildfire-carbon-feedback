#!/usr/bin/env python3
"""Validate fisheries baseline/pulse inputs or country-year welfare outputs.

This is a schema and accounting validator only. It does not estimate catch,
prices, surplus, damages, or an SCC.
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


PAIR_REQUIRED = {
    "draw_id", "scenario", "year", "country_id", "stock_id",
    "harvest_or_availability_tonnes", "climate_model_id",
    "ecosystem_model_id", "management_scenario", "welfare_draw_id",
    "coverage_status",
}
OUTPUT_REQUIRED = {
    "draw_id", "year", "country_id", "delta_consumer_surplus_usd",
    "delta_producer_surplus_usd", "delta_fisheries_welfare_usd",
    "coverage_status", "additive_eligible", "climate_model_id",
    "ecosystem_model_id", "management_scenario", "welfare_draw_id",
    "accounting_boundary_id", "overlap_review_status",
}
SCENARIOS = {"baseline", "pulse"}
COVERAGE = {"complete", "missing", "unmodeled", "suppressed"}
IDENTIFIERS = (
    "climate_model_id", "ecosystem_model_id", "management_scenario",
    "welfare_draw_id",
)
OVERLAP_REVIEW = {"passed", "pending", "failed"}
OVERLAP_EXCLUSION_FIELDS = (
    "includes_aquaculture",
    "includes_terrestrial_food_market_welfare",
    "includes_coral_or_reef_services",
    "includes_biodiversity_nonuse_value",
    "includes_ciam_coastal_impacts",
    "uses_gross_revenue_as_welfare",
)
OUTPUT_REQUIRED.update(OVERLAP_EXCLUSION_FIELDS)


def rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        return reader.fieldnames, list(reader)


def finite(value: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def validate_pairs(fieldnames: list[str], records: list[dict[str, str]]) -> None:
    missing = PAIR_REQUIRED - set(fieldnames)
    if missing:
        raise ValueError(f"paired input missing columns {sorted(missing)}")
    groups: dict[tuple[str, str, str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in records:
        scenario = row["scenario"].strip().lower()
        if scenario not in SCENARIOS:
            raise ValueError("scenario must be baseline or pulse")
        status = row["coverage_status"].strip().lower()
        if status not in COVERAGE:
            raise ValueError(f"unknown coverage_status {status!r}")
        quantity = row["harvest_or_availability_tonnes"].strip()
        if status == "complete":
            if finite(quantity, "harvest_or_availability_tonnes") < 0:
                raise ValueError("harvest_or_availability_tonnes must be nonnegative")
        elif quantity:
            raise ValueError("non-complete coverage must not encode a numeric zero or quantity")
        key = (row["draw_id"], row["year"], row["country_id"], row["stock_id"])
        if scenario in groups[key]:
            raise ValueError(f"duplicate {scenario} row for key {key}")
        groups[key][scenario] = row

    for key, paired in groups.items():
        if set(paired) != SCENARIOS:
            raise ValueError(f"key {key} lacks a matched baseline/pulse pair")
        for name in IDENTIFIERS:
            if paired["baseline"][name] != paired["pulse"][name]:
                raise ValueError(f"key {key} has unmatched {name}")


def validate_outputs(fieldnames: list[str], records: list[dict[str, str]], tolerance: float) -> None:
    missing = OUTPUT_REQUIRED - set(fieldnames)
    if missing:
        raise ValueError(f"welfare output missing columns {sorted(missing)}")
    if any(
        "revenue" in name.lower() and name not in OVERLAP_EXCLUSION_FIELDS
        for name in fieldnames
    ):
        raise ValueError("gross revenue fields are outside the welfare output contract")
    seen: set[tuple[str, str, str]] = set()
    boundary_signatures: dict[str, tuple[bool, ...]] = {}
    for row in records:
        key = (row["draw_id"], row["year"], row["country_id"])
        if key in seen:
            raise ValueError(f"duplicate welfare output key {key}")
        seen.add(key)
        status = row["coverage_status"].strip().lower()
        if status not in COVERAGE:
            raise ValueError(f"unknown coverage_status {status!r}")
        eligible = row["additive_eligible"].strip().lower()
        if eligible not in {"true", "false"}:
            raise ValueError("additive_eligible must be true or false")
        if not row["accounting_boundary_id"].strip():
            raise ValueError("accounting_boundary_id must be nonblank")
        overlap_review = row["overlap_review_status"].strip().lower()
        if overlap_review not in OVERLAP_REVIEW:
            raise ValueError(
                "overlap_review_status must be passed, pending, or failed"
            )
        overlap_flags: dict[str, bool] = {}
        for name in OVERLAP_EXCLUSION_FIELDS:
            value = row[name].strip().lower()
            if value not in {"true", "false"}:
                raise ValueError(f"{name} must be true or false")
            overlap_flags[name] = value == "true"
        boundary_id = row["accounting_boundary_id"].strip()
        boundary_signature = tuple(
            overlap_flags[name] for name in OVERLAP_EXCLUSION_FIELDS
        )
        previous_signature = boundary_signatures.setdefault(
            boundary_id, boundary_signature
        )
        if previous_signature != boundary_signature:
            raise ValueError(
                f"accounting_boundary_id {boundary_id!r} has inconsistent "
                "locked-exclusion flags"
            )
        if overlap_review == "passed" and any(overlap_flags.values()):
            included = sorted(name for name, value in overlap_flags.items() if value)
            raise ValueError(
                "passed overlap review contradicts locked exclusions: "
                + ", ".join(included)
            )
        if eligible == "true" and status != "complete":
            raise ValueError("only complete coverage may be additive eligible")
        if eligible == "true" and overlap_review != "passed":
            raise ValueError("only a passed overlap review may be additive eligible")
        values = (
            row["delta_consumer_surplus_usd"].strip(),
            row["delta_producer_surplus_usd"].strip(),
            row["delta_fisheries_welfare_usd"].strip(),
        )
        if status != "complete":
            if any(values):
                raise ValueError(
                    "non-complete welfare coverage must leave surplus fields blank, not encode zero"
                )
            continue
        consumer = finite(values[0], "consumer surplus")
        producer = finite(values[1], "producer surplus")
        welfare = finite(values[2], "fisheries welfare")
        scale = max(1.0, abs(consumer), abs(producer), abs(welfare))
        if abs((consumer + producer) - welfare) > tolerance * scale:
            raise ValueError("fisheries welfare does not equal consumer plus producer surplus")
        if eligible == "true" and any(not row[name].strip() for name in IDENTIFIERS):
            raise ValueError("eligible output is missing a matched-draw identifier")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("pairs", "outputs"))
    parser.add_argument("csv")
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()
    if args.tolerance < 0:
        raise ValueError("tolerance must be nonnegative")
    fieldnames, records = rows(Path(args.csv))
    if not records:
        raise ValueError("CSV has no data rows")
    if args.kind == "pairs":
        validate_pairs(fieldnames, records)
    else:
        validate_outputs(fieldnames, records, args.tolerance)
    print(f"validated {len(records)} {args.kind} rows")


if __name__ == "__main__":
    main()
