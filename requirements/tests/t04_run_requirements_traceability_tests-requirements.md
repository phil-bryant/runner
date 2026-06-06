# t04 run requirements traceability tests Wrapper Requirements

## Scope

Applies to `tests/t04_run_requirements_traceability_tests.sh`, the thin shell
entrypoint for the requirements-traceability lane. It is a delegating wrapper: it
resolves the shared runbook roots, selects the Python traceability engine on
`PYTHONPATH`, and hands the entire check to `python3 -m traceability.cli`. The
actual check behaviors it delegates to are specified per-module in the engine
requirements docs under `requirements/tests/py/traceability/`
(`cli-requirements.md`, `discovery-requirements.md`, `parsing-requirements.md`,
`verification-requirements.md`).

R001  Statement: Wrapper runs under a secure umask and strict shell mode.
Design: Set `umask 007` and `set -euo pipefail` at the top of the entrypoint so the lane fails closed on errors, unset variables, and broken pipes.
Tests:
- R001-T01: Verify the wrapper source sets `umask 007` and `set -euo pipefail`.

R005  Statement: Wrapper resolves runbook roots and runs from the target repo root.
Design: Source `src/scripts/runbook_common.sh` to resolve `RUNNER_HOME`/`RUNBOOK_REPO_ROOT`, then `cd "$RUNBOOK_REPO_ROOT"` so the check runs against the intended repo regardless of the caller's working directory.
Tests:
- R005-T01: Verify the wrapper sources `runbook_common.sh` and runs successfully from an unrelated working directory.

R010  Statement: Wrapper selects the traceability engine on PYTHONPATH (runner-first).
Design: Default `TRACEABILITY_PYTHONPATH` to `${RUNNER_HOME}/tests/py` so shared requirements/bats roots are evaluated consistently; honor a `TRACEABILITY_ENGINE_MODE=repo-first` override that falls back to the runner engine when the repo has no local engine.
Tests:
- R010-T01: Verify an end-to-end `--help` run reaches the Python CLI (engine importable on PYTHONPATH).

R020  Statement: Wrapper delegates the check to the Python traceability CLI with passthrough.
Design: `exec python3 -m traceability.cli "$@"` so all arguments are forwarded unchanged and the CLI's exit status becomes the lane's status.
Tests:
- R020-T01: Verify the wrapper delegates to `traceability.cli` and forwards arguments (usage banner on `--help`).

## Changelog

- 2026-06-06: Removed R015 and the wrapper's coverage self-exemption (the former exclude-source env knob); the wrapper is now covered by this doc like any source (anti-cheat: no self-exclusion).
- 2026-06-06: Created to reconcile the previously orphaned `#R` tags in the runner traceability wrapper and document the engine entrypoint contract. The authentic engine requirements doc (teller `ab65905^:requirements/t04_run_requirements_traceability_tests-requirements.md`, R001–R090) was recovered from git history; its behavior is now split across the wrapper doc and the per-module engine docs under `requirements/tests/py/traceability/` so each first-party source (`cli.py`, `discovery.py`, `parsing.py`, `verification.py`) is honestly traced rather than bundled behind a single thin entrypoint.
