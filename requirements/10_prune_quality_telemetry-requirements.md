# 10 prune quality telemetry Requirements

## Scope

Applies to `10_prune_quality_telemetry.sh`. This script prunes superseded quality lane-summary telemetry artifacts, keeping only the newest retention count and moving older `lane-summary-*.json` files to the macOS Trash instead of deleting them.

R001  Statement: Run in strict shell mode and fail fast on errors.
Design: Declare `set -euo pipefail` so unset variables, command failures, and broken pipes abort the telemetry pruning run immediately.
Tests:
- R001-T01: Verify the source declares `set -euo pipefail`.

R005  Statement: Execute from the resolved repository root regardless of caller working directory.
Design: Resolve `SCRIPT_DIR` from `${BASH_SOURCE[0]}`, allow `RUNBOOK_REPO_ROOT` to override it for pointer-driven invocations, and `cd` into it before reading telemetry artifacts.
Tests:
- R005-T01: Verify the source resolves `SCRIPT_DIR` from `${BASH_SOURCE[0]}` and honors `RUNBOOK_REPO_ROOT`.

R010  Statement: Enforce a non-negative retention count before pruning lane summaries.
Design: Validate `QUALITY_LANE_SUMMARY_KEEP` against `^[0-9]+$` and fail with guidance when invalid, then move the oldest `lane-summary-*.json` files to the Trash via `safe_move_to_trash` so only the newest `KEEP_COUNT` remain.
Tests:
- R010-T01: Verify the source validates `QUALITY_LANE_SUMMARY_KEEP` as a non-negative integer with the `^[0-9]+$` pattern.
- R010-T02: Verify the source prunes oldest `lane-summary-*.json` files via `safe_move_to_trash`.

## Changelog

- 2026-06-06: Converted from requirements-only to a full traceability doc reconciled to current source.
