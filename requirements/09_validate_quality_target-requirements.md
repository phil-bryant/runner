# 09 validate quality target Requirements

## Scope

Applies to `09_validate_quality_target.sh`. This script validates that recorded quality telemetry meets the configured score and lane-reliability targets across two consecutive ISO weeks, failing fast with actionable guidance when history is missing or insufficient.

R001  Statement: Run in strict shell mode and operate against the resolved target repository.
Design: Use `set -euo pipefail` so validation failures propagate immediately, and allow `RUNBOOK_REPO_ROOT` to override the script-derived `SCRIPT_DIR` so a pointer set (rNN_) targets the consuming repo, defaulting to self.
Tests:
- R001-T01: Verify the script declares `set -euo pipefail`.
- R001-T02: Verify the script honors a `RUNBOOK_REPO_ROOT` override for the working directory.

R005  Statement: Execute from the repository root regardless of caller working directory.
Design: Resolve `SCRIPT_DIR` from `${BASH_SOURCE[0]}` and `cd` into it before reading telemetry history.
Tests:
- R005-T01: Verify the script resolves `SCRIPT_DIR` from `BASH_SOURCE` and changes directory to it.

R010  Statement: Fail with actionable guidance when quality history is missing.
Design: If `quality-history.ndjson` does not exist under `QUALITY_TELEMETRY_DIR` (default `./artifacts/telemetry`), print a failure message to stderr that names the missing path and instructs operators to run `./07_run_all_tests_parallel.sh` over time.
Tests:
- R010-T01: Verify the missing-history guard emits `missing quality history` and references `07_run_all_tests_parallel.sh`.

R015  Statement: Enforce sufficient recent history before declaring quality target success.
Design: Parse history rows as JSON objects with `run_started_at`, filter to the last 21 days, and fail when fewer than two runs remain or when surviving runs do not span at least seven days.
Tests:
- R015-T01: Verify the script fails with insufficient-history messaging when recent runs are too few or too narrow in span.

R020  Statement: Require target attainment across consecutive ISO weeks.
Design: For recent runs, evaluate score and lane reliability thresholds (`QUALITY_TARGET_SCORE`, `QUALITY_TARGET_RELIABILITY`) and pass only when at least one qualifying run exists in two consecutive ISO weeks, including year rollover handling, reporting latest run context on success.
Tests:
- R020-T01: Verify the script evaluates consecutive ISO weeks and prints the validated PASS message.

## Changelog

- 2026-06-06: Converted from requirements-only to a full traceability doc reconciled to current source.
