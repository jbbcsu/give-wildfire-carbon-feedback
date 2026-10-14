"""Validate the biodiversity replication request and its pinned public-source audit.

This checker does not validate empirical parameters, damages, or an SCC.  It
fails closed unless the request remains an unsent, blocked seven-part request.
With ``--source-root``, it also reproduces the scoped negative search at the
pinned MimiGIVE revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


SCHEMA = "biodiversity_replication_request_v1"
EXPECTED_ARTIFACT_IDS = {
    "A1_executable_source_environment",
    "A2_regional_valuation_calibration",
    "A3_temperature_response_calibration",
    "A4_country_region_mapping",
    "A5_joint_uncertainty_pairing",
    "A6_matched_baseline_pulse_outputs",
    "A7_provenance_license_boundary",
}
EXPECTED_EXCLUSIONS = {
    "agriculture_and_crop_productivity",
    "fisheries_and_aquaculture",
    "coral_reef_tourism_and_recreation",
    "coastal_protection",
    "carbon_cycle_feedbacks",
    "hunting_and_subsistence",
    "commercial_harvest",
    "other_recreation",
    "other_market_and_use_ecosystem_services",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_request(request: dict[str, object]) -> dict[str, object]:
    require(request.get("schema") == SCHEMA, "request schema changed")
    require(request.get("request_status") == "unsent_blocking_artifact_request", "request must remain unsent")
    target = request.get("target_component")
    require(isinstance(target, dict), "target component is missing")
    require(target.get("name") == "biodiversity_nonuse_existence_value", "target must be nonuse existence value only")
    require(target.get("currency") == "USD" and target.get("price_year") == 2020, "currency basis changed")
    require(target.get("authorized_for_give") is False, "GIVE must remain unauthorized")
    require(target.get("published_benchmark_is_calibration") is False, "published benchmark cannot be calibration")

    publication = request.get("primary_publication")
    require(isinstance(publication, dict), "primary publication is missing")
    require(publication.get("replication_link_on_landing_page") is False, "public replication status changed; re-audit required")
    digest = publication.get("pdf_sha256_retrieved_2026_10_14")
    require(isinstance(digest, str) and len(digest) == 64, "publication PDF hash is missing")

    artifacts = request.get("required_artifacts")
    require(isinstance(artifacts, list) and len(artifacts) == 7, "exactly seven artifact groups are required")
    ids = {item.get("id") for item in artifacts if isinstance(item, dict)}
    require(ids == EXPECTED_ARTIFACT_IDS, "artifact groups changed")
    for item in artifacts:
        require(isinstance(item, dict), "artifact entry must be an object")
        require(item.get("license_required") is True, f"license is not required for {item.get('id')}")
        require(isinstance(item.get("minimum_files"), list) and item["minimum_files"], f"minimum files missing for {item.get('id')}")
        require(isinstance(item.get("required_content"), str) and item["required_content"].strip(), f"content specification missing for {item.get('id')}")

    columns = request.get("required_csv_columns")
    require(isinstance(columns, dict) and len(columns) == 6, "six tabular interfaces are required")
    for filename, names in columns.items():
        require(isinstance(filename, str) and filename.endswith(".csv"), "tabular interface filename changed")
        require(isinstance(names, list) and names and len(names) == len(set(names)), f"invalid columns for {filename}")

    boundary = request.get("overlap_boundary")
    require(isinstance(boundary, dict), "overlap boundary is missing")
    require(boundary.get("included") == ["nonuse_existence_value_only"], "included welfare boundary changed")
    require(set(boundary.get("excluded", [])) == EXPECTED_EXCLUSIONS, "overlap exclusions are incomplete")
    require(boundary.get("allocation_or_renormalization_allowed") is False, "allocation or renormalization must remain forbidden")

    gates = request.get("acceptance_gates")
    require(isinstance(gates, list) and len(gates) == len(set(gates)) and len(gates) >= 8, "acceptance gates are incomplete")
    current = request.get("current_gate")
    require(isinstance(current, dict), "current gate is missing")
    require(current.get("status") == "blocked_no_public_replication_artifacts", "blocked status changed")
    require(current.get("received_artifact_groups") == [], "received artifacts require a separate receipt audit")
    require(current.get("damage_or_scc_authorized") is False, "damage or SCC must remain unauthorized")
    return {
        "schema": "biodiversity_replication_request_audit_v1",
        "request_contract_valid": True,
        "artifact_group_count": len(artifacts),
        "overlap_exclusion_count": len(boundary["excluded"]),
        "status": current["status"],
        "damage_or_scc_authorized": False,
    }


def git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def audit_official_repository(request: dict[str, object], root: Path) -> dict[str, object]:
    audit = request["official_repository_audit"]
    require(isinstance(audit, dict), "official repository audit is missing")
    require(root.is_dir(), "source root does not exist")
    actual_commit = git_output(root, "rev-parse", "HEAD")
    require(actual_commit == audit.get("commit"), "official repository commit differs from pinned audit")
    tracked = [line for line in git_output(root, "ls-files").splitlines() if line]
    require(len(tracked) == audit.get("tracked_file_count"), "tracked file count differs from pinned audit")
    for relative, expected in audit.get("pinned_files", {}).items():
        path = root / relative
        require(path.is_file(), f"pinned source file missing: {relative}")
        require(sha256(path) == expected, f"pinned source hash differs: {relative}")

    terms = [term.casefold() for term in audit.get("case_insensitive_search_terms", [])]
    matches: list[str] = []
    for relative in tracked:
        path = root / relative
        try:
            content = path.read_text(encoding="utf-8").casefold()
        except (UnicodeDecodeError, OSError):
            continue
        if any(term in content for term in terms):
            matches.append(relative)
    matches.sort()
    require(matches == audit.get("expected_matching_tracked_files"), "official repository search result changed; re-audit required")
    return {
        "repository_url": audit["repository_url"],
        "commit": actual_commit,
        "tracked_file_count": len(tracked),
        "pinned_file_hashes_valid": True,
        "search_scope": "all git-tracked files decodable as UTF-8",
        "search_terms": audit["case_insensitive_search_terms"],
        "matching_tracked_files": matches,
        "biodiversity_component_found": bool(matches),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    result = validate_request(request)
    result["request"] = {"path": str(args.request.resolve()), "sha256": sha256(args.request)}
    if args.source_root is not None:
        result["official_repository_audit"] = audit_official_repository(request, args.source_root.resolve())
    else:
        result["official_repository_audit"] = {"performed": False}
    result["conclusion"] = "author_artifacts_required_no_public_source_version_route"
    implementation = Path(__file__).resolve()
    result["implementation"] = {"path": str(implementation), "sha256": sha256(implementation)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print("biodiversity replication request audit passed; GIVE gate remains blocked")


if __name__ == "__main__":
    main()
