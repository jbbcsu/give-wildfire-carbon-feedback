#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

PY=./.venv/bin/python
MEASURE=scripts/run_command_with_resource_receipt.py
YIELDS=data/interim/us_county/nass_national_all_practice_panel_1981_2019.parquet
CLASSIFIER=data/interim/us_county/nass_kuwayama_all_cropland_irrigation_classifier.csv
WEATHER=data/interim/us_county/usdm_aprsep_weather_controls_2001_2013.parquet
GRID=data/interim/us_county/cdl_2008_agricultural_grid_classifier.parquet
GRID_AUDIT=data/interim/us_county/cdl_2008_agricultural_grid_classifier_audit.json
GRID_RESOURCE=data/interim/us_county/cdl_2008_agricultural_grid_classifier_resource.json
OVERLAY_GRID=data/interim/us_county/cdl_2008_agricultural_overlay_grid.npz
OVERLAY_GRID_AUDIT=data/interim/us_county/cdl_2008_agricultural_overlay_grid_audit.json
EXPOSURE=data/interim/us_county/usdm_agricultural_exposure_classifier.parquet
EXPOSURE_AUDIT=data/interim/us_county/usdm_agricultural_exposure_classifier_audit.json
EXPOSURE_RESOURCE=data/interim/us_county/usdm_agricultural_exposure_classifier_resource.json

$PY us_county_validation/scripts/validate_cdl_agricultural_grid.py \
  --grid "$GRID" --audit "$GRID_AUDIT" \
  --config config/cdl_2008_agricultural_masks_v1.toml \
  --resource "$GRID_RESOURCE" \
  --out data/provenance/us_cdl_agricultural_grid_classifier_validation_20260922.json

$PY us_county_validation/scripts/validate_usdm_weekly_shapefile_archive.py \
  --config config/usdm_agricultural_area_shapes_v1.toml \
  --shape-dir data/raw/us_county/usdm_shapefiles \
  --out data/provenance/usdm_weekly_shapefile_archive_validation_20260922.json

$PY "$MEASURE" \
  --metrics-out data/interim/us_county/cdl_2008_agricultural_overlay_grid_resource.json -- \
  "$PY" us_county_validation/scripts/prepare_usdm_agricultural_overlay_grid.py \
  --grid "$GRID" --out "$OVERLAY_GRID" --audit-out "$OVERLAY_GRID_AUDIT"

$PY us_county_validation/scripts/run_usdm_agricultural_exposure_batches.py \
  --config config/usdm_agricultural_area_shapes_v1.toml \
  --prepared-grid "$OVERLAY_GRID" --prepared-grid-audit "$OVERLAY_GRID_AUDIT" \
  --shape-dir data/raw/us_county/usdm_shapefiles \
  --batch-dir data/interim/us_county/usdm_agricultural_exposure_batches \
  --batch-size 10 --out "$EXPOSURE" --audit-out "$EXPOSURE_AUDIT" \
  --resource-out "$EXPOSURE_RESOURCE"

$PY us_county_validation/scripts/validate_usdm_agricultural_exposure.py \
  --exposure "$EXPOSURE" --audit "$EXPOSURE_AUDIT" \
  --resource "$EXPOSURE_RESOURCE" \
  --out data/provenance/us_usdm_agricultural_exposure_classifier_validation_20260922.json

for basis in cultivated broad; do
  if [[ "$basis" == cultivated ]]; then
    response_config=config/usdm_kuwayama_agricultural_area_cultivated_v1.toml
    weather_config=config/usdm_kuwayama_agricultural_area_cultivated_weather_v1.toml
  else
    response_config=config/usdm_kuwayama_agricultural_area_broad_v1.toml
    weather_config=config/usdm_kuwayama_agricultural_area_broad_weather_v1.toml
  fi
  response=data/interim/us_county/usdm_agricultural_area_${basis}_response.parquet
  drought_result=data/interim/us_county/usdm_agricultural_area_${basis}_drought_only_results.json
  weather_result=data/interim/us_county/usdm_agricultural_area_${basis}_weather_results.json
  robustness_result=data/interim/us_county/usdm_agricultural_area_${basis}_weather_robustness.json

  $PY us_county_validation/scripts/adapt_usdm_agricultural_exposures.py \
    --config "$response_config" --exposure "$EXPOSURE" --out "$response" \
    --audit-out data/provenance/usdm_agricultural_area_${basis}_adapter_20260922.json

  $PY "$MEASURE" \
    --metrics-out data/interim/us_county/usdm_agricultural_area_${basis}_drought_only_resource.json -- \
    "$PY" us_county_validation/scripts/estimate_usdm_drought_only.py \
    --config "$response_config" --yields "$YIELDS" --classifier "$CLASSIFIER" \
    --exposures "$response" --out "$drought_result"

  $PY us_county_validation/scripts/validate_usdm_drought_only.py \
    --result "$drought_result" --yields "$YIELDS" --classifier "$CLASSIFIER" \
    --exposures "$response" \
    --out data/provenance/usdm_agricultural_area_${basis}_drought_only_validation_20260922.json

  $PY "$MEASURE" \
    --metrics-out data/interim/us_county/usdm_agricultural_area_${basis}_weather_resource.json -- \
    "$PY" us_county_validation/scripts/estimate_usdm_weather_hierarchy.py \
    --config "$weather_config" --yields "$YIELDS" --classifier "$CLASSIFIER" \
    --drought "$response" --weather "$WEATHER" --out "$weather_result"

  $PY us_county_validation/scripts/validate_usdm_weather_hierarchy.py \
    --result "$weather_result" --yields "$YIELDS" --classifier "$CLASSIFIER" \
    --drought "$response" --weather "$WEATHER" \
    --out data/provenance/usdm_agricultural_area_${basis}_weather_validation_20260922.json

  $PY "$MEASURE" \
    --metrics-out data/interim/us_county/usdm_agricultural_area_${basis}_robustness_resource.json -- \
    "$PY" us_county_validation/scripts/estimate_usdm_weather_robustness.py \
    --config config/usdm_weather_robustness_v1.toml --base-result "$weather_result" \
    --yields "$YIELDS" --classifier "$CLASSIFIER" --drought "$response" \
    --weather "$WEATHER" --out "$robustness_result"

  $PY us_county_validation/scripts/validate_usdm_weather_robustness.py \
    --result "$robustness_result" --base-result "$weather_result" \
    --yields "$YIELDS" --classifier "$CLASSIFIER" --drought "$response" \
    --weather "$WEATHER" \
    --out data/provenance/usdm_agricultural_area_${basis}_robustness_validation_20260922.json
done

$PY us_county_validation/scripts/summarize_usdm_agricultural_area_results.py \
  --county-exposure data/interim/us_county/usdm_octsep_exposures_2001_2013.parquet \
  --county-drought-result data/interim/us_county/usdm_octsep_drought_only_results_20260922.json \
  --county-weather-result data/interim/us_county/usdm_octsep_weather_hierarchy_results_20260922.json \
  --cultivated-exposure data/interim/us_county/usdm_agricultural_area_cultivated_response.parquet \
  --cultivated-drought-result data/interim/us_county/usdm_agricultural_area_cultivated_drought_only_results.json \
  --cultivated-weather-result data/interim/us_county/usdm_agricultural_area_cultivated_weather_results.json \
  --broad-exposure data/interim/us_county/usdm_agricultural_area_broad_response.parquet \
  --broad-drought-result data/interim/us_county/usdm_agricultural_area_broad_drought_only_results.json \
  --broad-weather-result data/interim/us_county/usdm_agricultural_area_broad_weather_results.json \
  --cultivated-robustness data/interim/us_county/usdm_agricultural_area_cultivated_weather_robustness.json \
  --broad-robustness data/interim/us_county/usdm_agricultural_area_broad_weather_robustness.json \
  --out data/provenance/usdm_agricultural_area_spatial_basis_comparison_20260922.json

echo "USDM agricultural-area analysis completed"
