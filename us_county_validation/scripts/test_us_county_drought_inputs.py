#!/usr/bin/env python3
"""Synthetic failure tests for the isolated county PDSI/SPEI input contract."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from build_county_crop_calendar_drought_features import (  # noqa: E402
    build_features,
    load_contract,
    validate_calendar,
    validate_monthly,
)
from extract_nclimdiv_county_pdsi import extract_rows, load_county_inventory  # noqa: E402
from validate_competing_moisture_family_support import validate_support  # noqa: E402


def fixed_record(internal_county: str, year: int, values: list[float]) -> str:
    if len(values) != 12:
        raise ValueError("synthetic record needs twelve values")
    record = f"{internal_county}05{year:04d}" + "".join(f"{value:7.2f}" for value in values) + "   \n"
    assert len(record) == 99
    return record


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    # NOAA internal state code 25 means Nebraska, not Census STATEFP 25.
    # These exact 2012 Cuming values also match NOAA's county API NE-039.
    cuming_values = [-1.58, -1.27, -2.44, -2.50, -2.34, -3.11, -4.70, -5.03, -5.56, -5.22, -5.21, -4.84]
    bulk = root / "pdsi.txt"
    bulk.write_text(fixed_record("25039", 2012, cuming_values), encoding="ascii", newline="")
    extracted = extract_rows(bulk, 2012, 2012, ["31039"])
    assert extracted.county_geoid.unique().tolist() == ["31039"]
    assert extracted.state_alpha.unique().tolist() == ["NE"]
    assert extracted.index_value.tolist() == cuming_values
    assert not extracted.irrigation_in_index.any()
    assert not extracted.response_estimation_authorized.any()
    assert not extracted.scc_authorized.any()
    try:
        extract_rows(bulk, 2012, 2012, ["25039"])
    except ValueError as error:
        assert "absent" in str(error)
    else:
        raise AssertionError("NOAA internal key was incorrectly accepted as a Census GEOID")
    try:
        extract_rows(bulk, 2012, 2012, [])
    except ValueError as error:
        assert "validated inventory" in str(error)
    else:
        raise AssertionError("PDSI extractor accepted an unbounded county request")

    inventory = pd.DataFrame({
        "county_geoid": ["31039"], "state": ["NE"],
        "boundary_source_id": ["us_census_tigerline_county_2019"],
        "boundary_vintage": ["2019"], "historical_status": ["stable"],
        "crosswalk_source_id": ["not_applicable"],
        "feature_construction_eligible": [True], "scc_authorized": [False],
    })
    inventory_path = root / "inventory.csv"
    inventory.to_csv(inventory_path, index=False)
    assert load_county_inventory(inventory_path).county_geoid.tolist() == ["31039"]
    unresolved = inventory.assign(historical_status="unresolved_change")
    unresolved.to_csv(root / "unresolved.csv", index=False)
    try:
        load_county_inventory(root / "unresolved.csv")
    except ValueError as error:
        assert "unresolved historical geography" in str(error)
    else:
        raise AssertionError("PDSI extractor accepted unresolved county geography")

    contract, family_contract = load_contract(
        PROJECT_ROOT / "config/us_county_drought_predictor_contract_v1.toml", "pdsi"
    )
    dates = pd.to_datetime(["2020-10-01", "2020-11-01", "2020-12-01", "2021-01-01", "2021-02-01"])
    monthly = pd.DataFrame({
        "county_geoid": ["31039"] * 5,
        "state_alpha": ["NE"] * 5,
        "date": dates,
        "year": dates.year,
        "month": dates.month,
        "index_value": [-1.0, -2.0, -3.0, -4.0, -1.0],
        "drought_family": ["pdsi"] * 5,
        "index_name": ["nclimdiv_county_pdsi"] * 5,
        "index_scale_months": [0] * 5,
        "index_scale_role": ["stateful_palmer_index_not_fixed_accumulation"] * 5,
        "index_distribution": ["palmer_water_balance"] * 5,
        "index_source_id": ["noaa_nclimdiv_county_pdsi_v1_0_0_20260806"] * 5,
        "index_calibration_start_year": [1931] * 5,
        "index_calibration_end_year": [1990] * 5,
        "index_calibration_role": ["publisher_fixed_independent_of_crop_outcomes"] * 5,
        "source_role": ["historical_county_benchmark_not_future_scc_input"] * 5,
        "irrigation_in_index": [False] * 5,
        "response_estimation_authorized": [False] * 5,
        "scc_authorized": [False] * 5,
    })
    calendar = pd.DataFrame({
        "state": ["NE"],
        "calendar_crop": ["corn_grain"],
        "harvest_year": [2021],
        "season_start": ["2021-01-15"],
        "season_end": ["2021-02-03"],
        "calendar_source_id": ["usda_nass_field_crops_usual_dates_2010"],
        "calendar_source_url": ["https://example.invalid/not-a-source"],
        "calendar_vintage": ["test"],
        "calendar_role": ["fixed_primary"],
        "boundary_rule": ["synthetic"],
        "stage_definition": ["equal_duration_0_30_70_100_engineering_proxy"],
        "feature_construction_eligible": [True],
        "scc_authorized": [False],
    })
    valid_monthly = validate_monthly(monthly, "pdsi", family_contract)
    valid_calendar = validate_calendar(calendar, contract["calendar"])
    features = build_features(valid_monthly, valid_calendar, "pdsi", -2.0, -3.0, 90, [0, 0.3, 0.7, 1])
    assert features.window_id.tolist() == ["preplant90", "season", "stage1", "stage2", "stage3"]
    preplant = features.loc[features.window_id.eq("preplant90")].iloc[0]
    assert preplant.window_days == 90
    assert np.isclose(preplant.index_day_weighted_mean, (-1 * 15 - 2 * 30 - 3 * 31 - 4 * 14) / 90)
    assert preplant.index_monthly_minimum == -4
    assert preplant.index_day_equivalents_at_or_below_moderate == 75
    assert preplant.index_day_equivalents_at_or_below_severe == 45
    stage3 = features.loc[features.window_id.eq("stage3")].iloc[0]
    assert stage3.window_days == 6
    assert np.isclose(stage3.index_day_weighted_mean, -2.5)
    assert stage3.index_day_equivalents_at_or_below_moderate == 3
    assert stage3.index_day_equivalents_at_or_below_severe == 3
    assert not features.response_estimation_authorized.any()
    assert not features.scc_authorized.any()

    contaminated = monthly.assign(precip_total_mm=1.0)
    try:
        validate_monthly(contaminated, "pdsi", family_contract)
    except ValueError as error:
        assert "direct weather" in str(error)
    else:
        raise AssertionError("PDSI family accepted a raw precipitation column")

    leaking = monthly.copy()
    leaking["response_estimation_authorized"] = True
    try:
        validate_monthly(leaking, "pdsi", family_contract)
    except ValueError as error:
        assert "cannot include irrigation or authorize" in str(error)
    else:
        raise AssertionError("drought input accepted an unauthorized estimation flag")

    incomplete = valid_monthly.loc[~valid_monthly.date.eq(pd.Timestamp("2020-12-01"))]
    try:
        build_features(incomplete, valid_calendar, "pdsi", -2.0, -3.0, 90, [0, 0.3, 0.7, 1])
    except ValueError as error:
        assert "incomplete" in str(error)
    else:
        raise AssertionError("crop-calendar drought features silently filled a missing month")

    wrong_calibration = monthly.copy()
    wrong_calibration["index_calibration_end_year"] = 2019
    try:
        validate_monthly(wrong_calibration, "pdsi", family_contract)
    except ValueError as error:
        assert "calibration period" in str(error)
    else:
        raise AssertionError("PDSI input accepted calibration drift")

    mixed_calibration = monthly.copy()
    mixed_calibration.loc[mixed_calibration.index[-1], "index_calibration_end_year"] = 1989
    try:
        validate_monthly(mixed_calibration, "pdsi", family_contract)
    except ValueError as error:
        assert "vary within" in str(error)
    else:
        raise AssertionError("PDSI input accepted row-varying calibration metadata")

    spei = monthly.copy()
    spei["drought_family"] = "spei"
    spei["index_name"] = "nclimgrid_monthly_spei"
    spei["index_scale_months"] = 3
    spei["index_scale_role"] = "three_month_accumulation"
    spei["index_distribution"] = "pearson_type_iii"
    spei["index_source_id"] = "noaa_nidis_nclimgrid_monthly_spei"
    spei["index_calibration_start_year"] = 1895
    spei["index_calibration_end_year"] = 2014
    _, spei_contract = load_contract(
        PROJECT_ROOT / "config/us_county_drought_predictor_contract_v1.toml", "spei"
    )
    assert validate_monthly(spei, "spei", spei_contract).index_scale_months.eq(3).all()

    keys = pd.DataFrame({
        "county_geoid": ["31039", "31039", "31041", "31041"],
        "outcome_crop": ["corn_grain"] * 4,
        "harvest_year": [2018, 2019, 2018, 2019],
        "irrigation_practice": ["non_irrigated"] * 4,
    })
    folds = keys.assign(
        spatial_fold=[0, 0, 1, 1],
        is_temporal_holdout=[False, True, False, True],
        is_climate_extreme=[False, True, False, False],
        validation_design="synthetic_common_outer_holdouts",
    )
    direct = keys.assign(feature_family="direct_weather", precip_total_mm=100.0, temperature_mean_c=20.0)
    pdsi_family = keys.assign(
        feature_family="pdsi", pdsi_stage_mean=-2.0,
        index_calibration_start_year=1931, index_calibration_end_year=1990,
        index_source_id="noaa_nclimdiv_county_pdsi_v1_0_0_20260806",
        irrigation_in_index=False, scc_authorized=False,
    )
    spei_family = keys.assign(
        feature_family="spei_3_pearson", spei_stage_mean=-1.0,
        index_calibration_start_year=1895, index_calibration_end_year=2014,
        index_source_id="noaa_nidis_nclimgrid_monthly_spei",
        index_scale_months=3, index_distribution="pearson_type_iii",
        irrigation_in_index=False, scc_authorized=False,
    )
    support_audit = validate_support(
        folds, {"direct_weather": direct, "pdsi": pdsi_family, "spei_3_pearson": spei_family}
    )
    assert support_audit["outcome_rows"] == 4
    assert support_audit["temporal_holdout_first_year"] == 2019
    assert set(support_audit["families"]) == {"direct_weather", "pdsi", "spei_3_pearson"}

    missing_support = spei_family.iloc[:-1]
    try:
        validate_support(folds, {"direct_weather": direct, "spei_3_pearson": missing_support})
    except ValueError as error:
        assert "common support" in str(error)
    else:
        raise AssertionError("family comparison accepted unequal outcome support")

    contaminated_pdsi = pdsi_family.assign(precip_total_mm=100.0)
    try:
        validate_support(folds, {"direct_weather": direct, "pdsi": contaminated_pdsi})
    except ValueError as error:
        assert "direct-weather columns" in str(error)
    else:
        raise AssertionError("common-support gate accepted raw weather in PDSI family")

    outcome_leak = pdsi_family.assign(yield_value=150.0)
    try:
        validate_support(folds, {"direct_weather": direct, "pdsi": outcome_leak})
    except ValueError as error:
        assert "outcome/leakage" in str(error)
    else:
        raise AssertionError("common-support gate accepted yield leakage in a predictor matrix")

    no_pdsi_predictor = pdsi_family.drop(columns="pdsi_stage_mean")
    try:
        validate_support(folds, {"direct_weather": direct, "pdsi": no_pdsi_predictor})
    except ValueError as error:
        assert "no recognized predictor" in str(error)
    else:
        raise AssertionError("common-support gate accepted a drought family with metadata only")

    late_calibration = spei_family.assign(index_calibration_end_year=2019)
    try:
        validate_support(folds, {"direct_weather": direct, "spei_3_pearson": late_calibration})
    except ValueError as error:
        assert "locked contract" in str(error)
    else:
        raise AssertionError("common-support gate accepted a nonpublisher SPEI calibration")

    early_keys = keys.assign(harvest_year=[2013, 2014, 2013, 2014])
    early_folds = early_keys.assign(
        spatial_fold=[0, 0, 1, 1], is_temporal_holdout=[False, True, False, True],
        is_climate_extreme=[False, True, False, False],
        validation_design="synthetic_calibration_overlap",
    )
    early_direct = direct.assign(harvest_year=[2013, 2014, 2013, 2014])
    early_spei = spei_family.assign(harvest_year=[2013, 2014, 2013, 2014])
    try:
        validate_support(early_folds, {"direct_weather": early_direct, "spei_3_pearson": early_spei})
    except ValueError as error:
        assert "not before temporal holdout" in str(error)
    else:
        raise AssertionError("common-support gate accepted a holdout overlapping fixed calibration")

    early_but_unlocked_calibration = pdsi_family.assign(index_calibration_start_year=1930)
    try:
        validate_support(folds, {"direct_weather": direct, "pdsi": early_but_unlocked_calibration})
    except ValueError as error:
        assert "locked contract" in str(error)
    else:
        raise AssertionError("common-support gate accepted a nonpublisher PDSI calibration")

    drifting_folds = folds.copy()
    drifting_folds.loc[1, "spatial_fold"] = 1
    try:
        validate_support(drifting_folds, {"direct_weather": direct, "pdsi": pdsi_family})
    except ValueError as error:
        assert "changes spatial fold" in str(error)
    else:
        raise AssertionError("common-support gate accepted a county that changes spatial fold")

print("U.S. county competing drought input tests passed")
