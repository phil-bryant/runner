#!/usr/bin/env bats
# Self-contained shell unit tests for the requirements-traceability lane wrapper
# (tests/t04_run_requirements_traceability_tests.sh). The wrapper is a thin
# delegating entrypoint; these tests assert its entrypoint contract and that it
# reaches the Python traceability CLI. Engine behavior is tested separately under
# tests/py/test_*.py.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  WRAPPER="${REPO_ROOT}/tests/t04_run_requirements_traceability_tests.sh"
  OTHER_DIR="$(cd "$(mktemp -d)" && pwd -P)"
}

teardown() {
  if [ -n "${OTHER_DIR:-}" ] && [ -d "${OTHER_DIR}" ]; then
    rmdir "${OTHER_DIR}" 2>/dev/null || true
  fi
}

@test "wrapper enforces secure umask and strict shell mode" {
  #R001-T01: entrypoint contract is umask 007 + strict shell mode.
  grep -Eq '^umask 007$' "$WRAPPER"
  grep -Eq '^set -euo pipefail$' "$WRAPPER"
}

@test "wrapper sources runbook_common and runs from any working directory" {
  #R005-T01: sources the shared contract and runs regardless of caller cwd.
  grep -q 'runbook_common.sh' "$WRAPPER"
  cd "$OTHER_DIR"
  run bash "$WRAPPER" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"Usage:"* ]]
}

@test "wrapper reaches the Python traceability CLI on PYTHONPATH" {
  #R010-T01: engine is importable; --help reaches the CLI usage banner.
  run bash "$WRAPPER" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"./tests/t04_run_requirements_traceability_tests.sh"* ]]
  [[ "$output" == *"Checks:"* ]]
}

@test "wrapper delegates to traceability.cli with argument passthrough" {
  #R020-T01: execs the Python CLI and forwards arguments unchanged.
  grep -Eq 'exec env' "$WRAPPER"
  grep -q 'python3 -m traceability.cli "\$@"' "$WRAPPER"
  run bash "$WRAPPER" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"Usage:"* ]]
}
