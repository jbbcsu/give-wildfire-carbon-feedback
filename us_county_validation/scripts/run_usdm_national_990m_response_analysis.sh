#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

PY=./.venv/bin/python
MEASURE=scripts/run_command_with_resource_receipt.py
PARTITIONS=data/interim/us_county/usdm_national_990m_state_partitions
EXPOSURE=data/interim/us_county/usdm_agricultural_exposure_990m_national.parquet
YIELDS=data/interim/us_county/nass_national_all_practice_panel_1981_2019.parquet
CLASSIFIER=data/interim/us_county/nass_kuwayama_all_cropland_irrigation_classifier.csv
WEATHER=data/interim/us_county/usdm_aprsep_weather_controls_2001_2013.parquet

$PY us_county_validation/scripts/merge_usdm_national_990m_state_partitions.py \
  --partition-dir "$PARTITIONS" --county-inventory "$CLASSIFIER" \
  --out "$EXPOSURE" \
  --audit-out data/provenance/usdm_national_990m_merged_validation_20260923.json

for basis in cultivated broad; do
  if [[ "$basis" == cultivated ]]; then
    response_config=config/usdm_kuwayama_agricultural_area_cultivated_990m_v1.toml
    weather_config=config/usdm_kuwayama_agricultural_area_cultivated_990m_weather_v1.toml
  else
    response_config=config/usdm_kuwayama_agricultural_area_broad_990m_v1.toml
    weather_config=config/usdm_kuwayama_agricultural_area_broad_990m_weather_v1.toml
  fi
  prefix=usdm_agricultural_area_990m_${basis}
  response=data/interim/us_county/${prefix}_response.parquet
  drought_result=data/interim/us_county/${prefix}_drought_only_results.json
  weather_result=data/interim/us_county/${prefix}_weather_results.json
  robustness_result=data/interim/us_county/${prefix}_weather_robustness.json

  $PY us_county_validation/scripts/adapt_usdm_agricultural_exposures.py \
    --config "$response_config" --exposure "$EXPOSURE" --out "$response" \
    --audit-out data/provenance/${prefix}_adapter_20260923.json

  $PY "$MEASURE" --metrics-out data/interim/us_county/${prefix}_drought_only_resource.json -- \
    "$PY" us_county_validation/scripts/estimate_usdm_drought_only.py \
    --config "$response_config" --yields "$YIELDS" --classifier "$CLASSIFIER" \
    --exposures "$response" --out "$drought_result"
  $PY us_county_validation/scripts/validate_usdm_drought_only.py \
    --result "$drought_result" --yields "$YIELDS" --classifier "$CLASSIFIER" \
    --exposures "$response" --out data/provenance/${prefix}_drought_only_validation_20260923.json

  $PY "$MEASURE" --metrics-out data/interim/us_county/${prefix}_weather_resource.json -- \
    "$PY" us_county_validation/scripts/estimate_usdm_weather_hierarchy.py \
    --config "$weather_config" --yields "$YIELDS" --classifier "$CLASSIFIER" \
    --drought "$response" --weather "$WEATHER" --out "$weather_result"
  $PY us_county_validation/scripts/validate_usdm_weather_hierarchy.py \
    --result "$weather_result" --yields "$YIELDS" --classifier "$CLASSIFIER" \
    --drought "$response" --weather "$WEATHER" \
    --out data/provenance/${prefix}_weather_validation_20260923.json

  $PY "$MEASURE" --metrics-out data/interim/us_county/${prefix}_robustness_resource.json -- \
    "$PY" us_county_validation/scripts/estimate_usdm_weather_robustness.py \
    --config config/usdm_weather_robustness_v1.toml --base-result "$weather_result" \
    --yields "$YIELDS" --classifier "$CLASSIFIER" --drought "$response" \
    --weather "$WEATHER" --out "$robustness_result"
  $PY us_county_validation/scripts/validate_usdm_weather_robustness.py \
    --result "$robustness_result" --base-result "$weather_result" \
    --yields "$YIELDS" --classifier "$CLASSIFIER" --drought "$response" \
    --weather "$WEATHER" \
    --out data/provenance/${prefix}_robustness_validation_20260923.json
done

$PY us_county_validation/scripts/summarize_usdm_agricultural_area_results.py \
  --county-exposure data/interim/us_county/usdm_octsep_exposures_2001_2013.parquet \
  --county-drought-result data/interim/us_county/usdm_octsep_drought_only_results_20260922.json \
  --county-weather-result data/interim/us_county/usdm_octsep_weather_hierarchy_results_20260922.json \
  --cultivated-exposure data/interim/us_county/usdm_agricultural_area_990m_cultivated_response.parquet \
  --cultivated-drought-result data/interim/us_county/usdm_agricultural_area_990m_cultivated_drought_only_results.json \
  --cultivated-weather-result data/interim/us_county/usdm_agricultural_area_990m_cultivated_weather_results.json \
  --broad-exposure data/interim/us_county/usdm_agricultural_area_990m_broad_response.parquet \
  --broad-drought-result data/interim/us_county/usdm_agricultural_area_990m_broad_drought_only_results.json \
  --broad-weather-result data/interim/us_county/usdm_agricultural_area_990m_broad_weather_results.json \
  --cultivated-robustness data/interim/us_county/usdm_agricultural_area_990m_cultivated_weather_robustness.json \
  --broad-robustness data/interim/us_county/usdm_agricultural_area_990m_broad_weather_robustness.json \
  --rejected-3_96km-comparison data/provenance/usdm_agricultural_area_spatial_basis_comparison_20260922.json \
  --out data/provenance/usdm_agricultural_area_990m_spatial_basis_comparison_20260923.json

echo "National 990 m USDM response analysis completed"
