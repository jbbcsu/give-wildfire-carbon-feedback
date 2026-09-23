#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

PY=./.venv/bin/python
SUMMARY=data/provenance/usdm_agricultural_area_990m_spatial_basis_comparison_20260923.json
MERGED=data/provenance/usdm_national_990m_merged_validation_20260923.json
INDEPENDENT=data/provenance/usdm_agricultural_area_990m_summary_independent_validation_20260923.json

validation_args=()
resource_args=()
for basis in cultivated broad; do
  for family in drought_only weather robustness; do
    validation_args+=(--component-validation "data/provenance/usdm_agricultural_area_990m_${basis}_${family}_validation_20260923.json")
    resource_args+=(--resource-receipt "data/interim/us_county/usdm_agricultural_area_990m_${basis}_${family}_resource.json")
  done
done

$PY us_county_validation/scripts/validate_usdm_national_990m_summary.py \
  --summary "$SUMMARY" \
  --merged-validation "$MERGED" \
  "${validation_args[@]}" \
  "${resource_args[@]}" \
  --out "$INDEPENDENT"

$PY us_county_validation/scripts/render_usdm_national_990m_results.py \
  --summary "$SUMMARY" \
  --merged-validation "$MERGED" \
  --independent-validation "$INDEPENDENT" \
  --out US_USDM_AGRICULTURAL_AREA_990M_RESULTS_20260923.md

echo "National 990 m USDM independent validation and result rendering completed"
