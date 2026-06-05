#!/usr/bin/env bats
# Unit tests for tests/t01_run_av_test.sh soft-pass and infection gating behavior.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  AV_SCRIPT="${REPO_ROOT}/tests/t01_run_av_test.sh"
  FAKE_BIN_DIR="${BATS_TEST_TMPDIR}/bin"
  FAKE_DB_DIR="${BATS_TEST_TMPDIR}/db"
  mkdir -p "$FAKE_BIN_DIR" "$FAKE_DB_DIR"
  touch "${FAKE_DB_DIR}/main.cvd"
  cat > "${FAKE_BIN_DIR}/clamscan" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
infected="${FAKE_CLAMSCAN_INFECTED:-0}"
errors="${FAKE_CLAMSCAN_ERRORS:-0}"
error_lines="${FAKE_CLAMSCAN_ERROR_LINES:-}"
echo "----------- SCAN SUMMARY -----------"
echo "Known viruses: 1"
echo "Scanned files: 12"
echo "Infected files: ${infected}"
echo "Total errors: ${errors}"
echo "Data scanned: 0.01 MB"
echo "Time: 0.01 sec"
if [[ -n "$error_lines" ]]; then
  OLD_IFS="$IFS"
  IFS='|'
  # shellcheck disable=SC2206
  parts=($error_lines)
  IFS="$OLD_IFS"
  for item in "${parts[@]}"; do
    echo "ERROR: ${item}"
  done
fi
exit "${FAKE_CLAMSCAN_EXIT:-0}"
EOF
  chmod +x "${FAKE_BIN_DIR}/clamscan"
}

run_av_script() {
  local report_dir="$1"
  shift
  PATH="${FAKE_BIN_DIR}:$PATH" \
  CLAMAV_DB_DIR="${FAKE_DB_DIR}" \
  SECURITY_REPORT_DIR="$report_dir" \
  CLAMAV_SCAN_TARGET="tests" \
  "$@" \
  "$AV_SCRIPT"
}

@test "soft-passes scan errors at or below threshold when infections are zero" {
  report_dir="${BATS_TEST_TMPDIR}/reports-soft-pass"
  run run_av_script "$report_dir" env \
    FAKE_CLAMSCAN_EXIT=2 \
    FAKE_CLAMSCAN_INFECTED=0 \
    FAKE_CLAMSCAN_ERRORS=2 \
    FAKE_CLAMSCAN_ERROR_LINES="fileA unreadable|fileB unreadable" \
    CLAMAV_MAX_SCAN_ERRORS=2 \
    AV_FAIL_ON_INFECTED=true

  [ "$status" -eq 0 ]
  [[ "$output" == *"ClamAV completed with scan errors: 2 (threshold=2)."* ]]
  [[ "$output" == *"ClamAV soft-pass"* ]]
  run python3 - <<'PY' "${report_dir}/clamav-summary.json"
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    payload = json.load(fh)

assert payload["exit_code"] == 2
assert payload["infected_files"] == 0
assert payload["total_errors"] == 2
assert payload["max_scan_errors"] == 2
PY
  [ "$status" -eq 0 ]
}

@test "fails when scan errors exceed threshold even with zero infections" {
  report_dir="${BATS_TEST_TMPDIR}/reports-threshold-fail"
  run run_av_script "$report_dir" env \
    FAKE_CLAMSCAN_EXIT=2 \
    FAKE_CLAMSCAN_INFECTED=0 \
    FAKE_CLAMSCAN_ERRORS=3 \
    FAKE_CLAMSCAN_ERROR_LINES="fileA unreadable|fileB unreadable|fileC unreadable" \
    CLAMAV_MAX_SCAN_ERRORS=2 \
    AV_FAIL_ON_INFECTED=true

  [ "$status" -eq 1 ]
  [[ "$output" == *"scan errors exceeded threshold (3 > 2)"* ]]
  run python3 - <<'PY' "${report_dir}/clamav-summary.json"
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    payload = json.load(fh)

assert payload["exit_code"] == 2
assert payload["infected_files"] == 0
assert payload["total_errors"] == 3
assert payload["max_scan_errors"] == 2
PY
  [ "$status" -eq 0 ]
}

@test "infection gate remains enforced when infected files are detected" {
  report_dir="${BATS_TEST_TMPDIR}/reports-infected"
  run run_av_script "$report_dir" env \
    FAKE_CLAMSCAN_EXIT=1 \
    FAKE_CLAMSCAN_INFECTED=1 \
    FAKE_CLAMSCAN_ERRORS=0 \
    CLAMAV_MAX_SCAN_ERRORS=5 \
    AV_FAIL_ON_INFECTED=true

  [ "$status" -eq 1 ]
  [[ "$output" == *"ClamAV detected infected files."* ]]
  [[ "$output" == *"Antivirus (AV) gate failed: infected files detected."* ]]
  run python3 - <<'PY' "${report_dir}/clamav-summary.json"
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    payload = json.load(fh)

assert payload["exit_code"] == 1
assert payload["infected_files"] == 1
assert payload["total_errors"] == 0
PY
  [ "$status" -eq 0 ]
}
