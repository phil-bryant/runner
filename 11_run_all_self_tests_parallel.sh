#!/usr/bin/env bash
# Runner self-run pointer: runs runner's own applicable lanes (RUN_LANE_ALLOWLIST in runner.env) against runner itself.
umask 007
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export RUNBOOK_REPO_ROOT="$SCRIPT_DIR"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/config/runbook/runner.env"
exec "${SCRIPT_DIR}/07_run_all_tests_parallel.sh" "$@"
