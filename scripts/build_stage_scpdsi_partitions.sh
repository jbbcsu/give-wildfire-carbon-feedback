#!/usr/bin/env bash
set -euo pipefail

# Usage: build_stage_scpdsi_partitions.sh SCPDSI CALENDAR CROP IRR YEAR0 YEAR1 OUTDIR THRESHOLD [CHUNK] [FRACTIONS]
if [[ $# -lt 8 || $# -gt 10 ]]; then
  echo "Usage: $0 SCPDSI.nc CALENDAR.nc CROP IRR YEAR0 YEAR1 OUTDIR THRESHOLD [CHUNK] [FRACTIONS]" >&2
  exit 2
fi
scpdsi=$1; calendar=$2; crop=$3; irrigation=$4; year0=$5; year1=$6; outdir=$7
threshold=$8; chunk=${9:-10}; fractions=${10:-0,0.3,0.7,1}
root="$(cd "$(dirname "$0")/.." && pwd)"
IFS=',' read -r -a stage_fractions_array <<< "$fractions"
expected_stages=$((${#stage_fractions_array[@]} - 1))
scpdsi_sha256=$(shasum -a 256 "$scpdsi" | awk '{print $1}')
calendar_sha256=$(shasum -a 256 "$calendar" | awk '{print $1}')
mkdir -p "$outdir"
for ((start=0; start<360; start+=chunk)); do
  stop=$((start + chunk))
  if (( stop > 360 )); then
    stop=360
  fi
  out="$outdir/${crop}_${irrigation}_stage_scpdsi_lat${start}_${stop}_${year0}_${year1}.parquet"
  manifest="${out}.manifest.json"
  if [[ -f "$out" ]] && "$root/.venv/bin/python" "$root/scripts/validate_stage_scpdsi_partition.py" \
      "$out" --manifest "$manifest" --threshold "$threshold" --expected-stages "$expected_stages" \
      --expected-crop "$crop" --expected-irrigation "$irrigation" \
      --expected-year-start "$year0" --expected-year-end "$year1" \
      --expected-lat-start "$start" --expected-lat-stop "$stop" \
      --expected-stage-fractions "$fractions" \
      --expected-scpdsi-sha256 "$scpdsi_sha256" \
      --expected-calendar-sha256 "$calendar_sha256" >/dev/null 2>&1; then
    echo "Present and valid: $out"
    continue
  fi
  "$root/.venv/bin/python" "$root/scripts/build_crop_stage_scpdsi_features.py" \
    --scpdsi "$scpdsi" --calendar "$calendar" --crop "$crop" --irrigation "$irrigation" \
    --year-start "$year0" --year-end "$year1" --lat-start "$start" --lat-stop "$stop" \
    --threshold "$threshold" --stage-fractions "$fractions" --out "$out" \
    --manifest-out "$manifest" --scpdsi-sha256 "$scpdsi_sha256" \
    --calendar-sha256 "$calendar_sha256"
done
