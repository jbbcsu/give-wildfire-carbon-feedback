#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

N="${1:-100}"
INCLUDE_STRESS="${2:-false}"
OUTPUT_DIR="${3:-output/wildfire_extension}"

julia --project=. wildfire_extension/run_wildfire_scc.jl "$N" "$INCLUDE_STRESS" "$OUTPUT_DIR"
