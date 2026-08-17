#!/usr/bin/env bash
set -euo pipefail

# Download resumable, Git-ignored ISIMIP3a GSWP3-W5E5 daily climate chunks.
# Usage: scripts/download_isimip3a_climate.sh pr tas [--all]
# By default it downloads 1981-2016-compatible chunks. --all additionally
# includes tasmax and tasmin for the final temperature-extreme specification.

root="$(cd "$(dirname "$0")/.." && pwd)"
dest="$root/data/raw/isimip3a_gswp3_w5e5_v1_3"
base="https://files.isimip.org/ISIMIP3a/InputData/climate/atmosphere/obsclim/global/daily/historical/GSWP3-W5E5"
chunks=(1981_1990 1991_2000 2001_2010 2011_2019)
variables=("$@")
if [[ " ${variables[*]} " == *" --all "* ]]; then
  variables=(pr tas tasmax tasmin)
fi
[[ ${#variables[@]} -gt 0 ]] || { echo "Provide one or more variables, e.g. pr tas" >&2; exit 2; }
mkdir -p "$dest"

for variable in "${variables[@]}"; do
  case "$variable" in pr|tas|tasmax|tasmin) ;; *) echo "Unsupported variable: $variable" >&2; exit 2;; esac
  for chunk in "${chunks[@]}"; do
    file="gswp3-w5e5_obsclim_${variable}_global_daily_${chunk}.nc"
    target="$dest/$file"
    echo "Downloading $file"
    curl --location --continue-at - --fail --retry 3 --retry-delay 5 \
      "$base/$file" --output "$target"
    shasum -a 512 "$target" >> "$dest/SHA512SUMS"
  done
done
