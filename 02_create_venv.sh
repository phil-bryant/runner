#!/usr/bin/env bash
umask 007

#R001: Fail fast on unrecoverable errors.
set -euo pipefail

#R002: Establish RUNNER_HOME (code) and RUNBOOK_REPO_ROOT (target repo) contract.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/src/scripts/runbook_common.sh"
runbook_cd_repo

#R003: Profile knobs (defaults reproduce the full teller behavior).
REQUIRE_PREREQ_SCRIPT="${REQUIRE_PREREQ_SCRIPT:-true}"
VENV_EXISTS_POLICY="${VENV_EXISTS_POLICY:-continue}"
INSTALL_VENV_TEST_CACHE="${INSTALL_VENV_TEST_CACHE:-true}"
ACTIVATION_HINT="${ACTIVATION_HINT:-activate}"

#R005: Require sibling prerequisites golden unless the profile opts out (e.g. e2e).
PREREQ_SCRIPT="${RUNNER_HOME}/01_install_prerequisites.sh"
if [ "$REQUIRE_PREREQ_SCRIPT" = "true" ] && [ ! -f "$PREREQ_SCRIPT" ]; then
    echo "❌ ERROR: Prerequisites script not found: $PREREQ_SCRIPT"
    echo "Please ensure 01_install_prerequisites.sh is in the runner home directory."
    exit 1
fi

PYTHON_BIN=""
#R010: Prefer python3.12, fallback to python3.
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

#R015: Fail if no supported interpreter is available.
if [ -z "$PYTHON_BIN" ]; then
    echo "❌ ERROR: No suitable Python interpreter found (tried python3.12, python3)."
    exit 1
fi

#R020: Name venv as <repo-basename>-venv (VENV_NAME from runbook_common).
VENV_DIR="$VENV_NAME"

print_activation_hint() {
    echo ""
    echo "To activate the virtual environment, run:"
    if [ "$ACTIVATION_HINT" = "source" ]; then
        echo "  source $VENV_DIR/bin/activate"
    else
        echo "  activate"
    fi
}

#R025: Refuse creation while another virtual environment is active.
if [ -n "${VIRTUAL_ENV:-}" ]; then
    echo "❌ ERROR: A virtual environment is currently active!"
    echo ""
    echo "Please deactivate first by running:"
    echo "  deactivate"
    echo ""
    echo "Then run this script again."
    exit 1
fi

#R030: Keep venv creation idempotent; VENV_EXISTS_POLICY governs the existing-venv path.
VENV_WAS_CREATED=0
if [ -d "$VENV_DIR" ]; then
    echo "✓ Virtual environment already exists: $VENV_DIR"
    if [ "$VENV_EXISTS_POLICY" = "exit" ]; then
        print_activation_hint
        exit 0
    fi
else
    #R035: Create venv with selected interpreter.
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    VENV_WAS_CREATED=1
fi

#R038: Optionally keep Hypothesis/pytest/ruff caches out of the repository root after activation.
if [ "$INSTALL_VENV_TEST_CACHE" = "true" ] && [ -f "${RUNNER_HOME}/src/scripts/install_venv_test_cache_env.sh" ]; then
    bash "${RUNNER_HOME}/src/scripts/install_venv_test_cache_env.sh" "$VENV_DIR"
fi

#R040: Print activation guidance after successful runs.
if [ "$VENV_WAS_CREATED" -eq 1 ]; then
    echo "✓ Created virtual environment: $VENV_DIR"
fi
print_activation_hint
