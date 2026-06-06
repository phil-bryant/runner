# 02 create venv Requirements

## Scope

These requirements govern `02_create_venv.sh`, the shared runner golden that
provisions the per-repo Python virtual environment. The script runs under the
shared runbook contract (the shared runbook_common helper), selects a Python
interpreter, and creates a `<repo>-venv` directory while honoring the profile
knobs that let consuming repos (teller/classy/matchy/mailcart) tune its
behavior. Every requirement below maps 1:1 to a scoped `#Rxxx:` tag in
`02_create_venv.sh` and is exercised by source-assertion tests in
`tests/sh/02_create_venv.bats`.

R001  Statement: The script runs in fail-fast strict shell mode so any unhandled error, unset variable, or failed pipe stage aborts the run.
Design: The very first executable line enables `set -euo pipefail` before any other logic executes.
Tests:
- R001-T01: Assert the source enables `set -euo pipefail`.

R002  Statement: The script establishes the RUNNER_HOME (engine) and RUNBOOK_REPO_ROOT (target repo) contract through the shared runbook helper and operates from the target repo root.
Design: It resolves its own directory, sources `src/scripts/runbook_common.sh`, then calls `runbook_cd_repo` to change into the target repository.
Tests:
- R002-T01: Assert the source sources `runbook_common.sh` and invokes `runbook_cd_repo`.

R003  Statement: The script exposes profile knobs with full-teller defaults so consuming profiles can tune prerequisite enforcement, existing-venv policy, test-cache installation, and activation hint style.
Design: It assigns `REQUIRE_PREREQ_SCRIPT`, `VENV_EXISTS_POLICY`, `INSTALL_VENV_TEST_CACHE`, and `ACTIVATION_HINT` using `${VAR:-default}` defaults that reproduce the original teller behavior.
Tests:
- R003-T01: Assert the source defines the four profile knobs with their default values.

R005  Statement: The script requires the sibling 01 prerequisites golden to exist unless the active profile opts out of that check.
Design: When `REQUIRE_PREREQ_SCRIPT` is true and `${RUNNER_HOME}/01_install_prerequisites.sh` is missing, it prints an error and exits non-zero.
Tests:
- R005-T01: Assert the source guards on `REQUIRE_PREREQ_SCRIPT` and references `01_install_prerequisites.sh`.

R010  Statement: The script prefers a `python3.12` interpreter and falls back to `python3` when 3.12 is unavailable.
Design: It probes `command -v python3.12` first and, failing that, `command -v python3`, recording the choice in `PYTHON_BIN`.
Tests:
- R010-T01: Assert the source probes `python3.12` then falls back to `python3`.

R015  Statement: The script fails if no supported Python interpreter can be found.
Design: When `PYTHON_BIN` is still empty after interpreter selection, it prints a "No suitable Python interpreter found" error and exits non-zero.
Tests:
- R015-T01: Assert the source errors out when no interpreter is found.

R020  Statement: The script names the virtual environment directory `<repo-basename>-venv` using the shared VENV_NAME value.
Design: It sets `VENV_DIR` to `$VENV_NAME`, which the runbook contract derives from the repository basename.
Tests:
- R020-T01: Assert the source assigns `VENV_DIR` from `VENV_NAME`.

R025  Statement: The script refuses to create a venv while another virtual environment is already active.
Design: When `VIRTUAL_ENV` is non-empty it prints a deactivate-first error and exits non-zero before touching any venv.
Tests:
- R025-T01: Assert the source detects an active `VIRTUAL_ENV` and refuses to continue.

R030  Statement: The script keeps venv handling idempotent, with VENV_EXISTS_POLICY governing what happens when the venv directory already exists.
Design: When the venv directory exists it reports the fact and, if `VENV_EXISTS_POLICY` is `exit`, prints the activation hint and exits zero instead of recreating.
Tests:
- R030-T01: Assert the source branches on an existing venv directory and honors the `exit` policy.

R035  Statement: The script creates the virtual environment with the selected interpreter when none exists yet.
Design: In the else branch it prints a creation message and runs `"$PYTHON_BIN" -m venv "$VENV_DIR"`, marking the venv as freshly created.
Tests:
- R035-T01: Assert the source creates the venv via `-m venv` with the selected interpreter.

R038  Statement: The script optionally installs the test-cache environment so Hypothesis/pytest/ruff caches stay out of the repository root after activation.
Design: When `INSTALL_VENV_TEST_CACHE` is true and the helper exists, it runs `src/scripts/install_venv_test_cache_env.sh` against the venv directory.
Tests:
- R038-T01: Assert the source conditionally runs `install_venv_test_cache_env.sh`.

R040  Statement: The script prints activation guidance after a successful run.
Design: It defines and calls `print_activation_hint`, which emits either a `source .../activate` line or the `activate` shortcut depending on `ACTIVATION_HINT`.
Tests:
- R040-T01: Assert the source defines and calls `print_activation_hint`.
