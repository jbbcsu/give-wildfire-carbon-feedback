#!/usr/bin/env python3
"""Fail closed on the bounded IPSL historical/three-SSP evidence bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CELLS = {
    ("historical", "pr"), ("historical", "tas"),
    ("ssp126", "pr"), ("ssp126", "tas"),
    ("ssp585", "pr"), ("ssp585", "tas"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts, "provenance path must be project-relative")
    result = (ROOT / path).resolve()
    result.relative_to(ROOT.resolve())
    return result


def index_cells(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("scenario")), str(row.get("variable")))
        require(key not in result, "IPSL scenario matrix duplicates a cell")
        result[key] = row
    require(set(result) == EXPECTED_CELLS, "IPSL scenario matrix lacks the exact new cell set")
    return result


def validate(path: Path, raw_root: Path) -> dict[str, object]:
    record = tomllib.loads(path.read_text(encoding="utf-8"))
    require(record.get("schema_version") == 1, "IPSL scenario matrix schema changed")
    require(record.get("esm") == "IPSL-CM6A-LR" and record.get("member") == "r1i1p1f1", "IPSL realization changed")
    require(record.get("rights") == "CC0 1.0" and record.get("dataset_version") == "20210512", "IPSL rights/version changed")
    require(set(record.get("scenarios", [])) == {"historical", "ssp126", "ssp370", "ssp585"}, "IPSL scenarios changed")
    cells = index_cells(record.get("cell", []))
    raw_bytes = 0
    for key, cell in cells.items():
        raw = raw_root / str(cell["file_name"])
        require(raw.is_file(), f"raw IPSL cell is missing: {raw}")
        require(raw.stat().st_size == int(cell["bytes"]), f"raw IPSL bytes differ: {raw.name}")
        require(sha512(raw) == str(cell["sha512"]), f"raw IPSL SHA-512 differs: {raw.name}")
        raw_bytes += raw.stat().st_size
        audit = json.loads(project_path(str(cell["content_audit"])).read_text(encoding="utf-8"))
        require(audit.get("result") == "passed", f"{key} content audit did not pass")
        require(audit.get("file_name") == raw.name, f"{key} content audit file changed")
        require(int(audit.get("bytes", -1)) == raw.stat().st_size, f"{key} content bytes changed")
        require(audit.get("sha512") == cell["sha512"], f"{key} content checksum changed")
        if key[0] != "historical":
            boundary = json.loads(project_path(str(cell["boundary_audit"])).read_text(encoding="utf-8"))
            require(boundary.get("result") == "passed" and boundary.get("variable") == key[1], f"{key} boundary did not pass")
        if key[1] == "tas":
            gmst = pd.read_parquet(project_path(str(cell["gmst_output"])))
            expected_years = list(range(2011, 2015)) if key[0] == "historical" else list(range(2015, 2021))
            require(gmst["year"].tolist() == expected_years, f"{key} GMST years changed")
            require(set(gmst["esm_id"].astype(str)) == {"IPSL-CM6A-LR"}, f"{key} GMST ESM changed")
            require(set(gmst["member_id"].astype(str)) == {"r1i1p1f1"}, f"{key} GMST member changed")
            require(set(gmst["scenario"].astype(str)) == {key[0]}, f"{key} GMST scenario changed")
            require(set(gmst["gmst_source_id"].astype(str)) == {str(cell["gmst_source_id"])}, f"{key} GMST source changed")
            require(
                np.allclose(gmst["gmst_value_k"].to_numpy(float), np.asarray(cell["gmst_values_k"], dtype=float), rtol=0, atol=1e-12),
                f"{key} GMST values changed",
            )

    for name, rows in (("historical", 2058), ("ssp126", 2744), ("ssp585", 2744)):
        audit = json.loads(project_path(f"data/interim/isimip3b_ipsl_{name}_smoke/reconciliation_audit.json").read_text(encoding="utf-8"))
        require(audit.get("status") == "passed", f"{name} feature reconciliation did not pass")
        require(int(audit.get("n_crop_year_grid_rows", -1)) == rows, f"{name} feature row count changed")
        require(all(float(value) == 0 for value in audit["max_absolute_differences"].values()), f"{name} feature reconciliation changed")

    holdout = json.loads(project_path(str(record["whole_scenario_holdout"]["audit"])).read_text(encoding="utf-8"))
    require(holdout.get("result") == "passed" and holdout.get("whole_scenario_holdout") is True, "IPSL scenario holdout did not pass")
    require(holdout.get("esm_id") == "IPSL-CM6A-LR" and holdout.get("member_id") == "r1i1p1f1", "IPSL holdout realization changed")
    for gate in ("whole_esm_holdout_in_this_product", "paired_baseline_pulse_paths", "support_flags", "damage_or_scc_authorized"):
        require(holdout.get(gate) is False, f"IPSL holdout unexpectedly opens {gate}")
    implementation = holdout.get("implementation", {})
    implementation_path = project_path(str(implementation.get("path", "")))
    require(implementation_path.is_file(), "IPSL holdout implementation is missing")
    sha256_digest = hashlib.sha256(implementation_path.read_bytes()).hexdigest()
    require(implementation.get("sha256") == sha256_digest, "IPSL holdout implementation hash changed")
    dependencies = implementation.get("dependencies", [])
    require(len(dependencies) == 2, "IPSL holdout dependency receipts are incomplete")
    for dependency in dependencies:
        dependency_path = project_path(str(dependency.get("path", "")))
        actual = hashlib.sha256(dependency_path.read_bytes()).hexdigest()
        require(dependency.get("sha256") == actual, f"IPSL holdout dependency hash changed: {dependency_path.name}")
    registered = record["whole_scenario_holdout"]
    for field in ("training_rows", "holdout_rows", "gmst_model_better_than_cell_mean_count"):
        require(int(holdout[field]) == int(registered[field]), f"IPSL holdout {field} changed")
    for field in ("median_rmse_ratio_to_cell_mean", "maximum_rmse_ratio_to_cell_mean"):
        require(abs(float(holdout[field]) - float(registered[field])) <= 1e-12, f"IPSL holdout {field} changed")
    return {
        "result": "passed",
        "new_complete_files": len(cells),
        "new_complete_file_bytes": raw_bytes,
        "same_realization_gmst_cells": 3,
        "feature_reconciliation_cells": 3,
        "whole_scenario_holdouts": int(holdout["holdout_rows"]),
        "production_emulator_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    parser.add_argument("--raw-root", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.record.resolve(), args.raw_root.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
