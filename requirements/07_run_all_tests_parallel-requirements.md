# 07 run all tests parallel Requirements

## Scope

Applies to `07_run_all_tests_parallel.sh`. This is the shared golden parallel
test orchestrator owned by the runner engine: it resolves the target repo,
discovers the numbered `tests/tNN_*` check lanes, launches them concurrently
each in its own session, streams per-lane pass/fail results in completion order,
gates the overall run, and emits optional quality telemetry. The runner self-run
(11_run_all_self_tests_parallel) and the consuming repos delegate to this
golden, but its behavioral source/test traceability is enforced here against the
first-party in-repo implementation.

R001  Statement: Run in strict shell mode with secure file permissions and fail fast.
Design: Set `umask 007` and `set -euo pipefail` at script entry so unset variables, failed commands, and broken pipelines abort the orchestrator and new artifacts are owner/group-private.
Tests:
- R001-T01: Verify the source sets `umask 007` and `set -euo pipefail`.

R005  Statement: Operate on the target repository and honor an optional self-run lane allow-list.
Design: Source `src/scripts/runbook_common.sh` and call `runbook_cd_repo` so an `rNN_` pointer's `RUNBOOK_REPO_ROOT` is used (defaulting to the runner itself); restrict discovery to `RUN_LANE_ALLOWLIST` entries (space/comma separated, matched by lane basename or stem) when that variable is non-empty.
Tests:
- R005-T01: Verify the source resolves the repo root via `runbook_common.sh` and `runbook_cd_repo`.
- R005-T02: Verify a non-empty `RUN_LANE_ALLOWLIST` filters discovered checks by basename or stem.

R010  Statement: Discover numbered check scripts dynamically from the filesystem.
Design: Glob `./tests/t*.sh`, exclude the orchestrator's own basename, keep only scripts whose names contain `test`/`tests`, sort with `sort -V`, and fail non-zero with actionable guidance when discovery yields zero lanes (no static order manifest).
Tests:
- R010-T01: Verify the source discovers lanes from `./tests` via a `t*.sh` glob and excludes its own basename.
- R010-T02: Verify the source fails non-zero with a "no numbered test scripts found" message when nothing is discovered.

R015  Statement: Launch every discovered check concurrently, each in its own session.
Design: Define an exported `run_lane_worker` and start each lane via `run_in_new_session bash -c '...' &` so lanes run in parallel as independent session leaders reachable for cleanup.
Tests:
- R015-T01: Verify the source launches lanes through `run_in_new_session` and the exported `run_lane_worker`.

R020  Statement: Capture each child exit code independently.
Design: Record each background job PID in `child_pids`, persist each lane's exit code to `${log}.exit`, and `wait` on every PID without aborting the run on the first failure.
Tests:
- R020-T01: Verify the source tracks `child_pids`, writes per-lane `.exit` files, and waits on each PID.

R025  Statement: Report per-lane pass/fail in completion order without losing results.
Design: Open a completion FIFO (`mkfifo`, fd 3); each worker writes `script|exit` the instant it finishes; the reader prints each `✅ PASS`/`❌ FAIL` line as it arrives, records each completion idempotently, and recovers any missed completions from on-disk `.exit` files.
Tests:
- R025-T01: Verify the source opens a completion FIFO and workers signal completion over fd 3.
- R025-T02: Verify the source records completions idempotently (`record_check_result`) and recovers missing ones (`recover_missing_completions`).

R030  Statement: Print the overall pass/fail gate and exit code.
Design: Exit `0` with an overall `✅ PASS` line when every lane succeeds; exit `1` with an overall `❌ FAIL` line summarizing `passed/total` when any lane fails.
Tests:
- R030-T01: Verify the source prints the overall PASS/FAIL gate and exits `0`/`1` accordingly.

R035  Statement: Persist per-check stdout/stderr log artifacts.
Design: Write each lane's combined output to `${PARALLEL_CHECKS_REPORT_DIR:-./artifacts/parallel}/<stem>.log` and reference the log path in FAIL summary lines.
Tests:
- R035-T01: Verify the source persists lane logs under `PARALLEL_CHECKS_REPORT_DIR`/`./artifacts/parallel`.

R040  Statement: Remain a standalone meta-runner that never invokes itself.
Design: Exclude the orchestrator's own basename from the discovered `CHECKS` set so it can never schedule itself as a child lane; child checks remain independent numbered entrypoints.
Tests:
- R040-T01: Verify the source skips its own basename (`SELF_SCRIPT_BASENAME`) during lane discovery.

R045  Statement: Emit continuous aggregate progress while checks are still running.
Design: Render a textual progress bar with completed/total counts and percentage that updates on a bounded interval while lanes run, without suppressing any per-lane completion line.
Tests:
- R045-T01: Verify the source renders a `Progress:` bar via `render_progress`.

R050  Statement: Prevent concurrent orchestrator invocations from the same repo root.
Design: Acquire a single-run lock file at repo-root scope via `noclobber`; fail immediately when a live owner PID holds it, and reclaim a stale lock whose owner no longer exists.
Tests:
- R050-T01: Verify the source acquires a single-run lock and fails when another run is already active.

R055  Statement: Terminate launched child checks on interrupt or termination.
Design: Trap `INT`/`TERM`, then `terminate_child_checks` signals each tracked lane's process tree/group (TERM then KILL), writes `.cleanup` provenance, releases the lock, and exits non-zero; a `PARALLEL_CHECKS_TEST_INTERRUPT=1` hook exercises the same path deterministically.
Tests:
- R055-T01: Verify the source traps signals and terminates tracked children via `terminate_child_checks`.

R060  Statement: Report orchestrator timing context for triage.
Design: Record a wall-clock start epoch and, before the overall gate, print one `Timing: wall <s>; long pole <script> (<s>)` line identifying total runtime and the slowest lane.
Tests:
- R060-T01: Verify the source prints a `Timing: wall ...; long pole ...` line.

R065  Statement: Support optional lane-skip CLI flags.
Design: Parse `--no-ui`, `--no-mutation`, and `--no-av` (plus `-h|--help`) before discovery; filter discovered lanes matching the configurable `UI_REGRESSION_PATTERN`/`MUTATION_LANE_PATTERN`/`AV_LANE_PATTERN` content patterns, export skipped lane stems via `PARALLEL_CHECKS_SKIPPED_LANES`, and reject unknown arguments with usage guidance.
Tests:
- R065-T01: Verify the usage/help text documents `--no-ui`, `--no-mutation`, and `--no-av`.
- R065-T02: Verify the source filters discovered lanes by the skip patterns and exports `PARALLEL_CHECKS_SKIPPED_LANES`.

R070  Statement: Quality scoring and telemetry are opt-out via an environment flag.
Design: Run the embedded quality-telemetry scorer (writing `quality-history.ndjson`/`quality-trend.json`) only when `QUALITY_SCORING_ENABLED` is not `false` (default `true`), so the orchestrator can run lane gating without telemetry when disabled.
Tests:
- R070-T01: Verify the telemetry block is guarded by `QUALITY_SCORING_ENABLED` (default `true`).

## Changelog

- 2026-06-06: Converted from `Requirements-only mode: true` to a full traceability doc with a 15-entry requirement set reconciled to the current orchestrator source (filesystem lane discovery, completion-FIFO ordering, single-run lock, scoped cleanup, lane-skip flags, and opt-out quality telemetry), plus a companion bats lane.
