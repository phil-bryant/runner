# 03 prepare supply chain integrity Requirements

## Scope

Applies to `03_prepare_supply_chain_integrity.sh`. This runner golden prepares supply-chain integrity artifacts (hash-pinned lockfiles plus SBOM/signing scaffolding) before the install and test lanes, running fail-fast inside the project virtual environment.

R001  Statement: Run fail-fast in strict shell mode and operate on the target repository root.
Design: Set a secure `umask 007` and `set -euo pipefail`, resolve `REPO_ROOT` from `RUNBOOK_REPO_ROOT` (defaulting to the script directory), and `cd` into it before doing any work.
Tests:
- R001-T01: Assert the script enables strict shell mode (`set -euo pipefail`) and resolves the target repo root via `RUNBOOK_REPO_ROOT` (`tests/sh/03_prepare_supply_chain_integrity.bats`).

R005  Statement: Require the project `<dir>-venv` virtual environment to exist and be the active `VIRTUAL_ENV`.
Design: Derive `VENV_DIR` from the current directory name and fail if the directory is missing, if no `VIRTUAL_ENV` is active, or if the active `VIRTUAL_ENV` resolved path does not match the expected project venv path.
Tests:
- R005-T01: Assert the script checks for the project venv directory and matches the active `VIRTUAL_ENV` resolved path against the expected venv path (`tests/sh/03_prepare_supply_chain_integrity.bats`).

R010  Statement: Compile hash-pinned runtime and security lockfiles from pip-tools `.in` manifests.
Design: Require `pip-compile` on PATH, remove any legacy venv `pip-tools` package to satisfy the dependency-freshness gate, then run `pip-compile --generate-hashes --resolver=backtracking` for the runtime and security source manifests.
Tests:
- R010-T01: Assert the script requires `pip-compile` on PATH and compiles hashed lockfiles with `--generate-hashes` and `--resolver=backtracking` (`tests/sh/03_prepare_supply_chain_integrity.bats`).
- R010-T02: Assert the script removes the legacy venv `pip-tools` package before compiling (`tests/sh/03_prepare_supply_chain_integrity.bats`).

R015  Statement: Prepare SBOM and signing scaffold artifacts before install and test lanes.
Design: Invoke `src/scripts/security/generate_supply_chain_artifacts.py` with the runtime/security lockfiles, output directory, and resolved signing mode.
Tests:
- R015-T01: Assert the script generates SBOM/signing artifacts via `generate_supply_chain_artifacts.py` with the resolved signing mode (`tests/sh/03_prepare_supply_chain_integrity.bats`).

R020  Statement: Default the supply-chain signing mode to required in CI and scaffold otherwise.
Design: When `SUPPLY_CHAIN_SIGNING_MODE` is unset, select `required` if `CI` is `true`/`1`, else `scaffold`; otherwise honor the provided value.
Tests:
- R020-T01: Assert the script defaults the signing mode to `required` under CI and to `scaffold` when CI is not set (`tests/sh/03_prepare_supply_chain_integrity.bats`).
