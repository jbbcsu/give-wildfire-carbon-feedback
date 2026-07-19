#!/usr/bin/env bash
set -euo pipefail

REPO="/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo"
N_DRAWS="${1:-10000}"
SEED="${2:-20260503}"
SCENARIOS="${3:-all}"
RUN_ID="${4:-$(date +%Y%m%d_%H%M%S)}"

OUTPUT_DIR="${REPO}/output/wildfire_temperature_feedback_mcs_${N_DRAWS}_full_${RUN_ID}"
LOG_DIR="${REPO}/output/wildfire_temperature_feedback_mcs_logs"
LOG_FILE="${LOG_DIR}/wildfire_temperature_feedback_mcs_${N_DRAWS}_${RUN_ID}.log"
PID_FILE="${LOG_DIR}/wildfire_temperature_feedback_mcs_${N_DRAWS}_${RUN_ID}.pid"
STATUS_FILE="${LOG_DIR}/wildfire_temperature_feedback_mcs_${N_DRAWS}_${RUN_ID}.status"

mkdir -p "${LOG_DIR}"
echo "$$" > "${PID_FILE}"

exec >> "${LOG_FILE}" 2>&1

echo "Started at $(date)"
echo "PID: $$"
echo "Repository: ${REPO}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Draws: ${N_DRAWS}"
echo "Seed: ${SEED}"
echo "Scenarios: ${SCENARIOS}"
echo "RUNNING" > "${STATUS_FILE}"

if "${REPO}/wildfire_extension/run_temperature_feedback_mcs.sh" \
  "${N_DRAWS}" \
  "${OUTPUT_DIR}" \
  "${SEED}" \
  "${SCENARIOS}"; then
  echo "COMPLETED" > "${STATUS_FILE}"
  echo "Completed at $(date)"
else
  status="$?"
  echo "FAILED ${status}" > "${STATUS_FILE}"
  echo "Failed with status ${status} at $(date)"
  exit "${status}"
fi
