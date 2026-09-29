#!/usr/bin/env python3
"""Validate the metadata-only soybean production portability closure."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DIRECT_ROLES = {
    "direct_receipt", "direct_panel", "heat_receipt", "heat_panel",
    "scpdsi_receipt", "scpdsi_panel", "calendar_noirr", "calendar_firr",
    "mirca_weights", "mirca_audit", "mirca_welfare_support",
    "country_proxy", "mapspam_production_audit", "faostat_value_audit",
    "value_crosswalk_audit",
}
PRODUCTION_ROLES = {"direct", "heat", "scpdsi", "country_proxy"}
REACQUISITION_IDS = {
    "gdhy", "isimip3a_daily", "ggcmi_calendars", "mirca_os_v2",
    "cru_scpdsi", "mapspam2000", "faostat_qv", "nga_genc", "unsd_m49",
}
REQUIRED_REBUILD_PATHS = {
    "config/continuous_global_panel_1982_2016_v1.toml",
    "config/soybean_global_response_readiness_audit_v1.toml",
    "config/soybean_continuous_design_heterogeneity_preflight_v1.toml",
    "scripts/run_continuous_global_panel_partitions.py",
    "scripts/assemble_continuous_global_panel_partitions.py",
    "scripts/allocate_irrigation_distribution_basis.py",
    "scripts/allocate_irrigation_heat_basis.py",
    "scripts/allocate_irrigation_scpdsi_basis.py",
    "scripts/assemble_continuous_candidate_periods.py",
    "scripts/build_mapspam_country_grid.py",
    "GLOBAL_COUNTRY_CONTROL_PROTOCOL_20260907.md",
    "environment/python-requirements.txt",
}


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def resolve_inside(root: Path, relative: str) -> Path:
    require(not Path(relative).is_absolute(), "portability path must be repository-relative")
    path = (root / relative).resolve()
    require(path == root or root in path.parents, "portability path escapes repository root")
    return path


def verify_binding(root: Path, item: dict[str, Any]) -> None:
    require(set(("path", "bytes", "sha256")) <= set(item), "incomplete file binding")
    path = resolve_inside(root, item["path"])
    require(path.is_file(), f"bound file is absent: {item['path']}")
    require(path.stat().st_size == item["bytes"], f"bound size differs: {item['path']}")
    require(sha256(path) == item["sha256"], f"bound hash differs: {item['path']}")


def validate_manifest(manifest: dict[str, Any], root: Path, *, verify_files: bool = True) -> dict[str, bool]:
    root = root.resolve()
    require(manifest.get("schema") == "soybean_pooled_response_production_portability/v1", "portability schema differs")
    require(manifest.get("status") == "metadata_only_portability_bound_no_real_access_or_fit", "portability status differs")
    access = manifest["content_access"]
    require(access == {"opaque_stream_hashing_only": True, "outcome_values_read": False, "table_schemas_inspected": False}, "content-access boundary differs")
    require(set(manifest["production_declared_path_roles"]) == PRODUCTION_ROLES, "production declared-path roles differ")

    direct = manifest["direct_artifacts"]
    require(len(direct) == 15, "direct artifact count differs")
    require({item["role"] for item in direct} == DIRECT_ROLES, "direct artifact roles differ")
    require(len({item["path"] for item in direct}) == 15, "direct artifact paths are not unique")
    require(all(item.get("ignored_untracked_required") is True for item in direct), "direct artifact is not marked ignored/untracked")

    periods = manifest["period_components"]
    require(len(periods) == 9, "period component count differs")
    require({(item["family"], item["period"]) for item in periods} == {(family, period) for family in ("direct", "heat", "scpdsi") for period in ("early", "middle", "later")}, "period component grid differs")
    missing = [item for item in periods if not item["locally_present"]]
    require(len(missing) == 3 and {(item["family"], item["period"]) for item in missing} == {(family, "middle") for family in ("direct", "heat", "scpdsi")}, "missing-period declaration differs")
    require(all(item["fallback"] == "middle_aggregate_checkpoint_all_20" for item in missing), "missing period lacks the frozen fallback")

    fallback = manifest["aggregate_fallback_group"]
    require(fallback["id"] == "middle_aggregate_checkpoint_all_20", "aggregate fallback id differs")
    require(fallback["source_partitions_retained"] is False, "evicted source-partition status differs")
    aggregates = fallback["aggregate_files"]
    require(len(aggregates) == 20 and len({item["path"] for item in aggregates}) == 20, "aggregate fallback count or uniqueness differs")
    require({item["crop"] for item in aggregates} == {"mai", "soy"}, "aggregate crop closure differs")
    require({item["family"] for item in aggregates} == {"direct_season", "direct_stage", "heat_season", "heat_stage", "historical_scpdsi_stage"}, "aggregate family closure differs")
    require({item["irrigation"] for item in aggregates} == {"firr", "noirr"}, "aggregate irrigation closure differs")

    country = manifest["country_proxy_transform"]
    require(country["required_declared_path_role"] == "country_proxy", "country proxy is not in production declared paths")
    require(country["redistribution_authorized"] is False, "country proxy redistribution opened")
    direct_country = next(item for item in direct if item["role"] == "country_proxy")
    require({key: country["input"][key] for key in ("path", "bytes", "sha256")} == {key: direct_country[key] for key in ("path", "bytes", "sha256")}, "country transform input differs from direct closure")

    rebuild = manifest["rebuild_bindings"]
    require({item["path"] for item in rebuild} == REQUIRED_REBUILD_PATHS, "rebuild binding closure differs")
    require(len(rebuild) == len(REQUIRED_REBUILD_PATHS), "duplicate rebuild binding")
    environment = manifest["environment"]
    env_binding = next(item for item in rebuild if item["path"] == "environment/python-requirements.txt")
    require(all(environment[key] == env_binding[key] for key in ("path", "bytes", "sha256")), "environment/rebuild binding differs")

    reacquisition = manifest["reacquisition"]
    require({item["source_id"] for item in reacquisition} == REACQUISITION_IDS, "reacquisition source closure differs")
    require(len(reacquisition) == len(REACQUISITION_IDS), "duplicate reacquisition source")
    for item in reacquisition:
        require(bool(item["license"]), f"missing license statement: {item['source_id']}")
        require(item["automated_reacquisition"] is (item["acquisition_script"] is not None), "acquisition automation flag differs")

    license_state = manifest["composite_license"]
    require(license_state["redistribution_authorized"] is False, "composite redistribution unexpectedly authorized")
    require(license_state["internal_reproduction_status"] == "conditional_on_source_terms_not_legal_clearance", "internal-reproduction status overstates license clearance")
    require(license_state["authorization_token_does_not_confer_redistribution_rights"] is True, "token/redistribution separation absent")
    require(len(license_state["blocking_terms"]) >= 4, "composite license blockers incomplete")
    require(not any(manifest["claim_gates"].values()), "portability manifest opens a claim gate")

    if verify_files:
        for item in direct:
            verify_binding(root, item)
        for item in periods:
            path = resolve_inside(root, item["path"])
            if item["locally_present"]:
                verify_binding(root, item)
            else:
                require(not path.exists(), f"manifest says missing but period exists: {item['path']}")
        verify_binding(root, fallback["receipt"])
        for item in aggregates:
            verify_binding(root, item)
        for key in ("receipt", "code", "protocol"):
            verify_binding(root, country[key])
        for item in rebuild:
            verify_binding(root, item)
        for item in reacquisition:
            verify_binding(root, item["provenance_record"])
            if item["acquisition_script"] is not None:
                verify_binding(root, item["acquisition_script"])
        verify_binding(root, environment)

    return {
        "metadata_only": True, "direct_15_bound": True, "period_9_bound": True,
        "aggregate_fallback_20_bound": True, "country_proxy_transform_bound": True,
        "production_declared_path_closure_bound": True, "rebuild_environment_bound": True,
        "reacquisition_and_license_bound": True, "claim_gates_closed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-cap-bytes", type=int, default=536870912)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh portability validation output required")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tests = json.loads(args.tests.read_text(encoding="utf-8"))
    checks = validate_manifest(manifest, args.root.resolve(), verify_files=True)
    require(tests["tests"]["all_pass"] and all(tests["tests"]["checks"].values()), "portability focused tests failed")
    rss = peak_rss_bytes()
    require(rss < args.memory_cap_bytes, "portability validator memory cap exceeded")
    implementation = Path(__file__).resolve()
    result = {
        "schema": "soybean_pooled_response_production_portability_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_metadata_only_portability_no_real_access_or_fit",
        "bindings": {
            "manifest": {"path": str(args.manifest), "sha256": sha256(args.manifest)},
            "tests": {"path": str(args.tests), "sha256": sha256(args.tests)},
            "implementation": {"path": str(implementation.relative_to(args.root.resolve())), "sha256": sha256(implementation)},
        },
        "checks": checks,
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": args.memory_cap_bytes, "memory_gate_passed": True},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks, "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()
