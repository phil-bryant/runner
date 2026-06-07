#!/usr/bin/env bats

#R001: Shared helper resolves the target pointer path.
src() {
  printf '%s' "${RUNBOOK_REPO_ROOT}/tests/t03_run_e2e_tests.sh"
}

@test "centralizes umask/strict mode via the shared pointer shim" {
  #R001-T01: Verify the pointer sources pointer_shim.sh.
  run grep "pointer_shim.sh" "$(src)"
  [ "$status" -eq 0 ]
}

@test "resolves the shim from supported script-root paths" {
  #R005-T01: Verify the pointer resolves SCRIPT_DIR and sources pointer_shim.sh.
  run grep 'SCRIPT_DIR=' "$(src)"
  [ "$status" -eq 0 ]
  run grep "pointer_shim.sh" "$(src)"
  [ "$status" -eq 0 ]
}

@test "selects its runbook profile explicitly before delegation" {
  #R010-T01: Verify the pointer sets RUNBOOK_PROFILE to eggnest.
  run grep 'RUNBOOK_PROFILE="eggnest"' "$(src)"
  [ "$status" -eq 0 ]
}

@test "delegates to the mapped runner e2e golden" {
  #R015-T01: Verify the pointer calls delegate_golden "05_run_e2e_tests.sh" with "$@".
  run grep 'delegate_golden "05_run_e2e_tests.sh" "$@"' "$(src)"
  [ "$status" -eq 0 ]
}
