#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../src/scripts/runbook_common.sh"
REPO_ROOT="$RUNBOOK_REPO_ROOT"
#R001: Run from repository root regardless of caller cwd.
cd "$REPO_ROOT"

#R005: Execute only the Swift unit-test lane.
RUN_SHELL_TESTS=false \
RUN_PYTHON_TESTS=false \
RUN_SQL_TESTS=false \
RUN_SWIFT_TESTS=true \
RUN_MACOS_UI_REGRESSION_TESTS=false \
  "${RUNNER_HOME}/src/scripts/run_unit_test_lanes.sh"
