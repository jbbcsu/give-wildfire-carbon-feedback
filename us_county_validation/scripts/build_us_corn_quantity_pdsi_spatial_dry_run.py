#!/usr/bin/env python3
"""Build a hash-bound metadata-only manifest; real execution fails closed."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
import zipfile
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import shapefile


PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT / "us_county_validation/us_corn_quantity_pdsi_spatial_run_adapter_v1.toml"
FALSE_GATES = (
    "real_outcome_read_authorized", "real_response_fit_authorized",
    "coefficient_output_authorized", "national_claim_authorized",
    "causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized",
)


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("adapter paths must be project-relative")
    resolved = (PROJECT / path).resolve()
    resolved.relative_to(PROJECT.resolve())
    return resolved


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if config.get("adapter_id") != "us_corn_quantity_pdsi_spatial_run_adapter_v1":
        raise ValueError("wrong adapter contract")
    if config.get("analysis_role") != "metadata_only_dry_run_manifest":
        raise ValueError("adapter role changed")
    if config.get("dry_run_authorized") is not True:
        raise ValueError("dry run is not authorized")
    for gate in FALSE_GATES:
        if config.get(gate) is not False:
            raise ValueError(f"adapter unexpectedly opens {gate}")
    auth = config["authorization"]
    if auth.get("real_run_enabled") is not False:
        raise ValueError("canonical adapter must keep real run disabled")
    for key in (
        "authorization_artifact_required", "authorization_must_bind_protocol_and_input_hashes",
        "gate_must_precede_outcome_column_open", "gate_must_precede_fit_import_or_invocation",
    ):
        if auth.get(key) is not True:
            raise ValueError(f"authorization requirement {key} changed")
    return config


def require_real_run_authorization(config: dict[str, Any], authorization_path: Path | None) -> dict[str, Any]:
    """First operation for any future real branch; canonical config always denies."""
    auth = config["authorization"]
    if auth.get("real_run_enabled") is not True:
        raise PermissionError("real run is disabled by the hash-bound adapter contract")
    if not config.get("real_outcome_read_authorized") or not config.get("real_response_fit_authorized"):
        raise PermissionError("outcome read and response fit require explicit contract authorization")
    if authorization_path is None:
        raise PermissionError("an explicit authorization artifact is required")
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    if authorization.get("status") != auth["required_status"] or authorization.get("scope") != auth["required_scope"]:
        raise PermissionError("authorization status or scope is invalid")
    expected = {
        "protocol_sha256": config["protocol"]["sha256"],
        "direct_sha256": config["direct"]["sha256"],
        "pdsi_sha256": config["pdsi"]["sha256"],
        "coordinate_archive_sha256": config["coordinates"]["archive_sha256"],
    }
    if authorization.get("bound_hashes") != expected:
        raise PermissionError("authorization does not bind the exact run inputs")
    return authorization


def _open_real_outcome_columns(_: dict[str, Any]) -> None:
    raise NotImplementedError("real outcome reader is intentionally absent from this dry-run adapter")


def _invoke_real_fit(_: dict[str, Any]) -> None:
    raise NotImplementedError("real fit implementation is intentionally absent from this dry-run adapter")


def execute_real_run(config: dict[str, Any], authorization_path: Path | None) -> None:
    require_real_run_authorization(config, authorization_path)
    _open_real_outcome_columns(config)
    _invoke_real_fit(config)


def parquet_metadata(section: dict[str, Any]) -> dict[str, Any]:
    path = project_path(section["path"])
    actual_hash = digest(path)
    if actual_hash != section["sha256"]:
        raise ValueError(f"input hash changed: {section['path']}")
    parquet = pq.ParquetFile(path)
    names = parquet.schema_arrow.names
    missing = sorted(set(section["required_schema_columns"]) - set(names))
    if missing:
        raise ValueError(f"parquet schema lacks {missing}")
    outcome = "yield_bu_acre"
    if outcome in section["future_feature_columns"]:
        raise ValueError("future feature projection includes the outcome column")
    return {
        "path": section["path"], "sha256": actual_hash,
        "size_bytes": int(path.stat().st_size),
        "rows_from_footer": int(parquet.metadata.num_rows),
        "row_groups": int(parquet.metadata.num_row_groups),
        "schema_columns": names,
        "future_feature_columns": list(section["future_feature_columns"]),
        "outcome_column_present_in_schema_only": outcome in names,
        "outcome_column_opened": False,
        "data_pages_read": False,
    }


def coordinate_metadata(section: dict[str, Any]) -> dict[str, Any]:
    manifest_path, archive_path = project_path(section["source_manifest"]), project_path(section["archive"])
    if digest(manifest_path) != section["source_manifest_sha256"]:
        raise ValueError("coordinate source manifest hash changed")
    if digest(archive_path) != section["archive_sha256"] or digest(archive_path, "sha512") != section["archive_sha512"]:
        raise ValueError("coordinate archive hash changed")
    lines = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    matches = [line for line in lines if line.get("local_path") == section["archive"]]
    if len(matches) != 1 or matches[0].get("source_url") != section["source_url"]:
        raise ValueError("coordinate provenance manifest does not uniquely bind the Census source")
    if matches[0].get("sha512") != section["archive_sha512"] or matches[0].get("archive_validation") != "zip_integrity_passed":
        raise ValueError("coordinate archive provenance validation changed")
    components = {}
    for key in ("dbf", "shp", "shx", "prj", "cpg"):
        path = project_path(section[key])
        components[key] = {"path": section[key], "sha256": digest(path), "size_bytes": int(path.stat().st_size)}
    reader = shapefile.Reader(dbf=str(project_path(section["dbf"])))
    fields = {field[0]: {"type": field[1], "length": field[2], "decimals": field[3]} for field in reader.fields[1:]}
    if set(section["required_dbf_fields"]) - set(fields):
        raise ValueError("TIGER DBF schema lacks required coordinate fields")
    if len(reader) != int(section["required_record_count"]):
        raise ValueError("TIGER DBF record count changed")
    prj = project_path(section["prj"]).read_text(encoding="utf-8")
    if any(token not in prj for token in section["required_crs_tokens"]):
        raise ValueError("TIGER CRS metadata changed")
    with zipfile.ZipFile(archive_path) as archive:
        archive_names = sorted(archive.namelist())
    return {
        "source": "Census TIGER/Line 2019 county",
        "source_url": section["source_url"],
        "manifest": {"path": section["source_manifest"], "sha256": section["source_manifest_sha256"]},
        "archive": {"path": section["archive"], "sha256": section["archive_sha256"], "sha512": section["archive_sha512"], "members": archive_names},
        "components": components,
        "dbf_record_count_from_header": int(len(reader)),
        "dbf_fields_from_header": fields,
        "coordinate_fields": ["INTPTLAT", "INTPTLON"],
        "crs_wkt": prj.strip(),
        "coordinate_records_read": 0,
        "geometry_records_read": 0,
    }


def build_manifest(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    protocol_path = project_path(config["protocol"]["path"])
    validation_path = project_path(config["protocol"]["validation_receipt"])
    readiness_path = project_path(config["readiness"]["receipt"])
    for path, expected in (
        (protocol_path, config["protocol"]["sha256"]),
        (validation_path, config["protocol"]["validation_sha256"]),
        (readiness_path, config["readiness"]["sha256"]),
    ):
        if digest(path) != expected:
            raise ValueError(f"bound receipt/protocol hash changed: {path}")
    protocol_validation = json.loads(validation_path.read_text(encoding="utf-8"))
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    if protocol_validation.get("status") != "validated_synthetic_only_protocol" or protocol_validation.get("real_outcome_rows_read") != 0 or protocol_validation.get("real_response_fits") != 0:
        raise ValueError("spatial protocol validation receipt is not eligible")
    inputs = readiness.get("inputs", {})
    if inputs.get("outcome_columns_read") != [] or inputs.get("exact_practice_pairs_and_exposures") is not True or inputs.get("exact_direct_pdsi_keys") is not True:
        raise ValueError("outcome-blind readiness receipt does not prove practice separation")
    for family in config["readiness"]["required_corn_families"]:
        item = next((x for x in readiness["family_readiness"] if x["crop"] == "corn_grain" and x["family"] == family), None)
        if not item or item.get("both_practices_pass") is not True:
            raise ValueError(f"readiness receipt does not pass corn {family}")
    direct = parquet_metadata(config["direct"])
    pdsi = parquet_metadata(config["pdsi"])
    coordinates = coordinate_metadata(config["coordinates"])
    cells = [
        {"crop": "corn_grain", "practice": practice, "family": family, "status": "blocked_pending_explicit_real_run_authorization"}
        for practice in config["readiness"]["required_practices"]
        for family in config["readiness"]["required_corn_families"]
    ]
    return {
        "schema": "us_corn_quantity_pdsi_spatial_dry_run_manifest_v1",
        "status": "dry_run_ready_but_real_run_unauthorized",
        "adapter_contract": {"path": str(config_path.relative_to(PROJECT)), "sha256": digest(config_path)},
        "adapter_implementation": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
        "protocol": {"path": config["protocol"]["path"], "sha256": config["protocol"]["sha256"]},
        "protocol_validation": {"path": config["protocol"]["validation_receipt"], "sha256": config["protocol"]["validation_sha256"]},
        "readiness_evidence": {"path": config["readiness"]["receipt"], "sha256": config["readiness"]["sha256"], "exact_practice_pairs_and_exposures": True, "paired_exposure_rows": inputs["paired_exposure_rows"], "evidence_reused_without_row_read": True},
        "inputs": {"direct": direct, "pdsi": pdsi, "coordinates": coordinates},
        "planned_run_cells": cells,
        "authorization": {"real_run_enabled": False, "authorization_artifact_required": True, "gate_precedes_outcome_open": True, "gate_precedes_fit_import_or_invocation": True},
        "outcome_columns_opened": [], "data_pages_read": 0, "coordinate_records_read": 0,
        "real_response_fits": 0, "coefficients_written": 0,
        **{gate: False for gate in FALSE_GATES},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--mode", choices=["dry-run", "real-run"], default="dry-run")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = load_config(config_path)
    if args.mode == "real-run":
        execute_real_run(config, args.authorization)
        return
    if args.authorization is not None:
        raise ValueError("dry run must not accept or inspect an authorization artifact")
    manifest = build_manifest(config_path)
    output = args.out.resolve() if args.out else project_path(config["output"]["dry_run_manifest"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "output": str(output), "planned_run_cells": len(manifest["planned_run_cells"])}, indent=2))


if __name__ == "__main__":
    main()
