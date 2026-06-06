#!/usr/bin/env bats
# Companion tests for 10_prune_quality_telemetry.sh requirements traceability.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/10_prune_quality_telemetry.sh"
}

@test "strict shell mode" {
  #R001-T01: source declares strict shell mode
  grep -q 'set -euo pipefail' "$SCRIPT"
}

@test "resolves repository root from script location" {
  #R005-T01: source resolves SCRIPT_DIR from BASH_SOURCE and honors RUNBOOK_REPO_ROOT
  grep -q 'SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE\[0\]}")" && pwd)"' "$SCRIPT"
  grep -q 'RUNBOOK_REPO_ROOT' "$SCRIPT"
}

@test "validates non-negative retention count" {
  #R010-T01: source validates QUALITY_LANE_SUMMARY_KEEP as a non-negative integer
  grep -q 'QUALITY_LANE_SUMMARY_KEEP' "$SCRIPT"
  grep -q '\^\[0-9\]+\$' "$SCRIPT"
}

@test "prunes oldest lane summaries to trash" {
  #R010-T02: source moves oldest lane-summary files via safe_move_to_trash
  grep -q 'lane-summary-\*.json' "$SCRIPT"
  grep -q 'safe_move_to_trash' "$SCRIPT"
}
