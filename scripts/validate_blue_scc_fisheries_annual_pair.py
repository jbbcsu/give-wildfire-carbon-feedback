#!/usr/bin/env python3
"""Fail-closed admission checks for requested Blue-SCC fisheries artifacts.

The package mode imports matched, undiscounted annual baseline/pulse country
paths and validates their provenance, support, semantics, and additivity.  The
public-summary mode demonstrates why the released SCC summaries are not an
admissible substitute.  Neither mode calculates a damage function or SCC.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "blue_scc_fisheries_annual_pair_v1"
SCHEMA_ID = "https://give.local/contracts/blue-scc-fisheries-annual-pair-v1.schema.json"
MAX_ANNUAL_ROWS_PER_PATH = 100_000
ANNUAL_FIELDS = (
    "run_id", "pulse_id", "run_configuration_id", "draw_id", "country_iso3",
    "year", "consumer_surplus", "producer_surplus", "currency", "price_year",
    "time_basis", "missingness_status",
)
MAPPING_FIELDS = (
    "source_country_key", "country_iso3", "give_country_id",
    "coefficient_available", "annual_path_available", "missingness_status",
    "missingness_reason",
)
GLOBAL_FIELDS = (
    "path_role", "run_id", "pulse_id", "run_configuration_id", "draw_id",
    "year", "consumer_surplus", "producer_surplus", "market_total", "currency",
    "price_year", "time_basis", "missingness_status",
)
FILE_ROLES = {"baseline_path", "pulse_path", "country_mapping", "global_reconciliation"}
EXCLUDED_BOUNDARY_FLAGS = (
    "includes_nutrition_or_mortality",
    "includes_indirect_or_induced_output",
    "uses_accounting_profit_as_producer_surplus",
    "uses_gross_revenue_as_welfare",
    "includes_aquaculture",
    "includes_coral_or_reef_services",
    "includes_biodiversity_nonuse_value",
    "includes_ciam_coastal_impacts",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_fields(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == fields, f"{label} fields changed or are incomplete")
    return value


def finite(value: Any, label: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be numeric")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    if positive:
        require(number > 0, f"{label} must be positive")
    if nonnegative:
        require(number >= 0, f"{label} must be nonnegative")
    return number


def csv_number(value: str, label: str) -> float:
    require(value.strip() != "", f"{label} is missing")
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"{label} is not numeric") from error
    require(math.isfinite(number), f"{label} must be finite")
    return number


def csv_integer(value: str, label: str) -> int:
    require(re.fullmatch(r"-?[0-9]+", value or "") is not None, f"{label} must be an integer")
    return int(value)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(left: float, right: float, absolute: float, relative: float) -> bool:
    return math.isclose(left, right, abs_tol=absolute, rel_tol=relative)


def validate_schema_identity(schema: dict[str, Any]) -> None:
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "unexpected JSON Schema dialect")
    require(schema.get("$id") == SCHEMA_ID, "contract schema id changed")
    require(schema.get("properties", {}).get("contract_version", {}).get("const") == CONTRACT_VERSION, "contract version changed")
    required = set(schema.get("required", []))
    require(required == {"contract_version", "bundle_id", "authorization", "source", "license", "files", "pulse", "coverage", "units", "welfare_boundary", "reconciliation"}, "manifest top-level contract changed")


def validate_manifest(manifest: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema_identity(schema)
    top = set(schema["required"])
    exact_fields(manifest, top, "manifest")
    require(manifest["contract_version"] == CONTRACT_VERSION, "wrong contract version")
    require(isinstance(manifest["bundle_id"], str) and manifest["bundle_id"].strip(), "bundle_id must be nonblank")

    authorization = exact_fields(manifest["authorization"], {"purpose", "import", "damage_function", "discounting", "scc"}, "authorization")
    require(authorization == {"purpose": "artifact_admission_only", "import": True, "damage_function": False, "discounting": False, "scc": False}, "authorization must forbid damage, discounting, and SCC")

    source = exact_fields(manifest["source"], {"repository_url", "repository_commit", "paper_doi", "derivation_id"}, "source")
    for name in ("repository_url", "paper_doi", "derivation_id"):
        require(isinstance(source[name], str) and source[name].strip(), f"source {name} must be nonblank")
    require(re.fullmatch(r"[0-9a-f]{40}", str(source["repository_commit"])) is not None, "source repository_commit must be a full commit")

    license_record = exact_fields(manifest["license"], {"license_id", "rights_holder", "redistribution_allowed", "derivative_use_allowed", "give_research_use_allowed", "attribution_text", "third_party_restrictions"}, "license")
    require(license_record["license_id"] not in {"", "NONE", "NOASSERTION"}, "license_id is unresolved")
    for name in ("rights_holder", "attribution_text"):
        require(isinstance(license_record[name], str) and license_record[name].strip(), f"license {name} must be nonblank")
    for name in ("redistribution_allowed", "derivative_use_allowed", "give_research_use_allowed"):
        require(license_record[name] is True, f"license does not explicitly permit {name}")
    require(license_record["third_party_restrictions"] == [], "unresolved third-party restrictions fail closed")

    files = exact_fields(manifest["files"], FILE_ROLES, "files")
    for role, record in files.items():
        record = exact_fields(record, {"relative_path", "sha256", "byte_size", "format", "media_type"}, f"files.{role}")
        require(isinstance(record["relative_path"], str) and record["relative_path"].strip(), f"files.{role} relative_path is blank")
        require(re.fullmatch(r"[0-9a-f]{64}", str(record["sha256"])) is not None, f"files.{role} sha256 is invalid")
        require(isinstance(record["byte_size"], int) and not isinstance(record["byte_size"], bool) and record["byte_size"] > 0, f"files.{role} byte_size is invalid")
        require(record["format"] == "csv" and record["media_type"] == "text/csv", f"files.{role} must be CSV")

    pulse = exact_fields(manifest["pulse"], {"pulse_id", "gas", "mass", "mass_unit", "pulse_year", "baseline_run_id", "pulse_run_id", "run_configuration_id", "climate_module", "socioeconomic_scenario", "discounting_applied"}, "pulse")
    for name in ("pulse_id", "baseline_run_id", "pulse_run_id", "run_configuration_id", "climate_module", "socioeconomic_scenario"):
        require(isinstance(pulse[name], str) and pulse[name].strip(), f"pulse {name} must be nonblank")
    require(pulse["baseline_run_id"] != pulse["pulse_run_id"], "baseline and pulse run IDs must differ")
    require(pulse["gas"] == "CO2" and pulse["mass_unit"] == "tCO2", "pulse must be explicit tCO2")
    finite(pulse["mass"], "pulse mass", positive=True)
    require(isinstance(pulse["pulse_year"], int) and not isinstance(pulse["pulse_year"], bool) and 1900 <= pulse["pulse_year"] <= 2300, "pulse year is invalid")
    require(pulse["discounting_applied"] is False, "annual input paths must be undiscounted")

    coverage = exact_fields(manifest["coverage"], {"country_count", "start_year", "end_year", "draw_ids", "complete", "missingness_rule"}, "coverage")
    require(isinstance(coverage["country_count"], int) and not isinstance(coverage["country_count"], bool) and coverage["country_count"] > 0, "country_count is invalid")
    require(all(isinstance(coverage[name], int) and not isinstance(coverage[name], bool) for name in ("start_year", "end_year")), "coverage years must be integers")
    require(1900 <= coverage["start_year"] <= coverage["end_year"] <= 2300, "coverage year range is invalid")
    draw_ids = coverage["draw_ids"]
    require(isinstance(draw_ids, list) and draw_ids and len(draw_ids) == len(set(draw_ids)), "draw_ids must be a nonempty unique list")
    require(all(isinstance(item, str) and item.strip() for item in draw_ids), "draw_ids must be nonblank strings")
    require(coverage["complete"] is True and coverage["missingness_rule"] == "explicit_no_zero_fill_imputation_or_renormalization", "coverage must be complete without imputation")
    expected_rows = coverage["country_count"] * (coverage["end_year"] - coverage["start_year"] + 1) * len(draw_ids)
    require(expected_rows <= MAX_ANNUAL_ROWS_PER_PATH, f"declared path exceeds the {MAX_ANNUAL_ROWS_PER_PATH}-row memory guard")

    units = exact_fields(manifest["units"], {"currency", "price_year", "time_basis", "value_basis"}, "units")
    require(units["currency"] == "USD" and units["time_basis"] == "annual_flow" and units["value_basis"] == "undiscounted_direct_welfare_level", "units/value basis is not admissible")
    require(isinstance(units["price_year"], int) and not isinstance(units["price_year"], bool) and 1900 <= units["price_year"] <= 2300, "price_year is invalid")

    boundary_fields = {"market_measure", "consumer_component", "producer_component", "nutrition_mortality_treatment", *EXCLUDED_BOUNDARY_FLAGS, "overlap_review_status", "accounting_boundary_id"}
    boundary = exact_fields(manifest["welfare_boundary"], boundary_fields, "welfare_boundary")
    require(boundary["market_measure"] == "direct_consumer_plus_producer_surplus", "market measure must be direct CS+PS")
    require(boundary["consumer_component"] == "consumer_surplus" and boundary["producer_component"] == "producer_surplus", "CS/PS semantics are unresolved")
    require(boundary["nutrition_mortality_treatment"] == "excluded_and_not_present_in_market_paths", "nutrition/mortality must be explicitly separate")
    for name in EXCLUDED_BOUNDARY_FLAGS:
        require(boundary[name] is False, f"overlap boundary failed: {name}")
    require(boundary["overlap_review_status"] == "passed", "overlap review has not passed")
    require(isinstance(boundary["accounting_boundary_id"], str) and boundary["accounting_boundary_id"].strip(), "accounting boundary ID is blank")

    reconciliation = exact_fields(manifest["reconciliation"], {"absolute_tolerance", "relative_tolerance", "country_paths_add_to_global", "market_total_equals_consumer_plus_producer"}, "reconciliation")
    absolute = finite(reconciliation["absolute_tolerance"], "absolute tolerance", nonnegative=True)
    relative = finite(reconciliation["relative_tolerance"], "relative tolerance", nonnegative=True)
    require(reconciliation["country_paths_add_to_global"] is True and reconciliation["market_total_equals_consumer_plus_producer"] is True, "additive identities must be required")
    return {"expected_rows": expected_rows, "absolute": absolute, "relative": relative}


def resolve_files(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    package_root = manifest_path.resolve().parent
    resolved: dict[str, Path] = {}
    for role, record in manifest["files"].items():
        candidate = package_root / record["relative_path"]
        require(not candidate.is_symlink(), f"files.{role} may not be a symlink")
        path = candidate.resolve()
        require(path.is_relative_to(package_root), f"files.{role} escapes the package directory")
        require(path.is_file(), f"files.{role} is absent")
        require(path.stat().st_size == record["byte_size"], f"files.{role} byte size mismatch")
        require(sha256(path) == record["sha256"], f"files.{role} sha256 mismatch")
        require(path not in resolved.values(), "file roles must use distinct files")
        resolved[role] = path
    return resolved


def rows(path: Path, expected_fields: tuple[str, ...]):
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == list(expected_fields), f"{path.name} columns changed")
        for line, row in enumerate(reader, 2):
            require(None not in row and all(value is not None for value in row.values()), f"{path.name}:{line} is malformed")
            yield line, row


def read_mapping(path: Path, manifest: dict[str, Any]) -> set[str]:
    countries: set[str] = set()
    source_keys: set[str] = set()
    give_ids: set[str] = set()
    for line, row in rows(path, MAPPING_FIELDS):
        require(row["source_country_key"].strip() and row["source_country_key"] not in source_keys, f"{path.name}:{line} source country key is blank or duplicated")
        require(re.fullmatch(r"[A-Z]{3}", row["country_iso3"]) is not None and row["country_iso3"] not in countries, f"{path.name}:{line} ISO3 is invalid or duplicated")
        require(row["give_country_id"].strip() and row["give_country_id"] not in give_ids, f"{path.name}:{line} GIVE country ID is blank or duplicated")
        require(row["coefficient_available"] == "true" and row["annual_path_available"] == "true", f"{path.name}:{line} mapping support is incomplete")
        require(row["missingness_status"] == "complete" and row["missingness_reason"] == "", f"{path.name}:{line} unresolved mapping missingness")
        source_keys.add(row["source_country_key"])
        countries.add(row["country_iso3"])
        give_ids.add(row["give_country_id"])
    require(len(countries) == manifest["coverage"]["country_count"], "country mapping count does not match manifest")
    return countries


def read_path(path: Path, role: str, manifest: dict[str, Any], countries: set[str], expected_rows: int) -> tuple[dict[tuple[str, str, int], tuple[float, float]], dict[tuple[str, int], tuple[float, float]]]:
    pulse = manifest["pulse"]
    coverage = manifest["coverage"]
    units = manifest["units"]
    expected_run = pulse[f"{role}_run_id"]
    draw_ids = set(coverage["draw_ids"])
    values: dict[tuple[str, str, int], tuple[float, float]] = {}
    sums: dict[tuple[str, int], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for line, row in rows(path, ANNUAL_FIELDS):
        require(len(values) < MAX_ANNUAL_ROWS_PER_PATH, f"{path.name} exceeds row guard")
        require(row["run_id"] == expected_run and row["pulse_id"] == pulse["pulse_id"] and row["run_configuration_id"] == pulse["run_configuration_id"], f"{path.name}:{line} run pairing metadata mismatch")
        require(row["draw_id"] in draw_ids and row["country_iso3"] in countries, f"{path.name}:{line} undeclared draw or country")
        year = csv_integer(row["year"], f"{path.name}:{line} year")
        require(coverage["start_year"] <= year <= coverage["end_year"], f"{path.name}:{line} year outside declared coverage")
        require(row["currency"] == units["currency"] and csv_integer(row["price_year"], f"{path.name}:{line} price_year") == units["price_year"] and row["time_basis"] == units["time_basis"], f"{path.name}:{line} unit mismatch")
        require(row["missingness_status"] == "complete", f"{path.name}:{line} is not complete")
        consumer = csv_number(row["consumer_surplus"], f"{path.name}:{line} consumer_surplus")
        producer = csv_number(row["producer_surplus"], f"{path.name}:{line} producer_surplus")
        key = (row["draw_id"], row["country_iso3"], year)
        require(key not in values, f"{path.name}:{line} duplicate path key")
        values[key] = (consumer, producer)
        sums[(row["draw_id"], year)][0] += consumer
        sums[(row["draw_id"], year)][1] += producer
    require(len(values) == expected_rows, f"{path.name} is not a complete draw-country-year rectangle")
    return values, {key: (value[0], value[1]) for key, value in sums.items()}


def validate_global(path: Path, manifest: dict[str, Any], path_sums: dict[str, dict[tuple[str, int], tuple[float, float]]]) -> tuple[int, float]:
    pulse = manifest["pulse"]
    coverage = manifest["coverage"]
    units = manifest["units"]
    absolute = manifest["reconciliation"]["absolute_tolerance"]
    relative = manifest["reconciliation"]["relative_tolerance"]
    observed: dict[tuple[str, str, int], tuple[float, float, float]] = {}
    max_error = 0.0
    for line, row in rows(path, GLOBAL_FIELDS):
        role = row["path_role"]
        require(role in {"baseline", "pulse"}, f"{path.name}:{line} invalid path role")
        require(row["run_id"] == pulse[f"{role}_run_id"] and row["pulse_id"] == pulse["pulse_id"] and row["run_configuration_id"] == pulse["run_configuration_id"], f"{path.name}:{line} run pairing metadata mismatch")
        year = csv_integer(row["year"], f"{path.name}:{line} year")
        aggregate_key = (row["draw_id"], year)
        require(row["draw_id"] in set(coverage["draw_ids"]) and coverage["start_year"] <= year <= coverage["end_year"], f"{path.name}:{line} undeclared draw or year")
        require(row["currency"] == units["currency"] and csv_integer(row["price_year"], f"{path.name}:{line} price_year") == units["price_year"] and row["time_basis"] == units["time_basis"], f"{path.name}:{line} unit mismatch")
        require(row["missingness_status"] == "complete", f"{path.name}:{line} is not complete")
        consumer = csv_number(row["consumer_surplus"], f"{path.name}:{line} consumer_surplus")
        producer = csv_number(row["producer_surplus"], f"{path.name}:{line} producer_surplus")
        total = csv_number(row["market_total"], f"{path.name}:{line} market_total")
        key = (role, row["draw_id"], year)
        require(key not in observed, f"{path.name}:{line} duplicate global key")
        require(aggregate_key in path_sums[role], f"{path.name}:{line} has no country aggregate")
        expected_consumer, expected_producer = path_sums[role][aggregate_key]
        comparisons = ((consumer, expected_consumer), (producer, expected_producer), (total, consumer + producer))
        for left, right in comparisons:
            max_error = max(max_error, abs(left - right))
            require(close(left, right, absolute, relative), f"{path.name}:{line} additive reconciliation failed")
        observed[key] = (consumer, producer, total)
    expected_global_rows = 2 * len(coverage["draw_ids"]) * (coverage["end_year"] - coverage["start_year"] + 1)
    require(len(observed) == expected_global_rows, "global reconciliation coverage is incomplete")
    for draw_id in coverage["draw_ids"]:
        for year in range(coverage["start_year"], coverage["end_year"] + 1):
            baseline = observed[("baseline", draw_id, year)]
            pulse_row = observed[("pulse", draw_id, year)]
            country_baseline = path_sums["baseline"][(draw_id, year)]
            country_pulse = path_sums["pulse"][(draw_id, year)]
            for component in range(2):
                global_delta = pulse_row[component] - baseline[component]
                country_delta = country_pulse[component] - country_baseline[component]
                max_error = max(max_error, abs(global_delta - country_delta))
                require(close(global_delta, country_delta, absolute, relative), "baseline/pulse country deltas do not add to the global delta")
    return len(observed), max_error


def validate_package(manifest_path: Path, schema_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    limits = validate_manifest(manifest, schema)
    files = resolve_files(manifest_path, manifest)
    countries = read_mapping(files["country_mapping"], manifest)
    baseline_values, baseline_sums = read_path(files["baseline_path"], "baseline", manifest, countries, limits["expected_rows"])
    pulse_values, pulse_sums = read_path(files["pulse_path"], "pulse", manifest, countries, limits["expected_rows"])
    require(set(baseline_values) == set(pulse_values), "baseline and pulse path keys are not matched")
    global_rows, max_error = validate_global(files["global_reconciliation"], manifest, {"baseline": baseline_sums, "pulse": pulse_sums})
    return {
        "contract_version": CONTRACT_VERSION,
        "bundle_id": manifest["bundle_id"],
        "status": "admitted_for_annual_path_review_no_scc_authority",
        "countries": len(countries),
        "matched_annual_path_rows": len(baseline_values),
        "global_reconciliation_rows": global_rows,
        "max_absolute_reconciliation_error": max_error,
        "nutrition_mortality_in_market_paths": False,
        "damage_function_calculated": False,
        "discounting_calculated": False,
        "scc_calculated": False,
    }


def audit_public_summaries(country_export: Path, global_export: Path, source_commit: str) -> dict[str, Any]:
    require(re.fullmatch(r"[0-9a-f]{40}", source_commit) is not None, "source commit must be a full commit")
    country_totals: dict[str, float] = defaultdict(float)
    country_rows = 0
    with country_export.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ["iso3", "scc", "oc_capital", "valuation"], "country export is not the pinned public SCC summary shape")
        for line, row in enumerate(reader, 2):
            if row["oc_capital"] == "Fisheries":
                require(re.fullmatch(r"[A-Z]{3}", row["iso3"]) is not None, f"country summary:{line} invalid ISO3")
                country_totals[row["valuation"]] += csv_number(row["scc"], f"country summary:{line} scc")
                country_rows += 1
    global_values: dict[str, float] = {}
    with global_export.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ["Asset type", "Valuation type", "SCC"], "global export is not the pinned public SCC summary shape")
        for line, row in enumerate(reader, 2):
            if row["Asset type"] == "Fisheries":
                require(row["Valuation type"] not in global_values, f"global summary:{line} duplicate fisheries valuation")
                global_values[row["Valuation type"]] = csv_number(row["SCC"], f"global summary:{line} SCC")
    comparable = sorted(set(country_totals) & set(global_values))
    additive = sum(close(country_totals[name], global_values[name], 1e-12, 1e-12) for name in comparable)
    require(country_rows > 0 and comparable, "public summaries contain no comparable fisheries rows")
    require(additive < len(comparable), "public summaries unexpectedly appear additive; re-audit required")
    return {
        "audit": "blue_scc_public_fisheries_summary_admission_v1",
        "source_commit": source_commit,
        "country_export": {"name": country_export.name, "byte_size": country_export.stat().st_size, "sha256": sha256(country_export), "fisheries_rows": country_rows},
        "global_export": {"name": global_export.name, "byte_size": global_export.stat().st_size, "sha256": sha256(global_export), "fisheries_rows": len(global_values)},
        "comparable_fisheries_summary_rows": len(comparable),
        "additive_fisheries_summary_rows": additive,
        "status": "rejected_not_matched_annual_artifact_package",
        "reasons": [
            "summary_not_matched_annual_baseline_pulse_paths",
            "pulse_metadata_absent",
            "complete_country_mapping_absent",
            "country_and_global_summaries_not_additive",
            "consumer_plus_producer_surplus_semantics_absent",
            "market_nutrition_mortality_boundary_not_machine_readable",
            "artifact_license_manifest_absent",
        ],
        "damage_function_calculated": False,
        "discounting_calculated": False,
        "scc_calculated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    package = subparsers.add_parser("package", help="validate a requested annual artifact package")
    package.add_argument("manifest", type=Path)
    package.add_argument("--schema", type=Path, default=ROOT / "config/blue_scc_fisheries_annual_pair_v1.schema.json")
    public = subparsers.add_parser("public-summary", help="fail-closed audit of released SCC summaries")
    public.add_argument("country_export", type=Path)
    public.add_argument("global_export", type=Path)
    public.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    if args.mode == "package":
        result = validate_package(args.manifest, args.schema)
    else:
        result = audit_public_summaries(args.country_export, args.global_export, args.source_commit)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
