#!/usr/bin/env bats
# Source-assertion unit tests for 02_create_venv.sh (runner golden venv setup).
# These tests verify that the implementing code for each requirement physically
# exists in the script without executing the venv creation (no network, sudo,
# or external interpreter side effects).

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/02_create_venv.sh"
}

@test "script enables fail-fast strict shell mode" {
  #R001-T01: source enables set -euo pipefail
  grep -q 'set -euo pipefail' "$SCRIPT"
}

@test "script wires the shared runbook contract" {
  #R002-T01: source sources runbook_common.sh and calls runbook_cd_repo
  grep -q 'runbook_common.sh' "$SCRIPT"
  grep -q 'runbook_cd_repo' "$SCRIPT"
}

@test "script defines profile knobs with defaults" {
  #R003-T01: source defines the four profile knobs with default values
  grep -q 'REQUIRE_PREREQ_SCRIPT="${REQUIRE_PREREQ_SCRIPT:-true}"' "$SCRIPT"
  grep -q 'VENV_EXISTS_POLICY="${VENV_EXISTS_POLICY:-continue}"' "$SCRIPT"
  grep -q 'INSTALL_VENV_TEST_CACHE="${INSTALL_VENV_TEST_CACHE:-true}"' "$SCRIPT"
  grep -q 'ACTIVATION_HINT="${ACTIVATION_HINT:-activate}"' "$SCRIPT"
}

@test "script requires sibling 01 prerequisites unless opted out" {
  #R005-T01: source guards on REQUIRE_PREREQ_SCRIPT and references 01_install_prerequisites.sh
  grep -q 'REQUIRE_PREREQ_SCRIPT' "$SCRIPT"
  grep -q '01_install_prerequisites.sh' "$SCRIPT"
}

@test "script prefers python3.12 then falls back to python3" {
  #R010-T01: source probes python3.12 then python3
  grep -q 'command -v python3.12' "$SCRIPT"
  grep -q 'command -v python3' "$SCRIPT"
}

@test "script fails when no interpreter is available" {
  #R015-T01: source errors out when no supported interpreter is found
  grep -q 'No suitable Python interpreter found' "$SCRIPT"
}

@test "script names the venv from VENV_NAME" {
  #R020-T01: source assigns VENV_DIR from VENV_NAME
  grep -q 'VENV_DIR="\$VENV_NAME"' "$SCRIPT"
}

@test "script refuses creation while another venv is active" {
  #R025-T01: source detects active VIRTUAL_ENV and refuses
  grep -q 'VIRTUAL_ENV' "$SCRIPT"
  grep -q 'A virtual environment is currently active' "$SCRIPT"
}

@test "script honors VENV_EXISTS_POLICY for an existing venv" {
  #R030-T01: source branches on existing venv directory and honors exit policy
  grep -q 'if \[ -d "\$VENV_DIR" \]' "$SCRIPT"
  grep -q 'VENV_EXISTS_POLICY" = "exit"' "$SCRIPT"
}

@test "script creates the venv with the selected interpreter" {
  #R035-T01: source creates the venv via -m venv with selected interpreter
  grep -q '"\$PYTHON_BIN" -m venv "\$VENV_DIR"' "$SCRIPT"
}

@test "script optionally installs the test-cache environment" {
  #R038-T01: source conditionally runs install_venv_test_cache_env.sh
  grep -q 'INSTALL_VENV_TEST_CACHE' "$SCRIPT"
  grep -q 'install_venv_test_cache_env.sh' "$SCRIPT"
}

@test "script prints activation guidance" {
  #R040-T01: source defines and calls print_activation_hint
  grep -q 'print_activation_hint()' "$SCRIPT"
  grep -q 'print_activation_hint$' "$SCRIPT"
}
