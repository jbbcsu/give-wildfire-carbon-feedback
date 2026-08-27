#!/usr/bin/env python3
"""Fail closed on the bounded MRI SSP1-2.6/SSP5-8.5 expansion bundle."""
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
    ("ssp126", "pr"),
    ("ssp126", "tas"),
    ("ssp585", "pr"),
    ("ssp585", "tas"),
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
        require(key not in result, "MRI scenario expansion duplicates a cell")
        result[key] = row
    require(set(result) == EXPECTED_CELLS, "MRI scenario expansion lacks the exact new cell set")
    return result


def validate(path: Path) -> dict[str, object]:
    record = tomllib.loads(path.read_text(encoding="utf-8"))
    require(record.get("schema_version") == 1, "MRI scenario expansion schema changed")
    require(record.get("esm") == "mri-esm2-0" and record.get("member") == "r1i1p1f1", "MRI realization changed")
    require(record.get("rights") == "CC0 1.0" and record.get("dataset_version") == "20210512", "MRI rights/version changed")
    require(set(record.get("complete_bounded_scenarios", [])) == {"historical", "ssp126", "ssp370", "ssp585"}, "MRI scenario coverage changed")
    cells = index_cells(record.get("cell", []))
    raw_bytes = 0
    for key, cell in cells.items():
        raw = project_path(str(cell["raw_path"]))
        require(raw.is_file(), f"raw MRI cell is missing: {raw}")
        require(raw.name == str(cell["file_name"]), f"raw MRI file name differs: {raw.name}")
        require(raw.stat().st_size == int(cell["bytes"]), f"raw MRI bytes differ: {raw.name}")
        require(sha512(raw) == str(cell["sha512"]), f"raw MRI SHA-512 differs: {raw.name}")
        require(str(cell.get("dataset_id", "")) and str(cell.get("file_id", "")), f"{key} API identities are missing")
        raw_bytes += raw.stat().st_size

        audit = json.loads(project_path(str(cell["content_audit"])).read_text(encoding="utf-8"))
        require(audit.get("result") == "passed", f"{key} content audit did not pass")
        require(audit.get("file_name") == raw.name, f"{key} content audit file changed")
        require(int(audit.get("bytes", -1)) == raw.stat().st_size, f"{key} content bytes changed")
        require(audit.get("sha512") == cell["sha512"], f"{key} content checksum changed")

        boundary = json.loads(project_path(str(cell["boundary_audit"])).read_text(encoding="utf-8"))
        require(boundary.get("result") == "passed" and boundary.get("variable") == key[1], f"{key} boundary did not pass")

        if key[1] == "tas":
            gmst = pd.read_parquet(project_path(str(cell["gmst_output"])))
            require(gmst["year"].tolist() == list(range(2015, 2021)), f"{key} GMST years changed")
            require(set(gmst["esm_id"].astype(str)) == {"mri-esm2-0"}, f"{key} GMST ESM changed")
            require(set(gmst["member_id"].astype(str)) == {"r1i1p1f1"}, f"{key} GMST member changed")
            require(set(gmst["scenario"].astype(str)) == {key[0]}, f"{key} GMST scenario changed")
            require(set(gmst["gmst_source_id"].astype(str)) == {str(cell["gmst_source_id"])}, f"{key} GMST source changed")
            require(
                np.allclose(gmst["gmst_value_k"].to_numpy(float), np.asarray(cell["gmst_values_k"], dtype=float), rtol=0, atol=1e-12),
                f"{key} GMST values changed",
            )

    for scenario in ("ssp126", "ssp585"):
        audit = json.loads(project_path(f"data/interim/isimip3b_mri_{scenario}_smoke/reconciliation_audit.json").read_text(encoding="utf-8"))
        require(audit.get("status") == "passed", f"{scenario} feature reconciliation did not pass")
        require(int(audit.get("n_crop_year_grid_rows", -1)) == 2744, f"{scenario} feature row count changed")
        require(all(float(value) == 0 for value in audit["max_absolute_differences"].values()), f"{scenario} feature reconciliation changed")

    holdout = json.loads(project_path(str(record["whole_scenario_holdout"]["audit"])).read_text(encoding="utf-8"))
    require(holdout.get("result") == "passed", "MRI scenario holdout did not pass")
    require(holdout.get("esm_id") == "mri-esm2-0" and holdout.get("member_id") == "r1i1p1f1", "MRI holdout realization changed")
    config_path = project_path(str(record["whole_scenario_holdout"]["config"]))
    require(holdout.get("config_sha256") == hashlib.sha256(config_path.read_bytes()).hexdigest(), "MRI holdout config hash changed")
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    limitations = config.get("limitations", {})
    for gate in ("complete_esm_matrix", "paired_baseline_pulse_paths", "support_flags", "damage_or_scc_authorized"):
        require(limitations.get(gate) is False, f"MRI config unexpectedly opens {gate}")
    implementation = holdout.get("implementation", {})
    implementation_path = project_path(str(implementation.get("path", "")))
    require(implementation.get("sha256") == hashlib.sha256(implementation_path.read_bytes()).hexdigest(), "MRI holdout implementation hash changed")
    registered = record["whole_scenario_holdout"]
    for field in ("training_rows", "holdout_rows", "gmst_model_better_than_cell_mean_count"):
        require(int(holdout[field]) == int(registered[field]), f"MRI holdout {field} changed")
    for field in ("median_rmse_ratio_to_cell_mean", "maximum_rmse_ratio_to_cell_mean"):
        require(abs(float(holdout[field]) - float(registered[field])) <= 1e-12, f"MRI holdout {field} changed")

    return {
        "result": "passed",
        "new_complete_files": len(cells),
        "new_complete_file_bytes": raw_bytes,
        "same_realization_gmst_cells": 2,
        "feature_reconciliation_cells": 2,
        "whole_scenario_holdouts": int(holdout["holdout_rows"]),
        "production_emulator_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.record.resolve()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
