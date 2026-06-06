#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/normalize_pytest_addopts.sh (runner engine helper).

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/normalize_pytest_addopts.sh"
}

@test "leaves PYTEST_ADDOPTS unchanged when no invalid --cache-dir flag is present" {
  #R001-T01: leaves PYTEST_ADDOPTS unchanged when no invalid --cache-dir flag is present
  run bash -c "export PYTEST_ADDOPTS='-q --maxfail=1'; source '${SRC}'; printf '%s\n' \"\$PYTEST_ADDOPTS\""
  [ "$status" -eq 0 ]
  [ "$output" = "-q --maxfail=1" ]
}

@test "strips invalid --cache-dir while preserving other addopts" {
  #R005-T01: strips invalid --cache-dir while preserving other addopts
  run bash -c "export PYTEST_ADDOPTS='-q --cache-dir=/tmp/bad --maxfail=1'; source '${SRC}'; printf '%s\n' \"\$PYTEST_ADDOPTS\""
  [ "$status" -eq 0 ]
  [[ "$output" != *"--cache-dir="* ]]
  [[ "$output" == *"-q"* ]]
  [[ "$output" == *"--maxfail=1"* ]]
}
