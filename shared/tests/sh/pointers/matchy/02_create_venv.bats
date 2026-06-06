#!/usr/bin/env bats

src() {
  printf '%s' "${RUNBOOK_REPO_ROOT}/02_create_venv.sh"
}

profile_path() {
  printf 'config/runbook/%s.env' "${RUNBOOK_REPO_NAME}"
}

@test "centralizes umask/strict mode via the shared pointer shim" {
  #R001-T01
  run grep "pointer_shim.sh" "$(src)"
  [ "$status" -eq 0 ]
}

@test "resolves the shim from the runner src/scripts tree" {
  #R005-T01
  run grep "runner/src/scripts" "$(src)"
  [ "$status" -eq 0 ]
}

@test "selects its runbook profile explicitly before delegation" {
  #R010-T01
  run grep "RUNBOOK_PROFILE=\"${RUNBOOK_REPO_NAME}\"" "$(src)"
  [ "$status" -eq 0 ]
}

@test "delegates to the mapped runner golden" {
  #R015-T01
  run grep 'delegate_golden "02_create_venv.sh" "$@"' "$(src)"
  [ "$status" -eq 0 ]
}
