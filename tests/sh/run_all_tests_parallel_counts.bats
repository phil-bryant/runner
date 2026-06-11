#!/usr/bin/env bats

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  PARALLEL_SCRIPT="${REPO_ROOT}/07_run_all_tests_parallel.sh"
}

#R001: shard-3 function tag
@test "parallel orchestrator remains shell-parseable" {
  run bash -n "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}

#R001: shard-3 function tag
@test "parallel PASS output includes bracketed test counts" {
  run grep -F '✅ PASS: ${completed_script} [${lane_test_count} tests] (${elapsed}s)' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}

#R001: shard-3 function tag
@test "parallel orchestrator resolves lane test counts via helper script" {
  run grep -F 'parallel_lane_test_count.py' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
  run grep -F 'resolve_lane_test_count "$completed_script" "$log"' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}

#R001: shard-3 function tag
@test "parallel orchestrator sums lane test counts into aggregate total" {
  run grep -F 'aggregate_test_count=0' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
  run grep -F 'aggregate_test_count=$((aggregate_test_count + lane_test_count))' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}

#R001: shard-3 function tag
@test "parallel final PASS output includes aggregate bracketed tests" {
  run grep -F '✅ PASS: all parallel checks succeeded [${aggregate_test_count} tests] (${pass_count}/${total})' "$PARALLEL_SCRIPT"
  [ "$status" -eq 0 ]
}

#R001: shard-3 function tag
@test "ui lane runtime watchdog fails hung UI lane" {
  local tmp_repo
  tmp_repo="$(mktemp -d "${BATS_TEST_TMPDIR}/ui-timeout.XXXXXX")"
  mkdir -p "${tmp_repo}/tests"
  cat > "${tmp_repo}/tests/t11_run_macos_ui_regression_tests.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
sleep 5
EOF
  chmod +x "${tmp_repo}/tests/t11_run_macos_ui_regression_tests.sh"

  run env \
    RUNBOOK_REPO_ROOT="$tmp_repo" \
    RUN_LANE_ALLOWLIST="" \
    PARALLEL_UI_LOCK_WAIT_TIMEOUT_SECONDS=10 \
    PARALLEL_UI_LANE_RUNTIME_TIMEOUT_SECONDS=2 \
    UI_LANE_LOCK_DIR="${tmp_repo}/.parallel-ui-tests.lock" \
    "$PARALLEL_SCRIPT"
  [ "$status" -eq 1 ]
  [[ "$output" == *"reason=lane-timeout"* ]]
  run grep -F "Timed out after 2s while running t11_run_macos_ui_regression_tests.sh." "${tmp_repo}/artifacts/parallel/t11_run_macos_ui_regression_tests.log"
  [ "$status" -eq 0 ]
}

#R001: shard-3 function tag
@test "ui lock wait logs owner diagnostics" {
  local tmp_repo
  local lock_owner
  tmp_repo="$(mktemp -d "${BATS_TEST_TMPDIR}/ui-lock-wait.XXXXXX")"
  mkdir -p "${tmp_repo}/tests"
  cat > "${tmp_repo}/tests/t12_run_macos_ui_regression_tests.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "quick lane"
EOF
  chmod +x "${tmp_repo}/tests/t12_run_macos_ui_regression_tests.sh"
  mkdir -p "${tmp_repo}/.parallel-ui-tests.lock"
  sleep 30 &
  lock_owner="$!"
  printf '%s\n' "$lock_owner" > "${tmp_repo}/.parallel-ui-tests.lock/pid"

  run env \
    RUNBOOK_REPO_ROOT="$tmp_repo" \
    RUN_LANE_ALLOWLIST="" \
    PARALLEL_UI_LOCK_WAIT_TIMEOUT_SECONDS=2 \
    PARALLEL_UI_LANE_RUNTIME_TIMEOUT_SECONDS=30 \
    UI_LANE_LOCK_DIR="${tmp_repo}/.parallel-ui-tests.lock" \
    "$PARALLEL_SCRIPT"
  kill "$lock_owner" 2>/dev/null || true
  wait "$lock_owner" 2>/dev/null || true
  [ "$status" -eq 1 ]
  run grep -F "Waiting for macOS UI lane lock (owner pid" "${tmp_repo}/artifacts/parallel/t12_run_macos_ui_regression_tests.log"
  [ "$status" -eq 0 ]
}
