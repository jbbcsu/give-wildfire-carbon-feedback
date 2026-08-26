#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
COUNTIES="${PROJECT_ROOT}/data/raw/us_county/tigerline/tl_2019_us_county/tl_2019_us_county.shp"
NCLIM_DIR="${PROJECT_ROOT}/data/raw/us_county/nclimgrid_daily"
CDL_ARCHIVE="${PROJECT_ROOT}/data/raw/us_county/cdl/2017_30m_cdls.zip"
NASS_DIR="${PROJECT_ROOT}/data/raw/us_county/nass_api/irrigation_practice_screen/yield_practice"
INTERIM="${PROJECT_ROOT}/data/interim/us_county"
CALENDAR="${PROJECT_ROOT}/config/us_county_ne_1981_calendar_smoke.csv"
SCRIPT_DIR="${PROJECT_ROOT}/us_county_validation/scripts"

"${VENV_PYTHON}" "${SCRIPT_DIR}/prepare_nass_practice_pair_support.py" \
  --corn-irrigated "${NASS_DIR}/survey_corn_irrigated_yield_all_years.json" \
  --corn-non-irrigated "${NASS_DIR}/survey_corn_non_irrigated_yield_all_years.json" \
  --soy-irrigated "${NASS_DIR}/survey_soybeans_irrigated_yield_all_years.json" \
  --soy-non-irrigated "${NASS_DIR}/survey_soybeans_non_irrigated_yield_all_years.json" \
  --county-geoid 31039 --harvest-year 1981 \
  --out "${INTERIM}/cuming_ne_nass_practice_pair_1981.parquet"

"${VENV_PYTHON}" "${SCRIPT_DIR}/build_county_polygon_nclimgrid_weights.py" \
  --counties "${COUNTIES}" --county-geoid 31039 \
  --climate "${NCLIM_DIR}/ncdd-198101-grd-scaled.nc" \
  --out "${INTERIM}/cuming_ne_nclimgrid_polygon_weights.parquet" \
  --audit-out "${INTERIM}/cuming_ne_nclimgrid_polygon_weights_audit.json"

"${VENV_PYTHON}" "${SCRIPT_DIR}/build_cdl_nclimgrid_crop_weights.py" \
  --counties "${COUNTIES}" --county-geoid 31039 \
  --climate "${NCLIM_DIR}/ncdd-198101-grd-scaled.nc" \
  --cdl-archive "${CDL_ARCHIVE}" \
  --calendar-crops corn_grain soybeans \
  --mask-temporal-role retrospective_2017_mask_sensitivity \
  --out "${INTERIM}/cuming_ne_2017_cdl_nclimgrid_weights.parquet" \
  --audit-out "${INTERIM}/cuming_ne_2017_cdl_nclimgrid_weights_audit.json"

CLIMATE_FILES=(
  "${NCLIM_DIR}/ncdd-198105-grd-scaled.nc"
  "${NCLIM_DIR}/ncdd-198106-grd-scaled.nc"
  "${NCLIM_DIR}/ncdd-198107-grd-scaled.nc"
  "${NCLIM_DIR}/ncdd-198108-grd-scaled.nc"
  "${NCLIM_DIR}/ncdd-198109-grd-scaled.nc"
  "${NCLIM_DIR}/ncdd-198110-grd-scaled.nc"
)

"${VENV_PYTHON}" "${SCRIPT_DIR}/build_county_nclimgrid_feature_smoke.py" \
  --weights "${INTERIM}/cuming_ne_nclimgrid_polygon_weights.parquet" \
  --climate "${CLIMATE_FILES[@]}" \
  --calendar "${CALENDAR}" \
  --outcomes "${INTERIM}/cuming_ne_nass_practice_pair_1981.parquet" \
  --calendar-role fixed_primary --wet-day-mm 1 \
  --out "${INTERIM}/cuming_ne_1981_nass_nclimgrid_feature_smoke.parquet" \
  --audit-out "${INTERIM}/cuming_ne_1981_nass_nclimgrid_feature_smoke_audit.json"

"${VENV_PYTHON}" "${SCRIPT_DIR}/build_crop_weighted_nclimgrid_feature_smoke.py" \
  --weights "${INTERIM}/cuming_ne_2017_cdl_nclimgrid_weights.parquet" \
  --climate "${CLIMATE_FILES[@]}" \
  --calendar "${CALENDAR}" \
  --outcomes "${INTERIM}/cuming_ne_nass_practice_pair_1981.parquet" \
  --calendar-role fixed_primary --wet-day-mm 1 \
  --out "${INTERIM}/cuming_ne_1981_nass_nclimgrid_2017_cdl_sensitivity_smoke.parquet" \
  --audit-out "${INTERIM}/cuming_ne_1981_nass_nclimgrid_2017_cdl_sensitivity_smoke_audit.json"

"${VENV_PYTHON}" "${SCRIPT_DIR}/compare_spatial_feature_smokes.py" \
  --primary "${INTERIM}/cuming_ne_1981_nass_nclimgrid_feature_smoke.parquet" \
  --sensitivity "${INTERIM}/cuming_ne_1981_nass_nclimgrid_2017_cdl_sensitivity_smoke.parquet" \
  --out "${INTERIM}/cuming_ne_1981_spatial_feature_smoke_comparison.csv" \
  --audit-out "${INTERIM}/cuming_ne_1981_spatial_feature_smoke_comparison_audit.json"

echo "Cuming 1981 spatial construction smoke complete; no response estimated."
