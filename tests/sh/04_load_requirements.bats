#!/usr/bin/env bats
# Source-assertion unit tests for 04_load_requirements.sh, the runner self-run
# compatibility shim. These tests assert on the shim's source text rather than
# executing it, because exec'ing the canonical generic loader requires a venv/pip
# bootstrap that is out of scope for a unit test.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/04_load_requirements.sh"
}

@test "shim runs with secure umask and strict shell mode" {
  #R001-T01: shim sets umask 007 and enables set -euo pipefail
  grep -q '^umask 007' "$SCRIPT"
  grep -q '^set -euo pipefail' "$SCRIPT"
}

@test "shim resolves SCRIPT_DIR and defaults RUNBOOK_REPO_ROOT to it" {
  #R005-T01: shim derives SCRIPT_DIR from BASH_SOURCE and defaults RUNBOOK_REPO_ROOT
  grep -q 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE\[0\]}")" && pwd)"' "$SCRIPT"
  grep -q 'export RUNBOOK_REPO_ROOT="${RUNBOOK_REPO_ROOT:-\$SCRIPT_DIR}"' "$SCRIPT"
}

@test "shim guards profile sourcing on self-run conditions" {
  #R010-T01: shim guards on self-run, unloaded-profile, env-present before sourcing
  grep -q '\[ "\$RUNBOOK_REPO_ROOT" = "\$SCRIPT_DIR" \] && \[ -z "${RUNBOOK_PROFILE_LOADED:-}" \] && \[ -f "${SCRIPT_DIR}/config/runbook/runner.env" \]' "$SCRIPT"
  grep -q 'source "${SCRIPT_DIR}/config/runbook/runner.env"' "$SCRIPT"
}

@test "shim marks the runner profile as loaded after sourcing" {
  #R010-T02: shim exports RUNBOOK_PROFILE_LOADED=runner after sourcing the profile
  grep -q 'export RUNBOOK_PROFILE_LOADED="runner"' "$SCRIPT"
}

@test "shim execs the generic loader with argument passthrough" {
  #R015-T01: shim execs load_requirements_generic.sh passing "$@" through
  grep -q 'exec "${SCRIPT_DIR}/src/scripts/load_requirements_generic.sh" "\$@"' "$SCRIPT"
}
