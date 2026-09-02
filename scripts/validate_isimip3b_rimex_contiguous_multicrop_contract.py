#!/usr/bin/env python3
"""Validate a preregistered contiguous GFDL crop × calendar-regime contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib

import numpy as np
import xarray as xr


SCHEMA = "isimip3b_rimex_contiguous_multicrop_regime_contract_v1"
CROPS = ["mai", "soy", "ri1", "ri2", "swh", "wwh"]
REGIMES = ["noirr", "firr"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(config_path: Path, root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    require(config.get("schema") == SCHEMA, "contract schema changed")
    require((config.get("esm"), config.get("member")) ==
            ("GFDL-ESM4", "r1i1p1f1"), "realization identity changed")
    require(config.get("scenario") in {"ssp126", "ssp370", "ssp585"}, "scenario is outside the frozen matrix")
    require((config.get("source_year_start"), config.get("source_year_end")) == (2031, 2060), "source years changed")
    require((config.get("feature_year_start"), config.get("feature_year_end")) == (2032, 2059), "feature years changed")
    require((config.get("centered_window_years"), config.get("center_year_start"), config.get("center_year_end")) ==
            (21, 2042, 2049), "centered window changed")
    require((config.get("lat_start"), config.get("lat_stop")) == (100, 102), "bounded latitude rows changed")
    for gate in ("response_estimation_authorized", "whole_esm_emulator_promoted", "whole_scenario_emulator_promoted", "irrigation_treatment_effect_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    expected_ids = [f"{crop}_{regime}" for crop in CROPS for regime in REGIMES]
    require(config.get("required_cells") == expected_ids, "ordered crop × regime declaration changed")
    cells = config.get("cells", [])
    require([cell.get("id") for cell in cells] == expected_ids, "cell records do not exactly match required_cells")
    calendar_records = []
    for cell in cells:
        require(cell.get("id") == f"{cell.get('crop')}_{cell.get('irrigation')}", "cell identity is inconsistent")
        path = root / str(cell["calendar"])
        observed_hash = sha256(path)
        require(observed_hash == cell.get("calendar_sha256"), f"calendar hash changed: {cell['id']}")
        with xr.open_dataset(path, engine="h5netcdf", decode_timedelta=False) as dataset:
            bounded = dataset.isel(lat=slice(int(config["lat_start"]), int(config["lat_stop"])))
            valid = np.isfinite(bounded.planting_day.values) & np.isfinite(bounded.maturity_day.values)
            valid &= (bounded.planting_day.values >= 1) & (bounded.maturity_day.values >= 1)
            observed_cells = int(valid.sum())
        require(observed_cells == cell.get("valid_calendar_cells"), f"calendar support changed: {cell['id']}")
        calendar_records.append({
            "id": cell["id"], "path": cell["calendar"], "sha256": observed_hash,
            "valid_calendar_cells": observed_cells,
            "expected_season_rows": observed_cells * 28,
            "expected_stage_rows": observed_cells * 28 * 3,
            "expected_centered_season_rows": observed_cells * 8,
            "expected_centered_stage_rows": observed_cells * 8 * 3,
        })

    sources = []
    for source in config.get("source_receipts", []):
        path = root / str(source["path"])
        observed = sha256(path)
        require(observed == source.get("sha256"), "source receipt hash changed")
        receipt = tomllib.loads(path.read_text(encoding="utf-8"))
        require(
            (receipt.get("esm"), receipt.get("member"), receipt.get("scenario")) ==
            (config["esm"], config["member"], config["scenario"]),
            "source receipt realization differs from contract",
        )
        require(
            receipt.get("daily_support_years") == [config["source_year_start"], config["source_year_end"]],
            "source receipt years differ from contract",
        )
        require(receipt.get("all_six_catalogue_files_byte_and_sha512_validated") is True,
                "source receipt lacks complete byte/checksum gates")
        require(receipt.get("all_six_files_full_content_validated") is True,
                "source receipt lacks complete content gates")
        file_records = receipt.get("files")
        if config["scenario"] != "ssp126":
            require(isinstance(file_records, list) and len(file_records) == 6,
                    "expanded scenario receipt must enumerate six validated files")
            expected_file_cells = {
                (variable, start, start + 9)
                for variable in ("pr", "tas") for start in (2031, 2041, 2051)
            }
            require({(item.get("variable"), *item.get("years", [])) for item in file_records} == expected_file_cells,
                    "expanded scenario receipt file matrix is incomplete")
            for item in file_records:
                audit_path = root / str(item["content_audit"])
                require(sha256(audit_path) == item.get("content_audit_sha256"),
                        "source content-audit hash changed")
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                require(audit.get("result") == "passed" and audit.get("variable") == item["variable"],
                        "source content audit did not pass")
                require(audit.get("file_name") == item["file_name"], "source content-audit filename changed")
                require(audit.get("bytes") == item["bytes"] and audit.get("sha512") == item["sha512"],
                        "source content-audit identity changed")
        sources.append({"path": source["path"], "sha256": observed})
    require(len(sources) == 1, "contract must bind exactly one complete contiguous source receipt")
    validation = config.get("validation", {})
    expected_feature_years = config["feature_year_end"] - config["feature_year_start"] + 1
    expected_center_years = config["center_year_end"] - config["center_year_start"] + 1
    require(validation.get("expected_feature_years") == expected_feature_years and
            validation.get("expected_center_years") == expected_center_years, "year counts changed")
    for gate in ("require_exact_year_sequences", "require_exact_stage_season_reconciliation", "require_common_same_realization_gmst", "require_all_crop_regime_pairs", "calendar_pair_is_not_irrigation_treatment"):
        require(validation.get(gate) is True, f"validation gate changed: {gate}")
    return {
        "schema": "isimip3b_rimex_contiguous_multicrop_regime_preregistration_v1",
        "status": "preregistered_before_feature_construction",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "realization": {"esm": config["esm"], "member": config["member"], "scenario": config["scenario"]},
        "sources": sources,
        "cells": calendar_records,
        "response_estimation_authorized": False,
        "irrigation_treatment_effect_authorized": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.config, args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("contiguous 12-cell crop × calendar-regime contract passed")


if __name__ == "__main__":
    main()
