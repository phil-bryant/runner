#!/usr/bin/env bash
# Thin pointer: selects the runner runbook profile and delegates to the runner golden via the shared shim.
RUNBOOK_PROFILE="runner"
# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/./src/scripts" && pwd -P)/pointer_shim.sh"
delegate_golden "07_run_all_tests_parallel.sh" "$@"
