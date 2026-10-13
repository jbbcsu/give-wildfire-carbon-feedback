#!/usr/bin/env python3
"""Consistency checks for the author-facing Blue-SCC artifact request."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
request = json.loads(
    (ROOT / "config/blue_scc_author_artifact_request_v1.json").read_text(encoding="utf-8")
)
market_receipt = json.loads(
    (ROOT / "data/provenance/blue_scc_market_component_transfer_audit_20261013.json")
    .read_text(encoding="utf-8")
)
nutrition_receipt = json.loads(
    (ROOT / "data/provenance/blue_scc_nutrition_give_transfer_audit_20261013.json")
    .read_text(encoding="utf-8")
)
benchmark_receipt = json.loads(
    (ROOT / "data/provenance/blue_scc_fisheries_literature_benchmark_20260826.json")
    .read_text(encoding="utf-8")
)

assert request["schema"] == "blue_scc_author_artifact_request_v1"
assert request["source"]["repository_commit"] == market_receipt["source"]["repository_commit"]
assert len(request["requested_files"]) == 17
assert len({item["id"] for item in request["requested_files"]}) == 17
assert all(item["status_at_pinned_commit"] != "available" for item in request["requested_files"])

required_results = {
    "bluerice/baseline/results/results_ocean_today_BASELINE.gdx",
    "bluerice/baseline/results/results_ocean_damage_BASELINE.gdx",
    "bluerice/baseline/results/results_ocean_damage_pulse_BASELINE.gdx",
}
assert required_results == {
    item["source_code_runtime_path"]
    for item in request["requested_files"]
    if "source_code_runtime_path" in item
}

figure_market = market_receipt["global_figure4_market_component"]["usd_per_tco2"]
country_market = market_receipt["published_2020_country_market_scc"]["sum_usd_per_tco2"]
questions = "\n".join(request["reconciliation_questions"])
identities = "\n".join(item["identity"] for item in request["required_reconciliation_identities"])
assert str(figure_market) in questions
assert str(country_market) in questions
assert str(figure_market) in identities

nutrition_reconciliation = nutrition_receipt["published_2020_country_scc"]["figure4_reconciliation"]
assert str(nutrition_reconciliation["Non-market use value"]["country_sum_usd_per_tco2"]) in questions
assert str(nutrition_reconciliation["Non-market use value"]["figure4_usd_per_tco2"]) in questions

flows = request["minimum_machine_readable_delivery"]["annual_country_market_flows"]
assert {"run_id", "pulse_id", "country_iso3", "year", "valuation"} == set(flows["primary_key"])
assert {"baseline_value", "pulse_value", "welfare_concept", "missingness_status"}.issubset(
    flows["required_columns"]
)
benchmark = request["external_benchmark_presentation"]
published = benchmark_receipt["published_figure4_baseline_summary"]
assert benchmark["fisheries_market"] == published["fisheries_market_scc_usd_per_tco2"]
assert benchmark["fisheries_nonmarket_use"] == published["fisheries_nonmarket_use_scc_usd_per_tco2"]
assert benchmark["fisheries_total"] == published["fisheries_total_scc_usd_per_tco2"]
assert benchmark["added_to_give"] is False
assert all(value is False for value in request["acceptance_gates"].values())

print("Blue-SCC author artifact request consistency tests passed")
