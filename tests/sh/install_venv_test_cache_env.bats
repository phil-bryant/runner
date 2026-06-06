#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/install_venv_test_cache_env.sh (runner engine helper).

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/install_venv_test_cache_env.sh"
  FIXTURE="$(mktemp -d)"
}

@test "appends the teller cache marker exactly once across repeated installs" {
  #R001-T01: appends the teller cache marker exactly once across repeated installs
  mkdir -p "${FIXTURE}/venv/bin"
  : > "${FIXTURE}/venv/bin/activate"
  run bash -c "source '${SRC}'; install_venv_test_cache_env '${FIXTURE}/venv'; install_venv_test_cache_env '${FIXTURE}/venv'"
  [ "$status" -eq 0 ]
  marker_count="$(grep -cF '# >>> teller test cache env >>>' "${FIXTURE}/venv/bin/activate")"
  [ "$marker_count" -eq 1 ]
}

@test "fails with a clear error when the activate script is missing" {
  #R005-T01: fails with a clear error when the activate script is missing
  mkdir -p "${FIXTURE}/venv/bin"
  run bash -c "source '${SRC}'; install_venv_test_cache_env '${FIXTURE}/venv'"
  [ "$status" -ne 0 ]
  [[ "$output" == *"activate script not found"* ]]
}
