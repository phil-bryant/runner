#!/usr/bin/env bats
# Companion tests for 08_report_quality_trends.sh requirements traceability.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/08_report_quality_trends.sh"
}

@test "strict shell mode and target repo resolution" {
  #R001-T01: source declares strict shell mode
  grep -q 'set -euo pipefail' "$SCRIPT"
  #R001-T02: source honors RUNBOOK_REPO_ROOT override for the target repo
  grep -q 'SCRIPT_DIR="${RUNBOOK_REPO_ROOT:-\$SCRIPT_DIR}"' "$SCRIPT"
}

@test "resolves script dir and changes into it" {
  #R005-T01: source resolves SCRIPT_DIR from BASH_SOURCE and cds into it
  grep -q 'SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE\[0\]}")" && pwd)"' "$SCRIPT"
  grep -q 'cd "\$SCRIPT_DIR"' "$SCRIPT"
}

@test "missing trend file fails with actionable guidance" {
  #R010-T01: source emits missing-trend guidance pointing at the parallel runner
  grep -q 'missing trend file' "$SCRIPT"
  grep -q '07_run_all_tests_parallel.sh' "$SCRIPT"
}

@test "renders local quality trend summary" {
  #R015-T01: source prints the trend header, rolling p95 metric, and PASS status
  grep -q 'Local quality trend report' "$SCRIPT"
  grep -q 'rolling20 wall p95' "$SCRIPT"
  grep -q 'status: PASS' "$SCRIPT"
}
