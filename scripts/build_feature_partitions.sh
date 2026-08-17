#!/usr/bin/env bash
set -euo pipefail

# Partition one crop/irrigation/calendar and climate-file interval by latitude.
# Usage: build_feature_partitions.sh PR.nc TAS.nc CALENDAR.nc CROP IRR YEAR0 YEAR1 OUTDIR [CHUNK]

if [[ $# -lt 8 || $# -gt 9 ]]; then
  echo "Usage: $0 PR.nc TAS.nc CALENDAR.nc CROP IRR YEAR0 YEAR1 OUTDIR [CHUNK]" >&2
  exit 2
fi
pr=$1; tas=$2; calendar=$3; crop=$4; irrigation=$5; year0=$6; year1=$7; outdir=$8; chunk=${9:-10}
root="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$outdir"
for ((start=0; start<360; start+=chunk)); do
  stop=$((start + chunk)); (( stop > 360 )) && stop=360
  out="$outdir/${crop}_${irrigation}_lat${start}_${stop}_${year0}_${year1}.parquet"
  [[ -f "$out" ]] && { echo "Present: $out"; continue; }
  "$root/.venv/bin/python" "$root/scripts/build_crop_year_features.py" \
    --precip "$pr" --temperature "$tas" --calendar "$calendar" --crop "$crop" --irrigation "$irrigation" \
    --year-start "$year0" --year-end "$year1" --lat-start "$start" --lat-stop "$stop" --out "$out"
done
