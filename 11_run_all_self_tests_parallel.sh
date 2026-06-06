#!/usr/bin/env bash
# Thin pointer: selects the runner runbook profile and delegates to the runner golden via the shared shim.
#R001: Source the shared runbook shim (secure umask, strict mode, root resolution).
# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/./src/scripts" && pwd -P)/pointer_shim.sh"
#R005: Select the runner self-run runbook profile before delegation.
select_runbook_profile "runner"
#R010: Delegate to the parallel-orchestrator golden with argument passthrough.
delegate_golden "07_run_all_tests_parallel.sh" "$@"
