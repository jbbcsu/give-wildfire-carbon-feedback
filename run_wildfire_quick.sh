#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:-output/wildfire_quick}"
MODE="${2:-temperature}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="$(cd "$REPO_ROOT/.." && pwd)"

export JULIA_DEPOT_PATH="${JULIA_DEPOT_PATH:-$WORKSPACE_ROOT/.julia_depot_1_6}"
export DATADEPS_ALWAYS_ACCEPT="${DATADEPS_ALWAYS_ACCEPT:-true}"

cd "$REPO_ROOT"

if [[ -n "${JULIA_BIN:-}" ]]; then
    "$JULIA_BIN" --project=. wildfire_extension/run_wildfire_quick.jl "$OUTPUT_DIR" "$MODE"
elif [[ -x "$WORKSPACE_ROOT/tools/julia-1.6.4/bin/julia" ]]; then
    arch -x86_64 "$WORKSPACE_ROOT/tools/julia-1.6.4/bin/julia" --project=. wildfire_extension/run_wildfire_quick.jl "$OUTPUT_DIR" "$MODE"
else
    julia --project=. wildfire_extension/run_wildfire_quick.jl "$OUTPUT_DIR" "$MODE"
fi
