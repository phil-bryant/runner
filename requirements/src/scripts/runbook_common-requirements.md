# Runbook Common Contract Requirements

## Scope

Applies to `src/scripts/runbook_common.sh`.

R001  Statement: Resolve `RUNNER_HOME` from this helper's own on-disk location.
Design: Derive `RUNNER_HOME` two levels up from `runner/src/scripts` using `BASH_SOURCE`, and export it for golden scripts to locate runner-owned code/helpers.
Tests:
- R001-T01: Source the helper and verify `RUNNER_HOME` is exported and points at the runner tree root.

R005  Statement: Default the operated-on repository to `RUNNER_HOME` for backward-compatible direct runs.
Design: Set `RUNBOOK_REPO_ROOT` to `RUNNER_HOME` when unset, canonicalize it, and export it so thin pointers can override per repo.
Tests:
- R005-T01: Source the helper with `RUNBOOK_REPO_ROOT` unset and verify it defaults to `RUNNER_HOME`.

R010  Statement: Derive the repo display name and conventional venv directory name.
Design: Compute `RUNBOOK_REPO_NAME` from the repo root basename and `VENV_NAME` as `<repo>-venv` unless overridden, exporting both.
Tests:
- R010-T01: Source the helper and verify `RUNBOOK_REPO_NAME` and `VENV_NAME` follow the `<repo>`/`<repo>-venv` convention.

R012  Statement: Shared traceability/test asset roots default to the operated-on repository.
Design: Default `TRACEABILITY_REQUIREMENTS_ROOTS` and `TRACEABILITY_TEST_ROOTS` under `RUNBOOK_REPO_ROOT` and export them.
Tests:
- R012-T01: Source the helper and verify the traceability requirement/test roots resolve under the repo root.

R013  Statement: Shell lane discovery defaults to the traceability test roots.
Design: Default `SHELL_BATS_ROOTS` to `TRACEABILITY_TEST_ROOTS` so bats discovery and requirements-to-test mapping share roots.
Tests:
- R013-T01: Source the helper and verify `SHELL_BATS_ROOTS` matches `TRACEABILITY_TEST_ROOTS`.

R015  Statement: Operate from the target repository root on demand.
Design: `runbook_cd_repo` changes the working directory into `RUNBOOK_REPO_ROOT`.
Tests:
- R015-T01: Define `runbook_cd_repo`, invoke it, and verify the working directory becomes the repo root.

R020  Statement: Provide uniform status output helpers for goldens.
Design: `rb_info`, `rb_ok`, `rb_warn`, and `rb_err` emit consistent info/success/warning/error formatting (errors to stderr).
Tests:
- R020-T01: Invoke the status helpers and verify their success/warning/error prefixes and stream routing.

R025  Statement: Ensure a Homebrew formula is present, installing it when missing.
Design: `rb_ensure_brew_formula` short-circuits when the probe command is already on PATH and otherwise installs via Homebrew.
Tests:
- R025-T01: Call `rb_ensure_brew_formula` for an already-present command and verify it reports availability without installing.

R030  Statement: Install a newline/space separated `BREW_FORMULAS` spec.
Design: `rb_install_brew_formulas` parses `formula` or `formula:command` entries and ensures each; an empty spec is a no-op.
Tests:
- R030-T01: Call `rb_install_brew_formulas` with an empty spec and verify it returns success without action.

R035  Statement: Resolve a usable Python interpreter for the target repo venv.
Design: `rb_repo_python` prefers the repo venv `python3` when importable and otherwise falls back to `command -v python3`.
Tests:
- R035-T01: Call `rb_repo_python` with no venv present and verify it falls back to a PATH `python3`.

R040  Statement: Resolve 1psa items with a bounded timeout to prevent stuck prompts.
Design: `rb_read_1psa_item` invokes `1psa` under a configurable `RB_ONEPSA_TIMEOUT_SECONDS` bound.
Tests:
- R040-T01: Verify `rb_read_1psa_item` honors the `RB_ONEPSA_TIMEOUT_SECONDS` timeout knob.

R041  Statement: Fall back to environment variables when 1psa cannot resolve an item.
Design: When `1psa` is missing or fails for any reason, `rb_read_1psa_item` resolves the item from the matching environment variable before hard-failing.
Tests:
- R041-T01: With `1psa` unavailable and a matching env var set, verify `rb_read_1psa_item` returns the env value.
- R041-T02: Verify 1psa command failures still recover via dotenv `ITEM.password` lookup.

R042  Statement: Provide case-insensitive environment-variable secret fallback.
Design: `rb_lookup_env_fallback` tries the item name verbatim, then an uppercased variant, emitting only the value.
Tests:
- R042-T01: Verify `rb_lookup_env_fallback` resolves a lowercase item name from its uppercased environment variable.
- R042-T02: Verify password fallback checks `ITEM.password` before bare `ITEM` in dotenv.
