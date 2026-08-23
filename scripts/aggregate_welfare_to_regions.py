#!/usr/bin/env python3
"""Aggregate validated country welfare changes to a declared GIVE region map.

This adapter is deterministic accounting scaffolding. It neither estimates
fisheries welfare nor discounts regional totals into an SCC. Regional values
are emitted only when every country declared for that region and draw-year is
present, complete, and already marked additive eligible upstream.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from validate_welfare_interface import (
    IDENTIFIERS,
    OVERLAP_EXCLUSION_FIELDS,
    rows,
    validate_outputs,
)


CROSSWALK_REQUIRED = {"country_id", "give_region_id"}
VALUE_FIELDS = (
    "delta_consumer_surplus_usd",
    "delta_producer_surplus_usd",
    "delta_fisheries_welfare_usd",
)
OUTPUT_FIELDS = (
    "draw_id",
    "year",
    "give_region_id",
    *VALUE_FIELDS,
    "coverage_status",
    "coverage_reason_codes",
    "additive_eligible",
    *IDENTIFIERS,
    "accounting_boundary_id",
    "overlap_review_status",
    *OVERLAP_EXCLUSION_FIELDS,
    "country_count_expected",
    "country_count_present",
    "country_count_complete",
)
AGGREGATION_IDENTIFIERS = (
    *IDENTIFIERS,
    "accounting_boundary_id",
    *OVERLAP_EXCLUSION_FIELDS,
)


def load_crosswalk(path: Path) -> dict[str, str]:
    fieldnames, records = rows(path)
    missing = CROSSWALK_REQUIRED - set(fieldnames)
    if missing:
        raise ValueError(f"country-region crosswalk missing columns {sorted(missing)}")
    if not records:
        raise ValueError("country-region crosswalk has no data rows")
    mapping: dict[str, str] = {}
    for row in records:
        country = row["country_id"].strip()
        region = row["give_region_id"].strip()
        if not country or not region:
            raise ValueError("crosswalk country_id and give_region_id must be nonblank")
        if country in mapping:
            raise ValueError(f"duplicate crosswalk country_id {country!r}")
        mapping[country] = region
    return mapping


def decimal_value(value: str, label: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label} must be a decimal number") from exc
    if not number.is_finite():
        raise ValueError(f"{label} must be finite")
    return number


def format_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def aggregate(
    records: list[dict[str, str]], mapping: dict[str, str]
) -> list[dict[str, str | int]]:
    by_draw_year: dict[tuple[str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in records:
        country = row["country_id"].strip()
        if country not in mapping:
            raise ValueError(f"country_id {country!r} is absent from the declared crosswalk")
        draw_year = (row["draw_id"].strip(), row["year"].strip())
        by_draw_year[draw_year][country] = row

    countries_by_region: dict[str, list[str]] = defaultdict(list)
    for country, region in mapping.items():
        countries_by_region[region].append(country)

    output: list[dict[str, str | int]] = []
    for (draw_id, year), country_rows in sorted(by_draw_year.items()):
        draw_identifiers: dict[str, str] = {}
        for name in AGGREGATION_IDENTIFIERS:
            observed = {row[name].strip() for row in country_rows.values() if row[name].strip()}
            if len(observed) > 1:
                raise ValueError(f"draw-year {(draw_id, year)} has unmatched {name}")
            draw_identifiers[name] = next(iter(observed), "")

        for region, expected_countries in sorted(countries_by_region.items()):
            present = [country_rows[c] for c in expected_countries if c in country_rows]
            complete = [
                row for row in present if row["coverage_status"].strip().lower() == "complete"
            ]
            eligible = [
                row for row in complete if row["additive_eligible"].strip().lower() == "true"
            ]

            reasons: set[str] = set()
            if len(present) != len(expected_countries):
                reasons.add("country_missing")
            for row in present:
                status = row["coverage_status"].strip().lower()
                if status != "complete":
                    reasons.add(f"country_{status}")
                elif row["overlap_review_status"].strip().lower() != "passed":
                    reasons.add(
                        "country_overlap_"
                        + row["overlap_review_status"].strip().lower()
                    )
                elif row["additive_eligible"].strip().lower() != "true":
                    reasons.add("country_not_additive_eligible")

            region_eligible = not reasons and len(eligible) == len(expected_countries)
            result: dict[str, str | int] = {
                "draw_id": draw_id,
                "year": year,
                "give_region_id": region,
                "coverage_status": "complete" if region_eligible else "incomplete",
                "coverage_reason_codes": ";".join(sorted(reasons)),
                "additive_eligible": str(region_eligible).lower(),
                **draw_identifiers,
                "overlap_review_status": (
                    "passed"
                    if region_eligible
                    else (
                        "failed"
                        if any(
                            row["overlap_review_status"].strip().lower() == "failed"
                            for row in present
                        )
                        else "pending"
                    )
                ),
                "country_count_expected": len(expected_countries),
                "country_count_present": len(present),
                "country_count_complete": len(complete),
            }
            if region_eligible:
                for field in VALUE_FIELDS:
                    total = sum(decimal_value(row[field], field) for row in eligible)
                    result[field] = format_decimal(total)
            else:
                for field in VALUE_FIELDS:
                    result[field] = ""
            output.append(result)
    return output


def verify_conservation(
    input_records: list[dict[str, str]],
    output_records: list[dict[str, str | int]],
    mapping: dict[str, str],
) -> None:
    input_totals: dict[tuple[str, str, str], dict[str, Decimal]] = defaultdict(
        lambda: {field: Decimal(0) for field in VALUE_FIELDS}
    )
    for row in input_records:
        if row["coverage_status"].strip().lower() != "complete":
            continue
        if row["additive_eligible"].strip().lower() != "true":
            continue
        key = (
            row["draw_id"].strip(),
            row["year"].strip(),
            mapping[row["country_id"].strip()],
        )
        for field in VALUE_FIELDS:
            input_totals[key][field] += decimal_value(row[field], field)
    for row in output_records:
        if row["additive_eligible"] != "true":
            continue
        key = (
            str(row["draw_id"]),
            str(row["year"]),
            str(row["give_region_id"]),
        )
        for field in VALUE_FIELDS:
            observed = decimal_value(str(row[field]), field)
            if input_totals[key][field] != observed:
                raise ValueError(
                    f"regional aggregation failed {field} conservation for {key}"
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("country_welfare_csv")
    parser.add_argument("country_region_crosswalk_csv")
    parser.add_argument("output_csv")
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()
    if args.tolerance < 0:
        raise ValueError("tolerance must be nonnegative")

    fieldnames, records = rows(Path(args.country_welfare_csv))
    if not records:
        raise ValueError("country welfare CSV has no data rows")
    validate_outputs(fieldnames, records, args.tolerance)
    mapping = load_crosswalk(Path(args.country_region_crosswalk_csv))
    output = aggregate(records, mapping)
    verify_conservation(records, output, mapping)

    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(output)
    print(f"wrote {len(output)} fail-closed region rows to {output_path}")


if __name__ == "__main__":
    main()
