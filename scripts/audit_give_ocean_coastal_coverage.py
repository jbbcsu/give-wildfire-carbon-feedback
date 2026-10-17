"""Fail-closed audit of ocean/coastal coverage in the exact GIVE target."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


SCHEMA = "give_ocean_coastal_coverage_v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_files(root: Path, files: dict[str, str]) -> None:
    for relative, expected in files.items():
        path = root / relative
        require(path.is_file(), f"missing pinned file: {relative}")
        require(sha256(path) == expected, f"hash changed: {relative}")


def validate_contract(contract: dict[str, object]) -> dict[str, object]:
    require(contract.get("schema") == SCHEMA, "contract schema changed")
    coverage = contract.get("coverage")
    require(isinstance(coverage, dict), "coverage inventory missing")
    coastal = coverage.get("coastal_sea_level_rise", {})
    require(coastal.get("status") == "represented_in_ciam_and_added_to_scc", "CIAM coverage status changed")
    require(coastal.get("generic_additional_coastal_flood_module_authorized") is False, "coastal double-count gate opened")
    require(len(coastal.get("covered_endpoints", [])) == 9, "CIAM endpoint inventory incomplete")
    ph = coverage.get("ocean_acidification", {})
    require(ph.get("status") == "physical_ph_driver_present_but_no_damage_connection", "pH boundary changed")
    require(ph.get("damage_aggregator_connection_present") is False, "unsupported pH damage connection claimed")
    ecosystem = coverage.get("ocean_ecosystem_nonmarket_welfare", {})
    require(ecosystem.get("selected_residual") == "consumer_welfare_from_coral_reef_recreation_and_tourism_only", "residual target changed")
    decisions = contract.get("candidate_decisions")
    require(isinstance(decisions, list) and len(decisions) == 5, "candidate inventory incomplete")
    selected = [item for item in decisions if item.get("decision") == "selected_research_target_but_not_yet_additive"]
    require([item.get("id") for item in selected] == ["coral_recreation_consumer_welfare"], "candidate selection changed")
    gates = contract.get("claim_gates")
    require(isinstance(gates, dict), "claim gates missing")
    for key in (
        "numeric_give_addition_authorized",
        "published_headline_scc_may_be_added",
        "service_bundle_allocation_allowed",
        "gross_revenue_or_trade_at_risk_may_be_called_welfare_loss",
    ):
        require(gates.get(key) is False, f"fail-closed gate opened: {key}")
    require(len(gates.get("required_before_addition", [])) == 5, "admission requirements incomplete")
    return {"contract_valid": True, "numeric_give_addition_authorized": False}


def audit_give(root: Path, contract: dict[str, object]) -> dict[str, object]:
    snapshot = contract["give_snapshot"]
    verify_files(root, snapshot["files"])
    aggregator = (root / "MimiGIVE/src/components/DamageAggregator.jl").read_text(encoding="utf-8")
    main = (root / "MimiGIVE/src/main_model.jl").read_text(encoding="utf-8")
    scc = (root / "MimiGIVE/src/scc.jl").read_text(encoding="utf-8")
    ciam = (root / "MimiCIAM/src/slrcost.jl").read_text(encoding="utf-8")
    ph = (root / "Mimi_NAS_pH/src/components/ocean_ph_component.jl").read_text(encoding="utf-8")
    for token in ("include_slr", "ciam_marginal_damages", "main_marginal_damages .+ ciam_marginal_damages", "_compute_ciam_marginal_damages"):
        require(token in aggregator + scc, f"missing GIVE/CIAM SCC token: {token}")
    for token in ("NoAdaptCost", "ProtectCost", "RetreatCost", "OptimalCost", "StormCapitalNoAdapt", "StormPopNoAdapt", "WetlandNoAdapt", "FloodNoAdapt", "RelocateNoAdapt"):
        require(token in ciam, f"missing CIAM endpoint token: {token}")
    for token in ("Mimi_NAS_pH.ocean_pH", "OceanPH => :atm_co2_conc"):
        require(token in main, f"missing ocean-pH driver token: {token}")
    require("pH = Variable" in ph, "ocean-pH output missing")
    require("OceanPH" not in aggregator, "ocean pH unexpectedly enters DamageAggregator")
    return {
        "pinned_hashes_valid": True,
        "ciam_is_added_to_scc": True,
        "ciam_endpoint_token_count": 9,
        "ocean_ph_physical_driver_present": True,
        "ocean_ph_damage_connection_present": False,
    }


def audit_blue(root: Path, contract: dict[str, object]) -> dict[str, object]:
    snapshot = contract["blue_scc_snapshot"]
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    require(commit == snapshot["commit"], "Blue-SCC commit changed")
    verify_files(root, snapshot["files"])
    coral = (root / "Code/Corals/003_CountryAggregation_Values.r").read_text(encoding="utf-8")
    ports_read = (root / "Code/Ports/001_ReadPortsDisruptions.r").read_text(encoding="utf-8")
    ports_fit = (root / "Code/Ports/002_Ports_TempCoeff.r").read_text(encoding="utf-8")
    compact = "".join(coral.split())
    require("100*(2+14369+4078+3418+1551+5580+6271+917)" in compact, "coral nonmarket bundle changed")
    for token in ("Revenue_risk_base", "Trade at-risk", "risk_percGDP_2050"):
        require(token in ports_read, f"ports source semantics changed: {token}")
    require("GDP_FractionChange_perC" in ports_fit, "ports GDP-fraction coefficient missing")
    return {
        "commit": commit,
        "pinned_hashes_valid": True,
        "coral_nonmarket_is_multiservice_bundle": True,
        "ports_combines_revenue_or_trade_risk_with_gdp_fraction_mapping": True,
        "overlap_cleared_additive_candidate_found": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--give-root", type=Path, required=True)
    parser.add_argument("--blue-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    result = {
        "schema": "give_ocean_coastal_coverage_receipt_v1",
        **validate_contract(contract),
        "contract_sha256": sha256(args.contract),
        "give_audit": audit_give(args.give_root, contract),
        "blue_scc_audit": audit_blue(args.blue_root, contract),
        "selection": "coral_recreation_consumer_welfare_research_target_only",
        "conclusion": "coastal_slr_already_covered_ocean_ecosystem_nonmarket_welfare_is_the_residual_gap",
    }
    implementation = Path(__file__).resolve()
    result["implementation_sha256"] = sha256(implementation)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print("ocean/coastal coverage audit passed; numeric coral residual remains gated")


if __name__ == "__main__":
    main()
