#!/usr/bin/env bash
# Runner self test pointer: runs the t02_run_dependency_freshness_tests golden lane against runner itself.
umask 007
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_HOME="$(cd "${SCRIPT_DIR}/.." && pwd)"
export RUNBOOK_REPO_ROOT="$RUNNER_HOME"
# shellcheck source=/dev/null
source "${RUNNER_HOME}/config/runbook/runner.env"
exec "${RUNNER_HOME}/tests/t02_run_dependency_freshness_tests.sh" "$@"
