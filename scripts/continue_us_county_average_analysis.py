#!/usr/bin/env python3
"""Fail-closed sequential calendar → features → audit → NASS → prediction route."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_bounded_job import run

PYTHON = ROOT / ".venv/bin/python"
WEATHER = ROOT / "data/interim/nclimgrid_county_averages_full_20260916/acquisition_summary.json"
CALENDAR = ROOT / "data/interim/us_county/nass_calendar_1981_2025_20260916"
FEATURES = ROOT / "data/interim/us_county/noaa_county_average_crop_year_features_20260916"
VALIDATION = ROOT / "data/interim/us_county/noaa_county_average_feature_validation_20260916"
PANEL = ROOT / "data/interim/us_county/noaa_county_average_nass_panel_20260916"
PREDICTION = ROOT / "data/interim/us_county/noaa_county_average_prediction_20260916"
PREDICTION_VALIDATION = ROOT / "data/interim/us_county/noaa_county_average_prediction_validation_20260916"
STATE_TREND = ROOT / "data/interim/us_county/noaa_county_average_state_trend_sensitivity_20260916"
STATE_TREND_VALIDATION = ROOT / "data/interim/us_county/noaa_county_average_state_trend_validation_20260916"
PDSI_PANEL = ROOT / "data/interim/us_county/noaa_county_average_pdsi_competitor_panel_20260916"
PDSI_PREDICTION = ROOT / "data/interim/us_county/noaa_county_average_pdsi_competitor_prediction_20260916"
PDSI_VALIDATION = ROOT / "data/interim/us_county/noaa_county_average_pdsi_competitor_validation_20260916"
IRRIGATION_SCREENS = ROOT / "data/interim/us_county/noaa_county_average_irrigation_screen_sensitivity_20260916"
IRRIGATION_VALIDATION = ROOT / "data/interim/us_county/noaa_county_average_irrigation_screen_validation_20260916"
WEATHER_COMPARISON = ROOT / "data/interim/us_county/noaa_county_weather_estimator_comparison_20260916"
WEATHER_COMPARISON_VALIDATION = ROOT / "data/interim/us_county/noaa_county_weather_estimator_validation_20260916"
PAIRED_ROUTE = ROOT / "data/interim/us_county/noaa_county_paired_practice_weather_route_20260916"
PAIRED_ROUTE_VALIDATION = ROOT / "data/interim/us_county/noaa_county_paired_practice_weather_route_validation_20260916"
JOBS = ROOT / "data/interim/us_county/noaa_county_average_pipeline_jobs_20260916"
FEATURE_PROTOCOL = ROOT / "US_COUNTY_AVERAGE_CROP_YEAR_FEATURE_PROTOCOL_20260916.md"
RESPONSE_PROTOCOL = ROOT / "US_COUNTY_AVERAGE_RESPONSE_PREANALYSIS_20260916.md"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def script(name: str) -> Path:
    return ROOT / "scripts" / name


def verify_calendar() -> None:
    result = json.loads((CALENDAR / "result.json").read_text())
    if (result["status"] != "nass_calendar_1981_2025_overlap_validated" or
        result["calendar_sha256"] != sha(CALENDAR / "nass_usual_date_calendars_1981_2025.csv") or
        result["protocol_sha256"] != sha(FEATURE_PROTOCOL) or
        result["code_sha256"] != sha(script("prepare_us_nass_calendar_2025.py"))):
        raise ValueError("calendar extension checkpoint invalid")


def verify_features() -> None:
    result = json.loads((FEATURES / "feature_summary.json").read_text())
    if (result["status"] != "complete" or result["completed_years"] != 45 or
        result["source_summary_sha256"] != sha(WEATHER) or
        result["calendar_sha256"] != sha(CALENDAR / "nass_usual_date_calendars_1981_2025.csv") or
        result["code_sha256"] != sha(script("continue_us_county_average_crop_year_features.py"))):
        raise ValueError("full NOAA feature summary checkpoint invalid")


def verify_validation() -> None:
    result = json.loads((VALIDATION / "result.json").read_text())
    if (result["status"] != "independent_county_average_crop_year_features_validated" or
        result["numeric_checks"] != 608 or
        result["code_sha256"] != sha(script("validate_us_county_average_crop_year_features.py"))):
        raise ValueError("independent weather feature validation checkpoint invalid")


def verify_panel() -> None:
    result = json.loads((PANEL / "result.json").read_text())
    if (result["status"] != "county_average_nass_panel_assembled_no_response" or
        result["panel_sha256"] != sha(PANEL / "panel.parquet") or
        result["preanalysis_protocol_sha256"] != sha(RESPONSE_PROTOCOL) or
        result["code_sha256"] != sha(script("assemble_us_county_average_nass_panel.py"))):
        raise ValueError("NASS/NOAA response panel checkpoint invalid")


def verify_prediction() -> None:
    result = json.loads((PREDICTION / "result.json").read_text())
    if (result["status"] != "us_county_average_predictive_benchmark_not_causal" or
        result["preanalysis_protocol_sha256"] != sha(RESPONSE_PROTOCOL) or
        result["panel_receipt_sha256"] != sha(PANEL / "result.json") or
        result["code_sha256"] != sha(script("estimate_us_county_average_terminal_prediction.py")) or
        result["climate_change_attribution_performed"] is not False or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("U.S. predictive benchmark checkpoint invalid")


def verify_prediction_validation() -> None:
    result = json.loads((PREDICTION_VALIDATION / "result.json").read_text())
    if (result["status"] != "independent_us_county_average_prediction_validated" or
        result["numeric_checks"] <= 0 or
        result["prediction_sha256"] != sha(PREDICTION / "result.json") or
        result["code_sha256"] != sha(script("validate_us_county_average_terminal_prediction.py")) or
        result["climate_change_attribution_performed"] is not False or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("independent U.S. prediction reconstruction invalid")


def verify_state_trend() -> None:
    result = json.loads((STATE_TREND / "result.json").read_text())
    protocol = ROOT / "US_COUNTY_AVERAGE_STATE_TREND_SENSITIVITY_20260916.md"
    if (result["status"] != "post_result_us_state_trend_sensitivity_not_causal" or
        result["panel_sha256"] != sha(PANEL / "panel.parquet") or
        result["primary_prediction_sha256"] != sha(PREDICTION / "result.json") or
        result["primary_validation_sha256"] != sha(PREDICTION_VALIDATION / "result.json") or
        result["protocol_sha256"] != sha(protocol) or
        result["code_sha256"] != sha(script("evaluate_us_county_average_state_trends.py")) or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("post-result state-trend sensitivity checkpoint invalid")


def verify_state_trend_validation() -> None:
    result = json.loads((STATE_TREND_VALIDATION / "result.json").read_text())
    if (result["status"] != "independent_post_result_state_trend_sensitivity_validated" or
        result["numeric_checks"] != 36 or
        result["source_result_sha256"] != sha(STATE_TREND / "result.json") or
        result["code_sha256"] != sha(script("validate_us_county_average_state_trends.py")) or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("independent post-result state-trend reconstruction invalid")


def verify_pdsi_panel() -> None:
    result = json.loads((PDSI_PANEL / "result.json").read_text())
    protocol = ROOT / "US_COUNTY_AVERAGE_PDSI_COMPETING_SENSITIVITY_20260916.md"
    if (result["status"] != "exact_support_us_pdsi_competitor_panel_built" or
        result["total_rows"] != 34288 or result["historical_rows"] != 30213 or
        result["terminal_rows"] != 4075 or result["historical_2019_parity_rows"] < 100 or
        result["historical_2019_max_abs_parity_error"] > 1e-10 or
        result["main_panel_sha256"] != sha(PANEL / "panel.parquet") or
        result["panel_sha256"] != sha(PDSI_PANEL / "panel_pdsi.parquet") or
        result["protocol_sha256"] != sha(protocol) or
        result["code_sha256"] != sha(script("assemble_us_county_average_pdsi_competitor.py")) or
        result["climate_attribution_or_scc"] is not False):
        raise ValueError("exact-support PDSI comparison panel checkpoint invalid")


def verify_pdsi_prediction() -> None:
    result = json.loads((PDSI_PREDICTION / "result.json").read_text())
    protocol = ROOT / "US_COUNTY_AVERAGE_PDSI_COMPETING_SENSITIVITY_20260916.md"
    if (result["status"] != "post_result_pdsi_competing_prediction_not_causal" or
        result["pdsi_panel_sha256"] != sha(PDSI_PANEL / "panel_pdsi.parquet") or
        result["pdsi_panel_receipt_sha256"] != sha(PDSI_PANEL / "result.json") or
        result["primary_result_sha256"] != sha(PREDICTION / "result.json") or
        result["state_trend_result_sha256"] != sha(STATE_TREND / "result.json") or
        result["protocol_sha256"] != sha(protocol) or
        result["code_sha256"] != sha(script("evaluate_us_county_average_pdsi_competitor.py")) or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("exact-support post-result PDSI prediction checkpoint invalid")


def verify_pdsi_validation() -> None:
    result = json.loads((PDSI_VALIDATION / "result.json").read_text())
    if (result["status"] != "independent_post_result_pdsi_competitor_validated" or
        result["numeric_checks"] != 96 or
        result["source_result_sha256"] != sha(PDSI_PREDICTION / "result.json") or
        result["code_sha256"] != sha(script("validate_us_county_average_pdsi_competitor.py")) or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("independent post-result PDSI score validation invalid")


def verify_irrigation_screens() -> None:
    result = json.loads((IRRIGATION_SCREENS / "result.json").read_text())
    protocol = ROOT / "US_COUNTY_AVERAGE_IRRIGATION_SCREEN_SENSITIVITY_20260916.md"
    if (result["status"] != "post_result_irrigation_screen_predictive_sensitivity_not_causal" or
        result["protocol_sha256"] != sha(protocol) or
        result["script_sha256"] != sha(script("evaluate_us_county_average_irrigation_screens.py")) or
        result["primary_panel_sha256"] != sha(PANEL / "panel.parquet") or
        result["primary_prediction_sha256"] != sha(PREDICTION / "result.json") or
        result["primary_2017_10pct_parity_passed"] is not True or
        set(result["screens"]) != {f"{year}_le_{threshold}pct"
                                    for year in (2017, 2022) for threshold in (10, 20, 30)} or
        result["climate_change_attribution_performed"] is not False or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("post-result irrigation-screen sensitivity checkpoint invalid")


def verify_irrigation_validation() -> None:
    result = json.loads((IRRIGATION_VALIDATION / "result.json").read_text())
    if (result["status"] != "independent_irrigation_screen_support_and_scores_validated" or
        result["numeric_and_support_checks"] != 498 or
        result["prediction_sha256"] != sha(IRRIGATION_SCREENS / "result.json") or
        result["code_sha256"] != sha(script("validate_us_county_average_irrigation_screens.py")) or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("independent irrigation-screen reconstruction invalid")


def verify_weather_comparison() -> None:
    result = json.loads((WEATHER_COMPARISON / "result.json").read_text())
    protocol = ROOT / "US_COUNTY_WEATHER_ESTIMATOR_COMPARISON_PROTOCOL_20260916.md"
    old = ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
    if (result["status"] != "source_only_exact_calendar_weather_estimator_comparison" or
        result["old_unique_weather_keys"] != 11861 or
        result["exact_calendar_matches"] != 11861 or
        result["old_source_sha256"] != sha(old) or
        result["new_feature_summary_sha256"] != sha(FEATURES / "feature_summary.json") or
        result["protocol_sha256"] != sha(protocol) or
        result["code_sha256"] != sha(script("compare_us_county_weather_estimators.py")) or
        result["yield_values_read"] is not False or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("source-only weather-estimator comparison invalid")


def verify_weather_comparison_validation() -> None:
    result = json.loads((WEATHER_COMPARISON_VALIDATION / "result.json").read_text())
    if (result["status"] != "independent_source_only_weather_estimator_comparison_validated" or
        result["numeric_and_support_checks"] != 191 or
        result["comparison_sha256"] != sha(WEATHER_COMPARISON / "result.json") or
        result["code_sha256"] != sha(script("validate_us_county_weather_estimators.py")) or
        result["yield_values_read"] is not False or
        result["economic_damage_or_scc_estimated"] is not False):
        raise ValueError("independent weather-estimator comparison invalid")


def verify_paired_route() -> None:
    result = json.loads((PAIRED_ROUTE / "result.json").read_text())
    old = ROOT / "data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet"
    protocol = ROOT / "US_PAIRED_PRACTICE_WEATHER_ROUTE_SENSITIVITY_20260916.md"
    if (result["status"] != "post_result_us_paired_practice_weather_route_association_sensitivity_not_causal" or
        result["paired_rows"] != 11857 or
        result["old_source_sha256"] != sha(old) or
        result["weather_comparison_sha256"] != sha(WEATHER_COMPARISON / "result.json") or
        result["weather_comparison_validation_sha256"] != sha(WEATHER_COMPARISON_VALIDATION / "result.json") or
        result["new_feature_summary_sha256"] != sha(FEATURES / "feature_summary.json") or
        result["protocol_sha256"] != sha(protocol) or
        result["code_sha256"] != sha(script("evaluate_us_paired_practice_weather_route.py")) or
        result["causal_claim_authorized"] is not False or
        result["scc_claim_authorized"] is not False):
        raise ValueError("paired historical weather-route sensitivity invalid")


def verify_paired_route_validation() -> None:
    result = json.loads((PAIRED_ROUTE_VALIDATION / "result.json").read_text())
    if (result["status"] != "independent_paired_weather_route_qr_cluster_validation_passed" or
        result["numeric_and_support_checks"] != 151 or
        result["maximum_absolute_disagreement"] > 1e-9 or
        result["sensitivity_result_sha256"] != sha(PAIRED_ROUTE / "result.json") or
        result["code_sha256"] != sha(script("validate_us_paired_practice_weather_route.py")) or
        result["causal_claim_authorized"] is not False or
        result["scc_claim_authorized"] is not False):
        raise ValueError("independent paired weather-route validation invalid")


def guarded_step(name: str, command: list[str], output: Path, max_output_mib: int, verify) -> None:
    if output.exists():
        verify()
        print(f"{name}: existing artifact reverified", flush=True)
        return
    receipt = JOBS / f"{name}.json"
    log = JOBS / f"{name}.log"
    if receipt.exists() or log.exists():
        raise ValueError(f"{name}: unresolved prior job evidence")
    result = run(command, receipt, log, max_mib=512, min_free_gib=130,
                 max_log_mib=1, write_paths=[output], max_new_disk_mib=max_output_mib)
    print(f"{name}: {result['status']} in {result['wall_seconds']:.1f}s; "
          f"peak RSS {result['sampled_peak_group_rss_bytes']/2**20:.1f}MiB", flush=True)
    if result["status"] != "completed":
        raise RuntimeError(f"{name}: inspect {log}")
    verify()


def main() -> None:
    weather = json.loads(WEATHER.read_text())
    if weather["status"] != "complete" or weather["completed_batches"] != 90 or weather["source_objects"] != 2700:
        raise ValueError("full NOAA source acquisition not complete")
    JOBS.mkdir(parents=True, exist_ok=True)
    guarded_step("calendar", [str(PYTHON), "-B", str(script("prepare_us_nass_calendar_2025.py")),
                              "--out-dir", str(CALENDAR)], CALENDAR, 16, verify_calendar)
    if (FEATURES / "feature_summary.json").exists():
        verify_features()
        print("features: existing complete summary reverified", flush=True)
    else:
        subprocess.run([str(PYTHON), "-B", str(script("continue_us_county_average_crop_year_features.py")),
                        "--max-new-years", "45"], check=True)
        verify_features()
    guarded_step("validation", [str(PYTHON), "-B", str(script("validate_us_county_average_crop_year_features.py")),
                                "--out-dir", str(VALIDATION)], VALIDATION, 4, verify_validation)
    guarded_step("panel", [str(PYTHON), "-B", str(script("assemble_us_county_average_nass_panel.py")),
                           "--out-dir", str(PANEL)], PANEL, 64, verify_panel)
    guarded_step("prediction", [str(PYTHON), "-B", str(script("estimate_us_county_average_terminal_prediction.py")),
                                "--out-dir", str(PREDICTION)], PREDICTION, 4, verify_prediction)
    guarded_step("prediction_validation", [str(PYTHON), "-B", str(script("validate_us_county_average_terminal_prediction.py")),
                                           "--out-dir", str(PREDICTION_VALIDATION)],
                 PREDICTION_VALIDATION, 4, verify_prediction_validation)
    guarded_step("state_trend_sensitivity", [str(PYTHON), "-B", str(script("evaluate_us_county_average_state_trends.py")),
                                             "--out-dir", str(STATE_TREND)],
                 STATE_TREND, 4, verify_state_trend)
    guarded_step("state_trend_validation", [str(PYTHON), "-B", str(script("validate_us_county_average_state_trends.py")),
                                            "--out-dir", str(STATE_TREND_VALIDATION)],
                 STATE_TREND_VALIDATION, 4, verify_state_trend_validation)
    guarded_step("pdsi_competitor_panel", [str(PYTHON), "-B", str(script("assemble_us_county_average_pdsi_competitor.py")),
                                           "--out-dir", str(PDSI_PANEL)],
                 PDSI_PANEL, 32, verify_pdsi_panel)
    guarded_step("pdsi_competitor_prediction", [str(PYTHON), "-B", str(script("evaluate_us_county_average_pdsi_competitor.py")),
                                                "--out-dir", str(PDSI_PREDICTION)],
                 PDSI_PREDICTION, 4, verify_pdsi_prediction)
    guarded_step("pdsi_competitor_validation", [str(PYTHON), "-B", str(script("validate_us_county_average_pdsi_competitor.py")),
                                                "--out-dir", str(PDSI_VALIDATION)],
                 PDSI_VALIDATION, 4, verify_pdsi_validation)
    guarded_step("irrigation_screen_sensitivity", [str(PYTHON), "-B", str(script("evaluate_us_county_average_irrigation_screens.py")),
                                                   "--out-dir", str(IRRIGATION_SCREENS)],
                 IRRIGATION_SCREENS, 16, verify_irrigation_screens)
    guarded_step("irrigation_screen_validation", [str(PYTHON), "-B", str(script("validate_us_county_average_irrigation_screens.py")),
                                                  "--out-dir", str(IRRIGATION_VALIDATION)],
                 IRRIGATION_VALIDATION, 4, verify_irrigation_validation)
    guarded_step("weather_estimator_comparison", [str(PYTHON), "-B", str(script("compare_us_county_weather_estimators.py")),
                                                  "--out-dir", str(WEATHER_COMPARISON)],
                 WEATHER_COMPARISON, 16, verify_weather_comparison)
    guarded_step("weather_estimator_validation", [str(PYTHON), "-B", str(script("validate_us_county_weather_estimators.py")),
                                                  "--out-dir", str(WEATHER_COMPARISON_VALIDATION)],
                 WEATHER_COMPARISON_VALIDATION, 4, verify_weather_comparison_validation)
    guarded_step("paired_practice_weather_route", [str(PYTHON), "-B", str(script("evaluate_us_paired_practice_weather_route.py")),
                                                  "--out-dir", str(PAIRED_ROUTE)],
                 PAIRED_ROUTE, 16, verify_paired_route)
    guarded_step("paired_practice_weather_route_validation", [str(PYTHON), "-B", str(script("validate_us_paired_practice_weather_route.py")),
                                                             "--out-dir", str(PAIRED_ROUTE_VALIDATION)],
                 PAIRED_ROUTE_VALIDATION, 4, verify_paired_route_validation)
    print(json.dumps({"status": "completed_source_feature_panel_prediction_chain",
                      "weather_source_sha256": sha(WEATHER),
                      "prediction_result_sha256": sha(PREDICTION / "result.json"),
                      "prediction_validation_sha256": sha(PREDICTION_VALIDATION / "result.json"),
                      "post_result_state_trend_sha256": sha(STATE_TREND / "result.json"),
                      "post_result_state_trend_validation_sha256": sha(STATE_TREND_VALIDATION / "result.json"),
                      "pdsi_competitor_panel_sha256": sha(PDSI_PANEL / "result.json"),
                      "pdsi_competitor_prediction_sha256": sha(PDSI_PREDICTION / "result.json"),
                      "pdsi_competitor_validation_sha256": sha(PDSI_VALIDATION / "result.json"),
                      "irrigation_screen_result_sha256": sha(IRRIGATION_SCREENS / "result.json"),
                      "irrigation_screen_validation_sha256": sha(IRRIGATION_VALIDATION / "result.json"),
                      "weather_estimator_comparison_sha256": sha(WEATHER_COMPARISON / "result.json"),
                      "weather_estimator_validation_sha256": sha(WEATHER_COMPARISON_VALIDATION / "result.json"),
                      "paired_practice_weather_route_sha256": sha(PAIRED_ROUTE / "result.json"),
                      "paired_practice_weather_route_validation_sha256": sha(PAIRED_ROUTE_VALIDATION / "result.json"),
                      "causal_or_scc_claim": False}), flush=True)


if __name__ == "__main__":
    main()
