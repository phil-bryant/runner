# Generic Load-Requirements Golden Requirements

## Scope

Applies to `src/scripts/load_requirements_generic.sh`.

R001  Statement: Establish the runner/repo contract and operate on the target repo.
Design: Source `runbook_common.sh` to set `RUNNER_HOME`/`RUNBOOK_REPO_ROOT` and `runbook_cd_repo` into the operated-on repository before installing.
Tests:
- R001-T01: Verify the script sources `runbook_common.sh` and changes into the repo root via `runbook_cd_repo`.

R005  Statement: Drive behavior from profile knobs with safe defaults.
Design: Provide `LOAD_REQUIREMENTS_*` knobs that default to a plain `pip install -r requirements.txt` with all optional behaviors off.
Tests:
- R005-T01: Verify default knob values keep a plain `requirements.txt` install with optional paths disabled.

R010  Statement: Require the target venv to exist and be the active interpreter.
Design: Fail when the conventional venv directory is missing, when no venv is active, or when a different venv is active than expected.
Tests:
- R010-T01: Run the script against a repo root with no venv and verify it errors that the virtual environment was not found.

R015  Statement: Resolve the requirements file, supporting optional CPU/GPU selection.
Design: When CPU/GPU mode is enabled, require and map a `cpu`/`gpu` argument to the matching requirements file; otherwise pick the first existing candidate from the knob list.
Tests:
- R015-T01: Verify the script maps `cpu`/`gpu` selection to `requirements-cpu.txt`/`requirements-gpu.txt`.

R020  Statement: Support optional SQLCipher build flags for pysqlcipher3 dependents.
Design: When the SQLCipher build knob is set, resolve the SQLCipher prefix and export `CPPFLAGS`/`CFLAGS`/`LDFLAGS`/`PKG_CONFIG_PATH`, failing when headers are absent.
Tests:
- R020-T01: Verify the SQLCipher branch exports build flags and fails when SQLCipher headers are missing.

R025  Statement: Support an optional hash-pinned pip bootstrap or a plain pip upgrade.
Design: When bootstrap is enabled, install a hash-pinned `pip==<version>` via `--require-hashes --only-binary`; otherwise optionally upgrade pip plainly.
Tests:
- R025-T01: Verify the bootstrap branch performs a hash-pinned pip install and the alternate branch performs a plain upgrade.

R030  Statement: Install requirements honoring hash-pinned lockfiles when present.
Design: Install with `--require-hashes` when the resolved requirements file contains `--hash=sha256:` pins, otherwise install normally.
Tests:
- R030-T01: Verify the installer selects `--require-hashes` only when the requirements file is hash-pinned.

R035  Statement: Optionally install sibling packages in editable mode.
Design: For each entry in the editable-siblings knob, resolve its directory, require a `pyproject.toml`, and `pip install -e` it.
Tests:
- R035-T01: Verify the editable-siblings loop requires `pyproject.toml` and installs each sibling editable.
