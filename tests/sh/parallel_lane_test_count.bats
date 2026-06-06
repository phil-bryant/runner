#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  HELPER="${REPO_ROOT}/src/scripts/parallel_lane_test_count.py"
  TEST_REPO="${BATS_TEST_TMPDIR}/repo"
  mkdir -p "${TEST_REPO}/artifacts/parallel"
}

run_count() {
  local lane_script="$1"
  local lane_log="$2"
  run python3 "$HELPER" \
    --lane-script "$lane_script" \
    --lane-log "$lane_log" \
    --repo-root "$TEST_REPO" \
    --report-dir "${TEST_REPO}/artifacts/parallel"
}

@test "traceability lane uses summary total count" {
  #R001-T01: Verify the traceability lane returns the total from a summary log line.
  log_file="${TEST_REPO}/artifacts/parallel/t04.log"
  cat > "$log_file" <<'EOF'
Traceability check for all requirements/**/*-requirements.md
Summary: total=7 pass=7 fail=0
✅ All traceability checks passed.
EOF

  run_count "t04_run_requirements_traceability_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "7" ]
}

@test "shell unit lane sums bats TAP plans" {
  #R005-T01: Verify the shell-unit lane sums multiple bats TAP plan counts.
  log_file="${TEST_REPO}/artifacts/parallel/t05.log"
  cat > "$log_file" <<'EOF'
1..2
ok 1 alpha
ok 2 beta
1..3
ok 1 gamma
ok 2 delta
ok 3 epsilon
EOF

  run_count "t05_run_shell_unit_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "5" ]
}

@test "python unit lane parses pytest passed summary" {
  #R010-T01: Verify the python-unit lane parses the pytest passed-summary count.
  log_file="${TEST_REPO}/artifacts/parallel/t06.log"
  cat > "$log_file" <<'EOF'
▶ Running Python unit tests (pytest)...
12 passed in 0.44s
EOF

  run_count "t06_run_python_unit_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "12" ]
}

@test "swift unit lane parses the last XCTest summary total" {
  #R012-T01: Verify the swift-unit lane parses the most recent XCTest summary total.
  log_file="${TEST_REPO}/artifacts/parallel/t08-swift.log"
  cat > "$log_file" <<'EOF'
Test Suite 'FeatureTests' passed at 2026-01-01 12:00:00.000.
	 Executed 2 tests, with 0 failures (0 unexpected) in 0.005 (0.006) seconds
Test Suite 'WidgetTests' passed at 2026-01-01 12:00:00.100.
	 Executed 3 tests, with 0 failures (0 unexpected) in 0.007 (0.008) seconds
Test Suite 'All tests' passed at 2026-01-01 12:00:00.200.
	 Executed 5 tests, with 0 failures (0 unexpected) in 0.012 (0.014) seconds
EOF

  run_count "t08_run_swift_unit_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "5" ]
}

@test "swift unit lane prefers Executed totals over trailing zero metadata" {
  #R012-T02: Verify trailing `Test run with 0 tests` metadata does not override real executed totals.
  log_file="${TEST_REPO}/artifacts/parallel/t08-swift-mixed.log"
  cat > "$log_file" <<'EOF'
Test Suite 'All tests' started at 2026-06-05 09:08:07.521.
Test Suite 'MyFeatureTests' passed at 2026-06-05 09:08:09.243.
	 Executed 174 tests, with 0 failures (0 unexpected) in 1.718 (1.722) seconds
Test Suite 'All tests' passed at 2026-06-05 09:08:09.244.
	 Executed 174 tests, with 0 failures (0 unexpected) in 1.720 (1.724) seconds
Test run with 0 tests in 0 suites passed after 0.001 seconds.
EOF

  run_count "t08_run_swift_unit_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "174" ]
}

@test "swift unit lane falls back to one when no summary exists" {
  #R030-T02: Verify an uncountable swift lane log still falls back to printing 1.
  log_file="${TEST_REPO}/artifacts/parallel/t08-swift-empty.log"
  cat > "$log_file" <<'EOF'
▶ Running Swift unit tests...
No XCTest summary emitted.
EOF

  run_count "t08_run_swift_unit_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]
}

@test "macOS UI regression lane parses scenario summary total" {
  #R018-T01: Verify the macOS UI regression lane reads the scenario count from the timing summary line.
  log_file="${TEST_REPO}/artifacts/parallel/t11-ui-summary.log"
  cat > "$log_file" <<'EOF'
⏱ t14 scenario 01 matchAndClassifyShellLoads: 265 ms
⏱ t14 scenario 02 searchFilter: 2560 ms
⏱ t14 scenarios total: 131434 ms over 32 scenarios; app launch: 4451 ms
EOF

  run_count "t11_run_macos_ui_regression_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "32" ]
}

@test "macOS UI regression lane falls back to selector line count" {
  #R018-T02: Verify scenario selector syntax in lane output expands to a unique selected-step count.
  log_file="${TEST_REPO}/artifacts/parallel/t11-ui-selector.log"
  cat > "$log_file" <<'EOF'
ℹ️  Using XCUITest profile 'smoke' with scenarios: 1-3,5,7-8
EOF

  run_count "t11_run_macos_ui_regression_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "6" ]
}

@test "macOS UI regression lane parses XCTest executed summary totals" {
  #R018-T04: Verify macOS UI regression output with XCTest summaries uses the executed test total.
  log_file="${TEST_REPO}/artifacts/parallel/t12-ui-xctest.log"
  cat > "$log_file" <<'EOF'
Test Suite 'MailcartUITests' passed at 2026-06-06 07:47:18.027.
	 Executed 7 tests, with 0 failures (0 unexpected) in 54.619 (54.624) seconds
Test Suite 'MailcartUITests.xctest' passed at 2026-06-06 07:47:18.028.
	 Executed 7 tests, with 0 failures (0 unexpected) in 54.619 (54.624) seconds
Test Suite 'All tests' passed at 2026-06-06 07:47:18.028.
	 Executed 7 tests, with 0 failures (0 unexpected) in 54.619 (54.625) seconds
EOF

  run_count "t12_run_macos_ui_regression_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "7" ]
}

@test "macOS UI regression lane falls back to one when unparseable" {
  #R030-T03: Verify macOS UI regression logs with no scenario hints still use the single-test fallback.
  log_file="${TEST_REPO}/artifacts/parallel/t11-ui-unparseable.log"
  cat > "$log_file" <<'EOF'
▶ Running macOS XCUITest smoke suite...
No scenario summary emitted.
EOF

  run_count "t11_run_macos_ui_regression_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]
}

@test "macOS UI regression lane uses steps artifact when log lacks selector" {
  #R018-T03: Verify the steps artifact selector is used when the lane log has no parsable scenario summary or selector line.
  log_file="${TEST_REPO}/artifacts/parallel/t14-ui-artifact.log"
  mkdir -p "${TEST_REPO}/artifacts/macos-ui-regression"
  printf '2-4,10\n' > "${TEST_REPO}/artifacts/macos-ui-regression/xcuitest-steps.env"
  cat > "$log_file" <<'EOF'
▶ Running macOS XCUITest smoke suite...
** TEST SUCCEEDED **
EOF

  run_count "t14_run_macos_ui_regression_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "4" ]
}

@test "fuzz lane reads property_test_count from summary artifact" {
  #R015-T01: Verify the fuzz lane reads property_test_count from its summary artifact.
  log_file="${TEST_REPO}/artifacts/parallel/t08.log"
  mkdir -p "${TEST_REPO}/artifacts/fuzz"
  cat > "${TEST_REPO}/artifacts/fuzz/fuzz-summary.json" <<'EOF'
{"property_test_count": 4}
EOF
  : > "$log_file"

  run_count "t08_run_fuzz_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "4" ]
}

@test "quality lane counts non-skipped sub-check reports" {
  #R020-T01: Verify the quality lane counts only non-skipped sub-check reports.
  log_file="${TEST_REPO}/artifacts/parallel/t00.log"
  report_dir="${TEST_REPO}/artifacts/quality/reports"
  mkdir -p "$report_dir"
  printf 'ok\n' > "${report_dir}/vulture.txt"
  printf 'ok\n' > "${report_dir}/radon.txt"
  printf 'skipped\n' > "${report_dir}/xenon.txt"
  printf 'ok\n' > "${report_dir}/periphery.txt"
  printf 'skipped\n' > "${report_dir}/lizard.txt"
  : > "$log_file"

  run_count "t00_run_code_quality_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "3" ]
}

@test "static security lane counts discovered tool artifacts from report path in log" {
  #R025-T01: Verify the static security lane counts discovered tool artifacts from the report path declared in the log.
  log_file="${TEST_REPO}/artifacts/parallel/t03.log"
  report_rel="./custom/security/reports"
  report_abs="${TEST_REPO}/custom/security/reports"
  mkdir -p "$report_abs"
  printf '{}\n' > "${report_abs}/semgrep.json"
  printf '{}\n' > "${report_abs}/pip-audit.json"
  printf '[]\n' > "${report_abs}/shellcheck.json"
  cat > "$log_file" <<EOF
✅ Security checks completed. Reports: ${report_rel}
EOF

  run_count "t03_run_static_security_tests.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "3" ]
}

@test "unknown lanes fall back to one test" {
  #R030-T01: Verify an unknown lane falls back to printing 1.
  log_file="${TEST_REPO}/artifacts/parallel/unknown.log"
  : > "$log_file"

  run_count "t99_unknown_lane.sh" "$log_file"
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]
}
