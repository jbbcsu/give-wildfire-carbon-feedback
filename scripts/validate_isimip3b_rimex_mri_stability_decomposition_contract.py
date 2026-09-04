#!/usr/bin/env python3
"""Validate the locked MRI dependence-failure decomposition contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib


SCHEMA = "isimip3b_rimex_mri_stability_decomposition_contract_v1"
CROPS = ["mai", "soy", "ri1", "ri2", "swh", "wwh"]
REGIMES = ["noirr", "firr"]
YEARS = list(range(2042, 2050))
SHARED_SCENARIOS = ["ssp126", "ssp370"]


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
    require(config.get("role", "").startswith("outcome_blind_diagnostic_"), "outcome-blind role changed")
    for gate in ("dependence_fit_authorized", "fair_feature_response_authorized", "response_estimation_authorized", "damage_or_scc_authorized"):
        require(config.get(gate) is False, f"closed gate changed: {gate}")

    sample = config.get("sample", {})
    require(sample.get("completed_templates_required") == 88, "completed-template sample changed")
    require(sample.get("focal_esm") == "MRI-ESM2-0", "focal ESM changed")
    require(sample.get("focal_esm_templates_required") == 16, "focal-template count changed")
    require(sample.get("nonfocal_templates_required") == 72, "nonfocal-template count changed")
    require(sample.get("shared_scenarios") == SHARED_SCENARIOS, "shared-scenario restriction changed")
    require(sample.get("focal_templates_per_shared_scenario") == 8, "focal scenario support changed")
    require(sample.get("nonfocal_templates_per_shared_scenario") == 24, "comparison scenario support changed")
    require(sample.get("center_years") == YEARS, "center-year blocks changed")
    require(sample.get("crops_required") == CROPS, "crop set changed")
    require(sample.get("irrigation_regimes_required") == REGIMES, "irrigation-regime set changed")
    require(sample.get("crop_regime_cells_required") == 12, "crop/regime count changed")
    require(sample.get("missing_focal_scenario") == "ssp585", "missing focal scenario changed")

    method = config.get("method", {})
    require(method.get("focal_coordinate_left") == "wet_logit", "focal left coordinate changed")
    require(method.get("focal_coordinate_right") == "rx1_given_rx5_logit", "focal right coordinate changed")
    require(method.get("locked_original_maximum_difference_gate") == 0.15, "locked maximum gate changed")
    require(abs(float(method.get("locked_original_failure_difference", 0)) - 0.19231787881198553) < 1e-15, "locked failure value changed")
    for gate in ("full_sample_failure_must_reproduce", "scenario_specific_diagnostics_required", "center_year_diagnostics_required", "crop_regime_diagnostics_required", "cell_correlations_use_each_complete_centered_crop_regime_field", "descriptive_only_no_p_values", "no_tolerance_retuning", "no_model_fit", "outcome_columns_forbidden"):
        require(method.get(gate) is True, f"method gate changed: {gate}")
    require("SSP1-2.6 and SSP3-7.0" in method.get("scenario_matched_primary_test", ""), "primary matched comparison changed")
    require("unchanged 0.15 gate" in method.get("scenario_imbalance_sufficient_definition", ""), "imbalance interpretation changed")

    outputs = config.get("outputs", {})
    require(outputs.get("scenario_matched_aggregate_required") is True, "matched aggregate output removed")
    require(outputs.get("shared_scenario_rows_required") == 2, "scenario output count changed")
    require(outputs.get("center_year_rows_required") == 8, "center-year output count changed")
    require(outputs.get("crop_regime_rows_required") == 12, "crop/regime output count changed")
    require(outputs.get("cell_template_rows_required") == 1056, "cell-template output count changed")

    resources = config.get("resources", {})
    require(resources.get("maximum_peak_resident_memory_bytes") == 2 * 1024**3, "memory ceiling changed")
    for gate in ("large_downloads_forbidden", "raw_rehydration_forbidden", "global_daily_inputs_forbidden", "derived_parquet_columns_only", "one_centered_season_and_stage_file_pair_read_at_a_time"):
        require(resources.get(gate) is True, f"resource gate changed: {gate}")

    sources = []
    for source in config.get("source_receipts", []):
        path = root / source["path"]
        observed = sha256(path)
        require(observed == source["sha256"], f"source receipt hash changed: {source['path']}")
        sources.append({**source, "sha256": observed})
    require(len(sources) == 3, "source receipt count changed")

    return {
        "schema": "isimip3b_rimex_mri_stability_decomposition_preregistration_v1",
        "status": "validated_before_mri_decomposition_outputs",
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(Path(__file__)),
        "sources": sources,
        "focal_esm": sample["focal_esm"],
        "shared_scenarios": sample["shared_scenarios"],
        "dependence_fit_authorized": False,
        "fair_feature_response_authorized": False,
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
    print("MRI dependence-failure decomposition preregistration passed")


if __name__ == "__main__":
    main()
