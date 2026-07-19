#!/usr/bin/env bash
set -euo pipefail

N_DRAWS="${1:-10000}"
OUTPUT_DIR="${2:-/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/output/wildfire_temperature_feedback_mcs_${N_DRAWS}}"
SEED="${3:-20260503}"
SCENARIOS="${4:-all}"

export JULIA_DEPOT_PATH="/Users/jbb/Dropbox/GIVE/.julia_depot_1_6"

/Users/jbb/Dropbox/GIVE/tools/julia-1.6.4/bin/julia \
  --project=/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo \
  /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/wildfire_extension/run_temperature_feedback_mcs.jl \
  "${N_DRAWS}" \
  "${OUTPUT_DIR}" \
  "${SEED}" \
  "${SCENARIOS}"
