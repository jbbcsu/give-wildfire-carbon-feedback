#!/usr/bin/env python3
"""Focused synthetic tests for the Blue-SCC annual-pair admission gate."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/validate_blue_scc_fisheries_annual_pair.py"
SCHEMA_PATH = ROOT / "config/blue_scc_fisheries_annual_pair_v1.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_blue_scc_fisheries_annual_pair", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_csv(path: Path, fields: tuple[str, ...], records: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def file_record(path: Path) -> dict[str, object]:
    return {
        "relative_path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "byte_size": path.stat().st_size,
        "format": "csv",
        "media_type": "text/csv",
    }


def build_package(directory: Path, *, defect: str | None = None) -> Path:
    mapping = [
        {"source_country_key": "United States", "country_iso3": "USA", "give_country_id": "USA", "coefficient_available": "true", "annual_path_available": "true", "missingness_status": "complete", "missingness_reason": ""},
        {"source_country_key": "Canada", "country_iso3": "CAN", "give_country_id": "CAN", "coefficient_available": "true", "annual_path_available": "true", "missingness_status": "complete", "missingness_reason": ""},
    ]
    if defect == "incomplete_mapping":
        mapping[1]["coefficient_available"] = "false"

    paths: dict[str, list[dict[str, object]]] = {"baseline": [], "pulse": []}
    for role, run_id, adjustment in (("baseline", "base-run", 0.0), ("pulse", "pulse-run", -0.5)):
        for year in (2050, 2051):
            for country, consumer, producer in (("USA", 10.0, 5.0), ("CAN", 4.0, 2.0)):
                paths[role].append({
                    "run_id": run_id,
                    "pulse_id": "pulse-one",
                    "run_configuration_id": "config-one",
                    "draw_id": "draw-one",
                    "country_iso3": country,
                    "year": year,
                    "consumer_surplus": consumer + year - 2050 + adjustment,
                    "producer_surplus": producer + adjustment / 2,
                    "currency": "USD",
                    "price_year": 2020,
                    "time_basis": "annual_flow",
                    "missingness_status": "complete",
                })
    if defect == "unmatched_path":
        paths["pulse"].pop()

    global_rows: list[dict[str, object]] = []
    for role, run_id in (("baseline", "base-run"), ("pulse", "pulse-run")):
        for year in (2050, 2051):
            subset = [row for row in paths[role] if row["year"] == year]
            consumer = sum(float(row["consumer_surplus"]) for row in subset)
            producer = sum(float(row["producer_surplus"]) for row in subset)
            global_rows.append({
                "path_role": role,
                "run_id": run_id,
                "pulse_id": "pulse-one",
                "run_configuration_id": "config-one",
                "draw_id": "draw-one",
                "year": year,
                "consumer_surplus": consumer,
                "producer_surplus": producer,
                "market_total": consumer + producer,
                "currency": "USD",
                "price_year": 2020,
                "time_basis": "annual_flow",
                "missingness_status": "complete",
            })
    if defect == "nonadditive":
        global_rows[0]["market_total"] = float(global_rows[0]["market_total"]) + 1.0

    mapping_path = directory / "country_mapping.csv"
    baseline_path = directory / "baseline_path.csv"
    pulse_path = directory / "pulse_path.csv"
    global_path = directory / "global_reconciliation.csv"
    write_csv(mapping_path, MODULE.MAPPING_FIELDS, mapping)
    write_csv(baseline_path, MODULE.ANNUAL_FIELDS, paths["baseline"])
    write_csv(pulse_path, MODULE.ANNUAL_FIELDS, paths["pulse"])
    write_csv(global_path, MODULE.GLOBAL_FIELDS, global_rows)

    manifest = {
        "contract_version": MODULE.CONTRACT_VERSION,
        "bundle_id": "synthetic-blue-scc-pair-v1",
        "authorization": {"purpose": "artifact_admission_only", "import": True, "damage_function": False, "discounting": False, "scc": False},
        "source": {"repository_url": "synthetic://blue-scc", "repository_commit": "a" * 40, "paper_doi": "synthetic:doi", "derivation_id": "synthetic-derivation"},
        "license": {"license_id": "CC0-1.0", "rights_holder": "Synthetic test", "redistribution_allowed": True, "derivative_use_allowed": True, "give_research_use_allowed": True, "attribution_text": "Synthetic test data", "third_party_restrictions": []},
        "files": {
            "baseline_path": file_record(baseline_path),
            "pulse_path": file_record(pulse_path),
            "country_mapping": file_record(mapping_path),
            "global_reconciliation": file_record(global_path),
        },
        "pulse": {"pulse_id": "pulse-one", "gas": "CO2", "mass": 1000000.0, "mass_unit": "tCO2", "pulse_year": 2020, "baseline_run_id": "base-run", "pulse_run_id": "pulse-run", "run_configuration_id": "config-one", "climate_module": "synthetic-climate", "socioeconomic_scenario": "synthetic-scenario", "discounting_applied": False},
        "coverage": {"country_count": 2, "start_year": 2050, "end_year": 2051, "draw_ids": ["draw-one"], "complete": True, "missingness_rule": "explicit_no_zero_fill_imputation_or_renormalization"},
        "units": {"currency": "USD", "price_year": 2020, "time_basis": "annual_flow", "value_basis": "undiscounted_direct_welfare_level"},
        "welfare_boundary": {
            "market_measure": "direct_consumer_plus_producer_surplus",
            "consumer_component": "consumer_surplus",
            "producer_component": "producer_surplus",
            "nutrition_mortality_treatment": "excluded_and_not_present_in_market_paths",
            "includes_nutrition_or_mortality": False,
            "includes_indirect_or_induced_output": False,
            "uses_accounting_profit_as_producer_surplus": False,
            "uses_gross_revenue_as_welfare": False,
            "includes_aquaculture": False,
            "includes_coral_or_reef_services": False,
            "includes_biodiversity_nonuse_value": False,
            "includes_ciam_coastal_impacts": False,
            "overlap_review_status": "passed",
            "accounting_boundary_id": "synthetic-direct-market-v1",
        },
        "reconciliation": {"absolute_tolerance": 1e-9, "relative_tolerance": 1e-12, "country_paths_add_to_global": True, "market_total_equals_consumer_plus_producer": True},
    }
    if defect == "license":
        manifest["license"]["license_id"] = "NOASSERTION"
    elif defect == "pulse_metadata":
        manifest["pulse"]["mass_unit"] = "tonnes_of_C"
    elif defect == "welfare_boundary":
        manifest["welfare_boundary"]["includes_nutrition_or_mortality"] = True
    elif defect == "hash":
        manifest["files"]["baseline_path"]["sha256"] = "0" * 64
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def expect_failure(defect: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        manifest = build_package(Path(temporary), defect=defect)
        try:
            MODULE.validate_package(manifest, SCHEMA_PATH)
        except ValueError:
            return
        raise AssertionError(f"defect passed: {defect}")


with tempfile.TemporaryDirectory() as temporary:
    manifest = build_package(Path(temporary))
    result = MODULE.validate_package(manifest, SCHEMA_PATH)
    assert result["status"] == "admitted_for_annual_path_review_no_scc_authority"
    assert result["matched_annual_path_rows"] == 4
    assert result["countries"] == 2
    assert result["scc_calculated"] is False
    completed = subprocess.run(["python3", str(MODULE_PATH), "package", str(manifest)], text=True, capture_output=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["scc_calculated"] is False

for failure in ("license", "pulse_metadata", "incomplete_mapping", "unmatched_path", "nonadditive", "welfare_boundary", "hash"):
    expect_failure(failure)

with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    country = directory / "country_level_scc.csv"
    global_file = directory / "scc.csv"
    write_csv(country, ("iso3", "scc", "oc_capital", "valuation"), [
        {"iso3": "USA", "scc": 0.4, "oc_capital": "Fisheries", "valuation": "Market value"},
        {"iso3": "CAN", "scc": 0.5, "oc_capital": "Fisheries", "valuation": "Market value"},
        {"iso3": "USA", "scc": 2.0, "oc_capital": "Fisheries", "valuation": "Non-market use value"},
        {"iso3": "CAN", "scc": 3.0, "oc_capital": "Fisheries", "valuation": "Non-market use value"},
    ])
    write_csv(global_file, ("Asset type", "Valuation type", "SCC"), [
        {"Asset type": "Fisheries", "Valuation type": "Market value", "SCC": 1.1},
        {"Asset type": "Fisheries", "Valuation type": "Non-market use value", "SCC": 6.0},
    ])
    rejection = MODULE.audit_public_summaries(country, global_file, "b" * 40)
    assert rejection["status"] == "rejected_not_matched_annual_artifact_package"
    assert rejection["additive_fisheries_summary_rows"] == 0
    assert rejection["scc_calculated"] is False
    assert "country_and_global_summaries_not_additive" in rejection["reasons"]

receipt = json.loads((ROOT / "data/provenance/blue_scc_public_fisheries_summary_admission_20261014.json").read_text(encoding="utf-8"))
assert receipt["source"]["repository_commit"] == "dbc0d8cb21c81f1508abfaf9e5c0f5671ccdd83f"
assert receipt["country_export"]["sha256"] == "bbe8f4ac053174fae41874ede12548cc4f9dc37b81e4e8f026b8854a510a96d9"
assert receipt["global_export"]["sha256"] == "16bc4d007610c4581a28216a7c185f02425a6a5f67dcf101daf0872734e380fa"
assert receipt["comparable_fisheries_summary_rows"] == 2
assert receipt["additive_fisheries_summary_rows"] == 0
assert receipt["scc_calculated"] is False

print("Blue-SCC fisheries annual-pair admission tests passed")
