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

mkdir -p "${LOG_DIR}"

nohup "${REPO}/wildfire_extension/run_temperature_feedback_mcs.sh" \
  "${N_DRAWS}" \
  "${OUTPUT_DIR}" \
  "${SEED}" \
  "${SCENARIOS}" \
  > "${LOG_FILE}" 2>&1 &

PID="$!"
echo "${PID}" > "${PID_FILE}"

echo "Started wildfire temperature-feedback MCS."
echo "PID: ${PID}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Log file: ${LOG_FILE}"
echo "PID file: ${PID_FILE}"
