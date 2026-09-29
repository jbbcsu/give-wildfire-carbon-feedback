#!/usr/bin/env python3
"""Independent metadata-only validation of the corn spatial dry-run manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import pyarrow.parquet as pq
import shapefile


PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / "us_county_validation/us_corn_quantity_pdsi_spatial_run_adapter_v1.toml"
MANIFEST = PROJECT / "data/provenance/us_corn_quantity_pdsi_spatial_dry_run_manifest_20260929.json"
OUTPUT = PROJECT / "data/provenance/us_corn_quantity_pdsi_spatial_dry_run_manifest_independent_validation_20260929.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("status") != "dry_run_ready_but_real_run_unauthorized":
        raise AssertionError("dry-run status changed")
    if manifest["adapter_contract"]["sha256"] != digest(CONFIG):
        raise AssertionError("adapter contract identity changed")
    implementation_path = PROJECT / manifest["adapter_implementation"]["path"]
    if manifest["adapter_implementation"]["sha256"] != digest(implementation_path):
        raise AssertionError("adapter implementation identity changed")
    for key in (
        "real_outcome_read_authorized", "real_response_fit_authorized",
        "coefficient_output_authorized", "national_claim_authorized",
        "causal_claim_authorized", "damage_claim_authorized", "scc_claim_authorized",
    ):
        if manifest.get(key) is not False:
            raise AssertionError(f"manifest unexpectedly opens {key}")
    if manifest.get("outcome_columns_opened") != [] or manifest.get("data_pages_read") != 0 or manifest.get("real_response_fits") != 0:
        raise AssertionError("manifest is not metadata-only")
    if len(manifest["planned_run_cells"]) != 4 or any(
        cell["status"] != "blocked_pending_explicit_real_run_authorization"
        for cell in manifest["planned_run_cells"]
    ):
        raise AssertionError("planned cells are not exactly four blocked cells")
    checks = 2
    for section, path_key, hash_key in (
        (config["protocol"], "path", "sha256"),
        (config["protocol"], "validation_receipt", "validation_sha256"),
        (config["readiness"], "receipt", "sha256"),
    ):
        if digest(PROJECT / section[path_key]) != section[hash_key]:
            raise AssertionError(f"bound evidence changed: {section[path_key]}")
        checks += 1
    for name in ("direct", "pdsi"):
        section = config[name]
        path = PROJECT / section["path"]
        parquet = pq.ParquetFile(path)
        reported = manifest["inputs"][name]
        if digest(path) != reported["sha256"] or parquet.metadata.num_rows != reported["rows_from_footer"]:
            raise AssertionError(f"{name} footer/hash changed")
        if parquet.schema_arrow.names != reported["schema_columns"]:
            raise AssertionError(f"{name} schema changed")
        if "yield_bu_acre" in reported["future_feature_columns"] or reported["outcome_column_opened"] is not False:
            raise AssertionError(f"{name} projection opens outcome")
        checks += 4
    coordinate = config["coordinates"]
    for key, hash_key in (
        ("source_manifest", "source_manifest_sha256"), ("archive", "archive_sha256")
    ):
        if digest(PROJECT / coordinate[key]) != coordinate[hash_key]:
            raise AssertionError(f"coordinate {key} hash changed")
        checks += 1
    for key in ("dbf", "shp", "shx", "prj", "cpg"):
        reported = manifest["inputs"]["coordinates"]["components"][key]
        if digest(PROJECT / coordinate[key]) != reported["sha256"]:
            raise AssertionError(f"coordinate component {key} changed")
        checks += 1
    reader = shapefile.Reader(dbf=str(PROJECT / coordinate["dbf"]))
    fields = [field[0] for field in reader.fields[1:]]
    if len(reader) != manifest["inputs"]["coordinates"]["dbf_record_count_from_header"]:
        raise AssertionError("coordinate record-count metadata changed")
    if any(field not in fields for field in coordinate["required_dbf_fields"]):
        raise AssertionError("coordinate schema changed")
    if manifest["inputs"]["coordinates"]["coordinate_records_read"] != 0:
        raise AssertionError("coordinate values were read")
    checks += 3
    if manifest["readiness_evidence"]["exact_practice_pairs_and_exposures"] is not True or manifest["readiness_evidence"]["evidence_reused_without_row_read"] is not True:
        raise AssertionError("practice separation evidence changed")
    checks += 2
    result = {
        "schema": "us_corn_quantity_pdsi_spatial_dry_run_independent_validation_v1",
        "status": "validated_independent_metadata_only_dry_run",
        "manifest": {"path": str(args.manifest.resolve().relative_to(PROJECT)), "sha256": digest(args.manifest)},
        "config": {"path": str(CONFIG.relative_to(PROJECT)), "sha256": digest(CONFIG)},
        "validator": {"path": str(Path(__file__).resolve().relative_to(PROJECT)), "sha256": digest(Path(__file__))},
        "checks": checks,
        "outcome_columns_opened": [], "data_pages_read": 0,
        "coordinate_records_read": 0, "real_response_fits": 0,
        "real_outcome_read_authorized": False, "real_response_fit_authorized": False,
        "national_claim_authorized": False, "causal_claim_authorized": False,
        "damage_claim_authorized": False, "scc_claim_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
