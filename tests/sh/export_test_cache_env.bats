#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/export_test_cache_env.sh (runner engine helper).

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/export_test_cache_env.sh"
  FIXTURE="$(mktemp -d)"
}

#R001: shard-3 function tag
teardown() {
  [ -n "${FIXTURE:-}" ] && [ -d "${FIXTURE}" ] && mv "${FIXTURE}" "${BATS_TEST_TMPDIR:-${TMPDIR:-/tmp}}/used.$$.$RANDOM" || true
}

@test "exports canonical cache locations under artifacts/cache" {
  #R001-T01: exports canonical cache locations under artifacts/cache
  run bash -c "source '${SRC}'; export_test_cache_env '${FIXTURE}'; printf '%s|%s|%s\n' \"\$CACHE_ROOT\" \"\$PYTHONPYCACHEPREFIX\" \"\$RUFF_CACHE_DIR\""
  [ "$status" -eq 0 ]
  [[ "$output" == *"${FIXTURE}/artifacts/cache"* ]]
  [[ "$output" == *"artifacts/cache/pycache"* ]]
  [[ "$output" == *"artifacts/cache/ruff"* ]]
}

@test "defaults Hypothesis storage under the cache root" {
  #R005-T01: defaults Hypothesis storage under the cache root
  run bash -c "source '${SRC}'; export_test_cache_env '${FIXTURE}'; printf '%s\n' \"\$HYPOTHESIS_STORAGE_DIRECTORY\""
  [ "$status" -eq 0 ]
  [[ "$output" == *"artifacts/cache/hypothesis"* ]]
  [ -d "${FIXTURE}/artifacts/cache/hypothesis" ]
}
