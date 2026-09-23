#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data/raw/hultgren_response/historical_git/dae5fe8d0d4a260328e4baa45b547368bd6790b3/corn_gmfd_v1_ready.dta"
OUTPUT="$ROOT/data/interim/hultgren_historical_replication"
STATA_BIN="${STATA_BIN:-/Applications/Stata/StataSE.app/Contents/MacOS/stata-se}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
EXPECTED_SHA256="06c2f0102580518a3eea88a6cd677af4636d40882452aa15b65ac7178cf9267a"

[[ -x "$STATA_BIN" ]] || { echo "Stata executable not found: $STATA_BIN" >&2; exit 2; }
[[ -x "$PYTHON_BIN" ]] || { echo "Python environment not found: $PYTHON_BIN" >&2; exit 2; }
[[ -f "$DATA" ]] || { echo "Historical source data not found: $DATA" >&2; exit 2; }

actual_sha256="$(shasum -a 256 "$DATA" | awk '{print $1}')"
[[ "$actual_sha256" == "$EXPECTED_SHA256" ]] || {
  echo "Historical source hash mismatch: $actual_sha256" >&2
  exit 3
}

mkdir -p "$OUTPUT"
(
  cd "$OUTPUT"
  "$STATA_BIN" -b do "$ROOT/scripts/hultgren_reproduce_maize_historical.do" \
    "$DATA" "$OUTPUT/corn_replicated.ster" "$OUTPUT/corn_replicated.log"
  "$STATA_BIN" -b do "$ROOT/scripts/hultgren_export_maize_estimate_machine.do" \
    "$OUTPUT/corn_replicated.ster" "$OUTPUT/coefficients.csv" \
    "$OUTPUT/covariance.csv" "$OUTPUT/metadata.txt"
)

PYTHONWARNINGS=error "$PYTHON_BIN" "$ROOT/scripts/validate_hultgren_maize_historical_replication.py"
