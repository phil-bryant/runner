# 96 clean generated files Requirements

## Scope

Applies to `96_clean_generated_files.sh`. This runner golden cleans generated
artifact outputs by moving selected report/log paths to `~/.Trash` (never
destructive deletion): security/fuzzing outputs, coverage outputs, test-run
logs, and traceability/quality logs.

R001  Statement: Script enforces strict fail-fast shell mode and uses Trash-based cleanup semantics.
Design: Set `umask 007` and `set -euo pipefail`, then route every cleanup operation through `move_target_to_trash` using `mv` into a run-scoped `~/.Trash` directory.
Tests:
- R001-T01: Verify the script enables strict mode and uses `move_target_to_trash`/`mv` for cleanup.

R005  Statement: Script operates on the resolved target repo root and initializes a run-scoped Trash directory lazily.
Design: Source `src/scripts/runbook_common.sh`, call `runbook_cd_repo`, resolve `REPO_ROOT="$RUNBOOK_REPO_ROOT"`, and create `~/.Trash/runner_generated_cleanup_*` only when a move is required.
Tests:
- R005-T01: Verify the script resolves `REPO_ROOT` through `runbook_common.sh` and lazily initializes a run-scoped Trash directory.

R010  Statement: Script cleans security and fuzzing report outputs.
Design: Attempt to move `./artifacts/security`, `./artifacts/security-dast`, and `./artifacts/fuzz` into the run-scoped Trash directory.
Tests:
- R010-T01: Verify the script targets security and fuzzing artifact paths for cleanup.

R015  Statement: Script cleans coverage outputs and parallel test-run logs.
Design: Attempt to move `./artifacts/coverage` and `./artifacts/parallel` into the run-scoped Trash directory.
Tests:
- R015-T01: Verify the script targets coverage and parallel test-log artifact paths for cleanup.

R020  Statement: Script cleans traceability and quality logs/reports.
Design: Attempt to move `./artifacts/traceability`, `./artifacts/traceability.latest.log`, `./artifacts/quality`, and `./artifacts/quality.latest.log` into the run-scoped Trash directory.
Tests:
- R020-T01: Verify the script targets traceability and quality artifact/log paths for cleanup.

R025  Statement: Missing targets are non-fatal and completion output is explicit.
Design: For absent targets increment skip counters without failure; print a no-op message when nothing is moved, otherwise print moved/skip summary lines including the run-scoped Trash path.
Tests:
- R025-T01: Verify the script emits explicit no-op/success summary output and treats missing targets as non-fatal.

## Changelog

- 2026-06-11: Added new generated-artifact cleanup golden for security/fuzz, coverage, test logs, and traceability/quality outputs via `~/.Trash`.
