#!/usr/bin/env bash
set -euo pipefail

# Build and validate one historical crop/irrigation/period panel end to end.
#
# Usage:
#   run_historical_crop_chunk.sh PR.nc TAS.nc CALENDAR.nc GDHY_ROOT \
#     CROP IRRIGATION YEAR0 YEAR1 PERIOD_TAG [LATITUDE_CHUNK]
#
# PERIOD_TAG is an output namespace such as 2011_2019. Raw inputs are never
# copied, and all generated products remain below ignored data/interim paths.

if [[ $# -lt 9 || $# -gt 10 ]]; then
  echo "Usage: $0 PR.nc TAS.nc CALENDAR.nc GDHY_ROOT CROP IRRIGATION YEAR0 YEAR1 PERIOD_TAG [LATITUDE_CHUNK]" >&2
  exit 2
fi

pr=$1
tas=$2
calendar=$3
gdhy_root=$4
crop=$5
irrigation=$6
year0=$7
year1=$8
period_tag=$9
chunk=${10:-10}

project_root="$(cd "$(dirname "$0")/.." && pwd)"
python_bin="$project_root/.venv/bin/python"

for input_path in "$pr" "$tas" "$calendar"; do
  if [[ ! -f "$input_path" ]]; then
    echo "Missing required input file: $input_path" >&2
    exit 1
  fi
done
if [[ ! -d "$gdhy_root" ]]; then
  echo "Missing GDHY root directory: $gdhy_root" >&2
  exit 1
fi
if [[ ! -x "$python_bin" ]]; then
  echo "Missing project Python environment: $python_bin" >&2
  exit 1
fi
if [[ ! "$year0" =~ ^[0-9]{4}$ || ! "$year1" =~ ^[0-9]{4}$ ]]; then
  echo "YEAR0 and YEAR1 must be ordered four-digit years" >&2
  exit 2
fi
if (( year0 > year1 )); then
  echo "YEAR0 and YEAR1 must be ordered four-digit years" >&2
  exit 2
fi
if [[ ! "$period_tag" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "PERIOD_TAG may contain only letters, numbers, and underscores" >&2
  exit 2
fi
case "$crop" in
  mai|soy|ri1|ri2|swh|wwh) ;;
  *)
    echo "Unsupported crop code: $crop" >&2
    exit 2
    ;;
esac
case "$irrigation" in
  noirr|firr) ;;
  *)
    echo "IRRIGATION must be noirr or firr" >&2
    exit 2
    ;;
esac
if [[ ! "$chunk" =~ ^[0-9]+$ ]]; then
  echo "LATITUDE_CHUNK must be a positive integer divisor of 360" >&2
  exit 2
fi
if (( chunk <= 0 || 360 % chunk != 0 )); then
  echo "LATITUDE_CHUNK must be a positive integer divisor of 360" >&2
  exit 2
fi

season_parts="$project_root/data/interim/features_${period_tag}/${crop}_${irrigation}"
stage_parts="$project_root/data/interim/stage_features_${period_tag}/${crop}_${irrigation}"
base="$project_root/data/interim/${crop}_${irrigation}_${year0}_${year1}"
expected_partitions=$((360 / chunk))

"$project_root/scripts/build_feature_partitions.sh" \
  "$pr" "$tas" "$calendar" "$crop" "$irrigation" \
  "$year0" "$year1" "$season_parts" "$chunk"

"$project_root/scripts/build_stage_feature_partitions.sh" \
  "$pr" "$tas" "$calendar" "$crop" "$irrigation" \
  "$year0" "$year1" "$stage_parts" "$chunk"

"$python_bin" "$project_root/scripts/combine_feature_partitions.py" \
  --directory "$season_parts" \
  --out "${base}_features.parquet" \
  --expected-partitions "$expected_partitions"

"$python_bin" "$project_root/scripts/combine_stage_feature_partitions.py" \
  --directory "$stage_parts" \
  --out "${base}_stage_features.parquet" \
  --expected-partitions "$expected_partitions" \
  --expected-stages 3

"$python_bin" "$project_root/scripts/reconcile_stage_season_features.py" \
  --stages "${base}_stage_features.parquet" \
  --season "${base}_features.parquet" \
  --out "${base}_stage_season_reconciliation.json"

"$python_bin" "$project_root/scripts/join_gdhy_yields.py" \
  --features "${base}_features.parquet" \
  --gdhy-root "$gdhy_root" \
  --out "${base}_estimation_panel.parquet"

"$python_bin" "$project_root/scripts/build_stage_estimation_panel.py" \
  --stages "${base}_stage_features.parquet" \
  --season-panel "${base}_estimation_panel.parquet" \
  --out "${base}_stage_estimation_panel.parquet" \
  --expected-stages 3

"$python_bin" "$project_root/scripts/add_precipitation_pattern_features.py" \
  --panel "${base}_stage_estimation_panel.parquet" \
  --out "${base}_stage_pattern_panel.parquet" \
  --stages 3

echo "Completed validated historical chunk: ${base}_stage_pattern_panel.parquet"
