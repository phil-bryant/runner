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

@test "parallel orchestrator sums lane test counts into aggregate total" {
  run grep -F 'aggregate_test_count=0' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
  run grep -F 'aggregate_test_count=$((aggregate_test_count + lane_test_count))' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}

@test "parallel final PASS output includes aggregate bracketed tests" {
  run grep -F '✅ PASS: all parallel checks succeeded [${aggregate_test_count} tests] (${pass_count}/${total})' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}
