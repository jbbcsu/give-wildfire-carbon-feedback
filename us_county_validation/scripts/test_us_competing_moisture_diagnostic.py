#!/usr/bin/env python3
"""Synthetic invariant tests for the U.S. competing-moisture diagnostic."""
from __future__ import annotations

import json
import math
import sys
import tempfile
import warnings
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from build_us_competing_moisture_inputs import (  # noqa: E402
    DEFAULT_PROTOCOL, build_inputs, build_source_receipt, load_protocol, sha256,
)
from evaluate_us_competing_moisture import (  # noqa: E402
    distribution_promotion_details,
    evaluate,
    evaluate_frames,
    fit_predictive_ols,
    purge_shared_first_difference_endpoints,
)
from validate_us_competing_moisture import validate_candidate  # noqa: E402

SYNTHETIC_STATES = [
    ("05", "AR"), ("08", "CO"), ("20", "KS"),
    ("31", "NE"), ("40", "OK"), ("48", "TX"),
]


def synthetic_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    direct_rows = []
    pdsi_rows = []
    windows = ["preplant90", "season", "stage1", "stage2", "stage3"]
    for county_number in range(1, 61):
        state_fips, state = SYNTHETIC_STATES[(county_number - 1) % len(SYNTHETIC_STATES)]
        geoid = f"{state_fips}{county_number:03d}"
        for crop_number, crop in enumerate(["corn_grain", "soybeans"]):
            for year in range(1998, 2017):
                phase = 0.37 * (year - 1998) + 0.11 * county_number + 0.2 * crop_number
                season_start = pd.Timestamp(year=year, month=4, day=1)
                season_end = pd.Timestamp(year=year, month=9, day=30)
                season_days = (season_end - season_start).days + 1
                fractions = [0.0, 0.3, 0.7, 1.0]
                window_dates = {
                    "preplant90": (
                        season_start - pd.Timedelta(days=90),
                        season_start - pd.Timedelta(days=1),
                    ),
                    "season": (season_start, season_end),
                }
                for stage, (left, right) in enumerate(
                    zip(fractions[:-1], fractions[1:], strict=True), start=1
                ):
                    window_dates[f"stage{stage}"] = (
                        season_start + pd.Timedelta(days=math.floor(left * season_days)),
                        season_start + pd.Timedelta(days=math.floor(right * season_days) - 1),
                    )
                precip = 430.0 + 65.0 * math.sin(phase) + 0.4 * county_number
                temperatures = [17.0 + 0.03 * (year - 1998), 22.0 + math.cos(phase), 18.0]
                pdsi = (precip - 430.0) / 65.0 + 0.05 * math.cos(phase * 1.7)
                common = {
                    "county_geoid": geoid,
                    "state": state,
                    "outcome_crop": crop,
                    "harvest_year": year,
                    "calendar_role": "fixed_primary",
                    "calendar_source_id": "synthetic_fixed_calendar",
                    "calendar_vintage": "2010",
                    "calendar_boundary_rule": "floor_midpoint_of_most_active_planting_and_harvest_intervals",
                    "stage_definition": "equal_duration_0_30_70_100_engineering_proxy",
                    "season_start": season_start,
                    "season_end": season_end,
                    "outcome_source_id": "synthetic_nass",
                    "weather_source_id": "synthetic_daily_weather",
                    "weather_grid_id": "nclimgrid_daily_conus_1_24_degree",
                    "weather_day_alignment": "source_date_label_unshifted_24h_ending_early_morning",
                    "wet_day_threshold_mm": 1.0,
                    "weight_role": "county_polygon_primary_proxy",
                    "crop_pixel_exposure": False,
                    "weather_exposure_shared_across_practices": True,
                    "feature_construction_eligible": True,
                    "stage1_tmean_c": temperatures[0],
                    "stage2_tmean_c": temperatures[1],
                    "stage3_tmean_c": temperatures[2],
                    "precip_mm": precip,
                    "cdd_max_days": 10.0,
                    "wet_day_frequency": 0.30,
                    "mean_wet_day_intensity_mm": 8.0,
                    "rx1day_mm": 25.0,
                    "rx5day_mm": 60.0,
                    "precipitation_concentration_hhi": 0.36,
                    "stage1_precip_share": 0.25,
                    "stage2_precip_share": 0.45,
                    "response_estimation_authorized": False,
                    "scc_authorized": False,
                }
                for practice in ["irrigated", "non_irrigated"]:
                    sensitivity = 0.00035 if practice == "irrigated" else 0.0010
                    crop_offset = 0.15 if crop == "corn_grain" else -0.15
                    practice_offset = 0.20 if practice == "irrigated" else 0.0
                    log_yield = (
                        4.0 + crop_offset + practice_offset + 0.012 * (year - 1998)
                        + sensitivity * precip + 0.004 * temperatures[1]
                        + 0.01 * math.sin(0.31 * county_number + year)
                    )
                    yield_value = math.exp(log_yield)
                    direct_rows.append({
                        **common,
                        "irrigation_practice": practice,
                        "yield_bu_acre": yield_value,
                    })
                    for window_number, window in enumerate(windows):
                        window_value = pdsi + 0.03 * window_number
                        window_start, window_end = window_dates[window]
                        pdsi_rows.append({
                            "county_geoid": geoid,
                            "state": state,
                            "outcome_crop": crop,
                            "harvest_year": year,
                            "irrigation_practice": practice,
                            "yield_bu_acre": yield_value,
                            "calendar_role": "fixed_primary",
                            "calendar_source_id": "synthetic_fixed_calendar",
                            "calendar_vintage": "2010",
                            "boundary_rule": "floor_midpoint_of_most_active_planting_and_harvest_intervals",
                            "stage_definition": "equal_duration_0_30_70_100_engineering_proxy",
                            "window_id": window,
                            "window_start": window_start,
                            "window_end": window_end,
                            "index_day_weighted_mean": window_value,
                            "index_source_id": "synthetic_pdsi",
                            "index_name": "nclimdiv_county_pdsi",
                            "index_scale_months": 0,
                            "index_distribution": "palmer_water_balance",
                            "drought_family": "pdsi",
                            "outcome_source_id": "synthetic_nass",
                            "monthly_value_day_weighted_not_daily_observation": True,
                            "index_calibration_start_year": 1931,
                            "index_calibration_end_year": 1990,
                            "irrigation_in_index": False,
                            "feature_construction_eligible": True,
                            "response_estimation_authorized_pdsi": False,
                            "scc_authorized_pdsi": False,
                        })
    direct = pd.DataFrame(direct_rows)
    pdsi = pd.DataFrame(pdsi_rows)
    missing_key = (
        direct.county_geoid.eq("05001")
        & direct.outcome_crop.eq("corn_grain")
        & direct.harvest_year.eq(2005)
    )
    direct = direct.loc[~missing_key].copy()
    pdsi_missing = (
        pdsi.county_geoid.eq("05001")
        & pdsi.outcome_crop.eq("corn_grain")
        & pdsi.harvest_year.eq(2005)
    )
    pdsi = pdsi.loc[~pdsi_missing].copy()
    return direct, pdsi


def synthetic_calendar(direct: pd.DataFrame) -> pd.DataFrame:
    calendar = direct[
        [
            "state", "outcome_crop", "harvest_year", "season_start", "season_end",
            "calendar_source_id", "calendar_vintage", "calendar_role",
            "calendar_boundary_rule", "stage_definition",
        ]
    ].drop_duplicates().rename(
        columns={
            "outcome_crop": "calendar_crop",
            "calendar_boundary_rule": "boundary_rule",
        }
    )
    calendar["feature_construction_eligible"] = True
    calendar["response_estimation_authorized"] = False
    calendar["scc_authorized"] = False
    return calendar.reset_index(drop=True)


protocol = deepcopy(load_protocol(DEFAULT_PROTOCOL))
protocol["direct_source"]["weather_source_id"] = "synthetic_daily_weather"
protocol["direct_source"]["calendar_source_id"] = "synthetic_fixed_calendar"
protocol["direct_source"]["outcome_source_id"] = "synthetic_nass"
protocol["pdsi_source"]["index_source_id"] = "synthetic_pdsi"
protocol["pdsi_source"]["calendar_source_id"] = "synthetic_fixed_calendar"
protocol["pdsi_source"]["outcome_source_id"] = "synthetic_nass"
direct_raw, pdsi_raw = synthetic_inputs()
calendar_raw = synthetic_calendar(direct_raw)
common, direct, pdsi, audit = build_inputs(direct_raw, pdsi_raw, calendar_raw, protocol)
assert len(common) == 4316
assert audit["nonconsecutive_or_initial_rows_not_differenced"] == 242
assert set(common.outcome_crop) == {"corn_grain", "soybeans"}
assert set(common.irrigation_practice) == {"irrigated", "non_irrigated"}
assert not ((common.county_geoid.eq("05001")) & (common.outcome_crop.eq("corn_grain"))
            & common.harvest_year.isin([2005, 2006])).any()
assert not any("pdsi" in column for column in direct.columns)
assert not any("precip" in column or "cdd" in column or "wet" in column for column in pdsi.columns)
assert common.harvest_year.sub(common.difference_previous_harvest_year).eq(1).all()

one_stratum = common.loc[
    common.outcome_crop.eq("corn_grain") & common.irrigation_practice.eq("non_irrigated")
].reset_index(drop=True)
test_mask = one_stratum.harvest_year.eq(2012).to_numpy(dtype=bool)
train_mask = one_stratum.harvest_year.lt(2012).to_numpy(dtype=bool)
purged_train, purged_rows = purge_shared_first_difference_endpoints(
    one_stratum, train_mask, test_mask
)
assert purged_rows > 0
assert not one_stratum.loc[purged_train, "harvest_year"].eq(2011).any()

result = evaluate_frames(common, direct, pdsi, protocol)
expected_metric_rows = 4 * 5 * (len(SYNTHETIC_STATES) + 2)
assert len(result["metrics"]) == expected_metric_rows
assert all(
    summary["direct_distribution_selected_on_development_leave_state_out"] is False
    for summary in result["comparison_summaries"]
)
assert result["causal_effect_estimated"] is False
assert result["damage_calculated"] is False
assert result["scc_calculated"] is False
assert result["coefficients_in_output"] is False
assert result["row_predictions_in_output"] is False
assert result["train_test_first_difference_level_endpoints_purged"] is True
assert all(
    metric["first_difference_level_endpoints_disjoint"] is True
    for metric in result["metrics"]
)
assert any(
    metric["split"] == "terminal_temporal_same_counties"
    and metric["train_rows_purged_shared_level_endpoint"] > 0
    for metric in result["metrics"]
)

# Exact collinearity must be handled by the registered SVD cutoff without
# emitting a numerical warning or retaining a nonfinite coefficient path.
solver_rows = 120
solver_frame = pd.DataFrame({
    "harvest_year": np.arange(2000, 2000 + solver_rows) % 20 + 2000,
    "delta_log_yield": np.sin(np.arange(solver_rows) / 9.0),
    "x": np.linspace(-1.0, 1.0, solver_rows),
})
solver_frame["x_exact_duplicate"] = solver_frame["x"]
solver_train = np.arange(solver_rows) < 90
solver_test = ~solver_train
with warnings.catch_warnings(record=True) as caught_solver_warnings:
    warnings.simplefilter("always")
    solver_metrics = fit_predictive_ols(
        solver_frame,
        ["x", "x_exact_duplicate"],
        solver_train,
        solver_test,
        1e-10,
        1e-8,
        1e-10,
    )
assert not [
    warning for warning in caught_solver_warnings
    if issubclass(warning.category, RuntimeWarning)
]
assert solver_metrics["linear_solver"] == "numpy_lstsq_with_registered_relative_svd_cutoff"
assert solver_metrics["design_rank"] < solver_metrics["design_columns_including_intercept"]
assert math.isfinite(solver_metrics["rmse"])
assert 0 < solver_metrics["smallest_retained_to_largest_singular_value_ratio"] <= 1

tiny_positive_rows = []
for model, rmse in [("direct_quantity", 0.1000), ("direct_quantity_distribution", 0.0999)]:
    tiny_positive_rows.append({
        "crop": "corn_grain", "irrigation_practice": "non_irrigated",
        "split": "development_leave_state_out", "split_id": "KS",
        "model": model, "rmse": rmse,
    })
promotion = distribution_promotion_details(
    tiny_positive_rows, "corn_grain", "non_irrigated", ["KS"], 0.0001, 0.01
)
assert promotion["improvements"]["KS"] > 0
assert promotion["selected"] is False

contaminated_pdsi = pdsi_raw.copy()
first = contaminated_pdsi.iloc[0]
where = (
    contaminated_pdsi.county_geoid.eq(first.county_geoid)
    & contaminated_pdsi.outcome_crop.eq(first.outcome_crop)
    & contaminated_pdsi.harvest_year.eq(first.harvest_year)
    & contaminated_pdsi.window_id.eq(first.window_id)
    & contaminated_pdsi.irrigation_practice.eq("irrigated")
)
contaminated_pdsi.loc[where, "index_day_weighted_mean"] += 1.0
try:
    build_inputs(direct_raw, contaminated_pdsi, calendar_raw, protocol)
except ValueError as error:
    assert "differs between irrigation-practice" in str(error)
else:
    raise AssertionError("builder accepted practice-specific PDSI exposure")

mismatched_outcome = pdsi_raw.copy()
first = mismatched_outcome.iloc[0]
one_key = (
    mismatched_outcome.county_geoid.eq(first.county_geoid)
    & mismatched_outcome.outcome_crop.eq(first.outcome_crop)
    & mismatched_outcome.harvest_year.eq(first.harvest_year)
    & mismatched_outcome.irrigation_practice.eq(first.irrigation_practice)
)
mismatched_outcome.loc[one_key, "yield_bu_acre"] += 1.0
try:
    build_inputs(direct_raw, mismatched_outcome, calendar_raw, protocol)
except ValueError as error:
    assert "disagree on outcome" in str(error)
else:
    raise AssertionError("builder accepted outcome disagreement across moisture inputs")

bad_pdsi_lineage = pdsi_raw.assign(boundary_rule="unlocked_calendar_rule")
try:
    build_inputs(direct_raw, bad_pdsi_lineage, calendar_raw, protocol)
except ValueError as error:
    assert "boundary_rule differs from the locked protocol" in str(error)
else:
    raise AssertionError("builder accepted an unlocked PDSI calendar rule")

bad_pdsi_window = pdsi_raw.copy()
bad_window_key = (
    bad_pdsi_window.county_geoid.eq("05001")
    & bad_pdsi_window.outcome_crop.eq("corn_grain")
    & bad_pdsi_window.harvest_year.eq(2000)
    & bad_pdsi_window.irrigation_practice.eq("non_irrigated")
    & bad_pdsi_window.window_id.eq("stage2")
)
bad_pdsi_window.loc[bad_window_key, "window_start"] = (
    pd.to_datetime(bad_pdsi_window.loc[bad_window_key, "window_start"])
    + pd.Timedelta(days=1)
)
try:
    build_inputs(direct_raw, bad_pdsi_window, calendar_raw, protocol)
except ValueError as error:
    assert "does not reconcile to the locked season/stage rule" in str(error)
else:
    raise AssertionError("builder accepted a shifted PDSI stage window")

bad_direct_dates = direct_raw.copy()
one_pair = bad_direct_dates.state.eq("AR") & bad_direct_dates.outcome_crop.eq("corn_grain")
bad_direct_dates.loc[one_pair, "season_start"] = (
    pd.to_datetime(bad_direct_dates.loc[one_pair, "season_start"]) + pd.Timedelta(days=1)
)
try:
    build_inputs(bad_direct_dates, pdsi_raw, calendar_raw, protocol)
except ValueError as error:
    assert "season_start differs from the bound calendar input" in str(error)
else:
    raise AssertionError("builder accepted cross-family crop-season disagreement")

bad_pdsi_state = pdsi_raw.copy()
one_state_key = bad_pdsi_state.county_geoid.eq("05001")
bad_pdsi_state.loc[one_state_key, "state"] = "CO"
try:
    build_inputs(direct_raw, bad_pdsi_state, calendar_raw, protocol)
except ValueError as error:
    assert "state does not reconcile to county GEOID" in str(error)
else:
    raise AssertionError("builder accepted cross-family state-lineage disagreement")

bad_direct_state = direct_raw.copy()
bad_pdsi_state = pdsi_raw.copy()
bad_direct_state.loc[bad_direct_state.state.eq("AR"), "state"] = "ZZ"
bad_pdsi_state.loc[bad_pdsi_state.state.eq("AR"), "state"] = "ZZ"
try:
    build_inputs(bad_direct_state, bad_pdsi_state, calendar_raw, protocol)
except ValueError as error:
    assert "state does not reconcile to county GEOID" in str(error)
else:
    raise AssertionError("builder accepted a shared false state/geographic holdout label")

for family in ["direct", "pdsi"]:
    bad_direct_eligibility = direct_raw.copy()
    bad_pdsi_eligibility = pdsi_raw.copy()
    target = bad_direct_eligibility if family == "direct" else bad_pdsi_eligibility
    target.loc[target.index[0], "feature_construction_eligible"] = False
    try:
        build_inputs(
            bad_direct_eligibility, bad_pdsi_eligibility, calendar_raw, protocol
        )
    except ValueError as error:
        assert "feature-ineligible" in str(error)
    else:
        raise AssertionError(f"builder accepted a feature-ineligible {family} row")

shifted_direct = direct_raw.copy()
shifted_pdsi = pdsi_raw.copy()
shift_direct = shifted_direct.state.eq("AR") & shifted_direct.outcome_crop.eq("corn_grain")
shift_pdsi = shifted_pdsi.state.eq("AR") & shifted_pdsi.outcome_crop.eq("corn_grain")
for column in ["season_start", "season_end"]:
    shifted_direct.loc[shift_direct, column] = (
        pd.to_datetime(shifted_direct.loc[shift_direct, column]) + pd.Timedelta(days=7)
    )
for column in ["window_start", "window_end"]:
    shifted_pdsi.loc[shift_pdsi, column] = (
        pd.to_datetime(shifted_pdsi.loc[shift_pdsi, column]) + pd.Timedelta(days=7)
    )
try:
    build_inputs(shifted_direct, shifted_pdsi, calendar_raw, protocol)
except ValueError as error:
    assert "differs from the bound calendar input" in str(error)
else:
    raise AssertionError("builder accepted shared source dates shifted from bound calendar")

contradictory_models = deepcopy(protocol)
contradictory_models["models"]["direct_quantity"] = ["pdsi_primary"]
try:
    evaluate_frames(common, direct, pdsi, contradictory_models)
except ValueError as error:
    assert "exact locked model schema" in str(error)
else:
    raise AssertionError("evaluator ignored a contradictory [models] contract")

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    protocol_path = root / "synthetic_protocol.toml"
    protocol_text = DEFAULT_PROTOCOL.read_text(encoding="utf-8")
    protocol_text = protocol_text.replace(
        'outcome_source_id = "nass_quickstats_direct_practice_screen"',
        'outcome_source_id = "synthetic_nass"',
    ).replace(
        'weather_source_id = "nclimgrid_daily_v1_0_0_20220829"',
        'weather_source_id = "synthetic_daily_weather"',
    ).replace(
        'calendar_source_id = "usda_nass_field_crops_usual_dates_2010"',
        'calendar_source_id = "synthetic_fixed_calendar"',
    ).replace(
        'index_source_id = "noaa_nclimdiv_county_pdsi_v1_0_0_20260806"',
        'index_source_id = "synthetic_pdsi"',
    )
    protocol_path.write_text(protocol_text, encoding="utf-8")
    assert load_protocol(protocol_path) == protocol
    raw_direct_path = root / "direct_weather.parquet"
    raw_pdsi_path = root / "pdsi_join.parquet"
    calendar_path = root / "calendar.csv"
    direct_raw.to_parquet(raw_direct_path, index=False)
    pdsi_raw.to_parquet(raw_pdsi_path, index=False)
    calendar_raw.to_csv(calendar_path, index=False)
    direct_validation_path = root / "direct_validation.json"
    pdsi_validation_path = root / "pdsi_validation.json"
    calendar_validation_path = root / "calendar_validation.json"
    direct_validation_path.write_text(
        json.dumps(
            build_source_receipt(raw_direct_path, "direct_weather", protocol_path),
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    pdsi_validation_path.write_text(
        json.dumps(
            build_source_receipt(raw_pdsi_path, "pdsi", protocol_path),
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    calendar_validation_path.write_text(
        json.dumps(
            build_source_receipt(calendar_path, "calendar", protocol_path),
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    input_dir = root / "inputs"
    input_dir.mkdir()
    paths = {
        "common": input_dir / "common_outcomes_controls_folds.parquet",
        "direct_weather": input_dir / "direct_weather.parquet",
        "pdsi": input_dir / "pdsi.parquet",
    }
    common.to_parquet(paths["common"], index=False)
    direct.to_parquet(paths["direct_weather"], index=False)
    pdsi.to_parquet(paths["pdsi"], index=False)
    audit["outputs"] = {
        name: {"path": str(path), "sha256": sha256(path)} for name, path in paths.items()
    }
    audit["inputs"] = {
        "direct_weather": {"path": str(raw_direct_path), "sha256": sha256(raw_direct_path)},
        "direct_validation": {
            "path": str(direct_validation_path), "sha256": sha256(direct_validation_path),
            "status": "validated_us_competing_moisture_source_input",
        },
        "pdsi_join": {"path": str(raw_pdsi_path), "sha256": sha256(raw_pdsi_path)},
        "pdsi_validation": {
            "path": str(pdsi_validation_path), "sha256": sha256(pdsi_validation_path),
            "status": "validated_us_competing_moisture_source_input",
        },
        "calendar": {"path": str(calendar_path), "sha256": sha256(calendar_path)},
        "calendar_validation": {
            "path": str(calendar_validation_path), "sha256": sha256(calendar_validation_path),
            "status": "validated_us_competing_moisture_source_input",
        },
        "protocol": {"path": str(protocol_path), "sha256": sha256(protocol_path)},
    }
    audit_path = root / "input_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    candidate = evaluate(
        input_dir,
        audit_path,
        raw_direct_path,
        direct_validation_path,
        raw_pdsi_path,
        pdsi_validation_path,
        calendar_path,
        calendar_validation_path,
        protocol_path,
    )
    candidate_path = root / "result.json"
    candidate_path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = validate_candidate(
        input_dir,
        audit_path,
        raw_direct_path,
        direct_validation_path,
        raw_pdsi_path,
        pdsi_validation_path,
        calendar_path,
        calendar_validation_path,
        candidate_path,
        protocol_path,
    )
    assert receipt["status"].startswith("validated_exact_recomputation")
    original_audit_text = audit_path.read_text(encoding="utf-8")
    false_count_audit = json.loads(original_audit_text)
    first_stratum = sorted(false_count_audit["strata"])[0]
    false_count_audit["strata"][first_stratum]["rows"] += 1
    audit_path.write_text(
        json.dumps(false_count_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    false_count_candidate = evaluate(
        input_dir, audit_path, raw_direct_path, direct_validation_path,
        raw_pdsi_path, pdsi_validation_path, calendar_path,
        calendar_validation_path, protocol_path,
    )
    candidate_path.write_text(
        json.dumps(false_count_candidate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        validate_candidate(
            input_dir, audit_path, raw_direct_path, direct_validation_path,
            raw_pdsi_path, pdsi_validation_path, calendar_path,
            calendar_validation_path, candidate_path, protocol_path,
        )
    except ValueError as error:
        assert "semantic fields differ from raw-source rebuild" in str(error)
    else:
        raise AssertionError("validator accepted a false semantic input-audit count")
    audit_path.write_text(original_audit_text, encoding="utf-8")
    candidate_path.write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    false_claim_audit = json.loads(original_audit_text)
    false_claim_audit["causal_effect_estimated"] = True
    audit_path.write_text(
        json.dumps(false_claim_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    try:
        evaluate(
            input_dir, audit_path, raw_direct_path, direct_validation_path,
            raw_pdsi_path, pdsi_validation_path, calendar_path,
            calendar_validation_path, protocol_path,
        )
    except ValueError as error:
        assert "invalid semantic gate causal_effect_estimated" in str(error)
    else:
        raise AssertionError("evaluator accepted a false causal claim in the input audit")
    audit_path.write_text(original_audit_text, encoding="utf-8")

    original_calendar_receipt = calendar_validation_path.read_text(encoding="utf-8")
    tampered_calendar_receipt = json.loads(original_calendar_receipt)
    tampered_calendar_receipt["lineage"]["calendar_vintage"] = ["tampered"]
    calendar_validation_path.write_text(
        json.dumps(tampered_calendar_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        evaluate(
            input_dir, audit_path, raw_direct_path, direct_validation_path,
            raw_pdsi_path, pdsi_validation_path, calendar_path,
            calendar_validation_path, protocol_path,
        )
    except ValueError as error:
        assert "calendar_validation hash differs" in str(error) or "receipt differs" in str(error)
    else:
        raise AssertionError("evaluator accepted a tampered calendar receipt")
    calendar_validation_path.write_text(original_calendar_receipt, encoding="utf-8")

    original_direct_receipt = direct_validation_path.read_text(encoding="utf-8")
    tampered_receipt = json.loads(original_direct_receipt)
    tampered_receipt["lineage"]["weather_source_id"] = ["tampered"]
    direct_validation_path.write_text(
        json.dumps(tampered_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    try:
        evaluate(
            input_dir,
            audit_path,
            raw_direct_path,
            direct_validation_path,
            raw_pdsi_path,
            pdsi_validation_path,
            calendar_path,
            calendar_validation_path,
            protocol_path,
        )
    except ValueError as error:
        assert "direct_validation hash differs" in str(error) or "receipt differs" in str(error)
    else:
        raise AssertionError("evaluator accepted a tampered source-validation receipt")
    direct_validation_path.write_text(original_direct_receipt, encoding="utf-8")
    original_direct_bytes = raw_direct_path.read_bytes()
    tampered_direct = direct_raw.copy()
    tampered_direct.loc[tampered_direct.index[0], "yield_bu_acre"] += 0.5
    tampered_direct.to_parquet(raw_direct_path, index=False)
    try:
        evaluate(
            input_dir,
            audit_path,
            raw_direct_path,
            direct_validation_path,
            raw_pdsi_path,
            pdsi_validation_path,
            calendar_path,
            calendar_validation_path,
            protocol_path,
        )
    except ValueError as error:
        assert "direct_weather hash differs" in str(error)
    else:
        raise AssertionError("evaluator accepted a raw direct-weather hash change")
    raw_direct_path.write_bytes(original_direct_bytes)
    tampered = dict(candidate)
    tampered["metrics"] = list(candidate["metrics"])
    tampered["metrics"][0] = dict(tampered["metrics"][0])
    tampered["metrics"][0]["rmse"] += 0.01
    candidate_path.write_text(json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        validate_candidate(
            input_dir,
            audit_path,
            raw_direct_path,
            direct_validation_path,
            raw_pdsi_path,
            pdsi_validation_path,
            calendar_path,
            calendar_validation_path,
            candidate_path,
            protocol_path,
        )
    except ValueError as error:
        assert "differs from full deterministic recomputation" in str(error)
    else:
        raise AssertionError("validator accepted a tampered aggregate metric")

print("U.S. competing-moisture predictive diagnostic tests passed")
