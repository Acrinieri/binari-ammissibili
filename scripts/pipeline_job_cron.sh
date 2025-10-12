#!/usr/bin/env bash
# Wrapper per cron/systemd: attiva il venv e invoca pipeline_job.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PATH="${REPO_ROOT}/.venv"

if [[ -d "${VENV_PATH}" ]]; then
  # shellcheck disable=SC1091
  source "${VENV_PATH}/bin/activate"
fi

exec "${REPO_ROOT}/scripts/pipeline_job.sh"
