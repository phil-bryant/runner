#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  PARALLEL_SCRIPT="${REPO_ROOT}/07_run_all_tests_parallel.sh"
}

@test "parallel orchestrator remains shell-parseable" {
  run bash -n "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}

@test "parallel PASS output includes bracketed test counts" {
  run grep -F '✅ PASS: ${completed_script} [${lane_test_count} tests] (${elapsed}s)' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}

@test "parallel orchestrator resolves lane test counts via helper script" {
  run grep -F 'parallel_lane_test_count.py' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
  run grep -F 'resolve_lane_test_count "$completed_script" "$log"' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}
