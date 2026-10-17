#!/usr/bin/env python3
"""Build a fail-closed scalar benchmark interface for air-pollution SCC evidence."""

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
SCHEMA = "air_pollution_literature_bridge_config/v1"
FIELDS = [
    "component_id", "physical_boundary", "source_type", "source_id", "pulse_year",
    "discounting", "currency_price_year", "mean_usd_per_tco2",
    "interval_low_usd_per_tco2", "interval_high_usd_per_tco2",
    "interval_level_percent", "interval_type", "locally_reproduced",
    "additive_to_give",
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
    workspace = root.parent.resolve()
    require(path.is_file() and not path.is_symlink(), f"missing regular evidence: {relative}")
    require(workspace in path.parents, f"evidence escapes GIVE workspace: {relative}")
    return path


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "unexpected config schema")
    require(config.get("benchmarks") and len(config["benchmarks"]) == 4,
            "exactly four registered benchmark rows required")
    require(set(config["hard_gates"].values()) == {False}, "hard gates must remain closed")
    return config


def validate_evidence(root: Path, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bound: dict[str, dict[str, Any]] = {}
    payloads: dict[str, dict[str, Any]] = {}
    for name, spec in config["bound_evidence"].items():
        path = resolve_bound(root, spec["path"])
        require(sha256(path) == spec["sha256"], f"evidence hash mismatch: {name}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(isinstance(payload, dict), f"evidence is not a JSON object: {name}")
        payloads[name] = payload
        bound[name] = {"path": spec["path"], "sha256": spec["sha256"], "bytes": path.stat().st_size}

    smoke = payloads["wildfire_smoke_draft_receipt"]
    admission = payloads["wildfire_smoke_admission"]
    epa = payloads["epa_article_source"]
    primary = payloads["mcduffie_primary_article_benchmark"]
    gate = payloads["epa_component_net_gate"]
    require(smoke["reported_global_partial_scc_2025_usd_per_tco2"] == 50.0,
            "smoke central benchmark changed")
    require(smoke["reported_conditional_95pct_interval"] == [18.5, 102.6],
            "smoke interval changed")
    require(admission["status"] == "rejected_incomplete_local_artifacts",
            "smoke admission status changed")
    require(admission["operational_artifact_admission"]["groups_passed"] == 0,
            "smoke admission group count changed")
    article = epa["article_reported_2pct_ramsey_usd_per_tco2"]
    require(article == {"ozone": 23.0, "pm25_nonwildfire_meteorological": -38.0, "net": -15.0},
            "EPA article benchmarks changed")
    primary_values = primary["reported_global_npv_usd_per_metric_ton_co2"]
    require(primary_values["surface_ozone"] == {
        "mean": 23.0, "median": 20.0, "interval_level_percent": 90,
        "interval_low": 7.0, "interval_high": 45.0,
    }, "primary-article ozone benchmark changed")
    require(primary_values["pm25"] == {
        "mean": -38.0, "median": -24.0, "interval_level_percent": 90,
        "interval_low": -118.0, "interval_high": -3.0,
    }, "primary-article PM2.5 benchmark changed")
    require(primary_values["net"] == {
        "mean": -15.0, "median": -2.0, "interval_level_percent": 90,
        "interval_low": -103.0, "interval_high": 30.0,
    }, "primary-article net benchmark changed")
    require(primary["local_reproduction_claimed"] is False and
            primary["give_transfer_authorized"] is False,
            "primary-article receipt promoted beyond evidence")
    require(gate["status"] == "blocked_final_article_artifacts_and_metadata_unavailable",
            "EPA reproduction gate changed")
    require(set(gate["hard_gates"].values()) == {False}, "EPA hard gate unexpectedly opened")
    return bound


def validate_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = config["benchmarks"]
    require(len({row["component_id"] for row in rows}) == len(rows), "duplicate component_id")
    by_id = {row["component_id"]: row for row in rows}
    require(by_id["wildfire_smoke_pm25_mortality"]["mean_usd_per_tco2"] == 50.0,
            "smoke benchmark differs from evidence")
    require(by_id["surface_ozone_health"]["mean_usd_per_tco2"] == 23.0,
            "ozone benchmark differs from evidence")
    require(by_id["nonwildfire_meteorological_pm25_health"]["mean_usd_per_tco2"] == -38.0,
            "PM2.5 benchmark differs from evidence")
    require(by_id["meteorological_ozone_pm25_net"]["mean_usd_per_tco2"] == -15.0,
            "net benchmark differs from evidence")
    require(23.0 + -38.0 == -15.0, "published component arithmetic changed")
    for row in rows:
        require(set(row) == set(FIELDS), f"unexpected benchmark fields: {row.get('component_id')}")
        require(isinstance(row["mean_usd_per_tco2"], (int, float)) and
                math.isfinite(row["mean_usd_per_tco2"]), "non-finite mean")
        require(row["locally_reproduced"] is False, "unreproduced benchmark promoted")
        require(row["additive_to_give"] is False, "benchmark marked additive")
        low, high, level = (row["interval_low_usd_per_tco2"],
                            row["interval_high_usd_per_tco2"], row["interval_level_percent"])
        require((low is None) == (high is None) == (level is None), "partial interval metadata")
        if low is not None:
            require(low <= row["mean_usd_per_tco2"] <= high, "mean outside interval")
            require(0 < level < 100, "invalid interval level")
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if row[key] is None else str(row[key]).lower()
                             if isinstance(row[key], bool) else row[key] for key in FIELDS})
    temporary.replace(path)


def build(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    evidence = validate_evidence(root, config)
    rows = validate_rows(config)
    table_path = root / config["outputs"]["table"]
    write_csv(table_path, rows)
    return {
        "schema": "air_pollution_literature_bridge_receipt/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "external_benchmarks_exported_not_additive",
        "give_interface": {
            "kind": "scalar_partial_scc_benchmark_table",
            "units": "USD per metric ton CO2",
            "row_count": len(rows),
            "eligible_for_headline_scc": False,
            "annual_country_damage_paths_available": False,
        },
        "bound_evidence": evidence,
        "output": {
            "path": str(table_path.relative_to(root)),
            "sha256": sha256(table_path),
            "bytes": table_path.stat().st_size,
        },
        "component_ids": [row["component_id"] for row in rows],
        "hard_gates": config["hard_gates"],
        "claim_limits": [
            "Values are source-reported benchmarks, not new estimates.",
            "No benchmark is added to baseline GIVE or to another component.",
            "Wildfire smoke and nonwildfire meteorological PM2.5 remain separate.",
            "The wildfire-smoke interval is conditional, not full structural uncertainty.",
            "EPA currency year, final-release reproduction, and same-stream additivity remain unresolved.",
        ],
        "config": {"path": str(config_path.relative_to(root)), "sha256": sha256(config_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path,
                        default=Path("config/air_pollution_literature_bridge_v1.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_config(config_path)
    receipt = build(root, config_path)
    receipt_path = root / config["outputs"]["receipt"]
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt_path.with_suffix(receipt_path.suffix + ".partial")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(receipt_path)
    print(json.dumps({"status": receipt["status"], "rows": receipt["give_interface"]["row_count"]}))


if __name__ == "__main__":
    main()
