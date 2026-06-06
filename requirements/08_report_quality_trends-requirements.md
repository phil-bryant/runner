# 08 report quality trends Requirements

## Scope

Applies to `08_report_quality_trends.sh`. The script reads quality-telemetry payloads produced by the parallel test runner and prints a human-readable local quality-trend summary, failing fast with actionable guidance when telemetry is missing.

R001  Statement: Run in strict shell mode and operate on the target repo, defaulting to the script's own location.
Design: Use `set -euo pipefail` to halt on setup or reporting failures, and allow `RUNBOOK_REPO_ROOT` (set by `rNN_` pointer invocations) to override `SCRIPT_DIR`, defaulting to self when unset.
Tests:
- R001-T01: Verify the script defines `set -euo pipefail`.
- R001-T02: Verify the script honors `RUNBOOK_REPO_ROOT` when resolving the target repo.

R005  Statement: Execute from repository root regardless of caller working directory.
Design: Resolve `SCRIPT_DIR` from `${BASH_SOURCE[0]}` and `cd` into it before reading telemetry paths.
Tests:
- R005-T01: Verify the script resolves `SCRIPT_DIR` and changes directory to it.

R010  Statement: Fail with actionable guidance when the trend payload is missing.
Design: If `quality-trend.json` does not exist under `QUALITY_TELEMETRY_DIR` (default `./artifacts/telemetry`), print a failure message to stderr that names the missing path and instructs operators to run `./07_run_all_tests_parallel.sh`.
Tests:
- R010-T01: Verify a missing trend file produces `missing trend file` guidance pointing at `./07_run_all_tests_parallel.sh`.

R015  Statement: Render a human-readable local trend summary from telemetry payloads.
Design: Parse `quality-trend.json` and optional `quality-history.ndjson` with `python3`, printing latest run/score, rolling 20-run metrics, rolling 14-day metrics, and a final status line (`PASS`, `WARN`, or `FAIL`) derived from `performance_slo`.
Tests:
- R015-T01: Verify the summary includes the `Local quality trend report` header, the `rolling20 wall p95` metric, and a `status: PASS` outcome line.

## Changelog

- 2026-06-06: Converted from requirements-only to a full traceability doc reconciled to current source.
