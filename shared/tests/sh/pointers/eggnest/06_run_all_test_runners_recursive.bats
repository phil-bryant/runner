#!/usr/bin/env bats

#R001: shard-3 function tag
src() {
  printf '%s' "${RUNBOOK_REPO_ROOT}/06_run_all_test_runners_recursive.sh"
}

@test "centralizes umask/strict mode via the shared pointer shim" {
  #R001-T01: Verify the pointer sources pointer_shim.sh.
  run grep "pointer_shim.sh" "$(src)"
  [ "$status" -eq 0 ]
}

@test "resolves the shim from the runner src/scripts tree" {
  #R005-T01: Verify the pointer locates the shim under runner/src/scripts.
  run grep "runner/src/scripts" "$(src)"
  [ "$status" -eq 0 ]
}

@test "selects the runners meta-run profile explicitly before delegation" {
  #R010-T01: Verify the pointer calls select_runbook_profile "eggnest-runners".
  run grep 'select_runbook_profile "eggnest-runners"' "$(src)"
  [ "$status" -eq 0 ]
}

@test "delegates to the mapped runner golden" {
  #R015-T01: Verify the pointer calls delegate_golden "07_run_all_tests_parallel.sh" with "$@".
  run grep 'delegate_golden "07_run_all_tests_parallel.sh" "$@"' "$(src)"
  [ "$status" -eq 0 ]
}
