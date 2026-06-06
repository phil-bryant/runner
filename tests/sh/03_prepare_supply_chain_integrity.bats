#!/usr/bin/env bats
# Source-assertion unit tests for 03_prepare_supply_chain_integrity.sh.
# These assert the golden's documented behavior by inspecting the script text;
# they deliberately do NOT execute pip-compile, require a venv, or touch the
# network, since the real lane mutates lockfiles and supply-chain artifacts.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/03_prepare_supply_chain_integrity.sh"
}

@test "runs fail-fast in strict shell mode and operates on the target repo root" {
  #R001-T01: strict shell mode and target repo root resolution
  [ -f "$SCRIPT" ]
  grep -q 'set -euo pipefail' "$SCRIPT"
  grep -q 'umask 007' "$SCRIPT"
  grep -q 'RUNBOOK_REPO_ROOT' "$SCRIPT"
}

@test "requires the project venv to exist and be the active VIRTUAL_ENV" {
  #R005-T01: project venv exists and active VIRTUAL_ENV matches
  grep -q 'VENV_DIR' "$SCRIPT"
  grep -q 'VIRTUAL_ENV' "$SCRIPT"
  grep -q 'EXPECTED_VENV_PATH' "$SCRIPT"
}

@test "compiles hash-pinned lockfiles from pip-tools manifests via pip-compile" {
  #R010-T01: requires pip-compile and compiles hashed lockfiles
  grep -q 'command -v pip-compile' "$SCRIPT"
  grep -q 'generate-hashes' "$SCRIPT"
  grep -q 'resolver=backtracking' "$SCRIPT"
}

@test "removes the legacy venv pip-tools package before compiling" {
  #R010-T02: legacy venv pip-tools removed before compile
  grep -q 'pip uninstall -y pip-tools' "$SCRIPT"
}

@test "prepares SBOM and signing scaffold artifacts via the security generator" {
  #R015-T01: SBOM/signing artifacts generated with resolved signing mode
  grep -q 'generate_supply_chain_artifacts.py' "$SCRIPT"
  grep -q 'signing-mode' "$SCRIPT"
}

@test "defaults the signing mode to required in CI and scaffold otherwise" {
  #R020-T01: signing mode defaults required in CI else scaffold
  grep -q 'SIGNING_MODE="required"' "$SCRIPT"
  grep -q 'SIGNING_MODE="scaffold"' "$SCRIPT"
}
