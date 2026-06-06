#!/usr/bin/env bats
# Thin-pointer tests for 11_run_all_self_tests_parallel.sh: verify it sources the
# shared shim, selects the runner profile, and delegates to the orchestrator
# golden. Behavior of the golden itself is tested under its own requirements.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  POINTER="${REPO_ROOT}/11_run_all_self_tests_parallel.sh"
}

@test "pointer sources the shared runbook shim" {
  #R001-T01: pointer sources pointer_shim.sh before delegating
  grep -q 'pointer_shim.sh' "$POINTER"
}

@test "pointer selects the runner self-run profile" {
  #R005-T01: pointer selects the runner runbook profile explicitly
  grep -q 'select_runbook_profile "runner"' "$POINTER"
}

@test "pointer delegates to the orchestrator golden with passthrough" {
  #R010-T01: pointer delegates to 07_run_all_tests_parallel.sh with "$@"
  grep -q 'delegate_golden "07_run_all_tests_parallel.sh" "\$@"' "$POINTER"
}
