#!/bin/bash
umask 007

#R001: Enforce strict fail-fast behavior.
set -euo pipefail

#R005: Source the runbook contract and resolve repo root, venv python, and test paths.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/src/scripts/runbook_common.sh"
REPO_ROOT="$RUNBOOK_REPO_ROOT"
PYTHON_BIN="${REPO_ROOT}/${VENV_NAME}/bin/python"
TESTS_DIR="${REPO_ROOT}/tests"
E2E_TEST="${TESTS_DIR}/test_e2e_cases.py"

#R015: Require the workspace venv python.
if [ ! -x "$PYTHON_BIN" ]; then
  echo "${VENV_NAME} python is required but was not found at ${PYTHON_BIN}."
  echo "From the eggnest repo root: ./r02_create_venv.sh, activate, ./r03_load_requirements.sh"
  exit 1
fi

#R020: Optional record mode refreshes ai_recording.json against the REAL LLM.
#R020: Usage: ./r05_run_e2e_tests.sh --record [case_name ...]
if [ "${1:-}" = "--record" ]; then
  shift
  echo "▶ Recording AI selections via the real matchy AI ranker (online)..."
  cd "$REPO_ROOT"
  PYTHONPATH="$TESTS_DIR" "$PYTHON_BIN" -m harness.record "$@"
  exit 0
fi

#R025: Refuse to run when pytest is unavailable in the venv.
if ! "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1; then
  echo "pytest is required in ${VENV_NAME} but was not found."
  echo "Run ./r03_load_requirements.sh from the eggnest repo root."
  exit 1
fi

#R030: Run engine-level matching cases (deterministic, offline).
echo "▶ Running eggnest engine-level matching cases..."
cd "$REPO_ROOT"
PYTHONPATH="$TESTS_DIR" "$PYTHON_BIN" -m pytest "$E2E_TEST" "$@"
