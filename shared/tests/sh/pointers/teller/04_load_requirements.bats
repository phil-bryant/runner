#!/usr/bin/env bats

src() {
  printf '%s' "${RUNBOOK_REPO_ROOT}/04_load_requirements.sh"
}

profile_path() {
  printf 'config/runbook/%s.env' "${RUNBOOK_REPO_NAME}"
}

@test "enables secure umask and strict shell mode" {
  #R001-T01
  run grep "umask 007" "$(src)"
  [ "$status" -eq 0 ]
  run grep "set -euo pipefail" "$(src)"
  [ "$status" -eq 0 ]
}

@test "derives script and runner paths from script location" {
  #R005-T01
  run grep "SCRIPT_DIR=" "$(src)"
  [ "$status" -eq 0 ]
  run grep "RUNNER_HOME=" "$(src)"
  [ "$status" -eq 0 ]
  run grep "runner" "$(src)"
  [ "$status" -eq 0 ]
}

@test "loads repo-specific runbook profile before delegation" {
  #R010-T01
  run grep "export RUNBOOK_REPO_ROOT" "$(src)"
  [ "$status" -eq 0 ]
  run grep "$(profile_path)" "$(src)"
  [ "$status" -eq 0 ]
}

@test "delegates to runner generic requirements loader" {
  #R015-T01
  run grep 'exec "${RUNNER_HOME}/src/scripts/load_requirements_generic.sh" "$@"' "$(src)"
  [ "$status" -eq 0 ]
}
