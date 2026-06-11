# 07 run all tests parallel Requirements

## Scope

Applies to `07_run_all_tests_parallel.sh`. This is the shared golden parallel
test orchestrator owned by the runner engine: it resolves the target repo,
discovers the numbered `tests/tNN_*` check lanes, launches them concurrently
each in its own session, streams per-lane pass/fail results in completion order,
gates the overall run. The runner self-run
(08_run_all_self_tests_parallel) and the consuming repos delegate to this
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

R011  Statement: Support an opt-in "runners" discovery mode that orchestrates per-repo run-all pointers instead of tNN lanes.
Design: When `PARALLEL_CHECKS_RUNNERS_MODE=true`, discover lanes shallowly across repo roots (`find . -maxdepth "$RUNNERS_DISCOVERY_MAXDEPTH" -name "$RUNNERS_DISCOVERY_GLOB" -type f -perm -u=x`, default glob `[0-9][0-9]_run_all_*tests_parallel.sh`) so lanes are repo-relative paths; resolve each token through `lane_script_path` (path) and `lane_log_label` (slashes→dashes, so same-basename pointers across repos get distinct logs); forward top-level optional skip/serialize flags (`--no-ui`, `--no-mutation`, `--no-av`, `--serialize-ui-mutation`) to delegated `*_run_all_*tests_parallel.sh` child pointers; and unset the runners-mode/meta-only env (`PARALLEL_CHECKS_RUNNERS_MODE`, `RUNNERS_DISCOVERY_GLOB`, `RUNNERS_DISCOVERY_MAXDEPTH`, `PARALLEL_CHECKS_REPORT_DIR`, `QUALITY_SCORING_ENABLED`) in the worker before exec so each child run-all pointer runs in normal tNN mode, in its own report dir, with its own scoring. Default mode (`false`) preserves the historical `./tests` tNN behavior byte-for-byte.
Tests:
- R011-T01: Verify the source gates a shallow `find`-based runners discovery on `PARALLEL_CHECKS_RUNNERS_MODE` with the `[0-9][0-9]_run_all_*tests_parallel.sh` glob.
- R011-T02: Verify the worker resolves lanes via `lane_script_path`/`lane_log_label` and unsets `PARALLEL_CHECKS_RUNNERS_MODE` before running a child lane.
- R011-T03: Verify delegated `*_run_all_*tests_parallel.sh` lanes receive forwarded top-level skip/serialize flags.

R012  Statement: Support a dry-run that lists the resolved lane set without executing anything.
Design: When `PARALLEL_CHECKS_LIST_ONLY=1`, after discovery and the existence check, print each lane's `lane_log_label` and `lane_script_path` (tab separated) and `exit 0` before opening the completion FIFO or launching lanes.
Tests:
- R012-T01: Verify the source honors `PARALLEL_CHECKS_LIST_ONLY=1` by printing the resolved lanes and exiting before launch.

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

R030  Statement: Print the overall pass/fail gate, aggregate count summary, and exit code.
Design: Exit `0` with an overall `✅ PASS: all parallel checks succeeded [<aggregate_tests> tests] (<passed>/<total>)` line when every lane succeeds; exit `1` with an overall `❌ FAIL` line summarizing `passed/total` when any lane fails.
Tests:
- R030-T01: Verify the source prints the overall PASS/FAIL gate and exits `0`/`1` accordingly.
- R030-T02: Verify the overall PASS line includes the aggregate bracketed test count and lane pass fraction format.

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
Design: Parse `--no-ui`, `--no-mutation`, and `--no-av` (plus `-h|--help`) before discovery; filter discovered lanes matching the configurable `UI_REGRESSION_PATTERN`/`MUTATION_LANE_PATTERN`/`AV_LANE_PATTERN` content patterns, iterate skipped stems using a nounset-safe empty-array expansion, export skipped lane stems via `PARALLEL_CHECKS_SKIPPED_LANES`, and reject unknown arguments with usage guidance.
Tests:
- R065-T01: Verify the usage/help text documents `--no-ui`, `--no-mutation`, and `--no-av`.
- R065-T02: Verify the source filters discovered lanes by the skip patterns and exports `PARALLEL_CHECKS_SKIPPED_LANES`.
- R065-T03: Verify the skipped-lane stem loop is nounset-safe when no lanes match (empty-array-safe expansion under `set -u`).

R066  Statement: Serialize macOS UI regression lanes through a single RUNNER_HOME-global lock.
Design: In the lane worker, gate any lane whose name matches `UI_REGRESSION_PATTERN` behind a pid-aware mkdir lock at `${UI_LANE_LOCK_DIR:-${SCRIPT_DIR}/.parallel-ui-tests.lock}`; because `SCRIPT_DIR` is `RUNNER_HOME` and every repo's pointer execs this same golden, the lock is shared across repos so concurrent UI lanes (e.g. classy and mailcart under the runners-mode meta-run) wait instead of fighting the SwiftPM build and window-server focus. Reclaim only a dead owner's lock (`kill -0`) and bound the wait with `PARALLEL_UI_LOCK_WAIT_TIMEOUT_SECONDS`; perform no unconditional startup cleanup so concurrent goldens cannot stomp a held lock.
Tests:
- R066-T01: Verify the worker gates `UI_REGRESSION_PATTERN` lanes behind the `.parallel-ui-tests.lock` with a pid-aware, bounded wait.
- R066-T02: Verify UI lanes enforce `PARALLEL_UI_LANE_RUNTIME_TIMEOUT_SECONDS` and log lock-owner wait diagnostics while blocked.

## Changelog

- 2026-06-07: Removed telemetry-specific requirements (R070, R075) after deleting quality telemetry/trend/target/prune functionality from the orchestrator.
- 2026-06-06: Converted from `Requirements-only mode: true` to a full traceability doc with a 15-entry requirement set reconciled to the current orchestrator source (filesystem lane discovery, completion-FIFO ordering, single-run lock, scoped cleanup, and lane-skip flags), plus a companion bats lane.
- 2026-06-06: Refined R030 to require the final PASS gate format `✅ PASS: all parallel checks succeeded [<aggregate_tests> tests] (<passed>/<total>)` and added numbered test mapping `R030-T02` for the aggregate summary string.
