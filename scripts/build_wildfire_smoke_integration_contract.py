#!/usr/bin/env python3
"""Build the source-pinned, fail-closed wildfire-smoke integration contract."""

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
SCHEMA = "wildfire_smoke_additive_integration_config/v1"
FIELDS = [
    "component_id", "estimate_role", "detailed_mean_usd_per_tco2",
    "rounded_headline_usd_per_tco2", "interval_low_usd_per_tco2",
    "interval_high_usd_per_tco2", "interval_level_percent", "interval_type",
    "source_monte_carlo_trials", "pulse_year", "currency_price_year", "units",
    "discount_label", "discount_prtp", "discount_eta", "price_conversion_factor",
    "source_scalar_pinned", "price_year_aligned", "pulse_year_aligned",
    "physical_emissions_boundary_separable", "joint_pm_health_function_cleared",
    "give_temperature_mortality_overlap_cleared", "annual_paths_available",
    "local_reproduction_passed", "additive_to_nonwildfire_air_pollution",
    "additive_to_baseline_give", "blocker_codes",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_bound(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    require(path.is_file() and not path.is_symlink(), f"missing regular evidence: {relative}")
    require(root.parent.resolve() in path.parents, f"evidence escapes GIVE workspace: {relative}")
    return path


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(payload.get("schema") == SCHEMA, "unexpected config schema")
    gates = payload["admission_gates"]
    expected_true = {
        "source_scalar_pinned", "source_price_year_matches_target",
        "source_pulse_year_matches_target", "target_discount_parameters_pinned",
    }
    expected_false = set(gates) - expected_true
    require(all(gates[name] is True for name in expected_true), "normalization gate unexpectedly closed")
    require(all(gates[name] is False for name in expected_false), "unsafe admission gate open")
    require(gates["additive_to_nonwildfire_air_pollution"] is False, "nonwildfire additivity promoted")
    require(gates["additive_to_baseline_give"] is False, "baseline GIVE additivity promoted")
    return payload


def validate_evidence(root: Path, config: dict[str, Any], source_pdf: Path) -> dict[str, Any]:
    bound: dict[str, Any] = {}
    payloads: dict[str, Any] = {}
    for name, spec in config["bound_evidence"].items():
        path = resolve_bound(root, spec["path"])
        require(sha256(path) == spec["sha256"], f"evidence hash mismatch: {name}")
        bound[name] = {"path": spec["path"], "sha256": spec["sha256"], "bytes": path.stat().st_size}
        if path.suffix == ".json":
            payloads[name] = json.loads(path.read_text(encoding="utf-8"))

    source = payloads["source_normalization_receipt"]
    source_spec = source["source"]
    require(source_pdf.is_file() and not source_pdf.is_symlink(), "source PDF unavailable")
    require(sha256(source_pdf) == source_spec["sha256"], "source PDF hash mismatch")
    require(source_pdf.stat().st_size == source_spec["bytes"], "source PDF byte count mismatch")
    require(source_spec["redistribution_authorized"] is False, "draft redistribution status changed")
    require(source_spec["source_file_committed"] is False, "confidential draft marked committed")

    overlap = payloads["overlap_audit"]
    require(overlap["overlap_assessment"]["mcduffie_vs_wildfire_smoke_physical_boundary_resolved"] is True,
            "physical PM source boundary not resolved")
    require(overlap["overlap_assessment"]["air_pollution_mortality_vs_give_temperature_mortality_cleared"] is False,
            "GIVE mortality overlap unexpectedly cleared")

    mcduffie = payloads["mcduffie_primary_source"]
    require(mcduffie["source_supported_facts"]["open_burning_including_wildfire_emissions_included"] is False,
            "nonwildfire PM boundary changed")

    discount_text = resolve_bound(root, config["bound_evidence"]["give_discount_parameters"]["path"]).read_text(encoding="utf-8")
    require("exp(0.001972641) - 1" in discount_text and "eta = 1.244458999" in discount_text,
            "GIVE 2% discount parameterization changed")
    expected_prtp = math.exp(0.001972641) - 1
    target = config["target_normalization"]["discounting"]
    require(math.isclose(target["prtp"], expected_prtp, rel_tol=0, abs_tol=1e-15), "target prtp changed")
    require(target["eta"] == 1.244458999, "target eta changed")
    return bound


def build_row(config: dict[str, Any]) -> dict[str, Any]:
    component = config["component"]
    target = config["target_normalization"]
    boundary = config["boundary_assessment"]
    gates = config["admission_gates"]
    require(component["source_detailed_mean_usd_per_tco2"] == 50.04, "source detailed mean changed")
    require(component["source_rounded_headline_usd_per_tco2"] == 50.0, "source headline changed")
    require(target["price_conversion_factor"] == 1.0, "unnecessary price conversion introduced")
    require(target["pulse_year_conversion"] == "none", "unnecessary pulse conversion introduced")
    require(boundary["wildfire_smoke_vs_nonwildfire_pm_physical_emissions_overlap"] is False,
            "physical source overlap changed")
    require(boundary["wildfire_smoke_vs_nonwildfire_pm_joint_health_function_consistency_cleared"] is False,
            "joint PM health-function gate opened")
    require(boundary["wildfire_smoke_vs_give_temperature_mortality_overlap_cleared"] is False,
            "temperature mortality gate opened")
    blockers = [
        "SOURCE_DISCOUNT_IMPLEMENTATION_UNVERIFIED",
        "NUMERICAL_PULSE_DEFINITION_UNAVAILABLE",
        "ANNUAL_COUNTRY_DRAW_PATHS_UNAVAILABLE",
        "LOCAL_NUMERICAL_REPRODUCTION_FAILED",
        "JOINT_PM_HEALTH_FUNCTION_UNCLEARED",
        "GIVE_TEMPERATURE_MORTALITY_OVERLAP_UNCLEARED",
    ]
    return {
        "component_id": component["component_id"],
        "estimate_role": "source_pinned_normalized_scalar_not_additive",
        "detailed_mean_usd_per_tco2": component["source_detailed_mean_usd_per_tco2"],
        "rounded_headline_usd_per_tco2": component["source_rounded_headline_usd_per_tco2"],
        "interval_low_usd_per_tco2": component["source_interval_low_usd_per_tco2"],
        "interval_high_usd_per_tco2": component["source_interval_high_usd_per_tco2"],
        "interval_level_percent": component["interval_level_percent"],
        "interval_type": component["interval_type"],
        "source_monte_carlo_trials": component["source_monte_carlo_trials"],
        "pulse_year": target["pulse_year"],
        "currency_price_year": target["currency_price_year"],
        "units": target["units"],
        "discount_label": target["discounting"]["label"],
        "discount_prtp": target["discounting"]["prtp"],
        "discount_eta": target["discounting"]["eta"],
        "price_conversion_factor": target["price_conversion_factor"],
        "source_scalar_pinned": gates["source_scalar_pinned"],
        "price_year_aligned": gates["source_price_year_matches_target"],
        "pulse_year_aligned": gates["source_pulse_year_matches_target"],
        "physical_emissions_boundary_separable": True,
        "joint_pm_health_function_cleared": False,
        "give_temperature_mortality_overlap_cleared": False,
        "annual_paths_available": False,
        "local_reproduction_passed": False,
        "additive_to_nonwildfire_air_pollution": False,
        "additive_to_baseline_give": False,
        "blocker_codes": "|".join(blockers),
    }


def write_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerow({key: str(value).lower() if isinstance(value, bool) else value for key, value in row.items()})
    temporary.replace(path)


def build(root: Path, config_path: Path, source_pdf: Path) -> dict[str, Any]:
    config = load_config(config_path)
    bound = validate_evidence(root, config, source_pdf)
    row = build_row(config)
    table = root / config["outputs"]["table"]
    write_csv(table, row)
    return {
        "schema": "wildfire_smoke_integration_contract_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "normalized_scalar_pinned_additive_integration_blocked",
        "source_pdf": {"sha256": sha256(source_pdf), "bytes": source_pdf.stat().st_size, "committed": False},
        "bound_evidence": bound,
        "normalized_result": {
            "component_id": row["component_id"],
            "detailed_mean_usd_per_tco2": row["detailed_mean_usd_per_tco2"],
            "interval_usd_per_tco2": [row["interval_low_usd_per_tco2"], row["interval_high_usd_per_tco2"]],
            "pulse_year": row["pulse_year"],
            "currency_price_year": row["currency_price_year"],
            "price_conversion_applied": False,
            "pulse_year_conversion_applied": False,
        },
        "headline_addition_authorized": False,
        "permitted_use": "external source-pinned scalar benchmark and reproduction target only",
        "output": {"path": config["outputs"]["table"], "sha256": sha256(table), "bytes": table.stat().st_size},
        "config": {"path": str(config_path.relative_to(root)), "sha256": sha256(config_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("config/wildfire_smoke_additive_integration_v1.json"))
    parser.add_argument("--source-pdf", type=Path, default=Path("/Users/jbb/Downloads/Fire_SC_CO2_draft (1).pdf"))
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    receipt = build(root, config_path, args.source_pdf.resolve())
    config = load_config(config_path)
    output = root / config["outputs"]["receipt"]
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "headline_addition_authorized": False}))


if __name__ == "__main__":
    main()
