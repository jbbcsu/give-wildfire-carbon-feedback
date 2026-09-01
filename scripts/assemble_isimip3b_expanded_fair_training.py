#!/usr/bin/env python3
"""Assemble the pinned early-, mid-, and end-century FAIR training surface.

This joins already validated bounded feature products. It does not fit or
authorize a production emulator, agricultural response, damage, or SCC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


CONFIG_SCHEMA = "isimip3b_expanded_fair_training_config_v1"
CONFIG_ROLE = "bounded_five_esm_early_mid_endcentury_training_join_not_production_response_damage_or_scc"
ESMS = {"GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"}
SCENARIOS = {"historical", "ssp126", "ssp370", "ssp585"}
FEATURES = {
    "tmean_c", "precip_mm", "wet_days_n", "cdd_max_days", "rx1day_mm", "rx5day_mm",
    "stage1_precip_share", "stage2_precip_share", "stage3_precip_share",
    "precipitation_timing_centroid", "precipitation_concentration_hhi",
}
KEYS = ["esm_id", "member_id", "scenario", "year", "lat", "lon_360", "crop", "irrigation", "feature_family"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_esm(values: pd.Series) -> pd.Series:
    lookup = {name.lower(): name for name in ESMS}
    normalized = values.astype(str).str.lower().map(lookup)
    if normalized.isna().any():
        raise ValueError("training contains an unregistered ESM")
    return normalized


def validate_frame(frame: pd.DataFrame, *, expected_rows: int, expected_years: set[int], expected_scenarios: set[str]) -> pd.DataFrame:
    required = set(KEYS) | {"harvest_year", "gmst_source_id", "gmst_value_k", "gmst_esm_id", "gmst_member_id", "feature_value"}
    if not required.issubset(frame.columns) or len(frame) != expected_rows:
        raise ValueError("training input schema or row count changed")
    frame = frame.copy()
    frame["esm_id"] = normalize_esm(frame["esm_id"])
    frame["gmst_esm_id"] = normalize_esm(frame["gmst_esm_id"])
    if set(frame["esm_id"].astype(str)) != ESMS or set(frame["scenario"].astype(str)) != expected_scenarios:
        raise ValueError("training input ESM/scenario coverage changed")
    if set(frame["year"].astype(int)) != expected_years or set(frame["feature_family"].astype(str)) != FEATURES:
        raise ValueError("training input year/feature coverage changed")
    if not (frame["year"].astype(int) == frame["harvest_year"].astype(int)).all():
        raise ValueError("training year and harvest year differ")
    if not (frame["esm_id"].astype(str) == frame["gmst_esm_id"].astype(str)).all():
        raise ValueError("feature and GMST ESM identity differ")
    if not (frame["member_id"].astype(str) == frame["gmst_member_id"].astype(str)).all():
        raise ValueError("feature and GMST realization differ")
    if not np.isfinite(frame[["gmst_value_k", "feature_value"]].to_numpy(float)).all():
        raise ValueError("training contains nonfinite values")
    if frame.duplicated(KEYS).any():
        raise ValueError("training input contains duplicate exact keys")
    return frame


def assemble(config_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA or config.get("role") != CONFIG_ROLE:
        raise ValueError("expanded FAIR training contract identity changed")
    limitations = config.get("limitations", {})
    for gate in ("production_emulator_authorized", "response_estimation_authorized", "damage_or_scc_authorized"):
        if limitations.get(gate) is not False:
            raise ValueError(f"expanded training unexpectedly opens {gate}")
    root = config_path.parent.parent
    frames: list[pd.DataFrame] = []
    receipts: list[dict[str, object]] = []
    for record in config.get("inputs", []):
        path = root / str(record["path"])
        if not path.is_file() or sha256(path) != str(record["sha256"]):
            raise ValueError(f"training input hash changed: {path}")
        years = set(map(int, record["expected_years"]))
        scenarios = set(map(str, record["expected_scenarios"]))
        frame = validate_frame(
            pd.read_parquet(path), expected_rows=int(record["expected_rows"]),
            expected_years=years, expected_scenarios=scenarios,
        )
        frames.append(frame)
        receipts.append({"id": str(record["id"]), "path": str(record["path"]), "sha256": sha256(path), "rows": len(frame)})
    if len(frames) != 3:
        raise ValueError("expanded training requires exactly three pinned periods")
    output = pd.concat(frames, ignore_index=True)
    if output.duplicated(KEYS).any():
        raise ValueError("expanded training periods overlap exact keys")
    if set(output["scenario"].astype(str)) != SCENARIOS or set(output["esm_id"].astype(str)) != ESMS:
        raise ValueError("expanded training product is incomplete")
    output = output.sort_values(KEYS, kind="mergesort").reset_index(drop=True)
    return output, {"inputs": receipts, "rows": len(output), "years": sorted(output["year"].astype(int).unique().tolist())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    output, metadata = assemble(config_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.out, index=False)
    root = config_path.parent.parent
    implementation = Path(__file__).resolve()
    audit = {
        "schema": "isimip3b_expanded_fair_training_audit_v1", "role": CONFIG_ROLE,
        "config": {"path": str(config_path.relative_to(root)), "sha256": sha256(config_path)},
        "implementation": {"path": str(implementation.relative_to(root)), "sha256": sha256(implementation)},
        **metadata,
        "esm_ids": sorted(ESMS), "scenarios": sorted(SCENARIOS), "feature_families": sorted(FEATURES),
        "output": {"artifact_name": args.out.name, "sha256": sha256(args.out)},
        "production_emulator_authorized": False, "response_estimation_authorized": False,
        "damage_or_scc_authorized": False,
        "limitation": "One crop/regime and two latitude rows; joins climate-feature support only.",
        "result": "passed_bounded_training_join_only",
    }
    args.audit_out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"expanded FAIR training join passed: {len(output)} rows")


if __name__ == "__main__":
    main()
