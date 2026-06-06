#!/usr/bin/env bats
# Self-contained static-inspection unit tests for src/scripts/security/run_dynamic_security_lane.sh.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/security/run_dynamic_security_lane.sh"
}

@test "dynamic lane is shell-parseable and defines a banner helper" {
  #R001-T01: Verify the lane defines a print_tool_header banner helper.
  run bash -n "$SRC"
  [ "$status" -eq 0 ]
  run grep -q '^print_tool_header() {' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane runs strict mode and resolves repo root" {
  #R005-T01: Verify strict-mode shell settings and security_init_repo_root invocation.
  run grep -q '^set -euo pipefail' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'security_init_repo_root "$SCRIPT_PATH"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane bootstraps an isolated security venv" {
  #R010-T01: Verify the lane creates an isolated security venv.
  run grep -q 'python3 -m venv "$SECURITY_VENV_DIR"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane validates configured DAST app script before launch" {
  #R012-T01: Verify the lane fails early when DAST_APP_SCRIPT does not exist.
  run grep -q 'DAST app script not found' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'resolved_dast_app_script' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane waits for a non-5xx readiness probe after health" {
  #R013-T01: Verify readiness gating waits for non-5xx endpoint responses before Schemathesis.
  run grep -q 'wait_for_http_non_5xx()' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'DAST_READY_PROBE_URL' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'Waiting for DAST readiness probe' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane defaults to DAST-on, SAST-off" {
  #R015-T01: Verify the RUN_DAST/RUN_SAST default toggles.
  run grep -q 'RUN_DAST="${RUN_DAST:-true}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'RUN_SAST="${RUN_SAST:-false}"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane prints completion markers with report path" {
  #R020-T01: Verify the lane prints completion markers with the report path.
  run grep -q 'Security checks completed. Reports: ${REPORT_DIR}' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'Dynamic Application Security Testing (DAST) checks completed.' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane captures baseline and registers a cleanup EXIT trap" {
  #R025-T01: Verify the lane captures a baseline and registers a cleanup EXIT trap.
  run grep -q 'dast_baseline.py' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'dast_cleanup.py' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'trap _cleanup_dast_state EXIT' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane parses ZAP summary and enforces threshold gate" {
  #R030-T01: Verify the lane parses the ZAP summary and enforces the configurable threshold gate.
  run grep -q 'zap-classification-summary.json' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'SECURITY_ZAP_FAIL_THRESHOLD' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'meet/exceed threshold' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane retries ZAP quick scan on proxy bind races" {
  #R031-T01: Verify ZAP quick scan retries on Address already in use proxy startup errors.
  run grep -q 'Address already in use' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'retrying quick scan on' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane treats Schemathesis findings as blocking by default" {
  #R035-T01: Verify Schemathesis findings are blocking by default.
  run grep -q 'Findings from Schemathesis are blocking by default' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'schemathesis_fail_on_findings' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane resolves a non-colliding Mailcart stub port" {
  #R040-T01: Verify the lane resolves a non-colliding Mailcart stub port when it matches the API.
  run grep -q '\[\[ "$mailcart_host" == "$base_host" \]\] && \[\[ "$mailcart_port" -eq "$base_port" \]\]' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'collide with API port' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane runs Schemathesis from the report directory" {
  #R045-T01: Verify the Schemathesis subprocess runs with the report directory as its working directory.
  run grep -q 'working_directory = Path(sys.argv\[2\])' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'cwd=working_directory,' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane redacts token-bearing Schemathesis artifacts" {
  #R050-T01: Verify token-bearing Schemathesis artifacts are redacted before persistence.
  run grep -q 'redact_secret_in_file "$schemathesis_raw_log"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'redact_secret_in_place "${report_dir_abs}/schemathesis-junit.xml"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "dynamic lane reinstalls the toolchain with hash-pinned requirements" {
  #R055-T01: Verify the toolchain reinstall uses --require-hashes.
  run grep -q -- '--require-hashes --force-reinstall -r "$SECURITY_REQUIREMENTS_FILE"' "$SRC"
  [ "$status" -eq 0 ]
}
