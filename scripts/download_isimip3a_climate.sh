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

expected_size() {
  case "$1_$2" in
    pr_1981_1990) echo 2351177152 ;; pr_1991_2000) echo 2361459207 ;;
    pr_2001_2010) echo 2354163982 ;; pr_2011_2019) echo 2111921882 ;;
    tas_1981_1990) echo 2030156146 ;; tas_1991_2000) echo 2030602039 ;;
    tas_2001_2010) echo 2030296959 ;; tas_2011_2019) echo 1827956492 ;;
    tasmax_1981_1990) echo 2045681376 ;; tasmax_1991_2000) echo 2046372269 ;;
    tasmax_2001_2010) echo 2045915343 ;; tasmax_2011_2019) echo 1842014493 ;;
    tasmin_1981_1990) echo 2056386729 ;; tasmin_1991_2000) echo 2057309879 ;;
    tasmin_2001_2010) echo 2056480718 ;; tasmin_2011_2019) echo 1851441309 ;;
    *) echo "No expected size recorded for $1_$2" >&2; exit 2 ;;
  esac
}

for variable in "${variables[@]}"; do
  case "$variable" in pr|tas|tasmax|tasmin) ;; *) echo "Unsupported variable: $variable" >&2; exit 2;; esac
  for chunk in "${chunks[@]}"; do
    file="gswp3-w5e5_obsclim_${variable}_global_daily_${chunk}.nc"
    target="$dest/$file"
    expected="$(expected_size "$variable" "$chunk")"
    if [[ -f "$target" && "$(stat -f %z "$target")" == "$expected" ]]; then
      echo "Verified-size file already present: $file"
      grep -q "  $target$" "$dest/SHA512SUMS" 2>/dev/null || shasum -a 512 "$target" >> "$dest/SHA512SUMS"
      continue
    fi
    echo "Downloading $file"
    curl --location --continue-at - --fail --retry 3 --retry-delay 5 \
      "$base/$file" --output "$target"
    [[ "$(stat -f %z "$target")" == "$expected" ]] || { echo "Size check failed for $file" >&2; exit 1; }
    grep -q "  $target$" "$dest/SHA512SUMS" 2>/dev/null || shasum -a 512 "$target" >> "$dest/SHA512SUMS"
  done
done
