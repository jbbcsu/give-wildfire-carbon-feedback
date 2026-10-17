#!/usr/bin/env python3
"""Independently validate the wildfire-smoke normalization and closed gates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(root: Path, config_path: Path, receipt_path: Path, source_pdf: Path | None = None) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(config["schema"] == "wildfire_smoke_additive_integration_config/v1", "bad config schema")
    require(receipt["schema"] == "wildfire_smoke_integration_contract_receipt/v1", "bad receipt schema")
    require(receipt["config"]["sha256"] == sha256(config_path), "config hash mismatch")
    require(receipt["status"] == "normalized_scalar_pinned_additive_integration_blocked", "bad status")
    require(receipt["headline_addition_authorized"] is False, "headline addition authorized")

    evidence_paths: dict[str, Path] = {}
    for name, spec in config["bound_evidence"].items():
        path = (root / spec["path"]).resolve()
        require(path.is_file() and not path.is_symlink(), f"missing regular evidence: {name}")
        require(root.parent.resolve() in path.parents, f"evidence escapes GIVE workspace: {name}")
        require(sha256(path) == spec["sha256"], f"evidence hash mismatch: {name}")
        require(receipt["bound_evidence"][name]["sha256"] == spec["sha256"],
                f"receipt evidence hash mismatch: {name}")
        evidence_paths[name] = path

    source_receipt_path = evidence_paths["source_normalization_receipt"]
    source = json.loads(source_receipt_path.read_text(encoding="utf-8"))
    require(source["source"]["redistribution_authorized"] is False, "draft redistribution status changed")
    require(source["source"]["source_file_committed"] is False, "draft marked committed")
    require(source["source_supported_result"]["detailed_mean_usd_per_tco2"] == 50.04, "source mean changed")
    require(source["source_supported_result"]["rounded_headline_mean_usd_per_tco2"] == 50.0,
            "source headline changed")
    require(source["source_supported_result"]["currency_price_year"] == 2020, "source price year changed")
    require(source["source_supported_result"]["pulse_year"] == 2025, "source pulse year changed")
    require(source["normalization_audit"]["price_conversion_required"] is False, "price conversion changed")
    require(source["normalization_audit"]["pulse_year_conversion_required"] is False, "pulse conversion changed")
    if source_pdf is not None:
        require(source_pdf.is_file(), "source PDF unavailable")
        require(sha256(source_pdf) == source["source"]["sha256"], "source PDF hash mismatch")
        require(source_pdf.stat().st_size == source["source"]["bytes"], "source PDF byte count mismatch")

    overlap = json.loads(evidence_paths["overlap_audit"].read_text(encoding="utf-8"))
    require(overlap["overlap_assessment"]["mcduffie_vs_wildfire_smoke_physical_boundary_resolved"] is True,
            "wildfire/nonwildfire physical boundary changed")
    require(overlap["overlap_assessment"]["air_pollution_mortality_vs_give_temperature_mortality_cleared"] is False,
            "GIVE temperature-mortality overlap unexpectedly cleared")
    mcduffie = json.loads(evidence_paths["mcduffie_primary_source"].read_text(encoding="utf-8"))
    require(mcduffie["source_supported_facts"]["open_burning_including_wildfire_emissions_included"] is False,
            "nonwildfire PM emissions boundary changed")
    discount_text = evidence_paths["give_discount_parameters"].read_text(encoding="utf-8")
    require("exp(0.001972641) - 1" in discount_text and "eta = 1.244458999" in discount_text,
            "GIVE discount source changed")

    gates = config["admission_gates"]
    for gate in (
        "source_discount_implementation_verified", "numerical_pulse_definition_available",
        "annual_country_draw_paths_available", "local_numerical_reproduction_passed",
        "nonwildfire_pm_joint_health_function_consistency_cleared",
        "give_temperature_mortality_overlap_cleared", "additive_to_nonwildfire_air_pollution",
        "additive_to_baseline_give",
    ):
        require(gates[gate] is False, f"unsafe config gate open: {gate}")

    discount = config["target_normalization"]["discounting"]
    require(math.isclose(discount["prtp"], math.exp(0.001972641) - 1, rel_tol=0, abs_tol=1e-15),
            "wrong Ramsey prtp")
    require(discount["eta"] == 1.244458999, "wrong Ramsey eta")

    table = root / receipt["output"]["path"]
    require(sha256(table) == receipt["output"]["sha256"], "table hash mismatch")
    with table.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == 1, "expected exactly one smoke scalar row")
    row = rows[0]
    require(row["component_id"] == "wildfire_smoke_pm25_mortality", "unexpected component")
    require(float(row["detailed_mean_usd_per_tco2"]) == 50.04, "wrong normalized mean")
    require(float(row["interval_low_usd_per_tco2"]) == 18.5, "wrong interval low")
    require(float(row["interval_high_usd_per_tco2"]) == 102.6, "wrong interval high")
    require(int(row["pulse_year"]) == 2025 and int(row["currency_price_year"]) == 2020,
            "wrong pulse or price year")
    require(float(row["price_conversion_factor"]) == 1.0, "unexpected price conversion")
    require(row["estimate_role"] == "source_pinned_normalized_scalar_not_additive", "unsafe estimate role")
    for field in (
        "joint_pm_health_function_cleared", "give_temperature_mortality_overlap_cleared",
        "annual_paths_available", "local_reproduction_passed",
        "additive_to_nonwildfire_air_pollution", "additive_to_baseline_give",
    ):
        require(row[field] == "false", f"unsafe table gate open: {field}")
    required_blockers = {
        "SOURCE_DISCOUNT_IMPLEMENTATION_UNVERIFIED", "NUMERICAL_PULSE_DEFINITION_UNAVAILABLE",
        "ANNUAL_COUNTRY_DRAW_PATHS_UNAVAILABLE", "LOCAL_NUMERICAL_REPRODUCTION_FAILED",
        "JOINT_PM_HEALTH_FUNCTION_UNCLEARED", "GIVE_TEMPERATURE_MORTALITY_OVERLAP_UNCLEARED",
    }
    require(set(row["blocker_codes"].split("|")) == required_blockers, "blocker set changed")
    return {
        "schema": "wildfire_smoke_integration_contract_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_source_normalization_and_fail_closed_additivity",
        "checks_passed": 57 if source_pdf is not None else 54,
        "source_pdf_reverified": source_pdf is not None,
        "headline_addition_authorized": False,
        "inputs": {
            "config_sha256": sha256(config_path), "receipt_sha256": sha256(receipt_path),
            "table_sha256": sha256(table), "source_receipt_sha256": sha256(source_receipt_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("config/wildfire_smoke_additive_integration_v1.json"))
    parser.add_argument("--receipt", type=Path, default=Path("data/provenance/wildfire_smoke_integration_contract_v1.json"))
    parser.add_argument("--source-pdf", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    receipt_path = args.receipt if args.receipt.is_absolute() else root / args.receipt
    source_pdf = args.source_pdf.resolve() if args.source_pdf else None
    result = validate(root, config_path, receipt_path, source_pdf)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output = root / config["outputs"]["validation"]
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks_passed"]}))


if __name__ == "__main__":
    main()
