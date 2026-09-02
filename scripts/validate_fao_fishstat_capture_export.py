#!/usr/bin/env python3
"""Independently reconcile a symbol-preserving FAO FishStat wide export."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import tomllib
from collections import Counter
from pathlib import Path


SCHEMA = "fao_fishstat_capture_headless_export_contract_v1"
ROLE = "observed_capture_record_integrity_gate_not_fishmip_calibration_allocation_welfare_damage_or_scc"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def validate(contract_path: Path, csv_path: Path, source_audit_path: Path, root: Path) -> dict[str, object]:
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    require(contract.get("schema") == SCHEMA and contract.get("role") == ROLE, "contract identity changed")
    source = contract["source"]
    export = contract["export"]
    boundaries = contract["boundaries"]
    require(source["workspace_version"] == "2026.1.0", "workspace version changed")
    require(source["annual_start_year"] == 1950 and source["annual_end_year"] == 2024, "year range changed")
    require(export["sort_key"] == "source_record_id", "sort key changed")
    require(export["require_complete_reference_joins"] is True, "reference join gate changed")
    require(export["require_nonblank_value_status_pairs"] is True, "value/status gate changed")
    for gate, value in boundaries.items():
        require(value is False, f"closed boundary changed: {gate}")

    audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    require(audit.get("schema") == "fao_fishstat_capture_headless_source_audit_v1", "source audit identity changed")
    require(audit.get("source_table") == source["capture_table"], "source table changed")
    require(audit.get("years") == [1950, 2024], "source audit years changed")
    require(audit["output"]["bytes"] == csv_path.stat().st_size, "CSV byte count changed")
    require(audit["output"]["sha256"] == digest(csv_path), "CSV SHA-256 changed")

    years = list(range(1950, 2025))
    fixed = [
        "source_record_id", "country_un_m49", "country_iso3", "country_name",
        "species_asfis_code", "species_scientific_name", "species_name",
        "fao_area_code", "fao_area_name", "environment_class",
        "measure_code", "measure_name", "unit", "unit_multiplier",
    ]
    expected_header = fixed + [item for year in years for item in (f"value_{year}", f"status_{year}")]
    allowed_status = set(export["required_status_codes"])
    allowed_measure = set(export["allowed_measure_codes"])
    allowed_environment = set(export["allowed_environment_classes"])
    nullable_resolved = set(export["nullable_resolved_fields"])
    require(nullable_resolved == {"country_iso3", "species_name"}, "nullable reference fields changed")
    status_counts: Counter[str] = Counter()
    blank_resolved_counts: Counter[str] = Counter()
    measure_counts: Counter[str] = Counter()
    environment_counts: Counter[str] = Counter({"inland": 0, "marine": 0})
    rows = annual_cells = positive = zeros = 0
    last_id = ""
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == expected_header, "CSV schema changed")
        for row in reader:
            record_id = row["source_record_id"]
            require(record_id and (not last_id or record_id > last_id), "record IDs are not strictly increasing")
            last_id = record_id
            for field in fixed:
                if row[field] == "":
                    require(field in nullable_resolved, f"blank resolved field: {field}")
                    blank_resolved_counts[field] += 1
            require(row["environment_class"] in allowed_environment, "unknown environment class")
            require(row["measure_code"] in allowed_measure, "unknown measure code")
            environment_counts[row["environment_class"]] += 1
            measure_counts[row["measure_code"]] += 1
            rows += 1
            for year in years:
                value_text = row[f"value_{year}"]
                status = row[f"status_{year}"]
                require(value_text != "" and status != "", "blank annual value/status pair")
                require(status in allowed_status, f"unknown status code: {status}")
                value = float(value_text)
                require(math.isfinite(value) and value >= 0, "invalid annual value")
                positive += value > 0
                zeros += value == 0
                annual_cells += 1
                status_counts[status] += 1

    require(rows == source["wide_record_count"], "wide record count changed")
    require(annual_cells == rows * len(years), "annual cell count changed")
    source_counts = audit["counts"]
    require(source_counts["wide_records"] == rows, "source/export record reconciliation failed")
    require(source_counts["annual_cells"] == annual_cells, "source/export annual-cell reconciliation failed")
    require(source_counts["positive_value_cells"] == positive, "positive-value reconciliation failed")
    require(source_counts["zero_value_cells"] == zeros, "zero-value reconciliation failed")
    require(source_counts["status_cells"] == dict(sorted(status_counts.items())), "status reconciliation failed")
    require(source_counts["measure_records"] == dict(sorted(measure_counts.items())), "measure reconciliation failed")
    require(source_counts["environment_records"] == dict(sorted(environment_counts.items())), "environment reconciliation failed")
    require(source_counts["value_null_cells"] == source_counts["status_blank_cells"] == 0, "source contained blank annual pairs")

    return {
        "schema": "fao_fishstat_capture_headless_export_validation_v1",
        "status": "wide_export_reconciled_value_and_status_pairs_preserved",
        "contract": {"path": contract_path.name if not contract_path.resolve().is_relative_to(root.resolve()) else contract_path.resolve().relative_to(root.resolve()).as_posix(), "sha256": digest(contract_path)},
        "implementation": {"path": Path(__file__).resolve().relative_to(root.resolve()).as_posix(), "sha256": digest(Path(__file__))},
        "export": {"path": export["canonical_filename"], "bytes": csv_path.stat().st_size, "sha256": digest(csv_path)},
        "records": rows,
        "annual_cells": annual_cells,
        "years": [years[0], years[-1]],
        "environment_records": dict(sorted(environment_counts.items())),
        "measure_records": dict(sorted(measure_counts.items())),
        "status_cells": dict(sorted(status_counts.items())),
        "blank_nullable_resolved_fields": dict(sorted(blank_resolved_counts.items())),
        "positive_value_cells": positive,
        "zero_value_cells": zeros,
        "fishstat_gui_menu_export_reconciled": False,
        "marine_tonnage_filter_authorized": False,
        "country_or_eez_allocation_authorized": False,
        "fishmip_observed_calibration_authorized": False,
        "welfare_translation_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.contract.resolve(), args.csv.resolve(), args.source_audit.resolve(), args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FAO FishStat capture export reconciliation passed")


if __name__ == "__main__":
    main()
