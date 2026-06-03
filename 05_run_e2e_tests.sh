#!/bin/bash
umask 007

#R001: Enforce strict fail-fast behavior.
set -euo pipefail

#R010: Resolve lane root from script location and use this lane's venv python.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#R010: Operate on the target repo (rNN_ pointer sets RUNBOOK_REPO_ROOT); default to self.
LANE_ROOT="${RUNBOOK_REPO_ROOT:-$SCRIPT_DIR}"
PYTHON_BIN="${LANE_ROOT}/e2e-venv/bin/python"

#R015: Require the lane venv python.
if [ ! -x "$PYTHON_BIN" ]; then
  echo "e2e-venv python is required but was not found at ${PYTHON_BIN}."
  echo "Run ./02_create_venv.sh, activate, then ./03_load_requirements.sh first."
  exit 1
fi

#R020: Optional record mode refreshes ai_recording.json against the REAL LLM.
#R020: Usage: ./05_run_e2e_tests.sh --record [case_name ...]
if [ "${1:-}" = "--record" ]; then
  shift
  echo "▶ Recording AI selections via the real matchy AI ranker (online)..."
  cd "$LANE_ROOT"
  PYTHONPATH="$LANE_ROOT" "$PYTHON_BIN" -m harness.record "$@"
  exit 0
fi

#R025: Refuse to run when pytest is unavailable in the venv.
if ! "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1; then
  echo "pytest is required in e2e-venv but was not found."
  echo "Run ./03_load_requirements.sh to install test dependencies."
  exit 1
fi

#R030: Run the engine-level end-to-end cases (deterministic, offline).
echo "▶ Running eggnest end-to-end matching cases..."
cd "$LANE_ROOT"
PYTHONPATH="$LANE_ROOT" "$PYTHON_BIN" -m pytest "$@"
