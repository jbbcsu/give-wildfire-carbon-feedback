#!/usr/bin/env python3
"""Validate the FishStat symbol-preserving CSV export contract before execution."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(contract_path: Path, root: Path) -> dict[str, object]:
    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
    require(contract.get("schema") == "fao_fishstat_capture_csv_export_contract_v1", "schema changed")
    source = contract.get("source", {})
    for path_key, hash_key in (("workspace_contract", "workspace_contract_sha256"), ("source_validation", "source_validation_sha256")):
        path = root / str(source[path_key])
        require(sha256(path) == source[hash_key], f"source receipt changed: {path_key}")
    for key in ("database", "derby_jar", "jjs"):
        require((root / str(source[key])).exists(), f"export runtime input missing: {key}")
    export = contract.get("export", {})
    require(export.get("table") == "TSD_CAPTURE_QUANTITY", "capture table changed")
    require(export.get("key_columns") == ["COUNTRY", "SPECIES", "AREA", "MEASURE"], "record keys changed")
    require((export.get("annual_start_year"), export.get("annual_end_year")) == (1950, 2024), "annual range changed")
    require(export.get("annual_column_pattern") == ["VALUE_Y{year}", "SYMBOL_Y{year}"], "value/symbol pairing changed")
    require(export.get("order_by") == export.get("key_columns"), "deterministic row order changed")
    require(export.get("encoding") == "UTF-8" and export.get("delimiter") == "," and export.get("line_ending") == "LF", "CSV encoding changed")
    require(export.get("null_serialization") == "empty CSV field; never zero", "null handling changed")
    execution = contract.get("execution", {})
    require(execution.get("database_copy_required") is True and execution.get("source_database_write_forbidden") is True, "source database isolation changed")
    require(execution.get("select_only") is True and execution.get("query_filter") == "none", "export selection changed")
    require(execution.get("record_export_completed") is False, "pre-execution gate changed")
    reconciliation = contract.get("reconciliation", {})
    for gate in ("exact_header_required", "exact_database_and_csv_row_count_required", "exact_key_order_required", "annual_value_columns_preserved", "annual_symbol_columns_preserved", "missing_and_suppressed_symbols_never_zero_filled"):
        require(reconciliation.get(gate) is True, f"reconciliation gate changed: {gate}")
    for gate in ("duplicate_key_rows_allowed", "marine_only_filter_validated", "country_iso3_crosswalk_validated", "fao_area_crosswalk_validated", "fishmip_calibration_authorized", "welfare_translation_authorized", "damage_or_scc_authorized"):
        require(reconciliation.get(gate) is False, f"closed gate changed: {gate}")
    columns = list(export["key_columns"])
    for year in range(1950, 2025):
        columns.extend([f"VALUE_Y{year}", f"SYMBOL_Y{year}"])
    return {
        "schema": "fao_fishstat_capture_csv_export_preregistration_v1",
        "status": "preregistered_before_record_export",
        "contract_sha256": sha256(contract_path),
        "implementation_sha256": sha256(Path(__file__)),
        "table": export["table"],
        "columns": columns,
        "column_count": len(columns),
        "output": export["output"],
        "record_export_completed": False,
        "fishmip_calibration_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.contract.resolve(), args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FishStat symbol-preserving CSV export preregistration passed")


if __name__ == "__main__":
    main()
