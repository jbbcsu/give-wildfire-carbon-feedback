#!/usr/bin/env python3
"""Build the metadata-only portability closure for pooled soybean execution.

Parquet and NetCDF artifacts are treated as opaque byte streams.  This script
does not import a table reader, inspect a schema, or read an outcome value.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
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
RECEIPTS = {
    "direct": "outputs/continuous_global_panel_1982_2016_v1/soy_1982_2016_direct_assembly_receipt.json",
    "heat": "outputs/continuous_global_panel_1982_2016_v1/soy_1982_2016_heat_assembly_receipt.json",
    "scpdsi": "outputs/continuous_global_panel_1982_2016_v1/soy_1982_2016_scpdsi_assembly_receipt.json",
}
MIDDLE_RECEIPT = "data/interim/continuous_global_panel_1982_2016_v1/assembled_middle_1990_2011/assembly_receipt.json"
REBUILD_PATHS = [
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
]
REACQUISITION = [
    ("gdhy", "data/provenance/gdhy_v1.2_v1.3_20190128.toml", None, "CC-BY-4.0; verify before redistribution"),
    ("isimip3a_daily", "data/provenance/isimip3a_daily_climate_plan.toml", "scripts/download_isimip3a_climate.sh", "CC0-1.0"),
    ("ggcmi_calendars", "data/provenance/isimip_crop_calendar_2015soc.toml", None, "CC0-1.0"),
    ("mirca_os_v2", "data/provenance/mirca_os_v2_irrigation_shares.toml", "scripts/download_mirca_os_v2.py", "CC-BY-4.0"),
    ("cru_scpdsi", "data/provenance/cru_scpdsi.toml", "scripts/download_cru_scpdsi.py", "ODbL; CRU attribution required"),
    ("mapspam2000", "data/provenance/mapspam2000_production.toml", "scripts/acquire_mapspam2000_production.py", "conflicting CC-BY-4.0/CC-BY-NC-3.0 statements; redistribution disabled"),
    ("faostat_qv", "data/provenance/faostat_qv_maize_soy.toml", "scripts/acquire_faostat_qv_maize_soy.py", "CC-BY-4.0 plus FAO terms"),
    ("nga_genc", "data/provenance/nga_genc_gec_crosswalk.toml", None, "NOASSERTION"),
    ("unsd_m49", "data/provenance/unsd_m49_country_codes.toml", None, "NOASSERTION"),
]


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(root: Path, path: Path) -> str:
    resolved = path.resolve()
    require(root == resolved or root in resolved.parents, "path escapes repository root")
    return str(resolved.relative_to(root))


def binding(root: Path, path: str) -> dict[str, Any]:
    target = (root / path).resolve()
    require(target.is_file(), f"required portability artifact is absent: {path}")
    return {"path": relative(root, target), "bytes": target.stat().st_size, "sha256": sha256(target)}


def build(root: Path) -> dict[str, Any]:
    readiness_path = root / "config/soybean_global_response_readiness_audit_v1.toml"
    readiness = tomllib.loads(readiness_path.read_text(encoding="utf-8"))
    sources = readiness["sources"]
    require(DIRECT_ROLES <= set(sources), "readiness config no longer exposes the direct portability closure")

    direct_artifacts = []
    for role in sorted(DIRECT_ROLES):
        item = binding(root, sources[role]["path"])
        require(item["sha256"] == sources[role]["sha256"], f"direct artifact hash differs: {role}")
        item.update({"role": role, "ignored_untracked_required": True})
        direct_artifacts.append(item)
    require(len({item["path"] for item in direct_artifacts}) == 15, "direct artifact closure is not exactly 15 unique files")

    period_components: list[dict[str, Any]] = []
    for family, receipt_path in RECEIPTS.items():
        receipt_file = root / receipt_path
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        require(receipt["family"] == family and len(receipt["periods"]) == 3, f"unexpected {family} receipt")
        for period in receipt["periods"]:
            path = root / period["path"]
            present = path.is_file()
            if present:
                require(path.stat().st_size == period["bytes"], f"period size differs: {period['path']}")
                require(sha256(path) == period["sha256"], f"period hash differs: {period['path']}")
            period_components.append({
                "family": family, "period": period["period"], "path": period["path"],
                "bytes": period["bytes"], "sha256": period["sha256"],
                "locally_present": present,
                "fallback": "middle_aggregate_checkpoint_all_20" if not present else None,
            })
    require(len(period_components) == 9, "period closure is not exactly nine components")
    require(sum(not item["locally_present"] for item in period_components) == 3, "expected exactly three absent middle candidates")

    middle_path = root / MIDDLE_RECEIPT
    middle = json.loads(middle_path.read_text(encoding="utf-8"))
    aggregate_fallbacks = []
    for record in middle["aggregate_tables"]:
        item = binding(root, record["path"])
        require(item["bytes"] == record["bytes"] and item["sha256"] == record["sha256"], f"aggregate fallback differs: {record['path']}")
        item.update({
            "crop": record["crop"], "family": record["family"],
            "irrigation": record["irrigation"], "rows": record["rows"],
        })
        aggregate_fallbacks.append(item)
    require(len(aggregate_fallbacks) == 20, "aggregate fallback closure is not exactly 20 files")

    proxy_receipt_path = root / "data/provenance/global_country_proxy_20260907.json"
    proxy_receipt = json.loads(proxy_receipt_path.read_text(encoding="utf-8"))
    country_transform = {
        "operation": "many_to_one join on exact lat and lon_360; retain only country_count == 1 for the primary fit",
        "required_declared_path_role": "country_proxy",
        "input": next(item for item in direct_artifacts if item["role"] == "country_proxy"),
        "receipt": binding(root, relative(root, proxy_receipt_path)),
        "code": binding(root, "scripts/build_mapspam_country_grid.py"),
        "protocol": binding(root, "GLOBAL_COUNTRY_CONTROL_PROTOCOL_20260907.md"),
        "redistribution_authorized": False,
    }
    require(country_transform["code"]["sha256"] == proxy_receipt["code_sha256"], "country transform code differs")
    require(country_transform["protocol"]["sha256"] == proxy_receipt["protocol_sha256"], "country transform protocol differs")

    reacquisition = []
    for source_id, record_path, script_path, license_text in REACQUISITION:
        record = binding(root, record_path)
        script = binding(root, script_path) if script_path else None
        reacquisition.append({
            "source_id": source_id, "provenance_record": record,
            "automated_reacquisition": script is not None, "acquisition_script": script,
            "license": license_text,
        })

    return {
        "schema": "soybean_pooled_response_production_portability/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "metadata_only_portability_bound_no_real_access_or_fit",
        "content_access": {
            "outcome_values_read": False, "table_schemas_inspected": False,
            "opaque_stream_hashing_only": True,
        },
        "production_declared_path_roles": ["direct", "heat", "scpdsi", "country_proxy"],
        "direct_artifacts": direct_artifacts,
        "period_components": period_components,
        "aggregate_fallback_group": {
            "id": "middle_aggregate_checkpoint_all_20",
            "receipt": binding(root, MIDDLE_RECEIPT),
            "source_partitions_retained": False,
            "aggregate_files": aggregate_fallbacks,
        },
        "country_proxy_transform": country_transform,
        "rebuild_bindings": [binding(root, path) for path in REBUILD_PATHS],
        "reacquisition": reacquisition,
        "composite_license": {
            "redistribution_authorized": False,
            "internal_reproduction_status": "conditional_on_source_terms_not_legal_clearance",
            "authorization_token_does_not_confer_redistribution_rights": True,
            "blocking_terms": [
                "MapSPAM source statements conflict between CC-BY-4.0 and CC-BY-NC-3.0",
                "country proxy receipt explicitly disables redistribution",
                "UNSD and NGA GENC records are NOASSERTION",
                "CRU scPDSI requires ODbL compliance and attribution",
            ],
        },
        "environment": {
            **binding(root, "environment/python-requirements.txt"),
            "python_version_used_to_generate": sys.version.split()[0],
        },
        "claim_gates": {
            "real_outcome_access_authorized": False, "production_fit_authorized": False,
            "causal_response_authorized": False, "winner_loser_claims_authorized": False,
            "damage_calculation_authorized": False, "scc_authorized": False,
            "give_integration_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh portability manifest output required")
    root = args.root.resolve()
    result = build(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "direct_artifacts": len(result["direct_artifacts"]),
        "period_components": len(result["period_components"]),
        "aggregate_fallbacks": len(result["aggregate_fallback_group"]["aggregate_files"]),
        "outcome_values_read": result["content_access"]["outcome_values_read"],
    }, indent=2))


if __name__ == "__main__":
    main()
