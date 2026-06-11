# t07 run mutation tests Requirements

## Scope

Applies to `tests/t07_run_mutation_tests.sh`.

R001  Statement: Mutation lane exposes CLI controls for preflight and cache modes.
Design: Parse `--preflight`/`--skip-preflight` (`--slow`/`--fast` aliases) and `--cache-smart|--cache-fresh|--cache-force`, with `--help` usage output and unknown-arg failure.
Tests:
- R001-T01: Verify usage text documents preflight/cache flags.
- R001-T02: Verify argument parser handles preflight/cache switches and rejects unknown args.

R005  Statement: Default execution favors fast local feedback with smart cache reuse.
Design: Default `MUTATION_RUN_PREFLIGHT=false` and `MUTATION_CACHE_MODE="smart"` so local runs skip preflight and reuse cache when compatible.
Tests:
- R005-T01: Verify source defaults set skip-preflight + smart-cache mode.

R010  Statement: Smart cache reuse is fingerprint-gated and metadata-backed.
Design: Compute a deterministic cache fingerprint from runtime/tooling/script inputs, compare against `cache-meta.json`, and only reuse cache on smart-mode fingerprint match.
Tests:
- R010-T01: Verify source defines fingerprint build/read/write helpers and cache metadata path.
- R010-T02: Verify smart-mode reuse gate requires both existing cache + matching saved fingerprint.

R015  Statement: Fresh/smart-miss modes rotate stale mutation artifacts safely.
Design: On cache miss or explicit `--cache-fresh`, move old `mutants` link/workdir to trash-safe paths before recreating the workdir symlink.
Tests:
- R015-T01: Verify source routes stale cache cleanup through `safe_move_to_trash` before link recreation.

R020  Statement: Preflight behavior is explicit and opt-in for slower runs.
Design: Default path prints preflight-skip guidance; `--preflight` runs pytest preflight and blocks mutation run on failures.
Tests:
- R020-T01: Verify source prints explicit default skip message and explicit preflight-enabled message.

R022  Statement: Coverage gating is enforced in the mutation summary parser.
Design: Mutation summary parsing checks `mutator_coverage` against `coverage_threshold` and fails the gate when the threshold is missed.
Tests:
- R022-T01: Verify source computes coverage gate status from parsed mutator coverage and threshold values.

R025  Statement: Optional file exclusions are persisted in mutation reporting outputs.
Design: The lane carries `MUTATION_EXCLUDE_FILES` through summary generation so exclusion context is recorded with each run.
Tests:
- R025-T01: Verify source defines `MUTATION_EXCLUDE_FILES` and forwards it into summary generation arguments.

R030  Statement: Mutation lane emits machine-readable summary artifacts.
Design: The lane writes `mutation-summary.json` for both normal and skipped runtime paths.
Tests:
- R030-T01: Verify source defines `MUTATION_SUMMARY` and writes JSON summary data.

R035  Statement: Mutation lane prints concise operator-facing pass/fail outcomes.
Design: After summary evaluation, the lane emits explicit PASS/FAIL/SKIP guidance including report path context.
Tests:
- R035-T01: Verify source includes explicit mutation lane completion and failure messaging.

R040  Statement: Mutation execution is wrapped in a timeout boundary.
Design: `run_with_timeout` executes mutmut with process-group termination and timeout exit status propagation.
Tests:
- R040-T01: Verify source defines the timeout wrapper and timeout handling branch.

R045  Statement: Mutation trend history is appended and rolled up per run.
Design: The lane records NDJSON history entries and writes rolling trend metrics to `mutation-trend.json`.
Tests:
- R045-T01: Verify source carries history/trend paths and appends trend processing logic.

R050  Statement: CI strictness fails when mutation execution is skipped for host incompatibility.
Design: Runtime-incompatibility skip path exits non-zero in CI while remaining non-fatal for local workflows.
Tests:
- R050-T01: Verify source includes CI strict-mode failure branch for mutation-skip path.

R055  Statement: Survivor-budget overflow is represented in gate outputs.
Design: Summary payload includes `survivor_budget` and `survivor_budget_failed` fields to enforce survivor count budgets.
Tests:
- R055-T01: Verify source includes survivor-budget and survivor-budget-failed summary fields.

R060  Statement: Curated equivalent mutants can be excluded from scoring.
Design: The parser supports `MUTATION_EQUIVALENTS_FILE` and excludes only explicit proven-equivalent survivors from score denominator.
Tests:
- R060-T01: Verify source references `MUTATION_EQUIVALENTS_FILE` and equivalent-mutant scoring exclusions.

