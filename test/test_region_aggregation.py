#!/usr/bin/env python3
from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "aggregate_welfare_to_regions.py"


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def run(
    country: Path, crosswalk: Path, output: Path, succeeds: bool
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["python3", str(ADAPTER), str(country), str(crosswalk), str(output)],
        capture_output=True,
        text=True,
    )
    if (result.returncode == 0) != succeeds:
        raise AssertionError(result.stdout + result.stderr)
    return result


def welfare(country: str, consumer: object, producer: object) -> dict[str, object]:
    total = "" if consumer == "" or producer == "" else float(consumer) + float(producer)
    return {
        "draw_id": "d1",
        "year": 2050,
        "country_id": country,
        "delta_consumer_surplus_usd": consumer,
        "delta_producer_surplus_usd": producer,
        "delta_fisheries_welfare_usd": total,
        "coverage_status": "complete",
        "additive_eligible": "true",
        "climate_model_id": "g1",
        "ecosystem_model_id": "e1",
        "management_scenario": "m1",
        "welfare_draw_id": "w1",
        "accounting_boundary_id": "marine_capture_surplus_v1",
        "overlap_review_status": "passed",
        "includes_aquaculture": "false",
        "includes_terrestrial_food_market_welfare": "false",
        "includes_coral_or_reef_services": "false",
        "includes_biodiversity_nonuse_value": "false",
        "includes_ciam_coastal_impacts": "false",
        "uses_gross_revenue_as_welfare": "false",
    }


with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    country_path = temp / "country.csv"
    crosswalk_path = temp / "crosswalk.csv"
    output_path = temp / "regions.csv"
    crosswalk = [
        {"country_id": "AAA", "give_region_id": "R1"},
        {"country_id": "BBB", "give_region_id": "R1"},
        {"country_id": "CCC", "give_region_id": "R2"},
    ]
    write_csv(crosswalk_path, crosswalk)
    records = [
        welfare("AAA", "1.25", "-0.25"),
        welfare("BBB", 2, 3),
        welfare("CCC", -1, -2),
    ]
    write_csv(country_path, records)
    run(country_path, crosswalk_path, output_path, True)
    with output_path.open(newline="", encoding="utf-8") as stream:
        output = {row["give_region_id"]: row for row in csv.DictReader(stream)}
    assert output["R1"]["delta_consumer_surplus_usd"] == "3.25"
    assert output["R1"]["delta_producer_surplus_usd"] == "2.75"
    assert output["R1"]["delta_fisheries_welfare_usd"] == "6"
    assert output["R1"]["additive_eligible"] == "true"
    assert output["R1"]["overlap_review_status"] == "passed"
    assert output["R1"]["accounting_boundary_id"] == "marine_capture_surplus_v1"
    assert output["R2"]["delta_fisheries_welfare_usd"] == "-3"

    # A declared but absent country fails its region closed; no partial total is emitted.
    write_csv(country_path, [records[0], records[2]])
    run(country_path, crosswalk_path, output_path, True)
    with output_path.open(newline="", encoding="utf-8") as stream:
        output = {row["give_region_id"]: row for row in csv.DictReader(stream)}
    assert output["R1"]["coverage_status"] == "incomplete"
    assert output["R1"]["coverage_reason_codes"] == "country_missing"
    assert output["R1"]["delta_fisheries_welfare_usd"] == ""
    assert output["R1"]["overlap_review_status"] == "pending"
    assert output["R2"]["delta_fisheries_welfare_usd"] == "-3"

    # Incomplete upstream coverage is preserved and never converted to numeric zero.
    missing = welfare("BBB", "", "")
    missing.update(coverage_status="suppressed", additive_eligible="false")
    write_csv(country_path, [records[0], missing, records[2]])
    run(country_path, crosswalk_path, output_path, True)
    with output_path.open(newline="", encoding="utf-8") as stream:
        output = {row["give_region_id"]: row for row in csv.DictReader(stream)}
    assert output["R1"]["coverage_reason_codes"] == "country_suppressed"
    assert output["R1"]["delta_fisheries_welfare_usd"] == ""

    # A complete row that has not cleared the overlap gate is also withheld.
    overlap_pending = dict(
        records[1], additive_eligible="false", overlap_review_status="pending"
    )
    write_csv(country_path, [records[0], overlap_pending, records[2]])
    run(country_path, crosswalk_path, output_path, True)
    with output_path.open(newline="", encoding="utf-8") as stream:
        output = {row["give_region_id"]: row for row in csv.DictReader(stream)}
    assert output["R1"]["coverage_reason_codes"] == "country_overlap_pending"
    assert output["R1"]["delta_fisheries_welfare_usd"] == ""

    # A passed overlap review does not force eligibility if another gate is pending.
    other_gate_pending = dict(records[1], additive_eligible="false")
    write_csv(country_path, [records[0], other_gate_pending, records[2]])
    run(country_path, crosswalk_path, output_path, True)
    with output_path.open(newline="", encoding="utf-8") as stream:
        output = {row["give_region_id"]: row for row in csv.DictReader(stream)}
    assert output["R1"]["coverage_reason_codes"] == "country_not_additive_eligible"

    # Boundary definitions cannot silently change within one draw-year.
    write_csv(country_path, [
        records[0],
        dict(records[1], accounting_boundary_id="different_boundary_v1"),
        records[2],
    ])
    run(country_path, crosswalk_path, output_path, False)

    write_csv(country_path, [
        records[0],
        dict(
            records[1],
            additive_eligible="false",
            includes_aquaculture="true",
            overlap_review_status="failed",
        ),
        records[2],
    ])
    run(country_path, crosswalk_path, output_path, False)

    # Country rows cannot silently cross model/draw identities, even across regions.
    write_csv(country_path, [records[0], records[1], dict(records[2], climate_model_id="g2")])
    run(country_path, crosswalk_path, output_path, False)

    # Every input country must occur in the explicitly declared region universe.
    write_csv(country_path, records + [welfare("ZZZ", 1, 1)])
    run(country_path, crosswalk_path, output_path, False)

print("fisheries country-to-region aggregation tests passed")
