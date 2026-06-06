#!/usr/bin/env bats
# Source-assertion tests for the 05_run_e2e_tests.sh runner golden. These assert
# the script's structure/behavior by inspecting the source so they run without a
# venv, pytest, or any online dependency.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/05_run_e2e_tests.sh"
}

@test "script enforces strict fail-fast shell mode" {
  #R001-T01: script enables set -euo pipefail for strict fail-fast behavior
  grep -q 'set -euo pipefail' "$SCRIPT"
}

@test "script sources runbook_common and resolves repo and venv paths" {
  #R005-T01: script sources runbook_common.sh and resolves repo/venv/test paths
  grep -q 'runbook_common.sh' "$SCRIPT"
  grep -q 'REPO_ROOT="\$RUNBOOK_REPO_ROOT"' "$SCRIPT"
  grep -q 'PYTHON_BIN=' "$SCRIPT"
  grep -q 'TESTS_DIR=' "$SCRIPT"
  grep -q 'E2E_TEST=' "$SCRIPT"
}

@test "script requires the workspace venv python to be executable" {
  #R015-T01: script exits with an error when the venv python is not executable
  grep -q 'if \[ ! -x "\$PYTHON_BIN" \]; then' "$SCRIPT"
  grep -q 'exit 1' "$SCRIPT"
}

@test "script supports an optional --record mode that exits after recording" {
  #R020-T01: --record mode invokes harness.record and exits without the pytest lane
  grep -q 'if \[ "\${1:-}" = "--record" \]; then' "$SCRIPT"
  grep -q 'harness.record' "$SCRIPT"
  grep -q 'exit 0' "$SCRIPT"
}

@test "script refuses to run when pytest is unavailable in the venv" {
  #R025-T01: script exits with an error when pytest is not available in the venv
  grep -q 'pytest --version' "$SCRIPT"
}

@test "script runs the e2e suite via pytest with passthrough args" {
  #R030-T01: script runs the e2e suite through pytest and forwards extra args
  grep -q '\-m pytest "\$E2E_TEST" "\$@"' "$SCRIPT"
}
