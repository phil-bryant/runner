#!/usr/bin/env bats
# Companion tests for 96_clean_generated_files.sh requirements traceability.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/96_clean_generated_files.sh"
}

@test "uses strict shell mode and trash-only move cleanup" {
  #R001-T01: source enables strict mode and routes cleanup through move_target_to_trash + mv
  grep -q 'umask 007' "$SCRIPT"
  grep -q 'set -euo pipefail' "$SCRIPT"
  grep -q 'move_target_to_trash()' "$SCRIPT"
  grep -q 'mv "\$source_path" "\$destination_path"' "$SCRIPT"
}

@test "resolves target repo root and lazily creates run-scoped trash dir" {
  #R005-T01: source resolves REPO_ROOT via runbook_common + runbook_cd_repo and mktemp trash dir
  grep -q 'runbook_common.sh' "$SCRIPT"
  grep -q 'runbook_cd_repo' "$SCRIPT"
  grep -q 'REPO_ROOT="\$RUNBOOK_REPO_ROOT"' "$SCRIPT"
  grep -q 'mktemp -d "\${HOME}/.Trash/runner_generated_cleanup_' "$SCRIPT"
}

@test "targets security and fuzzing artifact outputs" {
  #R010-T01: source attempts to clean security/security-dast/fuzz artifact paths
  grep -q 'move_target_to_trash "./artifacts/security"' "$SCRIPT"
  grep -q 'move_target_to_trash "./artifacts/security-dast"' "$SCRIPT"
  grep -q 'move_target_to_trash "./artifacts/fuzz"' "$SCRIPT"
}

@test "targets coverage and parallel test-run logs" {
  #R015-T01: source attempts to clean coverage and parallel artifact paths
  grep -q 'move_target_to_trash "./artifacts/coverage"' "$SCRIPT"
  grep -q 'move_target_to_trash "./artifacts/parallel"' "$SCRIPT"
}

@test "targets traceability and quality logs/reports" {
  #R020-T01: source attempts to clean traceability and quality paths
  grep -q 'move_target_to_trash "./artifacts/traceability"' "$SCRIPT"
  grep -q 'move_target_to_trash "./artifacts/traceability.latest.log"' "$SCRIPT"
  grep -q 'move_target_to_trash "./artifacts/quality"' "$SCRIPT"
  grep -q 'move_target_to_trash "./artifacts/quality.latest.log"' "$SCRIPT"
}

@test "prints explicit summary and keeps missing targets non-fatal" {
  #R025-T01: source prints no-op/success summary and tracks skipped paths
  grep -q 'No generated artifacts found to clean.' "$SCRIPT"
  grep -q 'Cleanup complete: moved' "$SCRIPT"
  grep -q 'Skipped .* missing target' "$SCRIPT"
  grep -q 'SKIPPED_COUNT=\$((SKIPPED_COUNT + 1))' "$SCRIPT"
}
