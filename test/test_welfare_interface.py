#!/usr/bin/env python3
from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_welfare_interface.py"


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def run(kind: str, path: Path, succeeds: bool) -> None:
    result = subprocess.run(["python3", str(VALIDATOR), kind, str(path)], capture_output=True, text=True)
    if (result.returncode == 0) != succeeds:
        raise AssertionError(result.stdout + result.stderr)


with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    pair = {
        "draw_id": "d1", "year": 2050, "country_id": "USA", "stock_id": "s1",
        "harvest_or_availability_tonnes": 10, "climate_model_id": "g1",
        "ecosystem_model_id": "e1", "management_scenario": "m1",
        "welfare_draw_id": "w1", "coverage_status": "complete",
    }
    pair_path = temp / "pairs.csv"
    write_csv(pair_path, [dict(pair, scenario="baseline"), dict(pair, scenario="pulse")])
    run("pairs", pair_path, True)
    write_csv(pair_path, [dict(pair, scenario="baseline"), dict(pair, scenario="pulse", climate_model_id="g2")])
    run("pairs", pair_path, False)

    output = {
        "draw_id": "d1", "year": 2050, "country_id": "USA",
        "delta_consumer_surplus_usd": -2, "delta_producer_surplus_usd": -3,
        "delta_fisheries_welfare_usd": -5, "coverage_status": "complete",
        "additive_eligible": "true", "climate_model_id": "g1",
        "ecosystem_model_id": "e1", "management_scenario": "m1",
        "welfare_draw_id": "w1", "accounting_boundary_id": "marine_capture_surplus_v1",
        "overlap_review_status": "passed", "includes_aquaculture": "false",
        "includes_terrestrial_food_market_welfare": "false",
        "includes_coral_or_reef_services": "false",
        "includes_biodiversity_nonuse_value": "false",
        "includes_ciam_coastal_impacts": "false",
        "uses_gross_revenue_as_welfare": "false",
    }
    output_path = temp / "outputs.csv"
    write_csv(output_path, [output])
    run("outputs", output_path, True)
    write_csv(output_path, [dict(output, delta_fisheries_welfare_usd=-4)])
    run("outputs", output_path, False)
    write_csv(output_path, [dict(
        output,
        additive_eligible="false",
        overlap_review_status="pending",
    )])
    run("outputs", output_path, True)
    write_csv(output_path, [dict(output, overlap_review_status="pending")])
    run("outputs", output_path, False)
    write_csv(output_path, [dict(output, includes_aquaculture="true")])
    run("outputs", output_path, False)
    write_csv(output_path, [dict(output, accounting_boundary_id="")])
    run("outputs", output_path, False)
    write_csv(output_path, [dict(output, gross_revenue_usd=10)])
    run("outputs", output_path, False)
    write_csv(output_path, [dict(
        output,
        coverage_status="missing",
        additive_eligible="false",
        delta_consumer_surplus_usd="",
        delta_producer_surplus_usd="",
        delta_fisheries_welfare_usd="",
    )])
    run("outputs", output_path, True)
    write_csv(output_path, [dict(
        output,
        coverage_status="missing",
        additive_eligible="false",
        delta_consumer_surplus_usd=0,
        delta_producer_surplus_usd=0,
        delta_fisheries_welfare_usd=0,
    )])
    run("outputs", output_path, False)

print("fisheries welfare-interface tests passed")
