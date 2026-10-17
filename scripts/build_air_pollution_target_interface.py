#!/usr/bin/env python3
"""Build a price-harmonized, fail-closed air-pollution target interface."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "air_pollution_target_interface_config/v1"
FIELDS = [
    "component_id", "source_group", "source_pulse_year", "target_pulse_year",
    "source_price_year", "target_price_year", "source_mean_usd_per_tco2",
    "target_price_mean_usd_per_tco2", "target_price_interval_low_usd_per_tco2",
    "target_price_interval_high_usd_per_tco2", "interval_level_percent",
    "interval_type", "price_year_harmonized", "pulse_year_harmonized",
    "physical_boundary_resolved", "mortality_overlap_cleared",
    "local_reproduction_passed", "annual_marginal_paths_available",
    "additive_to_baseline_give", "target_role", "blocker_codes",
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
    config = json.loads(path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "unexpected config schema")
    require(len(config.get("components", [])) == 4, "exactly four components required")
    require(config["portfolio_gates"] == {
        "published_price_year_resolved": True,
        "target_price_year_harmonized": True,
        "target_pulse_year_harmonized": False,
        "mortality_overlap_cleared": False,
        "annual_marginal_paths_available": False,
        "all_components_locally_reproduced": False,
        "any_component_additive_to_baseline_give": False,
    }, "portfolio gates differ from audited state")
    return config


def validate_evidence(root: Path, config: dict[str, Any]) -> tuple[dict[str, Any], Decimal]:
    payloads: dict[str, Any] = {}
    bound: dict[str, Any] = {}
    for name, spec in config["bound_evidence"].items():
        path = resolve_bound(root, spec["path"])
        require(sha256(path) == spec["sha256"], f"evidence hash mismatch: {name}")
        payloads[name] = json.loads(path.read_text(encoding="utf-8"))
        bound[name] = {"path": spec["path"], "sha256": spec["sha256"], "bytes": path.stat().st_size}

    primary = payloads["mcduffie_primary_source"]
    require(primary["source_supported_facts"]["currency_price_year"] == 2024,
            "McDuffie price year not supported")
    require(primary["source_supported_facts"]["pulse_year"] == 2030,
            "McDuffie pulse year changed")
    require(primary["source_supported_facts"]["open_burning_including_wildfire_emissions_included"] is False,
            "McDuffie physical boundary changed")
    for spec in primary["local_sources"].values():
        source = resolve_bound(root, spec["path"])
        require(sha256(source) == spec["sha256"], "primary-source artifact hash mismatch")

    conversion = payloads["price_conversion"]
    csv_path = resolve_bound(root, conversion["local_source"]["path"])
    require(sha256(csv_path) == conversion["local_source"]["sha256"], "deflator CSV hash mismatch")
    with csv_path.open(newline="", encoding="utf-8") as handle:
        values = {row["observation_date"][:4]: Decimal(row["A191RD3A086NBEA"])
                  for row in csv.DictReader(handle) if row["A191RD3A086NBEA"] != "."}
    require(values["2020"] == Decimal("105.377") and values["2024"] == Decimal("125.587"),
            "pinned deflator values changed")
    factor = values["2020"] / values["2024"]
    require(factor == Decimal(conversion["conversion"]["multiply_by"]),
            "documented conversion factor changed")

    overlap = payloads["overlap_audit"]
    give_path = resolve_bound(root, overlap["give_baseline"]["source_path"])
    require(sha256(give_path) == overlap["give_baseline"]["sha256"], "GIVE mortality code changed")
    require(overlap["overlap_assessment"]["air_pollution_mortality_vs_give_temperature_mortality_cleared"] is False,
            "mortality overlap unexpectedly cleared")
    require(overlap["decision"]["any_air_pollution_component_additive_to_baseline_give"] is False,
            "overlap audit unexpectedly permits addition")

    admission = payloads["wildfire_smoke_admission"]
    require(admission["status"] == "rejected_incomplete_local_artifacts", "smoke admission changed")
    require(admission["operational_artifact_admission"]["groups_passed"] == 0,
            "smoke artifacts unexpectedly admitted")
    return bound, factor


def money(value: float, factor: Decimal) -> str:
    return str((Decimal(str(value)) * factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def validate_and_transform(config: dict[str, Any], factor: Decimal) -> list[dict[str, Any]]:
    target = config["target"]
    rows = []
    for component in config["components"]:
        require(component["additive_to_baseline_give"] is False, "component promoted to additive")
        require(component["mortality_overlap_cleared"] is False, "mortality overlap promoted")
        require(component["local_reproduction_passed"] is False, "component promoted to reproduction")
        require(component["annual_marginal_paths_available"] is False, "annual paths invented")
        price_factor = Decimal("1") if component["source_price_year"] == target["currency_price_year"] else factor
        pulse_harmonized = component["source_pulse_year"] == target["pulse_year"]
        blockers = set(component["blocker_codes"])
        require(("PULSE_YEAR_UNHARMONIZED" in blockers) == (not pulse_harmonized),
                "pulse-year blocker inconsistent")
        require("MORTALITY_OVERLAP_UNCLEARED" in blockers, "missing mortality-overlap blocker")
        row = {
            "component_id": component["component_id"],
            "source_group": component["source_group"],
            "source_pulse_year": component["source_pulse_year"],
            "target_pulse_year": target["pulse_year"],
            "source_price_year": component["source_price_year"],
            "target_price_year": target["currency_price_year"],
            "source_mean_usd_per_tco2": component["source_mean"],
            "target_price_mean_usd_per_tco2": money(component["source_mean"], price_factor),
            "target_price_interval_low_usd_per_tco2": money(component["source_interval_low"], price_factor),
            "target_price_interval_high_usd_per_tco2": money(component["source_interval_high"], price_factor),
            "interval_level_percent": component["interval_level_percent"],
            "interval_type": component["interval_type"],
            "price_year_harmonized": True,
            "pulse_year_harmonized": pulse_harmonized,
            "physical_boundary_resolved": component["physical_boundary_resolved"],
            "mortality_overlap_cleared": False,
            "local_reproduction_passed": False,
            "annual_marginal_paths_available": False,
            "additive_to_baseline_give": False,
            "target_role": component["target_role"],
            "blocker_codes": "|".join(component["blocker_codes"]),
        }
        rows.append(row)
    require(len({row["component_id"] for row in rows}) == 4, "duplicate component ID")
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: str(value).lower() if isinstance(value, bool) else value
                             for key, value in row.items()})
    temporary.replace(path)


def build(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    bound, factor = validate_evidence(root, config)
    rows = validate_and_transform(config, factor)
    table = root / config["outputs"]["table"]
    write_csv(table, rows)
    return {
        "schema": "air_pollution_target_interface_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "price_harmonized_target_interface_blocked_from_give_addition",
        "target": config["target"],
        "price_conversion_factor_2024usd_to_2020usd": str(factor),
        "rows": len(rows),
        "bound_evidence": bound,
        "output": {"path": config["outputs"]["table"], "sha256": sha256(table), "bytes": table.stat().st_size},
        "portfolio_gates": config["portfolio_gates"],
        "permitted_use": "comparison and sensitivity benchmark only; not additive to baseline GIVE",
        "config": {"path": str(config_path.relative_to(root)), "sha256": sha256(config_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("config/air_pollution_target_interface_v1.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    receipt = build(root, config_path)
    config = load_config(config_path)
    output = root / config["outputs"]["receipt"]
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "rows": receipt["rows"]}))


if __name__ == "__main__":
    main()
