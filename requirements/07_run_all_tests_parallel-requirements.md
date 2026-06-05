# 07 run all tests parallel Requirements

## Scope

Requirements-only mode: true

Applies to `07_run_all_tests_parallel.sh`. This is the shared golden parallel orchestrator owned by the runner engine and exercised end-to-end by the consuming repos (teller/classy/matchy/mailcart) and by runner's own self-run (`11_run_all_self_tests_parallel.sh`) where its behavioral source/test traceability is enforced. Runner records it here as a self-run inventory entry so the numbered-script coverage and scope-alignment checks remain satisfied without duplicating downstream enforcement.

R065  Statement: Orchestrator supports optional lane-skip CLI flags.
Design: Parse `--no-ui`, `--no-mutation`, and `--no-av` to skip discovered lanes matching configurable content patterns (`UI_REGRESSION_PATTERN`, `MUTATION_LANE_PATTERN`, and `AV_LANE_PATTERN`) while keeping default behavior unchanged.
Tests:
- R065-T01: Verify orchestrator source usage/help text includes `--no-ui`, `--no-mutation`, and `--no-av`.
- R065-T02: Verify orchestrator source filters discovered checks using all skip patterns and exports skipped lane stems via `PARALLEL_CHECKS_SKIPPED_LANES`.

R070  Statement: Interrupt cleanup must be scoped to lane sessions launched by the current orchestrator invocation.
Design: `terminate_child_checks` iterates tracked lane session leaders (`child_pids`) and sends TERM/KILL to those process trees/process groups only; avoid repo-agnostic global process matching that can terminate sibling-repo lanes.
Tests:
- R070-T01: Verify orchestrator source cleanup path does not use script-path `pgrep -f` fallback and instead iterates tracked child session leaders.

R075  Statement: Cleanup-originated lane terminations must be diagnosable from orchestrator artifacts.
Design: For each cleanup signal sent, append provenance metadata (`timestamp`, `signal`, `reason`, `pid`) to `${lane_log}.cleanup`; classify failed lanes with cleanup metadata as `orchestrator-cleanup` and print provenance in the failure summary.
Tests:
- R075-T01: Verify orchestrator source writes `.cleanup` provenance records during cleanup and surfaces `orchestrator-cleanup` as failure reason when metadata exists.

## Changelog

- 2026-06-03: Documented optional `--no-mutation` lane skip behavior alongside `--no-ui`.
- 2026-06-04: Added scoped cleanup and cleanup-provenance requirements to prevent cross-repo lane termination ambiguity.
- 2026-06-05: Added `--no-av` skip behavior to lane-filter CLI requirements.
