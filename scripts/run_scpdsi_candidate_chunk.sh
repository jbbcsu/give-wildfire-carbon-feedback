#!/usr/bin/env bash
set -euo pipefail

# Build and fully validate one crop/period historical scPDSI candidate basis.
# CRU scPDSI remains a competing historical climatic-water-balance benchmark;
# this wrapper never fits a response or authorizes future, damage, or SCC use.
#
# Usage:
#   run_scpdsi_candidate_chunk.sh SCPDSI NOIRR_CAL FIRR_CAL NOIRR_PANEL \
#     FIRR_PANEL WEIGHTS CROP YEAR0 YEAR1 STEM [THRESHOLD] [LAT_CHUNK]

if [[ $# -lt 10 || $# -gt 12 ]]; then
  echo "Usage: $0 SCPDSI NOIRR_CAL FIRR_CAL NOIRR_PANEL FIRR_PANEL WEIGHTS CROP YEAR0 YEAR1 STEM [THRESHOLD] [LAT_CHUNK]" >&2
  exit 2
fi

scpdsi=$1
noirr_calendar=$2
firr_calendar=$3
noirr_panel=$4
firr_panel=$5
weights=$6
crop=$7
year0=$8
year1=$9
stem=${10}
threshold=${11:--2}
chunk=${12:-10}

project_root="$(cd "$(dirname "$0")/.." && pwd)"
python_bin="$project_root/.venv/bin/python"

for input_path in "$scpdsi" "$noirr_calendar" "$firr_calendar" "$noirr_panel" "$firr_panel" "$weights"; do
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
  echo "STEM may contain only letters, numbers, and underscores" >&2
  exit 2
fi
if [[ ! "$chunk" =~ ^[0-9]+$ ]] || (( chunk < 1 || chunk > 360 )); then
  echo "LAT_CHUNK must be an integer from 1 through 360" >&2
  exit 2
fi

expected_partitions=$(( (360 + chunk - 1) / chunk ))
drought_root="$project_root/data/interim/drought/scpdsi"
basis_root="$project_root/data/interim/irrigation_basis"
validation_root="$project_root/outputs/irrigation_basis"
noirr_parts="$drought_root/${stem}_noirr_parts"
firr_parts="$drought_root/${stem}_firr_parts"
noirr_drought="$drought_root/${stem}_noirr_stage_scpdsi.parquet"
firr_drought="$drought_root/${stem}_firr_stage_scpdsi.parquet"
noirr_drought_manifest="${noirr_drought}.manifest.json"
firr_drought_manifest="${firr_drought}.manifest.json"
candidate="$basis_root/${stem}_scpdsi_candidate.parquet"
audit="$basis_root/${stem}_scpdsi_candidate_allocation_audit.json"
validation="$validation_root/${stem}_scpdsi_candidate_validation.json"

mkdir -p "$drought_root" "$basis_root" "$validation_root"

"$project_root/scripts/build_stage_scpdsi_partitions.sh" \
  "$scpdsi" "$noirr_calendar" "$crop" noirr "$year0" "$year1" \
  "$noirr_parts" "$threshold" "$chunk"
"$project_root/scripts/build_stage_scpdsi_partitions.sh" \
  "$scpdsi" "$firr_calendar" "$crop" firr "$year0" "$year1" \
  "$firr_parts" "$threshold" "$chunk"

"$python_bin" "$project_root/scripts/combine_stage_scpdsi_partitions.py" \
  --directory "$noirr_parts" --out "$noirr_drought" \
  --manifest-out "$noirr_drought_manifest" \
  --expected-partitions "$expected_partitions" --expected-stages 3 --threshold "$threshold" \
  --scpdsi "$scpdsi" --calendar "$noirr_calendar" --crop "$crop" --irrigation noirr \
  --year-start "$year0" --year-end "$year1" --lat-start 0 --lat-stop 360
"$python_bin" "$project_root/scripts/combine_stage_scpdsi_partitions.py" \
  --directory "$firr_parts" --out "$firr_drought" \
  --manifest-out "$firr_drought_manifest" \
  --expected-partitions "$expected_partitions" --expected-stages 3 --threshold "$threshold" \
  --scpdsi "$scpdsi" --calendar "$firr_calendar" --crop "$crop" --irrigation firr \
  --year-start "$year0" --year-end "$year1" --lat-start 0 --lat-stop 360

"$python_bin" "$project_root/scripts/allocate_irrigation_scpdsi_basis.py" \
  --panel "$noirr_panel" --panel "$firr_panel" \
  --stage-scpdsi "$noirr_drought" --stage-scpdsi "$firr_drought" \
  --stage-scpdsi-manifest "$noirr_drought_manifest" \
  --stage-scpdsi-manifest "$firr_drought_manifest" \
  --raw-scpdsi "$scpdsi" --calendar "$noirr_calendar" --calendar "$firr_calendar" \
  --weights "$weights" --expected-irrigation noirr --expected-irrigation firr \
  --expected-crop "$crop" --expected-year-start "$year0" --expected-year-end "$year1" \
  --threshold "$threshold" --stages 3 \
  --exclude-missing-drought-cells --exclude-missing-weight-cells \
  --out "$candidate" --audit-out "$audit"

"$python_bin" "$project_root/scripts/validate_irrigation_scpdsi_basis.py" \
  --candidate "$candidate" --allocation-audit "$audit" \
  --panel "$noirr_panel" --panel "$firr_panel" \
  --stage-scpdsi "$noirr_drought" --stage-scpdsi "$firr_drought" \
  --stage-scpdsi-manifest "$noirr_drought_manifest" \
  --stage-scpdsi-manifest "$firr_drought_manifest" \
  --raw-scpdsi "$scpdsi" --calendar "$noirr_calendar" --calendar "$firr_calendar" \
  --weights "$weights" --expected-crop "$crop" \
  --expected-year-start "$year0" --expected-year-end "$year1" \
  --out "$validation"

echo "Completed validated historical-only scPDSI candidate basis for $stem"
