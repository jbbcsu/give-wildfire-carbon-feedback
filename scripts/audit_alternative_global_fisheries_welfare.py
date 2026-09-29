#!/usr/bin/env python3
"""Fail-closed literature/source audit of global climate-fisheries welfare candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SCHEMA = "alternative_global_fisheries_welfare_audit_config_v1"
CONFIG_ROLE = "source_first_fail_closed_screen_for_global_climate_fisheries_consumer_and_producer_surplus"
BOOLEAN_CRITERIA = (
    "usable_global_geographic_coverage",
    "climate_response",
    "consumer_surplus",
    "producer_surplus",
    "auditable_data_and_code",
    "usable_license",
    "marginal_pulse_compatible_or_pairable",
    "overlap_boundary_resolved",
)
SURPLUS_TERMS = ("consumer surplus", "consumer_surplus", "producer surplus", "producer_surplus")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_git(source_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def scan_country_csv(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        required = {"sovereign_iso3", "sovereign", "rcp", "scenario"}
        if not required.issubset(fields):
            raise ValueError(f"country output schema incomplete: {path}")
        rows = list(reader)
    return {
        "rows": len(rows),
        "columns": fields,
        "sovereign_iso3_count": len({row["sovereign_iso3"] for row in rows}),
        "sovereign_label_count": len({row["sovereign"] for row in rows}),
        "rcps": sorted({row["rcp"] for row in rows}),
        "scenarios": sorted({row["scenario"] for row in rows}),
        "consumer_surplus_column": any("consumer" in item.lower() and "surplus" in item.lower() for item in fields),
        "producer_surplus_column": any("producer" in item.lower() and "surplus" in item.lower() for item in fields),
        "profit_columns": [item for item in fields if item.lower().startswith("p")],
    }


def validate_candidates(config: dict) -> tuple[list[dict], list[str]]:
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("alternative-welfare config identity changed")
    if tuple(config["qualification"]["required"]) != BOOLEAN_CRITERIA:
        raise ValueError("qualification criteria changed")
    candidates = list(config.get("candidates", []))
    ids = [item.get("id") for item in candidates]
    if len(candidates) < 3 or len(set(ids)) != len(ids):
        raise ValueError("candidate screen is too small or has duplicate ids")
    required_text = {
        "id", "title", "primary_source", "official_repository", "license_access",
        "geographic_coverage", "response_semantics", "welfare_semantics",
        "pulse_compatibility", "overlap_risks",
    }
    for item in candidates:
        if not required_text.issubset(item) or any(key not in item for key in BOOLEAN_CRITERIA):
            raise ValueError(f"candidate record is incomplete: {item.get('id')}")
        if any(not isinstance(item[key], bool) for key in BOOLEAN_CRITERIA):
            raise ValueError(f"candidate criteria are not boolean: {item['id']}")
    qualifying = [item["id"] for item in candidates if all(item[key] for key in BOOLEAN_CRITERIA)]
    return candidates, qualifying


def audit_source(source_root: Path, pin: dict) -> dict[str, object]:
    if not source_root.is_dir():
        raise ValueError(f"source repository not found: {source_root}")
    head = run_git(source_root, "rev-parse", "HEAD")
    if head != pin["commit"]:
        raise ValueError(f"source commit changed: {head}")

    pinned_paths = {
        "readme": pin["readme"],
        "format_script": pin["format_script"],
        "approach1_csv": pin["approach1_csv"],
        "approach2_csv": pin["approach2_csv"],
    }
    hashes: dict[str, dict[str, str]] = {}
    for key, relative in pinned_paths.items():
        path = source_root / relative
        expected = pin[f"{key}_sha256"]
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"pinned source missing or hash changed: {key}")
        hashes[key] = {"path": relative, "sha256": expected}

    format_text = (source_root / pin["format_script"]).read_text(encoding="utf-8")
    required_evidence = (
        'readRDS(file.path(datadir, "eez_delta_k_df.rds"))',
        'readRDS(file.path(datadir, "global_cc_1nation_manuscript_2019Feb12.rds"))',
        "spread perfect uniformly",
        "profit_eez=profit*range_prop",
    )
    if any(token not in format_text for token in required_evidence):
        raise ValueError("expected allocation or missing-input evidence changed")

    missing_raw = list(pin["missing_raw_inputs"])
    if any((source_root / relative).exists() for relative in missing_raw):
        raise ValueError("a registered missing raw input is now present; re-review required")
    root_license_names = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING")
    root_licenses = [name for name in root_license_names if (source_root / name).is_file()]
    if root_licenses:
        raise ValueError("repository license state changed; re-review required")

    source_files = sorted(
        path for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".r", ".rmd"} and ".git" not in path.parts
    )
    hits = {term: 0 for term in SURPLUS_TERMS}
    for path in source_files:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for term in SURPLUS_TERMS:
            hits[term] += text.count(term)
    if len(source_files) != int(pin["expected_r_or_rmd_source_files"]) or sum(hits.values()) != int(pin["expected_surplus_term_hits"]):
        raise ValueError("released source inventory or surplus-term result changed")

    csvs = {
        "approach1": scan_country_csv(source_root / pin["approach1_csv"]),
        "approach2": scan_country_csv(source_root / pin["approach2_csv"]),
    }
    expected_rcps = sorted(pin["expected_rcps_each_csv"])
    expected_scenarios = sorted(pin["expected_scenarios_each_csv"])
    for name, summary in csvs.items():
        checks = (
            summary["rows"] == int(pin["expected_rows_each_csv"]),
            summary["sovereign_iso3_count"] == int(pin["expected_sovereign_iso3_each_csv"]),
            summary["sovereign_label_count"] == int(pin["expected_sovereign_labels_each_csv"]),
            summary["rcps"] == expected_rcps,
            summary["scenarios"] == expected_scenarios,
            not summary["consumer_surplus_column"],
            not summary["producer_surplus_column"],
        )
        if not all(checks):
            raise ValueError(f"released country output changed: {name}")

    return {
        "repository": pin["repository"],
        "commit": head,
        "commit_date": pin["commit_date"],
        "pinned_files": hashes,
        "root_license_files": root_licenses,
        "missing_raw_inputs": missing_raw,
        "r_or_rmd_source_files": len(source_files),
        "surplus_term_hits": hits,
        "country_outputs": csvs,
        "allocation_semantics": "global biomass_harvest_profit_times_species_range_share_assuming_uniform_distribution",
    }


def audit(config_path: Path, source_root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    candidates, qualifying = validate_candidates(config)
    source = audit_source(source_root, config["source_pin"])
    if qualifying:
        raise ValueError("a candidate now passes all gates; scientific re-review required")
    gates = dict(config["claim_gates"])
    if any(gates.values()):
        raise ValueError("config improperly opens a downstream gate")
    request = list(config["external_data_request"]["request"])
    if len(request) != 7 or len(set(request)) != len(request):
        raise ValueError("external data request changed or contains duplicates")
    return {
        "schema": "alternative_global_fisheries_welfare_audit_v1",
        "role": config["role"],
        "status": "negative_no_qualifying_published_global_climate_consumer_plus_producer_surplus_model",
        "screened_candidates": candidates,
        "qualification_criteria": list(BOOLEAN_CRITERIA),
        "qualifying_candidates": qualifying,
        "closest_candidate_source_audit": source,
        "decision": {
            "closest_candidate": config["source_pin"]["candidate_id"],
            "why_it_fails": [
                "coverage_is_58.2_percent_of_reported_2012_global_catch_not_complete",
                "profit_is_not_a_joint_consumer_plus_producer_surplus_measure",
                "consumer_surplus_is_absent",
                "raw_model_inputs_and_executable_model_core_are_not_in_the_release",
                "repository_has_no_explicit_root_license_at_pinned_commit",
                "released_outputs_are_rcp_and_management_scenarios_not_a_marginal_co2_pulse_pair",
                "uniform_range_share_allocation_does_not_identify_producer_or_consumer_incidence",
            ],
            "coefficient_transfer_authorized": False,
            "fit_authorized": False,
            "damage_or_scc_authorized": False,
        },
        "external_data_request": {
            "target": config["external_data_request"]["target"],
            "items": request,
        },
        "claim_gates": gates,
        "config": {"path": str(config_path.relative_to(ROOT)), "sha256": sha256(config_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path,
        default=ROOT / "config/alternative_global_fisheries_welfare_audit_v1.toml",
    )
    parser.add_argument("--source-root", type=Path, required=True, help="Pinned clone of SFG-UCSB/cc_trade")
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "data/provenance/alternative_global_fisheries_welfare_audit_20260928.json",
    )
    args = parser.parse_args()
    result = audit(args.config.resolve(), args.source_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(result["status"])


if __name__ == "__main__":
    main()
