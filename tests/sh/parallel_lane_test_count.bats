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
