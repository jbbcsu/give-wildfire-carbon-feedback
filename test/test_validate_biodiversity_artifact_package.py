import copy
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "python"))

from biodiversity_kernel import climate_deficit, country_damage  # noqa: E402
from validate_biodiversity_artifact_package import (  # noqa: E402
    ANNUAL_FIELDS,
    FILE_ROLES,
    GLOBAL_FIELDS,
    JOINT_FIELDS,
    MAPPING_FIELDS,
    PACKAGE_SCHEMA,
    PHI_FIELDS,
    REGIONAL_BETA_FIELDS,
    ROLE_GROUPS,
    URBAN_FIELDS,
    audit_public_evidence,
    country_aggregates,
    reconcile_annual,
    resolve_files,
    validate_joint_draws,
    validate_mapping,
    validate_package,
    validate_package_manifest,
    validate_pulse_manifest,
    validate_regional_beta,
    validate_urban_inputs,
)


REQUEST_PATH = ROOT / "config/biodiversity_replication_request_v1.json"
PUBLIC_AUDIT_PATH = ROOT / "data/provenance/biodiversity_public_release_audit_20261014.json"
REGIONS = [f"R{index:02d}" for index in range(1, 17)]


def write_csv(path: Path, fields: tuple[str, ...], records) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_record(path: Path, file_format: str) -> dict[str, object]:
    return {"relative_path": path.name, "sha256": digest(path), "byte_size": path.stat().st_size, "format": file_format}


def annual_row(run_id: str, year: int, role: str) -> dict[str, object]:
    pre_divergence = year == 2020
    stock = 0.90 if pre_divergence else (0.89 if role == "baseline" else 0.88)
    temperature = 1.0 if pre_divergence else (1.1 if role == "baseline" else 1.2)
    no_climate = 0.95
    deficit = climate_deficit(no_climate, stock)
    damage = country_damage(10.0, 100.0, stock, deficit, beta=2.0)
    return {
        "run_id": run_id,
        "path_role": role,
        "pulse_id": "pulse-one",
        "run_configuration_id": "config-one",
        "country_iso3": "AAA",
        "fund_region_id": "R01",
        "year": year,
        "temperature_change": temperature,
        "biodiversity_stock": stock,
        "no_climate_stock": no_climate,
        "climate_deficit": deficit,
        "population": 10.0,
        "income_per_capita": 100.0,
        "beta": 2.0,
        "undiscounted_damage_2020usd_per_year": damage,
        "discount_factor": 0.98,
        "missingness_status": "complete",
    }


def build_package(directory: Path) -> Path:
    paths: dict[str, Path] = {}
    text_roles = FILE_ROLES - {
        "regional_beta", "urban_phi_inputs", "phi_draws", "country_mapping",
        "joint_draws", "pulse_manifest", "annual_country_nonuse",
        "annual_global_nonuse", "checksums",
    }
    for role in text_roles:
        path = directory / f"{role}.txt"
        path.write_text(f"Synthetic evidence for {role}.\n", encoding="utf-8")
        paths[role] = path

    regional = directory / "regional_beta.csv"
    write_csv(regional, REGIONAL_BETA_FIELDS, (
        {"fund_region_id": region, "beta": 2.0, "eta": 0.5, "source_income": 100.0, "source_wtp": 1.0, "currency": "USD", "price_year": 2020, "income_unit": "USD_2020_per_capita", "wtp_unit": "USD_2020_per_capita", "derivation_id": "synthetic-derivation"}
        for region in REGIONS
    ))
    paths["regional_beta"] = regional

    urban = directory / "urban_phi_inputs.csv"
    write_csv(urban, URBAN_FIELDS, (
        {"group_id": f"group-{index:03d}", "study_id": "synthetic-study", "prediction_year": 2100, "temperature_change": 2.0, "taxon": "synthetic", "region": "global", "species_count": 10, "predicted_extinct_count": 10 if index < 3 else 2, "sample_weight": 1.0, "included": "false" if index < 3 else "true", "censor_reason": "all_extinct" if index < 3 else ""}
        for index in range(389)
    ))
    paths["urban_phi_inputs"] = urban

    phi = directory / "phi_draws.csv"
    write_csv(phi, PHI_FIELDS, (
        {"phi_draw_id": f"phi-{index:05d}", "phi": 0.001 + index / 100000000.0, "bootstrap_seed": "123", "method_id": "synthetic-bootstrap"}
        for index in range(20000)
    ))
    paths["phi_draws"] = phi

    mapping = directory / "country_fund_region_map.csv"
    write_csv(mapping, MAPPING_FIELDS, [{"country_id": "synthetic-country", "country_iso3": "AAA", "fund_region_id": "R01", "mapping_version": "synthetic-map-v1", "included": "true", "exclusion_reason": ""}])
    paths["country_mapping"] = mapping

    joint = directory / "joint_draws.csv"
    write_csv(joint, JOINT_FIELDS, (
        {"run_id": f"run-{index:05d}", "socioeconomic_draw_id": f"socio-{index:05d}", "climate_draw_id": f"climate-{index:05d}", "phi_draw_id": f"phi-{index:05d}", "beta_draw_id": "fixed_regional_beta", "discount_draw_id": f"discount-{index:05d}"}
        for index in range(10000)
    ))
    paths["joint_draws"] = joint

    pulse = directory / "pulse_manifest.json"
    pulse.write_text(json.dumps({"schema": "biodiversity_nonuse_pulse_manifest_v1", "pulse_id": "pulse-one", "gas": "CO2", "mass": 100000.0, "mass_unit": "tCO2", "pulse_year": 2020, "first_divergence_year": 2021, "injection_convention": "synthetic_atmospheric_injection", "run_configuration_id": "config-one", "normalization_applied": False, "discounting_applied": False}, indent=2) + "\n", encoding="utf-8")
    paths["pulse_manifest"] = pulse

    country_path = directory / "annual_country_nonuse.csv"
    write_csv(country_path, ANNUAL_FIELDS, (
        annual_row(f"run-{run:05d}", year, role)
        for run in range(10000)
        for year in (2020, 2021)
        for role in ("baseline", "pulse")
    ))
    paths["annual_country_nonuse"] = country_path

    global_path = directory / "annual_global_nonuse.csv"
    write_csv(global_path, GLOBAL_FIELDS, (
        {
            "run_id": row["run_id"],
            "path_role": row["path_role"],
            "pulse_id": row["pulse_id"],
            "run_configuration_id": row["run_configuration_id"],
            "year": row["year"],
            "undiscounted_damage_2020usd_per_year": row["undiscounted_damage_2020usd_per_year"],
            "currency": "USD",
            "price_year": 2020,
            "time_basis": "annual_flow",
            "missingness_status": "complete",
        }
        for run in range(10000)
        for year in (2020, 2021)
        for role in ("baseline", "pulse")
        for row in (annual_row(f"run-{run:05d}", year, role),)
    ))
    paths["annual_global_nonuse"] = global_path

    formats = {role: "text" for role in FILE_ROLES}
    formats.update({"regional_beta": "csv", "urban_phi_inputs": "csv", "phi_draws": "csv", "country_mapping": "csv", "joint_draws": "csv", "pulse_manifest": "json", "annual_country_nonuse": "csv", "annual_global_nonuse": "csv", "checksums": "sha256"})
    checksums = directory / "checksums.sha256"
    checksums.write_text("".join(f"{digest(path)}  {path.name}\n" for role, path in sorted(paths.items()) if role != "checksums"), encoding="utf-8")
    paths["checksums"] = checksums

    manifest = {
        "schema": PACKAGE_SCHEMA,
        "bundle_id": "synthetic:biodiversity-artifacts-v1",
        "authorization": {"purpose": "artifact_admission_only", "coefficient_estimation": False, "imputation": False, "damage_function": False, "discounting": False, "scc": False},
        "source": {"paper_doi": "synthetic:doi", "article_source_revision": "synthetic-revision", "preferred_specification_id": "synthetic-preferred", "random_seed": "123"},
        "artifact_groups": [{"artifact_id": artifact_id, "provided": True, "license_id": "synthetic-license", "file_roles": sorted(roles)} for artifact_id, roles in ROLE_GROUPS.items()],
        "licenses": [{"license_id": "synthetic-license", "rights_holder": "Synthetic test", "spdx_identifier_or_full_terms": "CC0-1.0", "redistribution_allowed": True, "derivative_use_allowed": True, "give_research_use_allowed": True, "attribution_text": "Synthetic test artifacts", "third_party_restrictions": []}],
        "files": {role: file_record(paths[role], formats[role]) for role in FILE_ROLES},
        "coverage": {"fund_region_ids": REGIONS, "country_count": 1, "start_year": 2020, "end_year": 2021, "mapping_version": "synthetic-map-v1", "urban_group_count": 389, "censored_all_extinct_count": 3, "phi_draw_count": 20000, "joint_draw_count": 10000, "complete": True, "missingness_rule": "explicit_no_imputation_allocation_or_renormalization"},
        "units": {"currency": "USD", "price_year": 2020, "time_basis": "annual_flow", "damage_basis": "undiscounted_nonuse_existence_value"},
        "overlap_boundary": {"included": ["nonuse_existence_value_only"], "excluded": ["agriculture_and_crop_productivity", "fisheries_and_aquaculture", "coral_reef_tourism_and_recreation", "coastal_protection", "carbon_cycle_feedbacks", "hunting_and_subsistence", "commercial_harvest", "other_recreation", "other_market_and_use_ecosystem_services"], "allocation_or_renormalization_allowed": False, "review_status": "passed", "accounting_boundary_id": "synthetic-nonuse-only-v1"},
        "reconciliation": {"absolute_tolerance": 1e-8, "relative_tolerance": 1e-12, "country_totals_equal_global": True, "baseline_pulse_keys_match": True, "pre_divergence_identity": True},
    }
    manifest_path = directory / "package_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


class BiodiversityArtifactPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary.name)
        cls.manifest_path = build_package(cls.directory)
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_complete_synthetic_package_passes_without_scc_authority(self):
        result = validate_package(self.manifest_path, REQUEST_PATH)
        self.assertEqual(result["artifact_groups"], 7)
        self.assertEqual(result["fund_regions"], 16)
        self.assertEqual(result["urban_groups"], 389)
        self.assertEqual(result["phi_draws"], 20000)
        self.assertEqual(result["joint_draws"], 10000)
        self.assertEqual(result["matched_country_pairs"], 20000)
        self.assertFalse(result["scc_calculated"])

    def test_unresolved_license_fails(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["licenses"][0]["spdx_identifier_or_full_terms"] = ""
        with self.assertRaisesRegex(ValueError, "full_terms.*blank"):
            validate_package_manifest(candidate, self.request)

    def test_missing_artifact_group_fails(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["artifact_groups"].pop()
        with self.assertRaisesRegex(ValueError, "seven artifact groups"):
            validate_package_manifest(candidate, self.request)

    def test_nonuse_overlap_leakage_fails(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["overlap_boundary"]["excluded"].remove("fisheries_and_aquaculture")
        with self.assertRaisesRegex(ValueError, "overlap exclusions"):
            validate_package_manifest(candidate, self.request)

    def test_hash_mismatch_fails(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["files"]["regional_beta"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "sha256 mismatch"):
            resolve_files(self.manifest_path, candidate)

    def test_invalid_pulse_unit_fails(self):
        path = self.directory / "invalid_pulse.json"
        pulse = json.loads((self.directory / "pulse_manifest.json").read_text(encoding="utf-8"))
        pulse["mass_unit"] = "tC"
        path.write_text(json.dumps(pulse), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "explicit tCO2"):
            validate_pulse_manifest(path)

    def test_incomplete_regional_coefficients_fail(self):
        path = self.directory / "incomplete_regional_beta.csv"
        write_csv(path, REGIONAL_BETA_FIELDS, [
            {"fund_region_id": region, "beta": 2.0, "eta": 0.5, "source_income": 100.0, "source_wtp": 1.0, "currency": "USD", "price_year": 2020, "income_unit": "USD_2020_per_capita", "wtp_unit": "USD_2020_per_capita", "derivation_id": "synthetic-derivation"}
            for region in REGIONS[:-1]
        ])
        with self.assertRaisesRegex(ValueError, "all 16 FUND regions"):
            validate_regional_beta(path, self.manifest)

    def test_wrong_climate_censor_count_fails(self):
        path = self.directory / "invalid_urban_phi_inputs.csv"
        write_csv(path, URBAN_FIELDS, (
            {"group_id": f"invalid-group-{index:03d}", "study_id": "synthetic-study", "prediction_year": 2100, "temperature_change": 2.0, "taxon": "synthetic", "region": "global", "species_count": 10, "predicted_extinct_count": 10 if index < 2 else 2, "sample_weight": 1.0, "included": "false" if index < 2 else "true", "censor_reason": "all_extinct" if index < 2 else ""}
            for index in range(389)
        ))
        with self.assertRaisesRegex(ValueError, "censored all-extinct count"):
            validate_urban_inputs(path, self.manifest)

    def test_incomplete_mapping_fails(self):
        path = self.directory / "incomplete_mapping.csv"
        write_csv(path, MAPPING_FIELDS, [{"country_id": "synthetic-country", "country_iso3": "AAA", "fund_region_id": "R01", "mapping_version": "synthetic-map-v1", "included": "false", "exclusion_reason": "unresolved"}])
        with self.assertRaisesRegex(ValueError, "incomplete mapping"):
            validate_mapping(path, self.manifest)

    def test_unknown_phi_in_joint_draw_fails(self):
        path = self.directory / "invalid_joint_draws.csv"
        write_csv(path, JOINT_FIELDS, [{"run_id": "run-one", "socioeconomic_draw_id": "socio-one", "climate_draw_id": "climate-one", "phi_draw_id": "unknown-phi", "beta_draw_id": "fixed_regional_beta", "discount_draw_id": "discount-one"}])
        manifest = copy.deepcopy(self.manifest)
        manifest["coverage"]["joint_draw_count"] = 1
        with self.assertRaisesRegex(ValueError, "unknown phi draw"):
            validate_joint_draws(path, manifest, {"phi-known"})

    def test_unmatched_annual_pair_fails(self):
        path = self.directory / "invalid_annual.csv"
        baseline = annual_row("run-00000", 2020, "baseline")
        pulse = annual_row("run-00000", 2020, "pulse")
        pulse["country_iso3"] = "BBB"
        write_csv(path, ANNUAL_FIELDS, [baseline, pulse])
        manifest = copy.deepcopy(self.manifest)
        manifest["coverage"]["joint_draw_count"] = 1
        manifest["coverage"]["start_year"] = 2020
        manifest["coverage"]["end_year"] = 2020
        stats: dict[str, int] = {}
        iterator = country_aggregates(path, manifest, {"AAA": "R01", "BBB": "R01"}, {"R01": 2.0}, {"run-00000"}, json.loads((self.directory / "pulse_manifest.json").read_text()), stats)
        with self.assertRaisesRegex(ValueError, "keys differ"):
            list(iterator)

    def test_nonadditive_global_output_fails(self):
        country_path = self.directory / "one_pair_country.csv"
        baseline = annual_row("run-00000", 2020, "baseline")
        pulse = annual_row("run-00000", 2020, "pulse")
        write_csv(country_path, ANNUAL_FIELDS, [baseline, pulse])
        global_path = self.directory / "one_pair_global_nonadditive.csv"
        write_csv(global_path, GLOBAL_FIELDS, [
            {"run_id": "run-00000", "path_role": role, "pulse_id": "pulse-one", "run_configuration_id": "config-one", "year": 2020, "undiscounted_damage_2020usd_per_year": float(row["undiscounted_damage_2020usd_per_year"]) + (1.0 if role == "baseline" else 0.0), "currency": "USD", "price_year": 2020, "time_basis": "annual_flow", "missingness_status": "complete"}
            for role, row in (("baseline", baseline), ("pulse", pulse))
        ])
        manifest = copy.deepcopy(self.manifest)
        manifest["coverage"]["joint_draw_count"] = 1
        manifest["coverage"]["start_year"] = 2020
        manifest["coverage"]["end_year"] = 2020
        with self.assertRaisesRegex(ValueError, "additivity failed"):
            reconcile_annual(country_path, global_path, manifest, {"AAA": "R01"}, {"R01": 2.0}, {"run-00000"}, json.loads((self.directory / "pulse_manifest.json").read_text()))

    def test_public_evidence_rejected_at_zero_of_seven(self):
        result = audit_public_evidence(REQUEST_PATH, PUBLIC_AUDIT_PATH)
        self.assertEqual(result["received_artifact_groups"], 0)
        self.assertEqual(result["required_artifact_groups"], 7)
        self.assertEqual(result["status"], "rejected_incomplete_public_evidence")
        self.assertFalse(result["scc_calculated"])
        receipt = json.loads((ROOT / "data/provenance/biodiversity_public_evidence_artifact_admission_20261014.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["source"]["source_commit"], result["source_commit"])
        self.assertEqual(receipt["source"]["request_sha256"], result["request_sha256"])
        self.assertEqual(receipt["source"]["public_audit_sha256"], result["public_audit_sha256"])
        self.assertEqual(receipt["reasons"], result["reasons"])

    def test_machine_contract_matches_implementation(self):
        contract = json.loads((ROOT / "config/biodiversity_artifact_package_contract_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["package_schema"], PACKAGE_SCHEMA)
        self.assertEqual({name: set(roles) for name, roles in contract["artifact_groups"].items()}, ROLE_GROUPS)
        self.assertEqual(tuple(contract["parsed_csv_columns"]["annual_country_nonuse"]), ANNUAL_FIELDS)
        self.assertEqual(tuple(contract["parsed_csv_columns"]["annual_global_nonuse"]), GLOBAL_FIELDS)


if __name__ == "__main__":
    unittest.main()
