#!/usr/bin/env python3
"""Synthetic integrity and failure-mode tests for the locked diagnostic."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from build_direct_scpdsi_common_support import (  # noqa: E402
    DIRECT_INPUT_CONTRACT,
    SCPDSI_INPUT_CONTRACT,
    SCPDSI_SOURCE_ROLE,
    build_bundle as build_common_bundle,
    sha256_file,
)
from build_direct_scpdsi_diagnostic_inputs import (  # noqa: E402
    FALSE_GATES,
    HEAT_CONTRACT_ID,
    OUTCOME,
    _block_fold,
    build_inputs,
    compute_outcome_blind_stress_plan,
    load_config,
)
from evaluate_direct_scpdsi_predictive_diagnostic import (  # noqa: E402
    _metrics,
    evaluate_files,
    evaluate_views,
    validate_view_frames,
)
from validate_direct_scpdsi_common_support import validate_bundle as validate_common  # noqa: E402
from validate_direct_scpdsi_predictive_diagnostic import (  # noqa: E402
    _check_result_structure,
    validate_diagnostic,
)


DIRECT_SOURCE_FEATURES = ["log1p_precip_mm", "cdd_max_days", "rx5day_mm"]
SCPDSI_SOURCE_FEATURES = [
    "season_scpdsi_mean", "season_scpdsi_min",
    "season_scpdsi_fraction_at_or_below_threshold",
    "stage1_scpdsi_mean", "stage2_scpdsi_mean", "stage3_scpdsi_mean",
]


def expect_failure(action: Callable[[], object], text: str) -> None:
    try:
        action()
    except (ValueError, FileNotFoundError, AssertionError) as error:
        assert text.lower() in str(error).lower(), str(error)
    else:
        raise AssertionError(f"Expected failure containing {text!r}")


# Hand-calculated golden metric case, independent of the regression evaluator.
golden = _metrics(np.array([1.0, 2.0, 4.0]), np.array([1.5, 1.5, 5.0]))
assert golden["n"] == 3
assert np.isclose(golden["mean_observed"], 7.0 / 3.0)
assert np.isclose(golden["sum_squared_error"], 1.5)
assert np.isclose(golden["sum_absolute_error"], 2.0)
assert np.isclose(golden["sum_squared_total"], 14.0 / 3.0)
assert np.isclose(golden["rmse"], np.sqrt(0.5))
assert np.isclose(golden["mae"], 2.0 / 3.0)
assert np.isclose(golden["r2"], 19.0 / 28.0)


def _locations(crop: str) -> list[tuple[float, float]]:
    selected: list[tuple[float, float]] = []
    counts = {fold: 0 for fold in range(5)}
    for lat_bin in range(4, 32):
        for lon_bin in range(0, 72, 3):
            lat = -90 + 5 * lat_bin + 2.5
            lon = 5 * lon_bin + 2.5
            _, fold = _block_fold(crop, lat, lon)
            if counts[fold] < 8:
                selected.append((lat, lon))
                counts[fold] += 1
            if min(counts.values()) >= 8:
                return selected
    raise AssertionError("Could not construct balanced synthetic spatial folds")


def _candidate_frames(crop: str, years: range, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    direct_rows: list[dict[str, object]] = []
    scpdsi_rows: list[dict[str, object]] = []
    heat_rows: list[dict[str, object]] = []
    for location_index, (lat, lon) in enumerate(_locations(crop)):
        latent = rng.normal()
        for year in years:
            log_precip = 5.4 + 0.25 * rng.normal() + 0.01 * (year - years.start)
            cdd = float(rng.gamma(2.0, 4.0))
            rx5 = float(rng.gamma(3.0, 8.0))
            scmean = float(-2.8 if rng.random() < 0.16 else rng.normal(-0.3, 0.8))
            scmin = scmean - abs(float(rng.normal(0.7, 0.2)))
            scfrac = float(np.clip((-scmean - 0.5) / 4.0 + rng.normal(0, 0.05), 0, 1))
            stages = [scmean + rng.normal(0, 0.35) for _ in range(3)]
            stage_tmeans = [18 + 2 * rng.normal() + 0.02 * (year - years.start) for _ in range(3)]
            heat29 = [max(0.0, rng.gamma(2.0, 4.0) + 0.05 * (year - years.start)) for _ in range(3)]
            heat30 = [max(0.0, value - rng.uniform(0.2, 1.5)) for value in heat29]
            log_yield = 1.1 + 0.004 * (year - years.start) + 0.015 * latent + 0.02 * log_precip + 0.01 * scmean - 0.002 * sum(heat29) + rng.normal(0, 0.04)
            common = {
                "harvest_year": year, "lat": lat, "lon_360": lon, "crop": crop,
                "yield_observed": True, "yield_t_ha": float(np.exp(log_yield)),
                "irrigation": "area_weighted",
                "exposure_allocation": "one_outcome_independent_fixed_area_weighted",
                "weight_source_id": "synthetic_mirca_2000",
                "weight_vintage": "fixed_2000",
                "basis_allocation_order": "regime_basis_before_fixed_area_weighting",
                "fit_authorized": False, "scc_authorized": False,
            }
            direct_rows.append({
                **common, "response_basis_contract_id": DIRECT_INPUT_CONTRACT,
                "log1p_precip_mm": log_precip, "cdd_max_days": cdd, "rx5day_mm": rx5,
                "stage1_tmean_c": stage_tmeans[0],
                "stage2_tmean_c": stage_tmeans[1],
                "stage3_tmean_c": stage_tmeans[2],
            })
            scpdsi_rows.append({
                **common, "response_basis_contract_id": SCPDSI_INPUT_CONTRACT,
                "water_stress_family": "climatic_water_balance_scpdsi",
                "drought_source_role": SCPDSI_SOURCE_ROLE,
                "direct_weather_terms_included": False,
                "causal_interpretation_authorized": False,
                "future_projection_authorized": False,
                "season_scpdsi_mean": scmean, "season_scpdsi_min": scmin,
                "season_scpdsi_fraction_at_or_below_threshold": scfrac,
                "stage1_scpdsi_mean": stages[0], "stage2_scpdsi_mean": stages[1],
                "stage3_scpdsi_mean": stages[2],
            })
            heat_row: dict[str, object] = {
                "harvest_year": year, "lat": lat, "lon_360": lon, "crop": crop,
                "yield_observed": True, "yield_t_ha": float(np.exp(log_yield)),
            }
            for stage in range(1, 4):
                heat_row[f"stage{stage}_tmean_c"] = stage_tmeans[stage - 1]
                heat_row[f"stage{stage}_tmax_29c_days"] = float(heat29[stage - 1] > 0)
                heat_row[f"stage{stage}_tmax_29c_degree_days"] = heat29[stage - 1]
                heat_row[f"stage{stage}_tmax_30c_days"] = float(heat30[stage - 1] > 0)
                heat_row[f"stage{stage}_tmax_30c_degree_days"] = heat30[stage - 1]
            heat_row.update({
                "heat_control_basis_contract_id": HEAT_CONTRACT_ID,
                "source_role": "common_nonmoisture_controls_only",
                "diagnostic_fit_authorized": True,
                **{gate: False for gate in FALSE_GATES},
            })
            heat_rows.append(heat_row)
    return pd.DataFrame(direct_rows), pd.DataFrame(scpdsi_rows), pd.DataFrame(heat_rows)


def _prepare(root: Path) -> tuple[Path, dict[str, Path], Path, Path]:
    template_path = PROJECT / "config" / "direct_scpdsi_predictive_diagnostic_v1.toml"
    template_text = template_path.read_text(encoding="utf-8")
    template = tomllib.loads(template_text)
    replacements: dict[str, str] = {}
    seed = 100
    for bundle in template["input_bundles"]:
        crop, episode = bundle["crop"], bundle["episode"]
        years = range(1982, 1990) if episode == "early" else range(2012, 2017)
        direct, scpdsi, heat = _candidate_frames(crop, years, seed)
        seed += 1
        paths = {name: root / f"{crop}_{episode}_{name}{'.json' if name.endswith(('audit','validation')) else '.parquet'}" for name in (
            "direct_view", "scpdsi_view", "common_audit", "common_validation",
            "direct_candidate", "direct_allocation_audit", "direct_validation",
            "scpdsi_candidate", "scpdsi_allocation_audit", "scpdsi_validation",
            "heat_control", "heat_validation",
        )}
        direct.to_parquet(paths["direct_candidate"], index=False)
        scpdsi.to_parquet(paths["scpdsi_candidate"], index=False)
        build_common_bundle(
            paths["direct_candidate"], paths["scpdsi_candidate"], paths["direct_view"],
            paths["scpdsi_view"], paths["common_audit"],
            DIRECT_SOURCE_FEATURES, SCPDSI_SOURCE_FEATURES,
        )
        common_receipt = validate_common(
            paths["direct_view"], paths["scpdsi_view"], paths["common_audit"],
            paths["direct_candidate"], paths["scpdsi_candidate"],
        )
        paths["common_validation"].write_text(json.dumps(common_receipt, sort_keys=True) + "\n")
        panel_hashes = ["a" * 64, "b" * 64]
        weight_hash = "c" * 64
        paths["direct_allocation_audit"].write_text(json.dumps({
            "candidate_sha256": sha256_file(paths["direct_candidate"]),
            "input_panel_sha256": panel_hashes,
            "weight_file_sha256": weight_hash,
            "irrigation_labels": ["noirr", "firr"],
            "wet_day_threshold_mm": 1.0,
        }, sort_keys=True) + "\n")
        paths["direct_validation"].write_text(json.dumps({
            "status": "validated_candidate_basis_not_fit_or_scc_authorized",
            "response_basis_contract_id": DIRECT_INPUT_CONTRACT, "crop": crop,
            "candidate_sha256": sha256_file(paths["direct_candidate"]),
            "allocation_audit_sha256": sha256_file(paths["direct_allocation_audit"]),
            "wet_day_threshold_mm": 1.0,
            "fit_authorized": False, "scc_authorized": False,
        }, sort_keys=True) + "\n")
        paths["scpdsi_allocation_audit"].write_text(json.dumps({
            "scpdsi_threshold": -2.0,
            "irrigation_labels": ["noirr", "firr"],
        }, sort_keys=True) + "\n")
        paths["scpdsi_validation"].write_text(json.dumps({
            "status": "validated_historical_scpdsi_candidate_not_fit_causal_future_damage_or_scc_authorized",
            "response_basis_contract_id": SCPDSI_INPUT_CONTRACT, "crop": crop,
            "candidate_sha256": sha256_file(paths["scpdsi_candidate"]),
            "allocation_audit_sha256": sha256_file(paths["scpdsi_allocation_audit"]),
            "scpdsi_threshold": -2.0,
            "input_panel_sha256": panel_hashes,
            "weight_file_sha256": weight_hash,
            "raw_source_and_calendar_manifest_chain_passed": True,
            "full_raw_metric_recomputation_passed": False,
            "fit_authorized": False, "causal_interpretation_authorized": False,
            "future_projection_authorized": False, "scc_authorized": False,
        }, sort_keys=True) + "\n")
        heat.to_parquet(paths["heat_control"], index=False)
        paths["heat_validation"].write_text(json.dumps({
            "schema_version": 1,
            "status": "validated_common_nonmoisture_heat_control_basis",
            "heat_control_basis_contract_id": HEAT_CONTRACT_ID,
            "crop": crop, "harvest_year_start": years.start, "harvest_year_end": years.stop - 1,
            "heat_control_sha256": sha256_file(paths["heat_control"]),
            "source_role": "common_nonmoisture_controls_only",
            "diagnostic_fit_authorized": True,
            "immediate_input_recomputation_passed": True,
            "raw_source_recomputation_performed": False,
            "source_files_sha256": {
                "direct_panel_noirr": panel_hashes[0],
                "direct_panel_firr": panel_hashes[1],
                "fixed_area_weights": weight_hash,
            },
            **{gate: False for gate in FALSE_GATES},
        }, sort_keys=True) + "\n")
        for field, old in bundle.items():
            if field in paths:
                replacements[old] = str(paths[field])
    config_text = template_text
    for old, new in replacements.items():
        config_text = config_text.replace(f'"{old}"', json.dumps(new))
    config_path = root / "diagnostic.toml"
    config_path.write_text(config_text, encoding="utf-8")
    output_dir = root / "views"
    audit_path = root / "input_audit.json"
    result_path = root / "result.json"
    build_inputs(config_path, output_dir, audit_path)
    view_paths = {name: output_dir / f"{name}_view.parquet" for name in ("direct", "scpdsi", "common", "split")}
    evaluate_files(config_path, audit_path, view_paths, result_path)
    return config_path, view_paths, audit_path, result_path


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    config_path, view_paths, audit_path, result_path = _prepare(root)
    receipt = validate_diagnostic(config_path, audit_path, view_paths, result_path)
    assert receipt["metric_arithmetic_recomputed"] is True
    assert receipt["common_bundles_revalidated"] is True
    assert receipt["family_stacking_authorized"] is False
    assert receipt["config_sha256"] == sha256_file(config_path)
    assert receipt["input_audit_sha256"] == sha256_file(audit_path)
    assert receipt["input_view_sha256"] == {
        name: sha256_file(path) for name, path in sorted(view_paths.items())
    }
    assert receipt["result_sha256"] == sha256_file(result_path)
    result = json.loads(result_path.read_text())
    assert result["result_count"] == 2 * 5 * 11
    assert result["coefficients_emitted"] is False
    assert result["predictions_emitted"] is False
    assert result["temporal_holdout_prospective"] is False
    audit = json.loads(audit_path.read_text())
    assert audit["stress_cutoffs"]["cutoff_scope"] == "crop_specific"
    assert set(audit["stress_cutoffs"]["values_by_crop"]) == {"mai", "soy"}

    # Validation receipts must bind exact candidate/audit hashes and thresholds.
    config = tomllib.loads(config_path.read_text())
    first_bundle = config["input_bundles"][0]
    direct_receipt_path = Path(first_bundle["direct_validation"])
    direct_receipt = json.loads(direct_receipt_path.read_text())
    direct_receipt["candidate_sha256"] = "0" * 64
    direct_receipt_path.write_text(json.dumps(direct_receipt, sort_keys=True) + "\n")
    expect_failure(lambda: build_inputs(config_path, root / "bad_hash_views", root / "bad_hash_audit.json"), "not hash-bound")
    direct_receipt["candidate_sha256"] = sha256_file(Path(first_bundle["direct_candidate"]))
    direct_receipt_path.write_text(json.dumps(direct_receipt, sort_keys=True) + "\n")

    scpdsi_receipt_path = Path(first_bundle["scpdsi_validation"])
    scpdsi_receipt = json.loads(scpdsi_receipt_path.read_text())
    scpdsi_receipt["scpdsi_threshold"] = -1.0
    scpdsi_receipt_path.write_text(json.dumps(scpdsi_receipt, sort_keys=True) + "\n")
    expect_failure(lambda: build_inputs(config_path, root / "bad_threshold_views", root / "bad_threshold_audit.json"), "threshold")
    scpdsi_receipt["scpdsi_threshold"] = -2.0
    scpdsi_receipt_path.write_text(json.dumps(scpdsi_receipt, sort_keys=True) + "\n")

    # Cutoff code refuses outcome columns, making outcome-blindness structural.
    split = pd.read_parquet(view_paths["split"])
    expect_failure(
        lambda: compute_outcome_blind_stress_plan(
            split[[*(["crop", "episode", "lat", "lon_360", "start_year", "end_year"]), OUTCOME]],
            0.95, -2.0,
        ),
        "cannot receive an outcome",
    )

    # Unequal heat/common outcomes fail before pair creation.
    heat_path = Path(config["input_bundles"][0]["heat_control"])
    original_heat = pd.read_parquet(heat_path)
    changed_heat = original_heat.copy()
    changed_heat.loc[0, "yield_t_ha"] += 0.1
    changed_heat.to_parquet(heat_path, index=False)
    heat_receipt_path = Path(config["input_bundles"][0]["heat_validation"])
    heat_receipt = json.loads(heat_receipt_path.read_text())
    heat_receipt["heat_control_sha256"] = sha256_file(heat_path)
    heat_receipt_path.write_text(json.dumps(heat_receipt, sort_keys=True) + "\n")
    expect_failure(lambda: build_inputs(config_path, root / "bad_views", root / "bad_audit.json"), "outcomes differ")
    original_heat.to_parquet(heat_path, index=False)
    heat_receipt["heat_control_sha256"] = sha256_file(heat_path)
    heat_receipt_path.write_text(json.dumps(heat_receipt, sort_keys=True) + "\n")

    changed_heat = original_heat.copy()
    changed_heat.loc[0, "stage1_tmean_c"] += 0.1
    changed_heat.to_parquet(heat_path, index=False)
    heat_receipt["heat_control_sha256"] = sha256_file(heat_path)
    heat_receipt_path.write_text(json.dumps(heat_receipt, sort_keys=True) + "\n")
    expect_failure(lambda: build_inputs(config_path, root / "bad_tmean_views", root / "bad_tmean_audit.json"), "stage1_tmean_c differs")
    original_heat.to_parquet(heat_path, index=False)
    heat_receipt["heat_control_sha256"] = sha256_file(heat_path)
    heat_receipt_path.write_text(json.dumps(heat_receipt, sort_keys=True) + "\n")

    # Cross-period/nonconsecutive pairs and endpoint-purge overlap fail.
    views = {name: pd.read_parquet(path) for name, path in view_paths.items()}
    bad_cross = {name: frame.copy() for name, frame in views.items()}
    for frame in bad_cross.values():
        frame.loc[0, "start_year"] = 1989
        frame.loc[0, "end_year"] = 2012
    expect_failure(lambda: validate_view_frames(bad_cross), "cross-period")
    bad_split = views["split"].copy()
    flag = "stress_direct_dry"
    test_endpoint = bad_split.loc[bad_split[flag], "start_endpoint_id"].iloc[0]
    candidate = bad_split.index[
        ~bad_split[flag]
        & (bad_split["start_endpoint_id"].eq(test_endpoint) | bad_split["end_endpoint_id"].eq(test_endpoint))
    ]
    if len(candidate):
        bad_split.loc[candidate[0], f"train_eligible_{flag}"] = True
    else:
        candidate = bad_split.index[~bad_split[flag]][0]
        bad_split.loc[candidate, "start_endpoint_id"] = test_endpoint
        bad_split.loc[candidate, f"train_eligible_{flag}"] = True
    expect_failure(lambda: validate_view_frames({**views, "split": bad_split}), "endpoint overlap")

    # Family stacking is forbidden in config and leakage is forbidden in views.
    stacked_path = root / "stacked.toml"
    stacked_path.write_text(
        config_path.read_text().replace(
            'candidate_features = ["direct__delta_log1p_precip_mm"]',
            'candidate_features = ["direct__delta_log1p_precip_mm", "scpdsi__delta_season_scpdsi_mean"]',
            1,
        )
    )
    expect_failure(lambda: load_config(stacked_path), "family stacking")
    leaked_direct = views["direct"].copy()
    leaked_direct.insert(8, "scpdsi__delta_season_scpdsi_mean", 0.0)
    expect_failure(lambda: validate_view_frames({**views, "direct": leaked_direct}), "schema")

    # Common-control mismatch, missing jobs, metric tampering, authorization,
    # and coefficient injection all fail at the result boundary.
    mismatch = copy.deepcopy(result)
    mismatch["models"][1]["common_controls"] = mismatch["models"][1]["common_controls"][:-1]
    expect_failure(lambda: _check_result_structure(mismatch), "common controls differ")
    missing_job = copy.deepcopy(result)
    missing_job["results"].pop()
    expect_failure(lambda: _check_result_structure(missing_job), "missing")
    bad_metric = copy.deepcopy(result)
    bad_metric["results"][0]["pooled_metrics"]["rmse"] += 0.01
    expect_failure(lambda: _check_result_structure(bad_metric), "rmse arithmetic")
    bad_authorization = copy.deepcopy(result)
    bad_authorization["scc_authorized"] = True
    expect_failure(lambda: _check_result_structure(bad_authorization), "must be exactly false")
    injected = copy.deepcopy(result)
    injected["effect_estimate"] = 1.0
    expect_failure(lambda: _check_result_structure(injected), "forbidden")

    # Missing result and audit/hash tampering fail closed.
    expect_failure(
        lambda: validate_diagnostic(config_path, audit_path, view_paths, root / "absent_result.json"),
        "missing",
    )
    tampered_audit = json.loads(audit_path.read_text())
    tampered_audit["scc_authorized"] = True
    audit_path.write_text(json.dumps(tampered_audit, sort_keys=True) + "\n")
    expect_failure(lambda: validate_diagnostic(config_path, audit_path, view_paths, result_path), "must be exactly false")
    build_inputs(config_path, view_paths["direct"].parent, audit_path)
    tampered_direct = pd.read_parquet(view_paths["direct"])
    tampered_direct.loc[0, "direct__delta_log1p_precip_mm"] += 1.0
    tampered_direct.to_parquet(view_paths["direct"], index=False)
    expect_failure(lambda: validate_diagnostic(config_path, audit_path, view_paths, result_path), "audit differs")
    rewritten_audit = json.loads(audit_path.read_text())
    rewritten_audit["output_files"]["direct"]["sha256"] = sha256_file(view_paths["direct"])
    audit_path.write_text(json.dumps(rewritten_audit, sort_keys=True) + "\n")
    expect_failure(
        lambda: validate_diagnostic(config_path, audit_path, view_paths, result_path),
        "differs from locked immediate-input recomputation",
    )

print("direct/scPDSI predictive diagnostic tests passed")
