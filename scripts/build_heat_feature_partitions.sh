#!/usr/bin/env bash
set -euo pipefail

# Usage: build_heat_feature_partitions.sh TASMAX CALENDAR CROP IRR YEAR0 YEAR1 OUTDIR THRESHOLDS [CHUNK]
if [[ $# -lt 8 || $# -gt 9 ]]; then
  echo "Usage: $0 TASMAX.nc CALENDAR.nc CROP IRR YEAR0 YEAR1 OUTDIR THRESHOLDS_CSV [CHUNK]" >&2
  exit 2
fi
tasmax=$1; calendar=$2; crop=$3; irrigation=$4; year0=$5; year1=$6; outdir=$7
thresholds_csv=$8; chunk=${9:-10}
root="$(cd "$(dirname "$0")/.." && pwd)"
IFS=',' read -r -a thresholds <<< "$thresholds_csv"
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
  out="$outdir/${crop}_${irrigation}_heat_lat${start}_${stop}_${year0}_${year1}.parquet"
  if [[ -f "$out" ]] && "$root/.venv/bin/python" "$root/scripts/validate_heat_partition.py" \
      "$out" "${threshold_args[@]}" >/dev/null 2>&1; then
    echo "Present and valid: $out"
    continue
  fi
  "$root/.venv/bin/python" "$root/scripts/build_crop_heat_features.py" \
    --tasmax "$tasmax" --calendar "$calendar" --crop "$crop" --irrigation "$irrigation" \
    --year-start "$year0" --year-end "$year1" --lat-start "$start" --lat-stop "$stop" \
    "${threshold_args[@]}" --out "$out"
done
