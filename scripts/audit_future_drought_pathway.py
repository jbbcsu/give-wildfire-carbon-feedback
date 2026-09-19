#!/usr/bin/env python3
"""Audit whether resident ISIMIP3b inputs can support future Hargreaves SPEI.

This is a metadata/readiness audit.  It deliberately does not open or hydrate
NetCDF data, estimate a drought response, or authorize damage/SCC use.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/provenance/isimip3b_daily_catalog_selection.csv"
RAW_ROOT = ROOT / "data/raw/isimip3b"
VARIABLES = ("pr", "tas", "tasmin", "tasmax")
SCENARIOS = ("historical", "ssp126", "ssp370", "ssp585")
LATE_PERIODS = ("2041_2050", "2091_2100")
FILE_RE = re.compile(
    r"^(?P<forcing>.+?)_(?P<member>r\di\dp\df\d)_w5e5_"
    r"(?P<scenario>historical|ssp\d+)_(?P<variable>pr|tas|tasmin|tasmax)_"
    r"global_daily_(?P<start>\d{4})_(?P<end>\d{4})\.nc$"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_catalog(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    required = {"forcing", "member", "scenario", "variable", "dataset_id", "rights", "public", "restricted"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("ISIMIP3b catalog schema changed")
    keys = [(r["forcing"], r["member"], r["scenario"], r["variable"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate dataset key in catalog")
    return rows


def scan_resident(root: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    rejected: list[str] = []
    for path in sorted(root.rglob("*.nc")):
        display_path = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path.relative_to(root)
        match = FILE_RE.match(path.name)
        if not match:
            rejected.append(str(display_path))
            continue
        stat = path.stat()
        record = match.groupdict()
        record.update(
            period=f"{record.pop('start')}_{record.pop('end')}",
            path=str(display_path),
            logical_bytes=stat.st_size,
            allocated_bytes=stat.st_blocks * 512,
        )
        records.append(record)
    return records, rejected


def build_audit(catalog_path: Path = CATALOG, raw_root: Path = RAW_ROOT) -> dict:
    catalog = read_catalog(catalog_path)
    resident, rejected = scan_resident(raw_root)
    forcings = sorted({r["forcing"] for r in catalog})
    members = sorted({r["member"] for r in catalog})
    expected = {
        (f, r["member"], s, v)
        for f in forcings
        for r in catalog
        if r["forcing"] == f
        for s in SCENARIOS
        for v in VARIABLES
    }
    catalog_keys = {(r["forcing"], r["member"], r["scenario"], r["variable"]) for r in catalog}
    if catalog_keys != expected:
        raise ValueError("catalog is not the registered five-ESM/four-scenario/four-variable matrix")
    catalog_public = all(
        r["public"].lower() == "true"
        and r["restricted"].lower() == "false"
        and r["rights"] == "CC0 1.0"
        for r in catalog
    )
    counts = Counter((r["scenario"], r["variable"]) for r in resident)
    late = [r for r in resident if r["scenario"] != "historical" and r["period"] in LATE_PERIODS]
    late_counts = Counter(r["variable"] for r in late)
    late_required = len(forcings) * 3 * len(LATE_PERIODS)
    gfdl_boundary = [
        r for r in resident
        if r["forcing"] == "gfdl-esm4"
        and ((r["scenario"] == "historical" and r["period"] == "2011_2014")
             or (r["scenario"] in {"ssp126", "ssp370", "ssp585"} and r["period"] == "2015_2020"))
    ]
    boundary_matrix = Counter((r["scenario"], r["variable"]) for r in gfdl_boundary)
    boundary_complete = all(
        boundary_matrix[(scenario, variable)] == 1
        for scenario in SCENARIOS
        for variable in VARIABLES
    )
    disk = shutil.disk_usage(raw_root)
    return {
        "schema": "future_drought_pathway_readiness_v1",
        "status": "metadata_audit_passed_primary_late_century_inputs_incomplete",
        "role": "readiness_only_not_content_validation_projection_response_damage_or_scc",
        "catalog": {
            "path": str(catalog_path.relative_to(ROOT)),
            "sha256": sha256(catalog_path),
            "rows": len(catalog),
            "forcings": forcings,
            "members": members,
            "scenarios": list(SCENARIOS),
            "variables": list(VARIABLES),
            "complete_factorial": True,
            "all_public_unrestricted_cc0": catalog_public,
        },
        "resident": {
            "root": str(raw_root.relative_to(ROOT)),
            "netcdf_files": len(resident),
            "logical_bytes": sum(r["logical_bytes"] for r in resident),
            "allocated_bytes": sum(r["allocated_bytes"] for r in resident),
            "unparsed_netcdf_files": rejected,
            "counts_by_scenario_variable": [
                {"scenario": s, "variable": v, "files": counts[(s, v)]}
                for s in SCENARIOS for v in VARIABLES
            ],
        },
        "late_century_hargreaves_primary": {
            "periods": list(LATE_PERIODS),
            "required_files_per_variable": late_required,
            "resident_files_by_variable": {v: late_counts[v] for v in VARIABLES},
            "complete_pr": late_counts["pr"] == late_required,
            "complete_tas": late_counts["tas"] == late_required,
            "complete_tasmin": late_counts["tasmin"] == late_required,
            "complete_tasmax": late_counts["tasmax"] == late_required,
            "primary_executable_now": all(late_counts[v] == late_required for v in ("pr", "tasmin", "tasmax")),
            "note": "Hargreaves PET requires tasmin and tasmax; tas is retained for common temperature controls and cross-checks.",
        },
        "resident_gfdl_boundary_pilot": {
            "historical_period": "2011_2014",
            "future_period": "2015_2020",
            "scenarios": ["ssp126", "ssp370", "ssp585"],
            "variables": list(VARIABLES),
            "files": len(gfdl_boundary),
            "complete": boundary_complete,
            "role": "eligible_for_bounded_transform_engineering_only_after_protocol_and_source-hash_validation",
        },
        "resource_snapshot": {
            "filesystem_free_bytes": disk.free,
            "fixed_free_space_floor_bytes": 130 * 1024**3,
            "bulk_acquisition_safe_now": disk.free > 132 * 1024**3,
        },
        "gates": {
            "raw_content_validated_by_this_audit": False,
            "future_drought_projection_complete": False,
            "drought_response_promoted": False,
            "causal_interpretation_authorized": False,
            "damage_authorized": False,
            "scc_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_audit()
    result["implementation"] = {
        "path": str(Path(__file__).resolve().relative_to(ROOT)),
        "sha256": sha256(Path(__file__).resolve()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "resident_files": result["resident"]["netcdf_files"],
        "late_century": result["late_century_hargreaves_primary"],
        "gfdl_boundary_complete": result["resident_gfdl_boundary_pilot"]["complete"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
