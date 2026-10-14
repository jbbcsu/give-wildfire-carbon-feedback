#!/usr/bin/env python3
"""Fail-closed admission audit for the Williams wildfire-smoke draft.

This script validates only the investigator-supplied receipt, extracted draft
metadata, and hash-bound validation receipts. It does not open wildfire-CO2
project files, estimate coefficients, run GIVE, or calibrate to the reported
partial SCC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SCHEMA = "williams_wildfire_smoke_admission_contract/v1"
MANIFEST_SCHEMA = "williams_wildfire_smoke_artifact_manifest/v1"
GROUP_RECEIPT_SCHEMA = "williams_wildfire_smoke_group_receipt/v1"
RECEIPT_SCHEMA = "williams_wildfire_smoke_admission_receipt/v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {label}") from exc
    require(isinstance(value, dict), f"JSON object required: {label}")
    return value


def read_contract(path: Path) -> dict[str, Any]:
    contract = read_json_bytes(path.read_bytes(), str(path))
    require(contract.get("schema") == CONTRACT_SCHEMA, "unexpected contract schema")
    require(contract.get("scope") == "wildfire_smoke_pm25_mortality_only", "scope changed")
    require(
        set(contract["hard_gates"].values()) == {False},
        "checked-in hard gates must all remain false",
    )
    require(contract["calibration_to_reported_values_allowed"] is False, "calibration prohibited")
    require(len(contract["required_artifact_groups"]) == 8, "exactly eight groups required")
    return contract


def read_source_evidence(workspace: Path, spec: dict[str, Any]) -> bytes:
    if spec["kind"] == "workspace_file":
        path = (workspace / spec["path"]).resolve()
        require(path.is_file() and not path.is_symlink(), f"missing evidence: {spec['path']}")
        payload = path.read_bytes()
    elif spec["kind"] == "git_blob":
        repo = workspace / spec["repository"]
        require(repo.is_dir(), f"missing evidence repository: {spec['repository']}")
        result = subprocess.run(
            ["git", "-C", str(repo), "show", f"{spec['commit']}:{spec['path']}"],
            check=False,
            capture_output=True,
        )
        require(result.returncode == 0, f"missing pinned evidence blob: {spec['path']}")
        payload = result.stdout
    else:
        raise ValueError("unsupported evidence kind")
    require(len(payload) == spec["bytes"], f"evidence size mismatch: {spec.get('path')}")
    require(sha256_bytes(payload) == spec["sha256"], f"evidence hash mismatch: {spec.get('path')}")
    return payload


def validate_source_evidence(workspace: Path, contract: dict[str, Any]) -> dict[str, Any]:
    receipt_spec = contract["source_evidence"]["draft_receipt"]
    receipt = read_json_bytes(read_source_evidence(workspace, receipt_spec), "draft receipt")
    expected = contract["reported_draft_values_external_only"]
    require(
        receipt["reported_global_partial_scc_2025_usd_per_tco2"]
        == expected["global_partial_scc_2025_usd_per_tco2"],
        "draft receipt central value changed",
    )
    require(
        receipt["reported_conditional_95pct_interval"] == expected["conditional_95pct_interval"],
        "draft receipt interval changed",
    )
    require(receipt["discount_rate_percent"] == expected["discount_rate_percent"], "rate changed")
    require(
        receipt["reported_leave_cesm_out_global_mean"] == expected["leave_cesm_out_global_mean"],
        "leave-CESM value changed",
    )
    require(receipt["evidence_class"] == "unpublished_external_module", "evidence class changed")
    require("not additive" in receipt["integration_status"], "integration status changed")

    text_spec = contract["source_evidence"]["draft_text"]
    draft_text = read_source_evidence(workspace, text_spec).decode("utf-8")
    missing = [token for token in text_spec["required_tokens"] if token not in draft_text]
    require(not missing, f"draft evidence tokens missing: {missing}")
    return {
        "draft_receipt_valid": True,
        "draft_text_valid": True,
        "draft_pdf_locally_available": contract["source_evidence"]["draft_pdf"]["locally_available"],
        "reported_values_role": "unpublished_external_claims_only",
        "calibration_target": False,
    }


def safe_regular_file(root: Path, relative: str) -> Path:
    require(relative and not Path(relative).is_absolute(), "relative artifact path required")
    path = (root / relative).resolve()
    require(path == root or root in path.parents, "artifact path escapes project root")
    require(path.is_file() and not path.is_symlink(), f"missing regular artifact: {relative}")
    return path


def read_bound_group_receipt(root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    require(set(spec) == {"path", "bytes", "sha256"}, "unexpected receipt binding fields")
    path = safe_regular_file(root, spec["path"])
    payload = path.read_bytes()
    require(len(payload) == spec["bytes"], f"receipt size mismatch: {spec['path']}")
    require(sha256_bytes(payload) == spec["sha256"], f"receipt hash mismatch: {spec['path']}")
    return read_json_bytes(payload, spec["path"])


def validate_conflict_resolutions(
    manifest: dict[str, Any], contract: dict[str, Any], test_mode: bool
) -> dict[str, bool]:
    resolutions = manifest.get("source_conflict_resolutions", {})
    trials = resolutions.get("monte_carlo_trials", {})
    horizon = resolutions.get("projection_horizon", {})
    trial_ok = (
        trials.get("resolved") is True
        and trials.get("draft_reported_trial_count")
        == contract["unresolved_source_conflicts"]["monte_carlo_trials"]["draft_figure_count"]
        and trials.get("admitted_trial_count")
        == contract["required_artifact_groups"]["monte_carlo_outputs"]["trial_count"]
        and isinstance(trials.get("authority_reference"), str)
        and bool(trials["authority_reference"].strip())
    )
    horizon_ok = (
        horizon.get("resolved") is True
        and horizon.get("start_year") == 2025
        and isinstance(horizon.get("end_year"), int)
        and isinstance(horizon.get("year_count"), int)
        and horizon.get("year_count") == horizon.get("end_year") - 2025 + 1
        and isinstance(horizon.get("authority_reference"), str)
        and bool(horizon["authority_reference"].strip())
    )
    if not test_mode:
        trial_ok = trial_ok and trials.get("authority_reference") != "synthetic_test_only"
        horizon_ok = horizon_ok and horizon.get("authority_reference") != "synthetic_test_only"
    return {"monte_carlo_trials": trial_ok, "projection_horizon": horizon_ok}


def evaluate_manifest(
    root: Path, contract: dict[str, Any], manifest_path: Path, *, test_mode: bool = False
) -> dict[str, Any]:
    resolved_manifest = manifest_path.resolve()
    require(root == resolved_manifest or root in resolved_manifest.parents, "manifest escapes project root")
    require(
        resolved_manifest.is_file() and not resolved_manifest.is_symlink(),
        "regular artifact manifest required",
    )
    manifest = read_json_bytes(manifest_path.read_bytes(), str(manifest_path))
    require(manifest.get("schema") == MANIFEST_SCHEMA, "unexpected artifact manifest schema")
    require(manifest.get("calibration_to_reported_values_performed") is False, "calibration forbidden")
    require(manifest.get("wildfire_co2_project_accessed") is False, "wildfire-CO2 scope violation")

    required = contract["required_artifact_groups"]
    submitted = manifest.get("groups", {})
    require(set(submitted).issubset(required), "unknown artifact group")
    group_results: dict[str, bool] = {}
    for group, expected_checks in required.items():
        if group not in submitted:
            group_results[group] = False
            continue
        receipt = read_bound_group_receipt(root, submitted[group]["validation_receipt"])
        require(receipt.get("schema") == GROUP_RECEIPT_SCHEMA, f"bad receipt schema: {group}")
        require(receipt.get("group") == group, f"receipt group mismatch: {group}")
        require(receipt.get("validation_passed") is True, f"group not validated: {group}")
        require(isinstance(receipt.get("bound_artifacts"), list), f"artifact list missing: {group}")
        require(receipt["bound_artifacts"], f"no bound artifacts: {group}")
        for artifact in receipt["bound_artifacts"]:
            require(
                set(artifact) == {"path", "bytes", "sha256"},
                f"bad bound artifact metadata: {group}",
            )
            require(artifact["bytes"] > 0, f"empty bound artifact: {group}")
            require(len(artifact["sha256"]) == 64, f"bad artifact hash: {group}")
        group_results[group] = receipt.get("checks") == expected_checks

    conflicts = validate_conflict_resolutions(manifest, contract, test_mode)
    all_groups = all(group_results.values()) and len(group_results) == len(required)
    admitted = all_groups and all(conflicts.values())
    return {
        "group_results": group_results,
        "groups_passed": sum(group_results.values()),
        "groups_required": len(required),
        "conflict_resolutions": conflicts,
        "artifact_package_admitted_for_reproduction": admitted,
        "reported_partial_scc_reproduced": False,
        "give_transfer_authorized": False,
        "replacement_or_addition_scc_authorized": False,
    }


def audit_current(root: Path, contract_path: Path) -> dict[str, Any]:
    contract = read_contract(contract_path)
    workspace = root.parent
    evidence = validate_source_evidence(workspace, contract)
    manifest_path = root / contract["candidate_manifest_path"]
    if manifest_path.exists():
        admission = evaluate_manifest(root, contract, manifest_path)
    else:
        required = contract["required_artifact_groups"]
        admission = {
            "group_results": {name: False for name in required},
            "groups_passed": 0,
            "groups_required": len(required),
            "conflict_resolutions": {
                "monte_carlo_trials": False,
                "projection_horizon": False,
            },
            "artifact_package_admitted_for_reproduction": False,
            "reported_partial_scc_reproduced": False,
            "give_transfer_authorized": False,
            "replacement_or_addition_scc_authorized": False,
        }
    require(not admission["artifact_package_admitted_for_reproduction"], "checked-in package must reject")
    return {
        "schema": RECEIPT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "rejected_incomplete_local_artifacts",
        "source_evidence": evidence,
        "operational_artifact_admission": admission,
        "unresolved_source_conflicts": contract["unresolved_source_conflicts"],
        "reported_draft_values": contract["reported_draft_values_external_only"],
        "reported_values_used_as_calibration_targets": False,
        "wildfire_co2_project_files_used": False,
        "hard_gates": contract["hard_gates"],
        "claim_status": (
            "investigator draft metadata is authenticated, but zero of eight operational artifact "
            "groups are admitted; reproduction, mortality-overlap clearance, GIVE transfer, and SCC "
            "addition remain closed"
        ),
        "contract": {
            "path": str(contract_path.relative_to(root)),
            "sha256": sha256(contract_path),
        },
        "implementation": {
            "validator": {
                "path": "scripts/validate_williams_wildfire_smoke_admission.py",
                "sha256": sha256(Path(__file__).resolve()),
            },
            "synthetic_tests": {
                "path": "test/test_williams_wildfire_smoke_admission.py",
                "sha256": sha256(root / "test/test_williams_wildfire_smoke_admission.py"),
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/williams_wildfire_smoke_admission_v1.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else root / args.contract
    result = audit_current(root, contract_path)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        require(not output.exists(), "fresh output path required")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
