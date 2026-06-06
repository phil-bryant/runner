# 05 run e2e tests Requirements

## Scope

Applies to `05_run_e2e_tests.sh`, the runner golden that runs the eggnest
engine-level end-to-end matching cases through the workspace virtualenv and
offers an optional online `--record` mode for refreshing AI recordings.

R001  Statement: Script enforces strict fail-fast shell behavior.
Design: Enable `set -euo pipefail` near the top so any unset variable, failed command, or broken pipe aborts the run immediately.
Tests:
- R001-T01: Verify the script enables `set -euo pipefail` for strict fail-fast behavior.

R005  Statement: Script sources the runbook contract and resolves repo and venv paths.
Design: Source `src/scripts/runbook_common.sh`, set `REPO_ROOT` from `RUNBOOK_REPO_ROOT`, and derive `PYTHON_BIN`, `TESTS_DIR`, and `E2E_TEST` from the resolved repo root and venv name.
Tests:
- R005-T01: Verify the script sources `runbook_common.sh` and resolves the repo root, venv python, tests dir, and e2e test paths.

R015  Statement: Script requires the workspace venv python to be present and executable.
Design: When `PYTHON_BIN` is not an executable file, print remediation guidance and exit with status 1 before doing any work.
Tests:
- R015-T01: Verify the script exits with an error when the venv python is not executable.

R020  Statement: Script supports an optional online `--record` mode that refreshes recordings then exits.
Design: When the first argument is `--record`, shift it off, change to the repo root, run `harness.record` with remaining arguments against the real LLM ranker, and exit 0.
Tests:
- R020-T01: Verify the `--record` mode invokes `harness.record` and exits without running the offline pytest lane.

R025  Statement: Script refuses to run when pytest is unavailable in the venv.
Design: Probe `pytest --version` in the venv python; when it is missing, print remediation guidance and exit with status 1.
Tests:
- R025-T01: Verify the script exits with an error when pytest is not available in the venv.

R030  Statement: Script runs the engine-level e2e matching cases via pytest with argument passthrough.
Design: Change to the repo root and run the `test_e2e_cases.py` suite through the venv pytest with `PYTHONPATH` pointed at the tests dir, forwarding any extra arguments.
Tests:
- R030-T01: Verify the script runs the e2e test suite through pytest and forwards passthrough arguments.
