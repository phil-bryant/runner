# 11 run all self tests parallel Pointer Requirements

## Scope

Applies to `11_run_all_self_tests_parallel.sh`, the runner self-run entrypoint.
It is a **thin pointer**: it sources the shared shim, selects the "runner"
runbook profile, and delegates to the parallel-orchestrator golden
07_run_all_tests_parallel.sh. The orchestrator's behavior is specified and
enforced in its own requirements doc; this doc covers only the pointer's
delegation contract (the sanctioned pattern that replaces
"Requirements-only mode: true" for delegating scripts).

R001  Statement: Pointer runs through the shared runbook shim.
Design: Source `src/scripts/pointer_shim.sh`, which establishes `umask 007`, `set -euo pipefail`, and `RUNNER_HOME`/`RUNBOOK_REPO_ROOT` resolution before delegation.
Tests:
- R001-T01: Verify the pointer sources `pointer_shim.sh`.

R005  Statement: Pointer selects the runner self-run profile explicitly.
Design: Call `select_runbook_profile "runner"` so `config/runbook/runner.env` is sourced before the golden runs.
Tests:
- R005-T01: Verify the pointer calls `select_runbook_profile "runner"`.

R010  Statement: Pointer delegates to the orchestrator golden with passthrough.
Design: Call `delegate_golden "07_run_all_tests_parallel.sh" "$@"` so the shim execs `${RUNNER_HOME}/07_run_all_tests_parallel.sh` with arguments unchanged.
Tests:
- R010-T01: Verify the pointer delegates to `07_run_all_tests_parallel.sh` with `"$@"`.

## Changelog

- 2026-06-06: Converted from `Requirements-only mode: true` to a full thin-pointer doc + thin test, per the policy that delegating scripts use thin pointer docs (never requirements-only) to cover their delegation contract.
