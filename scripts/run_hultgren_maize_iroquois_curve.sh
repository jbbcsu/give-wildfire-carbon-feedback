#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data/raw/hultgren_response/historical_git/dae5fe8d0d4a260328e4baa45b547368bd6790b3/corn_gmfd_v1_ready.dta"
ESTIMATE="$ROOT/data/raw/hultgren_response/3ccdffcd4e4ff6e55566ce76e2aac130ee86349a/corn_pbarkinks_200_100_250__.ster"
OUTPUT_DIR="$ROOT/data/interim/hultgren_maize_iroquois_curve_20260923"
STATA_BIN="${STATA_BIN:-/Applications/Stata/StataSE.app/Contents/MacOS/stata-se}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
EXPECTED_DATA_SHA256="06c2f0102580518a3eea88a6cd677af4636d40882452aa15b65ac7178cf9267a"

[[ -x "$STATA_BIN" ]] || { echo "Stata executable not found: $STATA_BIN" >&2; exit 2; }
[[ -x "$PYTHON_BIN" ]] || { echo "Python environment not found: $PYTHON_BIN" >&2; exit 2; }
[[ -f "$DATA" ]] || { echo "Historical source data not found: $DATA" >&2; exit 2; }
[[ -f "$ESTIMATE" ]] || { echo "Published estimate not found: $ESTIMATE" >&2; exit 2; }

actual_data_sha256="$(shasum -a 256 "$DATA" | awk '{print $1}')"
[[ "$actual_data_sha256" == "$EXPECTED_DATA_SHA256" ]] || {
  echo "Historical source hash mismatch: $actual_data_sha256" >&2
  exit 3
}

mkdir -p "$OUTPUT_DIR"
(
  cd "$OUTPUT_DIR"
  "$STATA_BIN" -b do "$ROOT/scripts/hultgren_export_iroquois_temperature_curve.do" \
    "$DATA" "$ESTIMATE" "$OUTPUT_DIR/stata_curve.csv"
)

PYTHONWARNINGS=error "$PYTHON_BIN" "$ROOT/scripts/validate_hultgren_maize_iroquois_curve.py"
