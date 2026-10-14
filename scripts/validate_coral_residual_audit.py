"""Fail-closed validator for the residual coral-reef candidate audit.

The source audit verifies public artifacts and accounting boundaries only.  It
does not estimate a damage function or social cost of carbon.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path


SCHEMA = "coral_residual_candidate_audit_v1"
EXPECTED_SOURCE_IDS = {
    "blue_scc_2026",
    "lane_et_al_2013",
    "spalding_et_al_2017",
    "brander_et_al_2024",
    "beck_et_al_2018",
}
EXPECTED_EXCLUSIONS = {
    "reef_fisheries_and_aquaculture",
    "food_raw_materials_and_ornamental_resources",
    "coral_nonuse_existence_and_bequest_value",
    "maintenance_of_life_cycles_and_genetic_diversity",
    "coral_coastal_protection_and_moderation_of_extreme_events",
    "erosion_prevention",
    "ciam_coastal_impacts",
    "generic_biodiversity_nonuse",
    "climate_regulation_and_carbon_cycle_feedbacks",
    "waste_treatment_and_soil_fertility",
    "aesthetic_and_inspiration_values_without_separate_incidence_evidence",
}
LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "copying.txt", "notice", "notice.txt"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_output(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def validate_contract(contract: dict[str, object]) -> dict[str, object]:
    require(contract.get("schema") == SCHEMA, "contract schema changed")
    rff = contract.get("rff_scope_source")
    require(isinstance(rff, dict), "RFF scope source is missing")
    require(rff.get("role") == "sector_scope_and_research_priorities_not_a_damage_function", "RFF report cannot be treated as a damage function")
    require(len(rff.get("pdf_sha256_retrieved_2026_10_14", "")) == 64, "RFF report source hash is missing")
    target = contract.get("target_component")
    require(isinstance(target, dict), "target component is missing")
    require(
        target.get("included_welfare_endpoint")
        == "consumer_welfare_from_opportunities_for_coral_reef_recreation_and_tourism_only",
        "target must remain recreation/tourism consumer welfare only",
    )
    require(target.get("authorized_for_give") is False, "GIVE must remain unauthorized")
    require(target.get("published_scc_may_be_used_as_calibration") is False, "published SCC cannot be calibration")
    require(target.get("allocation_or_renormalization_allowed") is False, "allocation and renormalization must remain forbidden")
    require(set(contract.get("mandatory_exclusions", [])) == EXPECTED_EXCLUSIONS, "overlap exclusions are incomplete")

    sources = contract.get("primary_sources")
    require(isinstance(sources, list) and len(sources) == 5, "five bounded primary-source candidates are required")
    require({source.get("id") for source in sources if isinstance(source, dict)} == EXPECTED_SOURCE_IDS, "source inventory changed")
    for source in sources:
        require(isinstance(source, dict), "source entry must be an object")
        require(source.get("residual_transfer_status", "").startswith(("blocked_", "excluded_")), f"source improperly admitted: {source.get('id')}")

    blue = contract.get("blue_repository")
    require(isinstance(blue, dict), "Blue-SCC source pin is missing")
    bundle = blue.get("nonmarket_bundle_int2020_per_ha_year")
    require(isinstance(bundle, dict), "Blue-SCC service bundle is missing")
    components = [value for key, value in bundle.items() if key not in {"bundle_total", "bundle_standard_error", "bundle_income_elasticity", "bundle_income_elasticity_standard_error"}]
    require(sum(components) == bundle.get("bundle_total") == 36186, "nonmarket service bundle does not sum")
    require(bundle.get("opportunities_for_recreation_and_tourism") == 6271, "recreation source value changed")
    require(blue.get("service_specific_recreation_scc_row_expected") is False, "service-specific SCC cannot be presumed")

    request = contract.get("required_author_artifacts")
    require(isinstance(request, list) and len(request) == 7 and len(request) == len(set(request)), "seven author artifact groups are required")
    interface = contract.get("give_interface_if_artifacts_pass")
    require(isinstance(interface, dict), "future GIVE interface is missing")
    require(interface.get("grain") == "draw_path_country_year", "GIVE interface grain changed")
    require(len(interface.get("required_fields", [])) >= 13, "GIVE interface fields are incomplete")
    require(len(interface.get("required_identities", [])) == 5, "GIVE identities are incomplete")

    gate = contract.get("current_gate")
    require(isinstance(gate, dict), "current gate is missing")
    require(gate.get("status") == "blocked_no_overlap_cleared_service_specific_welfare_path", "blocked status changed")
    require(gate.get("published_result_reproduced_here") is False, "published result cannot be claimed reproduced")
    require(gate.get("damage_or_scc_authorized") is False, "damage or SCC must remain unauthorized")
    return {
        "contract_valid": True,
        "candidate_count": len(sources),
        "exclusion_count": len(EXPECTED_EXCLUSIONS),
        "author_artifact_group_count": len(request),
        "status": gate["status"],
        "damage_or_scc_authorized": False,
    }


def verify_repository(root: Path, pin: dict[str, object]) -> tuple[list[str], list[str]]:
    require(root.is_dir(), "repository root does not exist")
    require(git_output(root, "rev-parse", "HEAD") == pin.get("commit"), "repository commit differs from pin")
    tracked = [item for item in git_output(root, "ls-files").splitlines() if item]
    require(len(tracked) == pin.get("tracked_file_count"), "tracked file count differs from pin")
    for relative, expected in pin.get("pinned_files", {}).items():
        path = root / relative
        require(path.is_file(), f"pinned file is missing: {relative}")
        require(sha256(path) == expected, f"pinned file hash differs: {relative}")
    license_files = [relative for relative in tracked if Path(relative).name.casefold() in LICENSE_NAMES]
    return tracked, license_files


def audit_blue_repository(contract: dict[str, object], root: Path) -> dict[str, object]:
    pin = contract["blue_repository"]
    require(isinstance(pin, dict), "Blue-SCC pin is missing")
    tracked, licenses = verify_repository(root, pin)
    require(bool(licenses) is pin.get("repository_license_file_expected"), "Blue-SCC license-file status changed")
    missing = [relative for relative in pin["missing_end_to_end_paths"] if not (root / relative).exists()]
    require(missing == pin["missing_end_to_end_paths"], "Blue-SCC end-to-end path status changed")

    with (root / "Data/SCC/out/scc.csv").open(newline="", encoding="utf-8") as handle:
        scc_rows = list(csv.DictReader(handle))
    coral_rows = {row["Valuation type"]: float(row["SCC"]) for row in scc_rows if row["Asset type"] == "Corals"}
    require(coral_rows == pin["published_coral_scc_rows_external_only"], "published coral SCC rows changed")
    require("Recreation and tourism" not in coral_rows, "unexpected service-specific recreation row requires re-audit")

    country_sums: dict[str, float] = defaultdict(float)
    country_counts: dict[str, int] = defaultdict(int)
    with (root / "Data/SCC/out/country_level_scc.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["oc_capital"] != "Corals":
                continue
            value = float(row["scc"])
            require(math.isfinite(value), "country SCC contains nonfinite value")
            country_sums[row["valuation"]] += value
            country_counts[row["valuation"]] += 1
    require(set(country_sums) == set(coral_rows), "country/global coral valuation labels differ")
    require(set(country_counts.values()) == {155}, "country-level coral row coverage changed")
    differences = {key: country_sums[key] - coral_rows[key] for key in coral_rows}
    require(any(abs(value) > 1e-6 for value in differences.values()), "country/global decomposition unexpectedly became additive")

    with (root / "Data/output_modules_input_rice50x/input_rice50x/corals_areaDam_Value.csv").open(newline="", encoding="utf-8") as handle:
        input_rows = list(csv.DictReader(handle))
    require(len(input_rows) == 81, "coral coefficient country coverage changed")
    require({row["units"] for row in input_rows} == {"Int2020$_perkm2_peryear"}, "coral valuation units changed")
    source = (root / "Code/Corals/003_CountryAggregation_Values.r").read_text(encoding="utf-8")
    compact = "".join(source.split())
    require("100*(2+14369+4078+3418+1551+5580+6271+917)" in compact, "nonmarket service construction changed")
    require("100*(51218)" in compact, "bundle uncertainty construction changed")

    return {
        "url": pin["url"],
        "commit": pin["commit"],
        "tracked_file_count": len(tracked),
        "pinned_hashes_valid": True,
        "repository_license_files": licenses,
        "missing_end_to_end_paths": missing,
        "published_coral_rows_external_only": coral_rows,
        "country_level_row_count_per_valuation": country_counts,
        "country_sums": country_sums,
        "country_sum_minus_global_row": differences,
        "country_rows_are_additive_global_decomposition": False,
        "service_specific_recreation_scc_row_found": False,
        "coral_input_country_count": len(input_rows),
        "residual_transfer_ready": False,
    }


def audit_rice_repository(contract: dict[str, object], root: Path) -> dict[str, object]:
    pin = contract["rice_repository"]
    require(isinstance(pin, dict), "RICE50x pin is missing")
    tracked, licenses = verify_repository(root, pin)
    require(licenses == ["LICENSE"], "RICE50x license-file status changed")
    require("GNU GENERAL PUBLIC LICENSE" in (root / "LICENSE").read_text(encoding="utf-8"), "RICE50x license text changed")
    module = (root / "modules/mod_ocean.gms").read_text(encoding="utf-8")
    for term in ("eq_ocean_nmuse_value_coral", "eq_ocean_nonuse_value_coral", "ocean_theta_1", "ocean_theta_2"):
        require(term in module, f"RICE50x ocean implementation missing {term}")
    return {
        "url": pin["url"],
        "release": pin["release"],
        "commit": pin["commit"],
        "tracked_file_count": len(tracked),
        "pinned_hashes_valid": True,
        "license": pin["license"],
        "ocean_module_present": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--blue-root", type=Path, required=True)
    parser.add_argument("--rice-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    result = {
        "schema": "coral_residual_public_source_audit_v1",
        **validate_contract(contract),
        "contract": {"path": str(args.contract.resolve()), "sha256": sha256(args.contract)},
        "blue_repository_audit": audit_blue_repository(contract, args.blue_root.resolve()),
        "rice_repository_audit": audit_rice_repository(contract, args.rice_root.resolve()),
        "conclusion": "published_global_coral_scc_exists_but_no_overlap_cleared_recreation_transfer",
    }
    implementation = Path(__file__).resolve()
    result["implementation"] = {"path": str(implementation), "sha256": sha256(implementation)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print("coral residual audit passed; overlap-cleared GIVE gate remains blocked")


if __name__ == "__main__":
    main()
