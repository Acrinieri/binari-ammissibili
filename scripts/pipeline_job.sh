#!/usr/bin/env bash
# Esegue la pipeline: genera l'input, chiama l'API e inoltra la risposta.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

RUNTIME_DIR="${RUNTIME_DIR:-${REPO_ROOT}/runtime}"
mkdir -p "${RUNTIME_DIR}"

INPUT_PATH="${INPUT_PATH:-${RUNTIME_DIR}/request.json}"
OUTPUT_PATH="${OUTPUT_PATH:-${RUNTIME_DIR}/response.json}"

TRAIN_CODE="${TRAIN_CODE:-12345}"
TRAIN_LENGTH="${TRAIN_LENGTH:-250}"
TRAIN_CATEGORY="${TRAIN_CATEGORY:-REG}"
PLANNED_TRACK="${PLANNED_TRACK:-}"
IS_PRM="${IS_PRM:-false}"

API_URL="${API_URL:-http://127.0.0.1:8000/tracks/suggestions}"
FORWARD_URL="${FORWARD_URL:-}"
TIMEOUT="${TIMEOUT:-10}"

GENERATE_ARGS=(
  --output "${INPUT_PATH}"
  --train-code "${TRAIN_CODE}"
  --train-length "${TRAIN_LENGTH}"
  --train-category "${TRAIN_CATEGORY}"
)

if [[ -n "${PLANNED_TRACK}" ]]; then
  GENERATE_ARGS+=(--planned-track "${PLANNED_TRACK}")
fi

if [[ "${IS_PRM}" == "true" ]]; then
  GENERATE_ARGS+=(--is-prm)
fi

python -m scripts.generate_input "${GENERATE_ARGS[@]}"

PIPELINE_ARGS=(
  --input "${INPUT_PATH}"
  --api-url "${API_URL}"
  --output-path "${OUTPUT_PATH}"
  --timeout "${TIMEOUT}"
)

if [[ -n "${FORWARD_URL}" ]]; then
  PIPELINE_ARGS+=(--forward-url "${FORWARD_URL}")
fi

python -m scripts.json_pipeline "${PIPELINE_ARGS[@]}"
