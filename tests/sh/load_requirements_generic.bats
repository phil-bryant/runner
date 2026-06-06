#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/load_requirements_generic.sh (generic load-requirements golden).

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/load_requirements_generic.sh"
}

@test "sources runbook_common contract and cds into the repo root" {
  #R001-T01: Verify the script sources runbook_common.sh and changes into the repo root via runbook_cd_repo.
  run bash -n "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'source "${SCRIPT_DIR}/runbook_common.sh"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q '^runbook_cd_repo' "$SRC"
  [ "$status" -eq 0 ]
}

@test "default knobs keep a plain requirements.txt install" {
  #R005-T01: Verify default knob values keep a plain requirements.txt install with optional paths disabled.
  run grep -q 'LOAD_REQUIREMENTS_FILES="${LOAD_REQUIREMENTS_FILES:-requirements.txt}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'LOAD_REQUIREMENTS_BOOTSTRAP_PIP="${LOAD_REQUIREMENTS_BOOTSTRAP_PIP:-false}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'LOAD_REQUIREMENTS_SQLCIPHER_BUILD="${LOAD_REQUIREMENTS_SQLCIPHER_BUILD:-false}"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "errors when the target venv is missing" {
  #R010-T01: Run the script against a repo root with no venv and verify it errors that the virtual environment was not found.
  workdir="${BATS_TEST_TMPDIR}/repo"
  mkdir -p "$workdir"
  run env RUNBOOK_REPO_ROOT="$workdir" VIRTUAL_ENV="" bash "$SRC"
  [ "$status" -ne 0 ]
  [[ "$output" == *"Virtual environment not found"* ]]
}

@test "maps cpu/gpu selection to matching requirements files" {
  #R015-T01: Verify the script maps cpu/gpu selection to requirements-cpu.txt/requirements-gpu.txt.
  run grep -q 'cpu) REQUIREMENTS_FILE="requirements-cpu.txt"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'gpu) REQUIREMENTS_FILE="requirements-gpu.txt"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "SQLCipher branch exports build flags and guards missing headers" {
  #R020-T01: Verify the SQLCipher branch exports build flags and fails when SQLCipher headers are missing.
  run grep -q 'SQLCIPHER_PREFIX/include/sqlcipher/sqlite3.h' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'export CPPFLAGS="-I\$SQLCIPHER_PREFIX/include' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'SQLCipher headers not found' "$SRC"
  [ "$status" -eq 0 ]
}

@test "supports hash-pinned pip bootstrap or plain upgrade" {
  #R025-T01: Verify the bootstrap branch performs a hash-pinned pip install and the alternate branch performs a plain upgrade.
  run grep -q 'pip install --upgrade --require-hashes --only-binary=:all: -r "$BOOTSTRAP_PIP_REQUIREMENTS"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'pip install --upgrade pip' "$SRC"
  [ "$status" -eq 0 ]
}

@test "selects require-hashes only for hash-pinned lockfiles" {
  #R030-T01: Verify the installer selects --require-hashes only when the requirements file is hash-pinned.
  run grep -q "grep -q -- '--hash=sha256:' \"\$REQUIREMENTS_FILE\"" "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'pip install --require-hashes -r "$REQUIREMENTS_FILE"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'pip install -r "$REQUIREMENTS_FILE"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "editable siblings loop requires pyproject and installs editable" {
  #R035-T01: Verify the editable-siblings loop requires pyproject.toml and installs each sibling editable.
  run grep -q 'for sibling in $LOAD_REQUIREMENTS_EDITABLE_SIBLINGS' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'if \[ -f "$sibling_dir/pyproject.toml" \]' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'pip install -e "$sibling_dir"' "$SRC"
  [ "$status" -eq 0 ]
}
