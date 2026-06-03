#!/usr/bin/env bash
umask 007
set -euo pipefail

# Generic, knob-driven load-requirements golden. The locked per-repo NN_load_requirements
# scripts are never edited; rNN_ load pointers set knobs and exec this wrapper instead.

#R001: Establish RUNNER_HOME / RUNBOOK_REPO_ROOT contract and operate on the target repo.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/runbook_common.sh"
runbook_cd_repo

#R005: Profile knobs (defaults keep a plain `pip install -r requirements.txt`).
LOAD_REQUIREMENTS_FILES="${LOAD_REQUIREMENTS_FILES:-requirements.txt}"
LOAD_REQUIREMENTS_CPU_GPU="${LOAD_REQUIREMENTS_CPU_GPU:-false}"
LOAD_REQUIREMENTS_BOOTSTRAP_PIP="${LOAD_REQUIREMENTS_BOOTSTRAP_PIP:-false}"
LOAD_REQUIREMENTS_PIP_UPGRADE="${LOAD_REQUIREMENTS_PIP_UPGRADE:-false}"
LOAD_REQUIREMENTS_SQLCIPHER_BUILD="${LOAD_REQUIREMENTS_SQLCIPHER_BUILD:-false}"
LOAD_REQUIREMENTS_EDITABLE_SIBLINGS="${LOAD_REQUIREMENTS_EDITABLE_SIBLINGS:-}"
BOOTSTRAP_PIP_VERSION="${BOOTSTRAP_PIP_VERSION:-25.3}"
BOOTSTRAP_PIP_SHA256="${BOOTSTRAP_PIP_SHA256:-9655943313a94722b7774661c21049070f6bbb0a1516bf02f7c8d5d9201514cd}"

VENV_DIR="$VENV_NAME"

#R010: Require the venv to exist and be active (matches locked scripts' contract).
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ ERROR: Virtual environment not found! Run ./02_create_venv.sh first."
    exit 1
fi
if [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "❌ ERROR: No virtual environment is currently active!"
    echo "Activate it first:  source $VENV_DIR/bin/activate"
    exit 1
fi
EXPECTED_VENV_PATH=$(cd "$VENV_DIR" && pwd -P)
CURRENT_VENV_PATH=$(cd "${VIRTUAL_ENV:-}" && pwd -P 2>/dev/null || echo "${VIRTUAL_ENV:-}")
if [ "$CURRENT_VENV_PATH" != "$EXPECTED_VENV_PATH" ]; then
    echo "⚠️  WARNING: A different virtual environment is active!"
    echo "Expected: $EXPECTED_VENV_PATH"
    echo "Current:  $CURRENT_VENV_PATH"
    exit 1
fi
echo "✅ Virtual environment is active: $VENV_DIR"

#R015: Resolve the requirements file. Optional CPU/GPU selection mirrors teller's locked path.
REQUIREMENTS_FILE=""
if [ "$LOAD_REQUIREMENTS_CPU_GPU" = "true" ] && { [ -f "requirements-cpu.txt" ] || [ -f "requirements-gpu.txt" ]; } && [ -z "${1:-}" ]; then
    echo "Usage: $0 {cpu|gpu}"
    exit 1
fi
if [ "$LOAD_REQUIREMENTS_CPU_GPU" = "true" ] && [ -n "${1:-}" ]; then
    case "$1" in
        cpu) REQUIREMENTS_FILE="requirements-cpu.txt" ;;
        gpu) REQUIREMENTS_FILE="requirements-gpu.txt" ;;
        *) echo "Error: Invalid parameter '$1' (expected cpu|gpu)"; exit 1 ;;
    esac
fi
if [ -z "$REQUIREMENTS_FILE" ]; then
    for candidate in $LOAD_REQUIREMENTS_FILES; do
        if [ -f "$candidate" ]; then
            REQUIREMENTS_FILE="$candidate"
            break
        fi
    done
fi
if [ -z "$REQUIREMENTS_FILE" ] || [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Error: No requirements file found (looked for: ${LOAD_REQUIREMENTS_FILES})."
    exit 1
fi
echo "Using requirements file: $REQUIREMENTS_FILE"

alias pip=pip3
shopt -s expand_aliases

#R020: Optional SQLCipher build flags (classy pysqlcipher3 dependency).
if [ "$LOAD_REQUIREMENTS_SQLCIPHER_BUILD" = "true" ]; then
    SQLCIPHER_PREFIX="${SQLCIPHER_PREFIX:-}"
    if [ -z "$SQLCIPHER_PREFIX" ] && command -v brew >/dev/null 2>&1; then
        SQLCIPHER_PREFIX="$(brew --prefix sqlcipher 2>/dev/null || true)"
    fi
    if [ -z "$SQLCIPHER_PREFIX" ] || [ ! -f "$SQLCIPHER_PREFIX/include/sqlcipher/sqlite3.h" ]; then
        echo "❌ ERROR: SQLCipher headers not found; pysqlcipher3 cannot be built."
        echo "Install SQLCipher with: brew install sqlcipher (or set SQLCIPHER_PREFIX)."
        exit 1
    fi
    export CPPFLAGS="-I$SQLCIPHER_PREFIX/include ${CPPFLAGS:-}"
    export CFLAGS="-I$SQLCIPHER_PREFIX/include ${CFLAGS:-}"
    export LDFLAGS="-L$SQLCIPHER_PREFIX/lib ${LDFLAGS:-}"
    export PKG_CONFIG_PATH="$SQLCIPHER_PREFIX/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
fi

#R025: Optional hash-pinned pip bootstrap (teller) or plain upgrade (matchy/mailcart).
if [ "$LOAD_REQUIREMENTS_BOOTSTRAP_PIP" = "true" ]; then
    BOOTSTRAP_PIP_REQUIREMENTS="$(mktemp "${TMPDIR:-/tmp}/runbook-bootstrap-pip.XXXXXX.txt")"
    trap 'rm -f "$BOOTSTRAP_PIP_REQUIREMENTS"' EXIT
    cat > "$BOOTSTRAP_PIP_REQUIREMENTS" <<EOF
pip==${BOOTSTRAP_PIP_VERSION} --hash=sha256:${BOOTSTRAP_PIP_SHA256}
EOF
    pip install --upgrade --require-hashes --only-binary=:all: -r "$BOOTSTRAP_PIP_REQUIREMENTS"
elif [ "$LOAD_REQUIREMENTS_PIP_UPGRADE" = "true" ]; then
    pip install --upgrade pip
fi

#R030: Install requirements, honoring hash-pinned lockfiles when present.
if grep -q -- '--hash=sha256:' "$REQUIREMENTS_FILE"; then
    pip install --require-hashes -r "$REQUIREMENTS_FILE"
else
    pip install -r "$REQUIREMENTS_FILE"
fi

#R035: Optionally install sibling packages editable (classy depends on teller).
for sibling in $LOAD_REQUIREMENTS_EDITABLE_SIBLINGS; do
    sibling_dir="$sibling"
    case "$sibling_dir" in
        /*) ;;
        *) sibling_dir="${RUNBOOK_REPO_ROOT}/${sibling_dir}" ;;
    esac
    if [ -f "$sibling_dir/pyproject.toml" ]; then
        echo "Installing sibling package editable from: $sibling_dir"
        pip install -e "$sibling_dir"
    else
        echo "❌ ERROR: sibling package not found at $sibling_dir"
        exit 1
    fi
done
