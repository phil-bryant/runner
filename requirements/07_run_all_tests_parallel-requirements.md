# 07 run all tests parallel Requirements

## Scope

Requirements-only mode: true

Applies to `07_run_all_tests_parallel.sh`. This is the shared golden parallel orchestrator owned by the runner engine and exercised end-to-end by the consuming repos (teller/classy/matchy/mailcart) and by runner's own self-run (`11_run_all_self_tests_parallel.sh`) where its behavioral source/test traceability is enforced. Runner records it here as a self-run inventory entry so the numbered-script coverage and scope-alignment checks remain satisfied without duplicating downstream enforcement.

R065  Statement: Orchestrator supports optional lane-skip CLI flags.
Design: Parse `--no-ui` and `--no-mutation` to skip discovered lanes matching configurable content patterns (`UI_REGRESSION_PATTERN` and `MUTATION_LANE_PATTERN`) while keeping default behavior unchanged.
Tests:
- R065-T01: Verify orchestrator source usage/help text includes `--no-ui` and `--no-mutation`.
- R065-T02: Verify orchestrator source filters discovered checks using both skip patterns and exports skipped lane stems via `PARALLEL_CHECKS_SKIPPED_LANES`.

## Changelog

- 2026-06-03: Documented optional `--no-mutation` lane skip behavior alongside `--no-ui`.
