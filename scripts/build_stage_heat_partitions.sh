#!/usr/bin/env bash
set -euo pipefail

# Usage: build_stage_heat_partitions.sh TASMAX CALENDAR CROP IRR YEAR0 YEAR1 OUTDIR THRESHOLDS [CHUNK] [FRACTIONS]
if [[ $# -lt 8 || $# -gt 10 ]]; then
  echo "Usage: $0 TASMAX.nc CALENDAR.nc CROP IRR YEAR0 YEAR1 OUTDIR THRESHOLDS_CSV [CHUNK] [FRACTIONS]" >&2
  exit 2
fi
tasmax=$1; calendar=$2; crop=$3; irrigation=$4; year0=$5; year1=$6; outdir=$7
thresholds_csv=$8; chunk=${9:-10}; fractions=${10:-0,0.3,0.7,1}
root="$(cd "$(dirname "$0")/.." && pwd)"
IFS=',' read -r -a thresholds <<< "$thresholds_csv"
IFS=',' read -r -a stage_fractions_array <<< "$fractions"
expected_stages=$((${#stage_fractions_array[@]} - 1))
if [[ ${#thresholds[@]} -eq 0 ]]; then
  echo "At least one heat threshold is required" >&2
  exit 2
fi
threshold_args=()
for threshold in "${thresholds[@]}"; do
  threshold_args+=(--threshold-c "$threshold")
done
mkdir -p "$outdir"
for ((start=0; start<360; start+=chunk)); do
  stop=$((start + chunk))
  if (( stop > 360 )); then
    stop=360
  fi
  out="$outdir/${crop}_${irrigation}_stage_heat_lat${start}_${stop}_${year0}_${year1}.parquet"
  if [[ -f "$out" ]] && "$root/.venv/bin/python" "$root/scripts/validate_stage_heat_partition.py" \
      "$out" "${threshold_args[@]}" --expected-stages "$expected_stages" >/dev/null 2>&1; then
    echo "Present and valid: $out"
    continue
  fi
  "$root/.venv/bin/python" "$root/scripts/build_crop_stage_heat_features.py" \
    --tasmax "$tasmax" --calendar "$calendar" --crop "$crop" --irrigation "$irrigation" \
    --year-start "$year0" --year-end "$year1" --lat-start "$start" --lat-stop "$stop" \
    --stage-fractions "$fractions" "${threshold_args[@]}" --out "$out"
done
