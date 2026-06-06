#!/usr/bin/env bats
# Companion tests for 09_validate_quality_target.sh requirements traceability.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/09_validate_quality_target.sh"
}

@test "strict shell mode" {
  #R001-T01: source declares strict shell mode
  grep -q 'set -euo pipefail' "$SCRIPT"
}

@test "target repo override" {
  #R001-T02: source honors RUNBOOK_REPO_ROOT override for working directory
  grep -q 'RUNBOOK_REPO_ROOT' "$SCRIPT"
}

@test "resolves repo root from script location" {
  #R005-T01: source resolves SCRIPT_DIR from BASH_SOURCE and cd's into it
  grep -q 'SCRIPT_DIR' "$SCRIPT"
  grep -q 'BASH_SOURCE' "$SCRIPT"
  grep -q 'cd "$SCRIPT_DIR"' "$SCRIPT"
}

@test "missing history guidance" {
  #R010-T01: source emits missing quality history guidance referencing 07_run_all_tests_parallel.sh
  grep -q 'missing quality history' "$SCRIPT"
  grep -q '07_run_all_tests_parallel.sh' "$SCRIPT"
}

@test "insufficient history guard" {
  #R015-T01: source fails on insufficient recent history span
  grep -q 'insufficient history to validate two consecutive weeks' "$SCRIPT"
  grep -q 'does not yet span two weeks' "$SCRIPT"
}

@test "consecutive iso weeks pass" {
  #R020-T01: source validates consecutive ISO weeks against quality targets and prints PASS
  grep -q 'QUALITY_TARGET_SCORE' "$SCRIPT"
  grep -q 'QUALITY_TARGET_RELIABILITY' "$SCRIPT"
  grep -q 'consecutive ISO weeks' "$SCRIPT"
  grep -q 'quality target validated for two consecutive weeks' "$SCRIPT"
}
