"""Import and fail-closed validate a biodiversity nonuse artifact package.

This admission gate validates provenance, licenses, empirical-input support,
matched annual accounting, and the nonuse-only overlap boundary.  It never
normalizes a pulse, discounts damages, estimates a damage function, or
calculates an SCC.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import re
from pathlib import Path
from typing import Any, Iterator

from biodiversity_kernel import climate_deficit, country_damage
from validate_replication_request import EXPECTED_ARTIFACT_IDS, EXPECTED_EXCLUSIONS, validate_request


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SCHEMA = "biodiversity_nonuse_artifact_package_v1"
PULSE_SCHEMA = "biodiversity_nonuse_pulse_manifest_v1"
ROLE_GROUPS = {
    "A1_executable_source_environment": {"source_revision", "project_toml", "manifest_toml", "run_instructions"},
    "A2_regional_valuation_calibration": {"regional_beta", "regional_beta_derivation"},
    "A3_temperature_response_calibration": {"urban_phi_inputs", "phi_draws", "phi_bootstrap"},
    "A4_country_region_mapping": {"country_mapping"},
    "A5_joint_uncertainty_pairing": {"joint_draws", "joint_draw_method"},
    "A6_matched_baseline_pulse_outputs": {"pulse_manifest", "annual_country_nonuse", "annual_global_nonuse"},
    "A7_provenance_license_boundary": {"checksums", "licenses_document", "nonuse_boundary_document"},
}
FILE_ROLES = set().union(*ROLE_GROUPS.values())
PARSED_FORMATS = {
    "regional_beta": "csv",
    "urban_phi_inputs": "csv",
    "phi_draws": "csv",
    "country_mapping": "csv",
    "joint_draws": "csv",
    "pulse_manifest": "json",
    "annual_country_nonuse": "csv",
    "annual_global_nonuse": "csv",
    "checksums": "sha256",
}
REGIONAL_BETA_FIELDS = (
    "fund_region_id", "beta", "eta", "source_income", "source_wtp", "currency",
    "price_year", "income_unit", "wtp_unit", "derivation_id",
)
URBAN_FIELDS = (
    "group_id", "study_id", "prediction_year", "temperature_change", "taxon",
    "region", "species_count", "predicted_extinct_count", "sample_weight",
    "included", "censor_reason",
)
PHI_FIELDS = ("phi_draw_id", "phi", "bootstrap_seed", "method_id")
MAPPING_FIELDS = (
    "country_id", "country_iso3", "fund_region_id", "mapping_version",
    "included", "exclusion_reason",
)
JOINT_FIELDS = (
    "run_id", "socioeconomic_draw_id", "climate_draw_id", "phi_draw_id",
    "beta_draw_id", "discount_draw_id",
)
ANNUAL_FIELDS = (
    "run_id", "path_role", "pulse_id", "run_configuration_id", "country_iso3",
    "fund_region_id", "year", "temperature_change", "biodiversity_stock",
    "no_climate_stock", "climate_deficit", "population", "income_per_capita",
    "beta", "undiscounted_damage_2020usd_per_year", "discount_factor",
    "missingness_status",
)
GLOBAL_FIELDS = (
    "run_id", "path_role", "pulse_id", "run_configuration_id", "year",
    "undiscounted_damage_2020usd_per_year", "currency", "price_year",
    "time_basis", "missingness_status",
)
PAIR_FIXED_FIELDS = (
    "pulse_id", "run_configuration_id", "country_iso3", "fund_region_id",
    "year", "population", "income_per_capita", "beta", "no_climate_stock",
    "discount_factor", "missingness_status",
)
PAIR_DYNAMIC_FIELDS = (
    "temperature_change", "biodiversity_stock", "climate_deficit",
    "undiscounted_damage_2020usd_per_year",
)
ROLE_ORDER = {"baseline": 0, "pulse": 1}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == fields, f"{label} fields changed or are incomplete")
    return value


def finite(value: Any, label: str, *, nonnegative: bool = False, positive: bool = False) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be numeric")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    if nonnegative:
        require(number >= 0, f"{label} must be nonnegative")
    if positive:
        require(number > 0, f"{label} must be positive")
    return number


def csv_float(value: str, label: str, *, nonnegative: bool = False, positive: bool = False) -> float:
    require(value.strip() != "", f"{label} is missing")
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"{label} must be numeric") from error
    require(math.isfinite(number), f"{label} must be finite")
    if nonnegative:
        require(number >= 0, f"{label} must be nonnegative")
    if positive:
        require(number > 0, f"{label} must be positive")
    return number


def csv_int(value: str, label: str) -> int:
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


def csv_rows(path: Path, fields: tuple[str, ...]) -> Iterator[tuple[int, dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == list(fields), f"{path.name} columns changed")
        for line, row in enumerate(reader, 2):
            require(None not in row and all(value is not None for value in row.values()), f"{path.name}:{line} malformed row")
            yield line, row


def validate_package_manifest(manifest: dict[str, Any], request: dict[str, Any]) -> None:
    validate_request(request)
    exact(manifest, {"schema", "bundle_id", "authorization", "source", "artifact_groups", "licenses", "files", "coverage", "units", "overlap_boundary", "reconciliation"}, "package manifest")
    require(manifest["schema"] == PACKAGE_SCHEMA, "package schema changed")
    require(isinstance(manifest["bundle_id"], str) and manifest["bundle_id"].strip(), "bundle_id is blank")
    require(manifest["authorization"] == {"purpose": "artifact_admission_only", "coefficient_estimation": False, "imputation": False, "damage_function": False, "discounting": False, "scc": False}, "authorization must forbid estimation, imputation, damage, discounting, and SCC")

    source = exact(manifest["source"], {"paper_doi", "article_source_revision", "preferred_specification_id", "random_seed"}, "source")
    for name in source:
        require(isinstance(source[name], str) and source[name].strip(), f"source {name} is blank")

    licenses = manifest["licenses"]
    require(isinstance(licenses, list) and licenses, "licenses are missing")
    license_ids: set[str] = set()
    for index, item in enumerate(licenses):
        item = exact(item, {"license_id", "rights_holder", "spdx_identifier_or_full_terms", "redistribution_allowed", "derivative_use_allowed", "give_research_use_allowed", "attribution_text", "third_party_restrictions"}, f"license[{index}]")
        license_id = item["license_id"]
        require(isinstance(license_id, str) and license_id not in {"", "NONE", "NOASSERTION"} and license_id not in license_ids, f"license[{index}] ID is blank, unresolved, or duplicated")
        license_ids.add(license_id)
        for name in ("rights_holder", "spdx_identifier_or_full_terms", "attribution_text"):
            require(isinstance(item[name], str) and item[name].strip(), f"license[{index}] {name} is blank")
        for name in ("redistribution_allowed", "derivative_use_allowed", "give_research_use_allowed"):
            require(item[name] is True, f"license[{index}] does not permit {name}")
        require(item["third_party_restrictions"] == [], f"license[{index}] has unresolved third-party restrictions")

    groups = manifest["artifact_groups"]
    require(isinstance(groups, list) and len(groups) == 7, "exactly seven artifact groups are required")
    observed_groups: set[str] = set()
    for index, group in enumerate(groups):
        group = exact(group, {"artifact_id", "provided", "license_id", "file_roles"}, f"artifact_group[{index}]")
        artifact_id = group["artifact_id"]
        require(artifact_id in EXPECTED_ARTIFACT_IDS and artifact_id not in observed_groups, f"artifact_group[{index}] ID is invalid or duplicated")
        observed_groups.add(artifact_id)
        require(group["provided"] is True, f"artifact group {artifact_id} is not provided")
        require(group["license_id"] in license_ids, f"artifact group {artifact_id} lacks a resolved license")
        require(set(group["file_roles"]) == ROLE_GROUPS[artifact_id], f"artifact group {artifact_id} file roles are incomplete")
    require(observed_groups == EXPECTED_ARTIFACT_IDS, "seven-part artifact request is incomplete")

    files = exact(manifest["files"], FILE_ROLES, "files")
    for role, record in files.items():
        record = exact(record, {"relative_path", "sha256", "byte_size", "format"}, f"files.{role}")
        require(isinstance(record["relative_path"], str) and record["relative_path"].strip(), f"files.{role} path is blank")
        require(re.fullmatch(r"[0-9a-f]{64}", str(record["sha256"])) is not None, f"files.{role} sha256 is invalid")
        require(isinstance(record["byte_size"], int) and not isinstance(record["byte_size"], bool) and record["byte_size"] > 0, f"files.{role} byte_size is invalid")
        if role in PARSED_FORMATS:
            require(record["format"] == PARSED_FORMATS[role], f"files.{role} format is invalid")

    coverage = exact(manifest["coverage"], {"fund_region_ids", "country_count", "start_year", "end_year", "mapping_version", "urban_group_count", "censored_all_extinct_count", "phi_draw_count", "joint_draw_count", "complete", "missingness_rule"}, "coverage")
    regions = coverage["fund_region_ids"]
    require(isinstance(regions, list) and len(regions) == 16 and len(set(regions)) == 16 and all(isinstance(item, str) and item.strip() for item in regions), "exactly 16 unique FUND regions are required")
    require(isinstance(coverage["country_count"], int) and not isinstance(coverage["country_count"], bool) and coverage["country_count"] > 0, "country_count is invalid")
    require(all(isinstance(coverage[name], int) and not isinstance(coverage[name], bool) for name in ("start_year", "end_year")), "coverage years must be integers")
    require(1900 <= coverage["start_year"] <= coverage["end_year"] <= 2500, "coverage years are invalid")
    require(isinstance(coverage["mapping_version"], str) and coverage["mapping_version"].strip(), "mapping_version is blank")
    require(coverage["urban_group_count"] == 389 and coverage["censored_all_extinct_count"] == 3, "Urban calibration must retain 389 groups and three censored all-extinct cases")
    require(coverage["phi_draw_count"] == 20000 and coverage["joint_draw_count"] == 10000, "article bootstrap/joint-draw counts must be 20,000 and 10,000")
    require(coverage["complete"] is True and coverage["missingness_rule"] == "explicit_no_imputation_allocation_or_renormalization", "coverage must be complete without imputation or allocation")

    units = exact(manifest["units"], {"currency", "price_year", "time_basis", "damage_basis"}, "units")
    require(units == {"currency": "USD", "price_year": 2020, "time_basis": "annual_flow", "damage_basis": "undiscounted_nonuse_existence_value"}, "unit or damage basis changed")

    boundary = exact(manifest["overlap_boundary"], {"included", "excluded", "allocation_or_renormalization_allowed", "review_status", "accounting_boundary_id"}, "overlap_boundary")
    require(boundary["included"] == ["nonuse_existence_value_only"], "included boundary is not nonuse-only")
    require(set(boundary["excluded"]) == EXPECTED_EXCLUSIONS, "overlap exclusions are incomplete")
    require(boundary["allocation_or_renormalization_allowed"] is False and boundary["review_status"] == "passed", "overlap review or no-allocation rule failed")
    require(isinstance(boundary["accounting_boundary_id"], str) and boundary["accounting_boundary_id"].strip(), "accounting boundary ID is blank")

    reconciliation = exact(manifest["reconciliation"], {"absolute_tolerance", "relative_tolerance", "country_totals_equal_global", "baseline_pulse_keys_match", "pre_divergence_identity"}, "reconciliation")
    finite(reconciliation["absolute_tolerance"], "absolute tolerance", nonnegative=True)
    finite(reconciliation["relative_tolerance"], "relative tolerance", nonnegative=True)
    require(reconciliation["country_totals_equal_global"] is True and reconciliation["baseline_pulse_keys_match"] is True and reconciliation["pre_divergence_identity"] is True, "reconciliation identities must be required")


def resolve_files(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    root = manifest_path.resolve().parent
    resolved: dict[str, Path] = {}
    for role, record in manifest["files"].items():
        candidate = root / record["relative_path"]
        require(not candidate.is_symlink(), f"files.{role} may not be a symlink")
        path = candidate.resolve()
        require(path.is_relative_to(root) and path.is_file(), f"files.{role} is absent or escapes package root")
        require(path not in resolved.values(), "file roles must resolve to distinct files")
        require(path.stat().st_size == record["byte_size"], f"files.{role} byte size mismatch")
        require(sha256(path) == record["sha256"], f"files.{role} sha256 mismatch")
        resolved[role] = path
    checksum_rows: dict[str, str] = {}
    for line, raw in enumerate(resolved["checksums"].read_text(encoding="utf-8").splitlines(), 1):
        parts = raw.split(None, 1)
        require(len(parts) == 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]) is not None, f"checksums:{line} is malformed")
        relative = parts[1].lstrip("* ")
        require(relative not in checksum_rows, f"checksums:{line} duplicates a path")
        checksum_rows[relative] = parts[0]
    expected = {record["relative_path"]: record["sha256"] for role, record in manifest["files"].items() if role != "checksums"}
    require(checksum_rows == expected, "checksums file does not exactly cover all other package files")
    return resolved


def validate_regional_beta(path: Path, manifest: dict[str, Any]) -> dict[str, float]:
    expected_regions = set(manifest["coverage"]["fund_region_ids"])
    result: dict[str, float] = {}
    for line, row in csv_rows(path, REGIONAL_BETA_FIELDS):
        region = row["fund_region_id"]
        require(region in expected_regions and region not in result, f"{path.name}:{line} region is undeclared or duplicated")
        beta = csv_float(row["beta"], f"{path.name}:{line} beta", nonnegative=True)
        csv_float(row["eta"], f"{path.name}:{line} eta", nonnegative=True)
        csv_float(row["source_income"], f"{path.name}:{line} source_income", positive=True)
        csv_float(row["source_wtp"], f"{path.name}:{line} source_wtp", nonnegative=True)
        require(row["currency"] == "USD" and csv_int(row["price_year"], f"{path.name}:{line} price_year") == 2020, f"{path.name}:{line} valuation currency basis mismatch")
        require(row["income_unit"].strip() and row["wtp_unit"].strip() and row["derivation_id"].strip(), f"{path.name}:{line} valuation provenance is incomplete")
        result[region] = beta
    require(set(result) == expected_regions, "regional beta table does not cover all 16 FUND regions")
    return result


def validate_urban_inputs(path: Path, manifest: dict[str, Any]) -> int:
    groups: set[str] = set()
    censored = 0
    for line, row in csv_rows(path, URBAN_FIELDS):
        group = row["group_id"]
        require(group.strip() and group not in groups, f"{path.name}:{line} group ID is blank or duplicated")
        groups.add(group)
        require(row["study_id"].strip() and row["taxon"].strip() and row["region"].strip(), f"{path.name}:{line} calibration provenance is incomplete")
        csv_int(row["prediction_year"], f"{path.name}:{line} prediction_year")
        csv_float(row["temperature_change"], f"{path.name}:{line} temperature_change")
        species = csv_int(row["species_count"], f"{path.name}:{line} species_count")
        extinct = csv_int(row["predicted_extinct_count"], f"{path.name}:{line} predicted_extinct_count")
        require(species > 0 and 0 <= extinct <= species, f"{path.name}:{line} extinction counts are invalid")
        csv_float(row["sample_weight"], f"{path.name}:{line} sample_weight", nonnegative=True)
        require(row["included"] in {"true", "false"}, f"{path.name}:{line} included must be true/false")
        if row["included"] == "false":
            require(extinct == species and row["censor_reason"] == "all_extinct", f"{path.name}:{line} excluded row is not a censored all-extinct case")
            censored += 1
        else:
            require(row["censor_reason"] == "", f"{path.name}:{line} included row has a censor reason")
    require(len(groups) == manifest["coverage"]["urban_group_count"], "Urban group count mismatch")
    require(censored == manifest["coverage"]["censored_all_extinct_count"], "censored all-extinct count mismatch")
    return len(groups)


def validate_phi_draws(path: Path, manifest: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    seed = manifest["source"]["random_seed"]
    for line, row in csv_rows(path, PHI_FIELDS):
        draw_id = row["phi_draw_id"]
        require(draw_id.strip() and draw_id not in ids, f"{path.name}:{line} phi draw ID is blank or duplicated")
        ids.add(draw_id)
        csv_float(row["phi"], f"{path.name}:{line} phi", nonnegative=True)
        require(row["bootstrap_seed"] == seed and row["method_id"].strip(), f"{path.name}:{line} bootstrap seed/method mismatch")
    require(len(ids) == manifest["coverage"]["phi_draw_count"], "phi draw count mismatch")
    return ids


def validate_mapping(path: Path, manifest: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    country_ids: set[str] = set()
    regions = set(manifest["coverage"]["fund_region_ids"])
    for line, row in csv_rows(path, MAPPING_FIELDS):
        require(row["country_id"].strip() and row["country_id"] not in country_ids, f"{path.name}:{line} country ID is blank or duplicated")
        require(re.fullmatch(r"[A-Z]{3}", row["country_iso3"]) is not None and row["country_iso3"] not in mapping, f"{path.name}:{line} ISO3 is invalid or duplicated")
        require(row["fund_region_id"] in regions and row["mapping_version"] == manifest["coverage"]["mapping_version"], f"{path.name}:{line} region or mapping version mismatch")
        require(row["included"] == "true" and row["exclusion_reason"] == "", f"{path.name}:{line} incomplete mapping fails closed")
        country_ids.add(row["country_id"])
        mapping[row["country_iso3"]] = row["fund_region_id"]
    require(len(mapping) == manifest["coverage"]["country_count"], "country mapping count mismatch")
    return mapping


def validate_joint_draws(path: Path, manifest: dict[str, Any], phi_ids: set[str]) -> set[str]:
    runs: set[str] = set()
    for line, row in csv_rows(path, JOINT_FIELDS):
        run_id = row["run_id"]
        require(run_id.strip() and run_id not in runs, f"{path.name}:{line} run ID is blank or duplicated")
        runs.add(run_id)
        require(row["phi_draw_id"] in phi_ids, f"{path.name}:{line} references an unknown phi draw")
        require(row["beta_draw_id"] == "fixed_regional_beta", f"{path.name}:{line} unsupported beta draw semantics")
        for name in ("socioeconomic_draw_id", "climate_draw_id", "discount_draw_id"):
            require(row[name].strip(), f"{path.name}:{line} {name} is blank")
    require(len(runs) == manifest["coverage"]["joint_draw_count"], "joint draw count mismatch")
    return runs


def validate_pulse_manifest(path: Path) -> dict[str, Any]:
    pulse = json.loads(path.read_text(encoding="utf-8"))
    pulse = exact(pulse, {"schema", "pulse_id", "gas", "mass", "mass_unit", "pulse_year", "first_divergence_year", "injection_convention", "run_configuration_id", "normalization_applied", "discounting_applied"}, "pulse manifest")
    require(pulse["schema"] == PULSE_SCHEMA, "pulse schema changed")
    for name in ("pulse_id", "injection_convention", "run_configuration_id"):
        require(isinstance(pulse[name], str) and pulse[name].strip(), f"pulse {name} is blank")
    require(pulse["gas"] == "CO2" and pulse["mass_unit"] == "tCO2", "pulse must be explicit tCO2")
    finite(pulse["mass"], "pulse mass", positive=True)
    require(isinstance(pulse["pulse_year"], int) and not isinstance(pulse["pulse_year"], bool), "pulse year must be an integer")
    require(isinstance(pulse["first_divergence_year"], int) and not isinstance(pulse["first_divergence_year"], bool) and pulse["first_divergence_year"] >= pulse["pulse_year"], "first divergence year is invalid")
    require(pulse["normalization_applied"] is False and pulse["discounting_applied"] is False, "admission paths must be unnormalized and undiscounted")
    return pulse


def validate_damage_row(row: dict[str, str], path: Path, line: int, mapping: dict[str, str], betas: dict[str, float], runs: set[str], pulse: dict[str, Any], manifest: dict[str, Any]) -> tuple[int, float]:
    require(row["run_id"] in runs, f"{path.name}:{line} unknown joint run")
    require(row["path_role"] in ROLE_ORDER, f"{path.name}:{line} invalid path role")
    require(row["pulse_id"] == pulse["pulse_id"] and row["run_configuration_id"] == pulse["run_configuration_id"], f"{path.name}:{line} pulse/run configuration mismatch")
    require(row["country_iso3"] in mapping and row["fund_region_id"] == mapping[row["country_iso3"]], f"{path.name}:{line} country-region mapping mismatch")
    year = csv_int(row["year"], f"{path.name}:{line} year")
    require(manifest["coverage"]["start_year"] <= year <= manifest["coverage"]["end_year"], f"{path.name}:{line} year outside coverage")
    require(row["missingness_status"] == "complete", f"{path.name}:{line} unresolved missingness")
    temperature = csv_float(row["temperature_change"], f"{path.name}:{line} temperature_change")
    stock = csv_float(row["biodiversity_stock"], f"{path.name}:{line} biodiversity_stock", positive=True)
    no_climate = csv_float(row["no_climate_stock"], f"{path.name}:{line} no_climate_stock", positive=True)
    deficit = csv_float(row["climate_deficit"], f"{path.name}:{line} climate_deficit", nonnegative=True)
    population = csv_float(row["population"], f"{path.name}:{line} population", nonnegative=True)
    income = csv_float(row["income_per_capita"], f"{path.name}:{line} income_per_capita", nonnegative=True)
    beta = csv_float(row["beta"], f"{path.name}:{line} beta", nonnegative=True)
    damage = csv_float(row["undiscounted_damage_2020usd_per_year"], f"{path.name}:{line} damage", nonnegative=True)
    csv_float(row["discount_factor"], f"{path.name}:{line} discount_factor", nonnegative=True)
    require(close(beta, betas[row["fund_region_id"]], 1e-12, 1e-12), f"{path.name}:{line} beta does not match regional valuation table")
    expected_deficit = climate_deficit(no_climate, stock)
    require(close(deficit, expected_deficit, 1e-12, 1e-12), f"{path.name}:{line} climate deficit does not reproduce")
    expected_damage = country_damage(population, income, stock, deficit, beta=beta)
    require(close(damage, expected_damage, 1e-8, 1e-12), f"{path.name}:{line} annual damage does not reproduce")
    _ = temperature
    return year, damage


def country_aggregates(path: Path, manifest: dict[str, Any], mapping: dict[str, str], betas: dict[str, float], runs: set[str], pulse: dict[str, Any], stats: dict[str, int]) -> Iterator[tuple[tuple[str, int, str], float]]:
    iterator = iter(csv_rows(path, ANNUAL_FIELDS))
    previous_pair: tuple[str, int, str] | None = None
    group: tuple[str, int] | None = None
    group_sums = {"baseline": 0.0, "pulse": 0.0}
    pair_count = 0
    while True:
        try:
            baseline_line, baseline = next(iterator)
        except StopIteration:
            break
        try:
            pulse_line, pulse_row = next(iterator)
        except StopIteration as error:
            raise ValueError(f"{path.name} ends with an unmatched row") from error
        require(baseline["path_role"] == "baseline" and pulse_row["path_role"] == "pulse", f"{path.name}:{baseline_line}-{pulse_line} rows must be baseline then pulse")
        baseline_year, baseline_damage = validate_damage_row(baseline, path, baseline_line, mapping, betas, runs, pulse, manifest)
        pulse_year, pulse_damage = validate_damage_row(pulse_row, path, pulse_line, mapping, betas, runs, pulse, manifest)
        pair_key = (baseline["run_id"], baseline_year, baseline["country_iso3"])
        require(pair_key == (pulse_row["run_id"], pulse_year, pulse_row["country_iso3"]), f"{path.name}:{baseline_line}-{pulse_line} baseline/pulse keys differ")
        require(previous_pair is None or pair_key > previous_pair, f"{path.name}:{baseline_line} path keys must be unique and sorted")
        previous_pair = pair_key
        for name in PAIR_FIXED_FIELDS:
            require(baseline[name] == pulse_row[name], f"{path.name}:{baseline_line}-{pulse_line} paired fixed field differs: {name}")
        if baseline_year < pulse["first_divergence_year"]:
            for name in PAIR_DYNAMIC_FIELDS:
                require(baseline[name] == pulse_row[name], f"{path.name}:{baseline_line}-{pulse_line} pre-divergence identity failed: {name}")
        new_group = (baseline["run_id"], baseline_year)
        if group is not None and new_group != group:
            yield (group[0], group[1], "baseline"), group_sums["baseline"]
            yield (group[0], group[1], "pulse"), group_sums["pulse"]
            group_sums = {"baseline": 0.0, "pulse": 0.0}
        group = new_group
        group_sums["baseline"] += baseline_damage
        group_sums["pulse"] += pulse_damage
        pair_count += 1
    if group is not None:
        yield (group[0], group[1], "baseline"), group_sums["baseline"]
        yield (group[0], group[1], "pulse"), group_sums["pulse"]
    expected_pairs = len(runs) * len(mapping) * (manifest["coverage"]["end_year"] - manifest["coverage"]["start_year"] + 1)
    require(pair_count == expected_pairs, "annual country paths are not a complete run-country-year rectangle")
    stats["matched_country_pairs"] = pair_count


def global_rows(path: Path, manifest: dict[str, Any], runs: set[str], pulse: dict[str, Any], stats: dict[str, int]) -> Iterator[tuple[tuple[str, int, str], float]]:
    previous: tuple[str, int, int] | None = None
    count = 0
    for line, row in csv_rows(path, GLOBAL_FIELDS):
        require(row["run_id"] in runs and row["path_role"] in ROLE_ORDER, f"{path.name}:{line} unknown run or path role")
        require(row["pulse_id"] == pulse["pulse_id"] and row["run_configuration_id"] == pulse["run_configuration_id"], f"{path.name}:{line} pulse/run configuration mismatch")
        year = csv_int(row["year"], f"{path.name}:{line} year")
        require(manifest["coverage"]["start_year"] <= year <= manifest["coverage"]["end_year"], f"{path.name}:{line} year outside coverage")
        require(row["currency"] == "USD" and csv_int(row["price_year"], f"{path.name}:{line} price_year") == 2020 and row["time_basis"] == "annual_flow", f"{path.name}:{line} unit mismatch")
        require(row["missingness_status"] == "complete", f"{path.name}:{line} unresolved missingness")
        damage = csv_float(row["undiscounted_damage_2020usd_per_year"], f"{path.name}:{line} damage", nonnegative=True)
        order_key = (row["run_id"], year, ROLE_ORDER[row["path_role"]])
        require(previous is None or order_key > previous, f"{path.name}:{line} global keys must be unique and sorted")
        previous = order_key
        count += 1
        yield (row["run_id"], year, row["path_role"]), damage
    expected = 2 * len(runs) * (manifest["coverage"]["end_year"] - manifest["coverage"]["start_year"] + 1)
    require(count == expected, "annual global rows are incomplete")
    stats["global_rows"] = count


def reconcile_annual(country_path: Path, global_path: Path, manifest: dict[str, Any], mapping: dict[str, str], betas: dict[str, float], runs: set[str], pulse: dict[str, Any]) -> dict[str, Any]:
    stats: dict[str, int] = {}
    absolute = manifest["reconciliation"]["absolute_tolerance"]
    relative = manifest["reconciliation"]["relative_tolerance"]
    maximum_error = 0.0
    sentinel = object()
    for country_item, global_item in itertools.zip_longest(
        country_aggregates(country_path, manifest, mapping, betas, runs, pulse, stats),
        global_rows(global_path, manifest, runs, pulse, stats),
        fillvalue=sentinel,
    ):
        require(country_item is not sentinel and global_item is not sentinel, "country/global annual coverage differs")
        country_key, country_value = country_item
        global_key, global_value = global_item
        require(country_key == global_key, "country/global annual keys differ")
        maximum_error = max(maximum_error, abs(country_value - global_value))
        require(close(country_value, global_value, absolute, relative), f"country/global additivity failed for {country_key}")
    return {**stats, "maximum_absolute_reconciliation_error": maximum_error}


def validate_package(manifest_path: Path, request_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    request = json.loads(request_path.read_text(encoding="utf-8"))
    validate_package_manifest(manifest, request)
    files = resolve_files(manifest_path, manifest)
    betas = validate_regional_beta(files["regional_beta"], manifest)
    urban_count = validate_urban_inputs(files["urban_phi_inputs"], manifest)
    phi_ids = validate_phi_draws(files["phi_draws"], manifest)
    mapping = validate_mapping(files["country_mapping"], manifest)
    runs = validate_joint_draws(files["joint_draws"], manifest, phi_ids)
    pulse = validate_pulse_manifest(files["pulse_manifest"])
    annual = reconcile_annual(files["annual_country_nonuse"], files["annual_global_nonuse"], manifest, mapping, betas, runs, pulse)
    return {
        "schema": "biodiversity_nonuse_artifact_admission_v1",
        "bundle_id": manifest["bundle_id"],
        "status": "admitted_for_source_and_scientific_review_no_scc_authority",
        "artifact_groups": 7,
        "licenses": len(manifest["licenses"]),
        "fund_regions": len(betas),
        "urban_groups": urban_count,
        "phi_draws": len(phi_ids),
        "joint_draws": len(runs),
        "countries": len(mapping),
        **annual,
        "imputation_or_renormalization_performed": False,
        "pulse_normalization_performed": False,
        "discounting_performed": False,
        "damage_function_estimated": False,
        "scc_calculated": False,
    }


def audit_public_evidence(request_path: Path, audit_path: Path) -> dict[str, Any]:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    validate_request(request)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    require(audit.get("schema") == "biodiversity_replication_request_audit_v1", "public audit schema changed")
    repository = audit.get("official_repository_audit")
    require(isinstance(repository, dict) and repository.get("commit") == request["official_repository_audit"]["commit"], "public audit source commit mismatch")
    require(repository.get("pinned_file_hashes_valid") is True and repository.get("biodiversity_component_found") is False, "public evidence status changed; re-audit required")
    require(audit.get("artifact_group_count") == 7 and audit.get("status") == "blocked_no_public_replication_artifacts", "public artifact status changed")
    require(request["current_gate"]["received_artifact_groups"] == [], "public request unexpectedly records received artifacts")
    return {
        "schema": "biodiversity_public_evidence_artifact_admission_v1",
        "source_commit": repository["commit"],
        "request_sha256": sha256(request_path),
        "public_audit_sha256": sha256(audit_path),
        "received_artifact_groups": 0,
        "required_artifact_groups": 7,
        "status": "rejected_incomplete_public_evidence",
        "reasons": [
            "no_public_biodiversity_component_found_at_pinned_official_commit",
            "regional_valuation_coefficients_absent",
            "temperature_response_inputs_and_draws_absent",
            "article_country_region_mapping_absent",
            "joint_uncertainty_pairing_absent",
            "matched_annual_baseline_pulse_outputs_absent",
            "artifact_licenses_and_nonuse_boundary_absent",
        ],
        "imputation_or_renormalization_performed": False,
        "damage_function_estimated": False,
        "scc_calculated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    package = subparsers.add_parser("package")
    package.add_argument("manifest", type=Path)
    package.add_argument("--request", type=Path, default=ROOT / "config/biodiversity_replication_request_v1.json")
    public = subparsers.add_parser("public-evidence")
    public.add_argument("--request", type=Path, default=ROOT / "config/biodiversity_replication_request_v1.json")
    public.add_argument("--audit", type=Path, default=ROOT / "data/provenance/biodiversity_public_release_audit_20261014.json")
    args = parser.parse_args()
    result = validate_package(args.manifest, args.request) if args.mode == "package" else audit_public_evidence(args.request, args.audit)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
