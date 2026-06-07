#!/usr/bin/env bats

#R001: Shared helper resolves the target pointer path.
src() {
  printf '%s' "${RUNBOOK_REPO_ROOT}/tests/t05_run_shell_unit_tests.sh"
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

@test "selects its runbook profile explicitly before delegation" {
  #R010-T01: Verify the pointer sets RUNBOOK_PROFILE to eggnest.
  run grep 'RUNBOOK_PROFILE="eggnest"' "$(src)"
  [ "$status" -eq 0 ]
}

@test "delegates to the mapped runner shell-unit golden" {
  #R015-T01: Verify the pointer calls delegate_golden "tests/t05_run_shell_unit_tests.sh" with "$@".
  run grep 'delegate_golden "tests/t05_run_shell_unit_tests.sh" "$@"' "$(src)"
  [ "$status" -eq 0 ]
}
