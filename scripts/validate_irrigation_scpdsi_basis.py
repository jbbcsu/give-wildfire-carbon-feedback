#!/usr/bin/env python3
"""Recompute and validate an aggregate-outcome historical scPDSI basis."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype

from allocate_irrigation_scpdsi_basis import (
    CONTRACT_ID,
    SOURCE_ROLE,
    allocate_scpdsi_candidate,
    sha256_file,
)
from allocate_outcome_exposures import KEYS, read_table
from scpdsi_partition_provenance import validate_combined_manifest
from validate_stage_scpdsi_partition import validate_frame


def _hash_json(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_exact_false(mapping: dict[str, object], key: str) -> None:
    if key not in mapping or mapping[key] is not False:
        raise ValueError(f"{key} must be exactly false")


def validate_candidate(
    candidate_path: Path,
    audit_path: Path,
    panel_paths: list[Path],
    drought_paths: list[Path],
    drought_manifest_paths: list[Path],
    raw_scpdsi_path: Path,
    calendar_paths: list[Path],
    weights_path: Path,
    *,
    expected_crop: str,
    expected_year_start: int,
    expected_year_end: int,
) -> dict[str, object]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("response_basis_contract_id") != CONTRACT_ID:
        raise ValueError("Unexpected scPDSI response-basis contract")
    if audit.get("water_stress_family") != "climatic_water_balance_scpdsi":
        raise ValueError("Unexpected water-stress family")
    if audit.get("drought_source_role") != SOURCE_ROLE:
        raise ValueError("scPDSI source role is not historical-benchmark-only")
    if audit.get("basis_allocation_order") != "regime_basis_before_fixed_area_weighting":
        raise ValueError("scPDSI basis allocation order drifted")
    if audit.get("direct_weather_terms_included") is not False:
        raise ValueError("Direct-weather terms must not be stacked into this candidate basis")
    if audit.get("competing_family_not_stacked") is not True:
        raise ValueError("Competing-family non-stacking gate is missing")
    for flag in (
        "fit_authorized",
        "causal_interpretation_authorized",
        "future_projection_authorized",
        "scc_authorized",
    ):
        _require_exact_false(audit, flag)

    if audit.get("input_panel_files") != [str(path) for path in panel_paths]:
        raise ValueError("Panel paths differ from the allocation audit")
    if audit.get("input_scpdsi_files") != [str(path) for path in drought_paths]:
        raise ValueError("scPDSI paths differ from the allocation audit")
    if audit.get("input_scpdsi_manifest_files") != [str(path) for path in drought_manifest_paths]:
        raise ValueError("scPDSI source-manifest paths differ from the allocation audit")
    if audit.get("raw_scpdsi_file") != str(raw_scpdsi_path):
        raise ValueError("Raw scPDSI path differs from the allocation audit")
    if audit.get("crop_calendar_files") != [str(path) for path in calendar_paths]:
        raise ValueError("Crop-calendar paths differ from the allocation audit")
    if audit.get("weight_file") != str(weights_path):
        raise ValueError("Weight path differs from the allocation audit")
    panel_hashes = [sha256_file(path) for path in panel_paths]
    drought_hashes = [sha256_file(path) for path in drought_paths]
    drought_manifest_hashes = [sha256_file(path) for path in drought_manifest_paths]
    raw_scpdsi_hash = sha256_file(raw_scpdsi_path)
    calendar_hashes = [sha256_file(path) for path in calendar_paths]
    weight_hash = sha256_file(weights_path)
    if audit.get("input_panel_sha256") != panel_hashes:
        raise ValueError("A panel SHA-256 differs from the allocation audit")
    if audit.get("input_scpdsi_sha256") != drought_hashes:
        raise ValueError("An scPDSI SHA-256 differs from the allocation audit")
    if audit.get("input_scpdsi_manifest_sha256") != drought_manifest_hashes:
        raise ValueError("A stage-scPDSI manifest SHA-256 differs from the allocation audit")
    if audit.get("raw_scpdsi_sha256") != raw_scpdsi_hash:
        raise ValueError("Raw scPDSI SHA-256 differs from the allocation audit")
    if audit.get("crop_calendar_sha256") != calendar_hashes:
        raise ValueError("A crop-calendar SHA-256 differs from the allocation audit")
    if audit.get("weight_file_sha256") != weight_hash:
        raise ValueError("The weight SHA-256 differs from the allocation audit")

    threshold = float(audit["scpdsi_threshold"])
    stages = int(audit["stage_count"])
    expected_irrigation = list(audit["irrigation_labels"])
    if not (
        len(panel_paths)
        == len(drought_paths)
        == len(drought_manifest_paths)
        == len(calendar_paths)
        == len(expected_irrigation)
    ):
        raise ValueError("The regime-specific source lists have different lengths")
    combined_manifests = [
        validate_combined_manifest(
            manifest_path,
            drought_path,
            scpdsi_path=raw_scpdsi_path,
            calendar_path=calendar_path,
            expected_crop=expected_crop,
            expected_irrigation=irrigation,
            expected_year_start=expected_year_start,
            expected_year_end=expected_year_end,
            expected_stages=stages,
            expected_threshold=threshold,
        )
        for manifest_path, drought_path, calendar_path, irrigation in zip(
            drought_manifest_paths, drought_paths, calendar_paths, expected_irrigation
        )
    ]
    if audit.get("stage_source_manifest_contract_ids") != [
        str(manifest["contract_id"]) for manifest in combined_manifests
    ]:
        raise ValueError("Stage source-manifest contract IDs differ from the allocation audit")
    if audit.get("raw_source_and_calendar_manifest_chain_validated") is not True:
        raise ValueError("Allocation audit lacks the raw-source/calendar manifest-chain gate")
    if audit.get("full_raw_metric_recomputation_in_candidate_validator") is not False:
        raise ValueError("Candidate validator must not overclaim full raw metric recomputation")
    panel = pd.concat([read_table(path) for path in panel_paths], ignore_index=True)
    drought_frames = [read_table(path) for path in drought_paths]
    for frame in drought_frames:
        validate_frame(frame, threshold, stages)
    drought = pd.concat(drought_frames, ignore_index=True)
    validate_frame(drought, threshold, stages)
    recomputed, recomputed_audit = allocate_scpdsi_candidate(
        panel,
        drought,
        read_table(weights_path),
        expected_irrigation,
        threshold=threshold,
        stages=stages,
        exclude_missing_drought_cells=(
            audit.get("drought_coverage_policy")
            == "exclude_entire_crop_grid_year_if_any_regime_missing_without_infill"
        ),
        exclude_missing_weight_cells=(
            audit.get("missing_weight_policy")
            == "exclude_entire_crop_grid_year_outcome_without_infill_or_renormalization"
        ),
    )
    for key, value in recomputed_audit.items():
        if audit.get(key) != value:
            raise ValueError(f"Allocation-audit field differs on full recomputation: {key}")

    candidate = read_table(candidate_path)
    if list(candidate.columns) != list(recomputed.columns):
        raise ValueError("Candidate schema differs from the fully recomputed basis")
    pd.testing.assert_frame_equal(
        candidate.reset_index(drop=True),
        recomputed.reset_index(drop=True),
        check_dtype=True,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    if candidate.empty or candidate.duplicated(KEYS).any():
        raise ValueError("Candidate must contain unique, nonempty crop-grid-year rows")
    if set(candidate["crop"].astype(str).unique()) != {expected_crop}:
        raise ValueError("Candidate crop differs from the expected crop")
    years = sorted(candidate["harvest_year"].astype(int).unique())
    if years != list(range(expected_year_start, expected_year_end + 1)):
        raise ValueError("Candidate does not contain the exact expected year range")
    feature_names = list(audit["basis_features"])
    if len(feature_names) != int(audit["basis_feature_count"]):
        raise ValueError("Basis feature count differs from the audit")
    if not np.isfinite(candidate[feature_names].to_numpy(dtype=float)).all():
        raise ValueError("Candidate contains nonfinite drought-basis values")
    forbidden = {
        "precip_mm",
        "log1p_precip_mm",
        "tmean_c",
        "cdd_max_days",
        "rx1day_mm",
        "rx5day_mm",
    }
    if forbidden & set(candidate.columns):
        raise ValueError("Direct-weather terms leaked into the competing scPDSI basis")
    for flag in (
        "fit_authorized",
        "causal_interpretation_authorized",
        "future_projection_authorized",
        "scc_authorized",
    ):
        if flag not in candidate or not is_bool_dtype(candidate[flag].dtype) or candidate[flag].any():
            raise ValueError(f"Candidate {flag} must be false for every row")

    return {
        "schema_version": 1,
        "status": "validated_historical_scpdsi_candidate_not_fit_causal_future_damage_or_scc_authorized",
        "response_basis_contract_id": CONTRACT_ID,
        "crop": expected_crop,
        "harvest_year_start": expected_year_start,
        "harvest_year_end": expected_year_end,
        "rows": int(len(candidate)),
        "observed_outcomes": int(candidate["yield_observed"].sum()),
        "basis_feature_count": len(feature_names),
        "candidate_sha256": sha256_file(candidate_path),
        "allocation_audit_sha256": _hash_json(audit_path),
        "input_panel_sha256": panel_hashes,
        "input_scpdsi_sha256": drought_hashes,
        "weight_file_sha256": weight_hash,
        "full_derived_allocation_recomputation_passed": True,
        "raw_source_and_calendar_manifest_chain_passed": True,
        "full_raw_metric_recomputation_passed": False,
        "competing_family_not_stacked": True,
        "fit_authorized": False,
        "causal_interpretation_authorized": False,
        "future_projection_authorized": False,
        "scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--allocation-audit", required=True)
    parser.add_argument("--panel", action="append", required=True)
    parser.add_argument("--stage-scpdsi", action="append", required=True)
    parser.add_argument("--stage-scpdsi-manifest", action="append", required=True)
    parser.add_argument("--raw-scpdsi", required=True)
    parser.add_argument("--calendar", action="append", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--expected-crop", required=True)
    parser.add_argument("--expected-year-start", type=int, required=True)
    parser.add_argument("--expected-year-end", type=int, required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    result = validate_candidate(
        Path(args.candidate),
        Path(args.allocation_audit),
        [Path(path) for path in args.panel],
        [Path(path) for path in args.stage_scpdsi],
        [Path(path) for path in args.stage_scpdsi_manifest],
        Path(args.raw_scpdsi),
        [Path(path) for path in args.calendar],
        Path(args.weights),
        expected_crop=args.expected_crop,
        expected_year_start=args.expected_year_start,
        expected_year_end=args.expected_year_end,
    )
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
