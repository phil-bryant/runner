#!/usr/bin/env bats
# Companion traceability tests for 07_run_all_tests_parallel.sh. Each @test
# asserts a real behavioral token in the orchestrator source so the requirement
# IDs stay mapped to genuine implementation, not boilerplate.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/07_run_all_tests_parallel.sh"
}

@test "strict shell mode and secure umask" {
  #R001-T01: source sets umask 007 and strict shell mode
  grep -q 'umask 007' "$SCRIPT"
  grep -q 'set -euo pipefail' "$SCRIPT"
}

@test "resolves the target repo via the runbook contract" {
  #R005-T01: source resolves repo root via runbook_common.sh and runbook_cd_repo
  grep -q 'src/scripts/runbook_common.sh' "$SCRIPT"
  grep -q 'runbook_cd_repo' "$SCRIPT"
}

@test "honors an optional self-run lane allow-list" {
  #R005-T02: source filters discovered checks by RUN_LANE_ALLOWLIST basename/stem
  grep -q 'RUN_LANE_ALLOWLIST' "$SCRIPT"
  grep -q 'allow_normalized' "$SCRIPT"
}

@test "discovers numbered lanes from the filesystem" {
  #R010-T01: source globs ./tests t*.sh and excludes its own basename
  grep -q 'CHECKS_DIR="./tests"' "$SCRIPT"
  grep -q 'SELF_SCRIPT_BASENAME' "$SCRIPT"
}

@test "fails when no numbered test scripts are discovered" {
  #R010-T02: source exits non-zero with a no-checks-found message
  grep -q 'no numbered test scripts found' "$SCRIPT"
}

@test "launches lanes concurrently in their own sessions" {
  #R015-T01: source launches lanes via run_in_new_session and run_lane_worker
  grep -q 'run_in_new_session' "$SCRIPT"
  grep -q 'run_lane_worker' "$SCRIPT"
}

@test "captures each child exit code independently" {
  #R020-T01: source tracks child_pids, writes .exit files, and waits per PID
  grep -q 'child_pids+=' "$SCRIPT"
  grep -q '\.exit' "$SCRIPT"
  grep -q 'wait "\$pid"' "$SCRIPT"
}

@test "reports completions over a FIFO" {
  #R025-T01: source opens a completion FIFO and workers signal over fd 3
  grep -q 'mkfifo' "$SCRIPT"
  grep -q '>&3' "$SCRIPT"
}

@test "records completions idempotently and recovers missed ones" {
  #R025-T02: source uses record_check_result and recover_missing_completions
  grep -q 'record_check_result' "$SCRIPT"
  grep -q 'recover_missing_completions' "$SCRIPT"
}

@test "prints the overall pass/fail gate" {
  #R030-T01: source prints overall PASS/FAIL gate and exits 0/1
  grep -q 'all parallel checks succeeded' "$SCRIPT"
  grep -Eq 'exit (0|1)' "$SCRIPT"
}

@test "formats final PASS gate with aggregate test count" {
  #R030-T02: source prints final PASS as aggregate bracketed tests plus pass/total
  grep -q '✅ PASS: all parallel checks succeeded \[${aggregate_test_count} tests\] (${pass_count}/${total})' "$SCRIPT"
}

@test "persists per-check log artifacts" {
  #R035-T01: source persists lane logs under PARALLEL_CHECKS_REPORT_DIR
  grep -q 'PARALLEL_CHECKS_REPORT_DIR' "$SCRIPT"
}

@test "remains a standalone meta-runner" {
  #R040-T01: source excludes its own basename from lane discovery
  grep -q 'script" == "\$SELF_SCRIPT_BASENAME"' "$SCRIPT"
}

@test "renders continuous aggregate progress" {
  #R045-T01: source renders a Progress: bar via render_progress
  grep -q 'render_progress' "$SCRIPT"
  grep -q 'Progress:' "$SCRIPT"
}

@test "prevents concurrent runs from the same repo root" {
  #R050-T01: source acquires a single-run lock and fails when one is active
  grep -q 'acquire_single_run_lock' "$SCRIPT"
  grep -q 'already active' "$SCRIPT"
}

@test "terminates child checks on interrupt" {
  #R055-T01: source traps signals and terminates tracked children
  grep -q 'terminate_child_checks' "$SCRIPT"
  grep -q "trap 'signal_exit_code=130' INT" "$SCRIPT"
}

@test "reports orchestrator timing context" {
  #R060-T01: source prints a Timing wall / long pole line
  grep -q 'Timing: wall' "$SCRIPT"
}

@test "documents optional lane-skip flags" {
  #R065-T01: usage text documents --no-ui, --no-mutation, and --no-av
  grep -q -- '--no-ui' "$SCRIPT"
  grep -q -- '--no-mutation' "$SCRIPT"
  grep -q -- '--no-av' "$SCRIPT"
}

@test "filters discovered lanes and exports skipped stems" {
  #R065-T02: source filters by skip patterns and exports PARALLEL_CHECKS_SKIPPED_LANES
  grep -q 'UI_REGRESSION_PATTERN' "$SCRIPT"
  grep -q 'PARALLEL_CHECKS_SKIPPED_LANES' "$SCRIPT"
}

@test "quality telemetry is opt-out" {
  #R070-T01: telemetry block is guarded by QUALITY_SCORING_ENABLED
  grep -q 'QUALITY_SCORING_ENABLED' "$SCRIPT"
}

@test "discovers per-repo run-all pointers in runners mode" {
  #R011-T01: runners discovery is gated on PARALLEL_CHECKS_RUNNERS_MODE via a shallow find + glob
  grep -q 'PARALLEL_CHECKS_RUNNERS_MODE' "$SCRIPT"
  grep -q 'RUNNERS_DISCOVERY_GLOB' "$SCRIPT"
  grep -q 'find . -maxdepth' "$SCRIPT"
}

@test "resolves runners-mode lanes and isolates child env" {
  #R011-T02: worker resolves lanes via lane_script_path/lane_log_label and unsets runners-mode env before exec
  grep -q 'lane_script_path' "$SCRIPT"
  grep -q 'lane_log_label' "$SCRIPT"
  grep -q 'unset PARALLEL_CHECKS_RUNNERS_MODE' "$SCRIPT"
}

@test "lists the resolved lane set as a dry run" {
  #R012-T01: PARALLEL_CHECKS_LIST_ONLY=1 prints lanes and exits before launching
  grep -q 'PARALLEL_CHECKS_LIST_ONLY' "$SCRIPT"
}

@test "serializes macOS UI lanes through a shared lock" {
  #R066-T01: UI_REGRESSION_PATTERN lanes are gated behind a pid-aware .parallel-ui-tests.lock with a bounded wait
  grep -q '\.parallel-ui-tests\.lock' "$SCRIPT"
  grep -q 'PARALLEL_UI_LOCK_WAIT_TIMEOUT_SECONDS' "$SCRIPT"
}
