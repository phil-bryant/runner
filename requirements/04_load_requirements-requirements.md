# 04 load requirements Requirements

## Scope

Applies to `04_load_requirements.sh`, the thin runner self-run compatibility shim
that prepares a secure, runner-targeted environment and then delegates the actual
requirements load to the canonical generic loader (load_requirements_generic). The
shim exists so direct `./04_load_requirements.sh` invocations against the runner
repo itself keep the runner profile's secure bootstrap defaults without
duplicating (and drifting from) the generic loader's logic.

R001  Statement: Shim runs with a secure umask and strict shell mode.
Design: Set `umask 007` and `set -euo pipefail` at the top of the script so the self-run shim fails fast and creates artifacts with restrictive permissions.
Tests:
- R001-T01: Verify `04_load_requirements.sh` sets `umask 007` and enables `set -euo pipefail`.

R005  Statement: Shim resolves its own directory and defaults RUNBOOK_REPO_ROOT to it.
Design: Compute `SCRIPT_DIR` from `BASH_SOURCE[0]` with `pwd`, then export `RUNBOOK_REPO_ROOT` defaulting to `SCRIPT_DIR` when the caller has not already set it, so self-runs target the runner repo.
Tests:
- R005-T01: Verify the shim derives `SCRIPT_DIR` from `BASH_SOURCE[0]` and exports `RUNBOOK_REPO_ROOT` defaulting to `SCRIPT_DIR`.

R010  Statement: Shim sources the runner profile only for self-runs without a preloaded profile.
Design: When `RUNBOOK_REPO_ROOT` equals `SCRIPT_DIR`, no `RUNBOOK_PROFILE_LOADED` is set, and `config/runbook/runner.env` exists, source that profile and mark `RUNBOOK_PROFILE_LOADED=runner` so self-test workflows inherit the pinned-pip bootstrap defaults.
Tests:
- R010-T01: Verify the shim guards profile sourcing on the self-run, unloaded-profile, env-present conditions before sourcing `config/runbook/runner.env`.
- R010-T02: Verify the shim marks `RUNBOOK_PROFILE_LOADED=runner` after sourcing the runner profile.

R015  Statement: Shim delegates to the canonical generic loader with argument passthrough.
Design: `exec` `${SCRIPT_DIR}/src/scripts/load_requirements_generic.sh "$@"` so the canonical loader performs the real work and all arguments are passed through unchanged, avoiding drift.
Tests:
- R015-T01: Verify the shim execs `src/scripts/load_requirements_generic.sh` passing `"$@"` through unchanged.
