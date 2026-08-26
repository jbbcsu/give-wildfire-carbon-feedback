#!/usr/bin/env bash
set -euo pipefail

# Build the corrected aggregate-irrigation diagnostic inputs for one crop and
# period. This wrapper preserves one GDHY outcome per crop/grid/year, builds
# nonlinear weather terms within each irrigation regime before applying fixed
# MIRCA shares, runs the minimal coefficient-suppressing predictive audit, and
# validates (but does not fit) the broader precipitation-distribution basis.
#
# Usage:
#   run_irrigation_basis_chunk.sh NOIRR_PANEL FIRR_PANEL WEIGHTS \
#     CROP YEAR0 YEAR1 OUTPUT_STEM
#
# CROP is currently restricted to mai or soy because those are the only exact,
# production-eligible MIRCA-to-GDHY crop mappings. All generated products are
# below ignored data/interim or outputs paths and are SCC-ineligible.

if [[ $# -ne 7 ]]; then
  echo "Usage: $0 NOIRR_PANEL FIRR_PANEL WEIGHTS CROP YEAR0 YEAR1 OUTPUT_STEM" >&2
  exit 2
fi

noirr_panel=$1
firr_panel=$2
weights=$3
crop=$4
year0=$5
year1=$6
stem=$7

project_root="$(cd "$(dirname "$0")/.." && pwd)"
python_bin="$project_root/.venv/bin/python"

for input_path in "$noirr_panel" "$firr_panel" "$weights"; do
  if [[ ! -f "$input_path" ]]; then
    echo "Missing required input file: $input_path" >&2
    exit 1
  fi
done
if [[ ! -x "$python_bin" ]]; then
  echo "Missing project Python environment: $python_bin" >&2
  exit 1
fi
case "$crop" in
  mai|soy) ;;
  *)
    echo "CROP must be mai or soy until another season-specific MIRCA mapping passes" >&2
    exit 2
    ;;
esac
if [[ ! "$year0" =~ ^[0-9]{4}$ || ! "$year1" =~ ^[0-9]{4}$ ]] || (( year0 > year1 )); then
  echo "YEAR0 and YEAR1 must be ordered four-digit years" >&2
  exit 2
fi
if [[ ! "$stem" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "OUTPUT_STEM may contain only letters, numbers, and underscores" >&2
  exit 2
fi

interim="$project_root/data/interim/irrigation_basis"
output="$project_root/outputs/irrigation_basis"
mkdir -p "$interim" "$output"

minimal="$interim/${stem}_minimal.parquet"
minimal_audit="$interim/${stem}_minimal_allocation_audit.json"
minimal_validation="$interim/${stem}_minimal_validation.parquet"
minimal_evaluation="$output/${stem}_minimal_response_evaluation.json"
minimal_summary="$output/${stem}_minimal_response_summary.json"
distribution="$interim/${stem}_distribution_candidate.parquet"
distribution_audit="$interim/${stem}_distribution_candidate_allocation_audit.json"
distribution_validation="$output/${stem}_distribution_candidate_validation.json"

"$python_bin" "$project_root/scripts/allocate_irrigation_response_basis.py" \
  --panel "$noirr_panel" \
  --panel "$firr_panel" \
  --weights "$weights" \
  --basis-block seasonal \
  --basis-block stage1 \
  --basis-block stage2 \
  --basis-block stage3 \
  --expected-irrigation noirr \
  --expected-irrigation firr \
  --exclude-missing-weight-cells \
  --out "$minimal" \
  --audit-out "$minimal_audit"

"$python_bin" "$project_root/scripts/make_validation_folds.py" \
  --panel "$minimal" \
  --out "$minimal_validation" \
  --spatial-folds 5 \
  --block-degrees 5 \
  --temporal-holdout-years 2 \
  --extreme-quantile 0.95 \
  --seed precipitation-scc-v1

"$python_bin" "$project_root/scripts/evaluate_crop_response_models.py" \
  --panel "$minimal_validation" \
  --spec "$project_root/config/response_evaluation_spec.toml" \
  --input-basis-mode prebuilt_irrigation_weighted_basis \
  --out "$minimal_evaluation"

"$python_bin" "$project_root/scripts/validate_response_evaluation_audit.py" \
  --audit "$minimal_evaluation" \
  --spec "$project_root/config/response_evaluation_spec.toml" \
  --expected-crop "$crop" \
  --expected-year-start "$year0" \
  --expected-year-end "$year1" \
  --expected-input-basis-mode prebuilt_irrigation_weighted_basis \
  --summary-out "$minimal_summary"

"$python_bin" "$project_root/scripts/allocate_irrigation_distribution_basis.py" \
  --panel "$noirr_panel" \
  --panel "$firr_panel" \
  --weights "$weights" \
  --expected-irrigation noirr \
  --expected-irrigation firr \
  --stages 3 \
  --exclude-missing-weight-cells \
  --out "$distribution" \
  --audit-out "$distribution_audit"

"$python_bin" "$project_root/scripts/validate_irrigation_distribution_basis.py" \
  --panel "$distribution" \
  --allocation-audit "$distribution_audit" \
  --expected-crop "$crop" \
  --stages 3 \
  --out "$distribution_validation"

echo "Completed SCC-ineligible irrigation-basis diagnostics for $stem"
