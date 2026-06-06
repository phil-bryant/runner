#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/runbook_common.sh (shared golden contract).

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/runbook_common.sh"
}

@test "exports RUNNER_HOME pointing at the runner tree root" {
  #R001-T01: Source the helper and verify RUNNER_HOME is exported and points at the runner tree root.
  run bash -c "unset RUNNER_HOME RUNBOOK_REPO_ROOT; source '${SRC}'; printf '%s' \"\$RUNNER_HOME\""
  [ "$status" -eq 0 ]
  [ "$output" = "$REPO_ROOT" ]
}

@test "defaults RUNBOOK_REPO_ROOT to RUNNER_HOME when unset" {
  #R005-T01: Source the helper with RUNBOOK_REPO_ROOT unset and verify it defaults to RUNNER_HOME.
  run bash -c "unset RUNNER_HOME RUNBOOK_REPO_ROOT; source '${SRC}'; [ \"\$RUNBOOK_REPO_ROOT\" = \"\$RUNNER_HOME\" ] && printf ok"
  [ "$status" -eq 0 ]
  [ "$output" = "ok" ]
}

@test "derives repo name and venv name by convention" {
  #R010-T01: Source the helper and verify RUNBOOK_REPO_NAME and VENV_NAME follow the repo/repo-venv convention.
  run bash -c "unset RUNNER_HOME RUNBOOK_REPO_ROOT RUNBOOK_REPO_NAME VENV_NAME; source '${SRC}'; printf '%s|%s' \"\$RUNBOOK_REPO_NAME\" \"\$VENV_NAME\""
  [ "$status" -eq 0 ]
  [ "$output" = "runner|runner-venv" ]
}

@test "defaults traceability requirement/test roots under the repo root" {
  #R012-T01: Source the helper and verify the traceability requirement/test roots resolve under the repo root.
  run bash -c "unset RUNNER_HOME RUNBOOK_REPO_ROOT TRACEABILITY_REQUIREMENTS_ROOTS TRACEABILITY_TEST_ROOTS; source '${SRC}'; printf '%s|%s' \"\$TRACEABILITY_REQUIREMENTS_ROOTS\" \"\$TRACEABILITY_TEST_ROOTS\""
  [ "$status" -eq 0 ]
  [ "$output" = "${REPO_ROOT}/requirements|${REPO_ROOT}/tests/sh" ]
}

@test "defaults SHELL_BATS_ROOTS to the traceability test roots" {
  #R013-T01: Source the helper and verify SHELL_BATS_ROOTS matches TRACEABILITY_TEST_ROOTS.
  run bash -c "unset RUNNER_HOME RUNBOOK_REPO_ROOT TRACEABILITY_TEST_ROOTS SHELL_BATS_ROOTS; source '${SRC}'; [ \"\$SHELL_BATS_ROOTS\" = \"\$TRACEABILITY_TEST_ROOTS\" ] && printf ok"
  [ "$status" -eq 0 ]
  [ "$output" = "ok" ]
}

@test "runbook_cd_repo changes into the repo root" {
  #R015-T01: Define runbook_cd_repo, invoke it, and verify the working directory becomes the repo root.
  run bash -c "unset RUNNER_HOME RUNBOOK_REPO_ROOT; source '${SRC}'; runbook_cd_repo; pwd -P"
  [ "$status" -eq 0 ]
  [ "$output" = "$(cd "$REPO_ROOT" && pwd -P)" ]
}

@test "status helpers use consistent prefixes and stream routing" {
  #R020-T01: Invoke the status helpers and verify their success/warning/error prefixes and stream routing.
  run bash -c "source '${SRC}'; rb_ok done; rb_warn careful"
  [ "$status" -eq 0 ]
  [[ "$output" == *"✅ done"* ]]
  [[ "$output" == *"⚠️  careful"* ]]
  run bash -c "source '${SRC}'; rb_err boom 2>/dev/null"
  [ -z "$output" ]
  run bash -c "source '${SRC}'; rb_err boom 2>&1 1>/dev/null"
  [[ "$output" == *"❌ boom"* ]]
}

@test "rb_ensure_brew_formula reports available command without installing" {
  #R025-T01: Call rb_ensure_brew_formula for an already-present command and verify it reports availability without installing.
  run bash -c "source '${SRC}'; rb_ensure_brew_formula bash bash"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Available on PATH"* ]]
}

@test "rb_install_brew_formulas treats an empty spec as a no-op" {
  #R030-T01: Call rb_install_brew_formulas with an empty spec and verify it returns success without action.
  run bash -c "source '${SRC}'; rb_install_brew_formulas ''"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "rb_repo_python falls back to PATH python3 when no venv exists" {
  #R035-T01: Call rb_repo_python with no venv present and verify it falls back to a PATH python3.
  run bash -c "unset RUNNER_HOME RUNBOOK_REPO_ROOT VENV_NAME; export RUNBOOK_REPO_ROOT='${BATS_TEST_TMPDIR}'; VENV_NAME=nonexistent-venv; source '${SRC}'; rb_repo_python"
  [ "$status" -eq 0 ]
  [[ "$output" == *"python3"* ]]
}

@test "rb_read_1psa_item honors the configurable timeout knob" {
  #R040-T01: Verify rb_read_1psa_item honors the RB_ONEPSA_TIMEOUT_SECONDS timeout knob.
  run grep -q 'timeout_seconds="${RB_ONEPSA_TIMEOUT_SECONDS:-12}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q "timeout=timeout_seconds" "$SRC"
  [ "$status" -eq 0 ]
}

@test "rb_read_1psa_item falls back to env var when 1psa is unavailable" {
  #R041-T01: With 1psa unavailable and a matching env var set, verify rb_read_1psa_item returns the env value.
  run bash -c "source '${SRC}'; PATH='' MY_SECRET_ITEM=fromenv rb_read_1psa_item MY_SECRET_ITEM"
  [ "$status" -eq 0 ]
  [ "$output" = "fromenv" ]
}

@test "rb_lookup_env_fallback resolves lowercase name from uppercased env var" {
  #R042-T01: Verify rb_lookup_env_fallback resolves a lowercase item name from its uppercased environment variable.
  run bash -c "source '${SRC}'; LOCALHOST_TOKEN=upper_value rb_lookup_env_fallback localhost_token"
  [ "$status" -eq 0 ]
  [ "$output" = "upper_value" ]
}
