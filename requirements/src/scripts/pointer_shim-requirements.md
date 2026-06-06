# Pointer Shim Requirements

## Scope

Applies to `src/scripts/pointer_shim.sh`, the shared boilerplate sourced by every
thin runbook pointer (sibling repos, eggnest workspace root, and runner's own
self-run pointer) before it delegates to a runner golden.

R001  Statement: Shim enables secure umask and strict shell mode.
Design: Set `umask 007` and `set -euo pipefail` at source time so every pointer runs identically.
Tests:
- R001-T01: Verify a pointer that sources the shim runs with `umask 007` and strict shell mode.

R005  Statement: Shim resolves RUNNER_HOME from its own location.
Design: Compute `RUNNER_HOME` from the shim's physical path (`runner/src/scripts` -> `runner`) and export it, independent of the sourcing pointer.
Tests:
- R005-T01: Verify the shim exports `RUNNER_HOME` pointing at the runner tree regardless of pointer location.

R010  Statement: Shim resolves RUNBOOK_REPO_ROOT from the sourcing pointer's directory.
Design: Derive the pointer directory from `BASH_SOURCE[1]` with `pwd -P`; when that directory is a `tests/` subdir, resolve to its parent so the repo root is used. Export `RUNBOOK_REPO_ROOT`.
Tests:
- R010-T01: Verify a top-level pointer resolves `RUNBOOK_REPO_ROOT` to its own repo directory.
- R010-T02: Verify a pointer under `tests/` resolves `RUNBOOK_REPO_ROOT` to the repo root, not the tests dir.

R015  Statement: Shim sources runbook profiles via explicit profile-selection API.
Design: Provide `select_runbook_profile "<profile>"` that sources `runner/config/runbook/<profile>.env`, exports `RUNBOOK_PROFILE`, and marks the profile loaded. Fail with a clear message when the profile argument is empty or the profile file is missing.
Tests:
- R015-T01: Verify the shim sources `config/runbook/<profile>.env` for the selected profile.
- R015-T02: Verify the shim aborts when `select_runbook_profile` is called without a profile argument.

R016  Statement: Shim preserves legacy pointer compatibility for delegation.
Design: In `delegate_golden`, if a pointer still sets `RUNBOOK_PROFILE` and has not called `select_runbook_profile`, auto-load that profile before `exec` to keep older pointers working during migration.
Tests:
- R016-T01: Verify `delegate_golden` auto-loads `RUNBOOK_PROFILE` when explicit profile selection was not called.

R020  Statement: Shim delegates to the mapped runner golden with argument passthrough.
Design: Provide `delegate_golden <target> "$@"` that `exec`s `${RUNNER_HOME}/<target>`, supporting top-level goldens and nested paths (`src/scripts/...`, `tests/tNN_...`).
Tests:
- R020-T01: Verify `delegate_golden` execs the resolved golden under RUNNER_HOME and passes arguments through.
