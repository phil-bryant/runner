---
name: parallel lane test counts
overview: Add per-lane test-count reporting to parallel PASS lines in the runner orchestrator. Counts will prioritize real framework test cases, then internal check counts for multi-step lanes, and finally fallback to 1 when no reliable source exists.
todos:
  - id: inspect-points
    content: Locate and wire PASS-line count injection point in orchestrator record_check_result.
    status: completed
  - id: add-count-helper
    content: Create a helper parser script that returns per-lane integer test counts with fallback behavior.
    status: completed
  - id: integrate-format
    content: Integrate helper output into PASS line format as [nn tests] while preserving existing fail/progress logic.
    status: completed
  - id: add-tests
    content: Add/adjust tests for helper counting logic and PASS output formatting.
    status: completed
  - id: verify-end-to-end
    content: Run targeted validation and one constrained parallel run to confirm output and no regressions.
    status: completed
isProject: false
---

# Add Per-Lane Test Counts To Parallel PASS Output

## Goal
Update parallel lane PASS output from `✅ PASS: <lane> (57s)` to `✅ PASS: <lane> [nn tests] (57s)` in [`07_run_all_tests_parallel.sh`](07_run_all_tests_parallel.sh), with `nn` computed as:
- real test-case counts when available,
- otherwise summed internal sub-check counts for multi-step lanes,
- otherwise fallback `1`.

## Implementation Plan

- Add a lane test-count resolver in [`07_run_all_tests_parallel.sh`](07_run_all_tests_parallel.sh) and call it from `record_check_result` before printing PASS lines.
- Introduce a small parser helper (Python) at [`src/scripts/parallel_lane_test_count.py`](src/scripts/parallel_lane_test_count.py) so count logic stays maintainable and testable instead of embedding complex shell parsing.
- Pass resolver inputs (`lane script name`, `lane log path`, `repo root`, `report dir`) and have the helper return a single integer to stdout; on parse/command failure, shell defaults to `1`.
- Update PASS emission format in `record_check_result` to include `[${lane_test_count} tests]` while keeping fail formatting unchanged.

## Counting Strategy (Priority Order)

- **Framework case counts first**
  - `t05`: parse Bats TAP totals from lane log (sum TAP plans / `ok` coverage robustly).
  - `t06`: parse pytest summary counts from lane log (`N passed` / collected cases).
  - `t08`: read `property_test_count` from `fuzz-summary.json`.
  - `t04`: parse traceability CLI `Summary: total=...` from lane log.
- **Then internal sub-check counts for multi-step lanes**
  - `t00`, `t02`, `t03`, `t09`: count executed internal checks using known artifacts/summaries (prefer machine-readable files when present; avoid pure heuristic log-only counting when possible).
  - `t07`: use mutation summary `total` (mutation cases) if available; otherwise fallback path.
- **Fallback**
  - Any lane with no reliable source returns `1` (per your preference).

## Test Coverage Changes

- Add focused tests for the new count helper under [`tests/py`](tests/py) (or existing shell test area if that fits repo conventions better):
  - verifies framework parsing paths (Bats/pytest/traceability/fuzz),
  - verifies multi-step lane check counting behavior,
  - verifies fallback-to-1 on missing/invalid artifacts.
- Add/adjust shell-level test(s) that assert PASS line format now includes `[nn tests]` in orchestrator output path.

## Validation

- Run targeted tests for the new helper and orchestrator formatting assertions.
- Run one end-to-end parallel invocation (with a constrained lane allow-list) and verify PASS lines render as:
  - `✅ PASS: t01_run_av_test.sh [1 tests] (57s)`
  - multi-step lanes show summed counts > 1 when applicable.
- Confirm no regression in fail-line behavior, progress rendering, or telemetry artifacts.
