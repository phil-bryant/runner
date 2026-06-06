#!/usr/bin/env bash
umask 007

#R001: Run with bash and fail fast on unrecoverable errors.
set -euo pipefail

#R002: Establish RUNNER_HOME (code) and RUNBOOK_REPO_ROOT (target repo) contract.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/src/scripts/runbook_common.sh"

#R003: Profile knobs. Defaults reproduce the full teller installer when run directly.
PREREQ_MODE="${PREREQ_MODE:-install}"
PREREQ_BANNER="${PREREQ_BANNER:-Prerequisites Installer}"
BREW_FORMULAS="${BREW_FORMULAS:-go git swiftlint shellcheck gitleaks bats-core:bats clamav:clamscan perl cpanminus:cpanm mkcert peripheryapp/periphery/periphery:periphery pip-tools:pip-compile sqlcipher:sqlcipher cosign:cosign}"
BREW_CASKS="${BREW_CASKS:-}"
PREREQ_ENABLE_ZAP="${PREREQ_ENABLE_ZAP:-true}"
PREREQ_ENABLE_1PSA="${PREREQ_ENABLE_1PSA:-true}"
PREREQ_1PSA_ADVISORY="${PREREQ_1PSA_ADVISORY:-false}"
PREREQ_1PSA_SUDO_VIA_1PSA="${PREREQ_1PSA_SUDO_VIA_1PSA:-true}"
PREREQ_ENABLE_XCODE="${PREREQ_ENABLE_XCODE:-true}"
PREREQ_ENABLE_XCODE_TOOLCHAIN="${PREREQ_ENABLE_XCODE_TOOLCHAIN:-false}"
PREREQ_ENABLE_XCODE_FIRST_LAUNCH="${PREREQ_ENABLE_XCODE_FIRST_LAUNCH:-false}"
PREREQ_ENABLE_SWIFT="${PREREQ_ENABLE_SWIFT:-false}"
PREREQ_ENABLE_PG_INSTALL="${PREREQ_ENABLE_PG_INSTALL:-true}"
PREREQ_ENABLE_PGTAP="${PREREQ_ENABLE_PGTAP:-true}"
PREREQ_VERIFY_COMMANDS="${PREREQ_VERIFY_COMMANDS:-}"
PREREQ_VERIFY_SQLCIPHER_HEADERS="${PREREQ_VERIFY_SQLCIPHER_HEADERS:-false}"
PREREQ_FINAL_GUIDANCE="${PREREQ_FINAL_GUIDANCE:-}"
PREREQ_SUCCESS_GUIDANCE="${PREREQ_SUCCESS_GUIDANCE:-}"
PREREQ_EXTRA_HOOK="${PREREQ_EXTRA_HOOK:-}"

#R004: Sibling tooling clones live beside the target repo (default parent of RUNBOOK_REPO_ROOT).
PARENT_DIR="$(dirname "$RUNBOOK_REPO_ROOT")"
ONEPSA_REPO_URL="${ONEPSA_REPO_URL:-https://github.com/phil-bryant/1psa.git}"
ONEPSA_DIR="${ONEPSA_DIR:-${PARENT_DIR}/1psa}"
ONEPSA_LOCAL_BIN="${ONEPSA_DIR}/bin/1psa"
PG_INSTALL_REPO_URL="${PG_INSTALL_REPO_URL:-https://github.com/phil-bryant/pg_install}"
PG_INSTALL_DIR="${PG_INSTALL_DIR:-${PARENT_DIR}/pg_install}"
PGTAP_REPO_URL="${PGTAP_REPO_URL:-https://github.com/theory/pgtap.git}"
PGTAP_DIR="${PGTAP_DIR:-${PARENT_DIR}/pgtap}"
ZAP_APP_PATH="${ZAP_APP_PATH:-/Applications/ZAP.app}"
ZAP_CLI_PATH="${ZAP_CLI_PATH:-${ZAP_APP_PATH}/Contents/MacOS/ZAP.sh}"
#R020: Default sudo credential item/field, overridable via environment.
PSA_INSTALL_SUDO_ITEM="${PSA_INSTALL_SUDO_ITEM:-odus}"

#R001: shard-3 function tag
print_header() {
    echo "============================================================"
    echo "${PREREQ_BANNER}"
    echo "============================================================"
    echo ""
}

ensure_homebrew() {
    #R005: Verify Homebrew is present before package actions.
    echo "[Homebrew] Checking..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "❌ [Homebrew] Not installed."
        echo ""
        echo "Please install Homebrew first by running:"
        echo "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo ""
        echo "After installation, add Homebrew to your PATH and run this script again."
        echo "For more information, visit: https://brew.sh/"
        exit 1
    fi
    echo "✅ [Homebrew] Installed"
}

ensure_pgtap_source_install() {
    #R085: Ensure pgTAP source is present and installed when pg_prove is missing.
    echo ""
    echo "[pgTAP] Checking..."
    if { command -v pg_prove >/dev/null 2>&1 && pg_prove --version >/dev/null 2>&1; } || [ -x "${HOME}/perl5/bin/pg_prove" ]; then
        echo "✅ [pgTAP] pg_prove available (PATH or ~/perl5/bin)"
        return
    fi
    echo "⚠️  [pgTAP] pg_prove missing on PATH"
    if [ -d "$PGTAP_DIR/.git" ]; then
        echo "✅ [pgTAP] Source repository present at ${PGTAP_DIR}"
    elif [ -e "$PGTAP_DIR" ]; then
        echo "❌ [pgTAP] ${PGTAP_DIR} exists but is not a git repository"
        echo "Please remove or rename it, then run this script again."
        exit 1
    else
        rb_ensure_brew_formula "git"
        echo "[pgTAP] Cloning source into ${PARENT_DIR}..."
        git clone "$PGTAP_REPO_URL" "$PGTAP_DIR"
    fi
    if [ ! -f "${PGTAP_DIR}/Makefile" ]; then
        echo "❌ [pgTAP] Missing Makefile in ${PGTAP_DIR}"
        exit 1
    fi
    echo "[pgTAP] Building from source..."
    make -C "$PGTAP_DIR"
    echo "[pgTAP] Installing from source..."
    make -C "$PGTAP_DIR" install
    echo "✅ [pgTAP] Source install completed"
}

ensure_pgtap_sourcehandler() {
    #R090: Ensure TAP::Parser::SourceHandler::pgTAP installs with user-local cpanm.
    echo ""
    echo "[pgTAP Perl] Checking..."
    if { command -v pg_prove >/dev/null 2>&1 && pg_prove --version >/dev/null 2>&1; } || [ -x "${HOME}/perl5/bin/pg_prove" ]; then
        echo "✅ [pgTAP Perl] TAP::Parser::SourceHandler::pgTAP and pg_prove available"
        return
    fi
    if ! command -v cpanm >/dev/null 2>&1; then
        echo "❌ [pgTAP Perl] cpanm is required but not available on PATH"
        exit 1
    fi
    brew_perl_prefix="$(brew --prefix perl 2>/dev/null || true)"
    if [[ -n "$brew_perl_prefix" && -x "${brew_perl_prefix}/bin/perl" ]]; then
        export PATH="${brew_perl_prefix}/bin:${PATH}"
    fi
    echo "[pgTAP Perl] Installing TAP::Parser::SourceHandler::pgTAP via user-local cpanm..."
    cpanm --local-lib="${HOME}/perl5" --reinstall TAP::Parser::SourceHandler::pgTAP
    if [ -x "${HOME}/perl5/bin/pg_prove" ] || command -v pg_prove >/dev/null 2>&1; then
        echo "✅ [pgTAP Perl] TAP::Parser::SourceHandler::pgTAP installed"
        if [ ! -x "$(command -v pg_prove 2>/dev/null || true)" ]; then
            echo "ℹ️  [pgTAP Perl] pg_prove installed to ${HOME}/perl5/bin/pg_prove (not on PATH)"
        fi
    else
        echo "❌ [pgTAP Perl] Install completed but pg_prove/module are still unavailable"
        exit 1
    fi
}

ensure_zap_cli() {
    #R070: Ensure local OWASP ZAP CLI is installed via Homebrew cask when missing.
    echo ""
    echo "[ZAP] Checking..."
    if [ -x "$ZAP_CLI_PATH" ]; then
        echo "✅ [ZAP] CLI available at ${ZAP_CLI_PATH}"
        return
    fi
    echo "⚠️  [ZAP] CLI wrapper missing at ${ZAP_CLI_PATH}"
    echo "[ZAP] Installing Homebrew cask 'zap'..."
    brew install --cask zap
    if [ -x "$ZAP_CLI_PATH" ]; then
        echo "✅ [ZAP] Installed and CLI available at ${ZAP_CLI_PATH}"
    else
        echo "❌ [ZAP] Install completed but CLI wrapper is still missing at ${ZAP_CLI_PATH}"
        echo "Open ZAP.app once if macOS blocked first launch, then rerun this script."
        exit 1
    fi
}

#R045: Run a privileged command, optionally feeding the sudo password from 1psa.
rb_privileged() {
    if [ "$PREREQ_1PSA_SUDO_VIA_1PSA" = "true" ]; then
        "$ONEPSA_LOCAL_BIN" -f "$PSA_INSTALL_SUDO_ITEM" "$PSA_INSTALL_SUDO_ITEM" | sudo -S "$@"
    else
        sudo "$@"
    fi
}

ensure_1psa() {
    #R010: Ensure 1psa is available on PATH (advisory-only when configured).
    echo ""
    echo "[1psa] Checking..."
    if command -v 1psa >/dev/null 2>&1; then
        echo "✅ [1psa] Available on PATH"
        return
    fi
    if [ "$PREREQ_1PSA_ADVISORY" = "true" ]; then
        echo "1psa is recommended for secrets lookup but is not installed."
        return
    fi
    rb_ensure_brew_formula "go"
    rb_ensure_brew_formula "git"
    if [ ! -d "$ONEPSA_DIR" ]; then
        echo "[1psa] Cloning source into ${PARENT_DIR}..."
        git clone "$ONEPSA_REPO_URL" "$ONEPSA_DIR"
    else
        echo "✅ [1psa] Source directory already exists at ${ONEPSA_DIR}"
    fi
    if [ ! -f "${ONEPSA_DIR}/Makefile" ]; then
        echo "❌ [1psa] Missing Makefile in ${ONEPSA_DIR}"
        exit 1
    fi
    echo "[1psa] Building from source..."
    make -C "$ONEPSA_DIR"
    if [ ! -x "$ONEPSA_LOCAL_BIN" ]; then
        echo "❌ [1psa] Expected local binary missing at ${ONEPSA_LOCAL_BIN}"
        exit 1
    fi
    echo "[1psa] Installing with sudo..."
    rb_privileged make -C "$ONEPSA_DIR" install
    if command -v 1psa >/dev/null 2>&1; then
        echo "✅ [1psa] Installed and available on PATH"
    else
        echo "❌ [1psa] Install finished but command is still unavailable"
        exit 1
    fi
}

ensure_pg_install() {
    #R025: Ensure pg_install repository exists and is verifiable.
    echo ""
    echo "[pg_install] Checking..."
    if [ -d "$PG_INSTALL_DIR/.git" ]; then
        echo "✅ [pg_install] Repository present at ${PG_INSTALL_DIR}"
    elif [ -e "$PG_INSTALL_DIR" ]; then
        echo "❌ [pg_install] ${PG_INSTALL_DIR} exists but is not a git repository"
        echo "Please remove or rename it, then run this script again."
        exit 1
    else
        rb_ensure_brew_formula "git"
        echo "[pg_install] Cloning repository into ${PARENT_DIR}..."
        git clone "$PG_INSTALL_REPO_URL" "$PG_INSTALL_DIR"
        if [ -d "$PG_INSTALL_DIR/.git" ]; then
            echo "✅ [pg_install] Installed at ${PG_INSTALL_DIR}"
        else
            echo "❌ [pg_install] Clone step completed but repository was not found"
            exit 1
        fi
    fi
}

ensure_xcode_toolchain() {
    #R060: Verify base Xcode toolchain (xcodebuild, xcrun, clang++).
    echo ""
    echo "[Xcode Toolchain] Checking..."
    local missing=0
    for tool in xcodebuild xcrun clang++; do
        if command -v "$tool" >/dev/null 2>&1; then
            echo "✅ [Xcode Toolchain] $tool available"
        else
            echo "❌ [Xcode Toolchain] $tool not found"
            missing=1
        fi
    done
    if [ "$missing" -ne 0 ]; then
        echo "Install Xcode or Xcode Command Line Tools, then rerun."
        echo "Tip: xcode-select --install"
        exit 1
    fi
}

ensure_swift_tooling() {
    #R055: Ensure the Swift compiler (swiftc) is discoverable via xcrun.
    echo ""
    echo "[Swift] Checking..."
    if xcrun --find swiftc >/dev/null 2>&1; then
        echo "✅ [Swift] swiftc available via xcrun"
    else
        echo "❌ [Swift] swiftc not discoverable via xcrun"
        echo "Install full Xcode and rerun this installer."
        exit 1
    fi
}

ensure_xcode_ready() {
    #R065: Ensure xcodebuild exists and Xcode first-launch/license setup is complete.
    echo ""
    echo "[Xcode] Checking..."
    if ! command -v xcodebuild >/dev/null 2>&1; then
        echo "❌ [Xcode] xcodebuild not found."
        echo "Install Xcode (or Command Line Tools) and run this script again."
        echo "Tip: xcode-select --install"
        exit 1
    fi
    if xcodebuild -checkFirstLaunchStatus >/dev/null 2>&1; then
        echo "✅ [Xcode] First-launch status already configured"
        return
    fi
    echo "⚠️  [Xcode] First-launch setup required; running with sudo..."
    sudo -k
    rb_privileged xcodebuild -runFirstLaunch
    if ! xcodebuild -license check >/dev/null 2>&1; then
        echo "⚠️  [Xcode] Accepting Xcode license..."
        sudo -k
        rb_privileged xcodebuild -license accept
    fi
    if xcodebuild -checkFirstLaunchStatus >/dev/null 2>&1; then
        echo "✅ [Xcode] First-launch setup completed"
    else
        echo "❌ [Xcode] First-launch setup did not complete successfully"
        exit 1
    fi
}

run_verify_mode() {
    #R050: Verify-only profile (e.g. classy): check commands and headers, no installs.
    echo "▶ ${PREREQ_BANNER}"
    local missing=()
    if [ -n "$PREREQ_VERIFY_COMMANDS" ]; then
        while IFS= read -r line; do
            line="$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
            [ -n "$line" ] || continue
            local cmd="${line%%|*}"
            local hint="${line#*|}"
            command -v "$cmd" >/dev/null 2>&1 || missing+=("$hint")
        done <<< "$PREREQ_VERIFY_COMMANDS"
    fi
    if [ "$PREREQ_VERIFY_SQLCIPHER_HEADERS" = "true" ]; then
        local sqlcipher_prefix="${SQLCIPHER_PREFIX:-}"
        if [ -z "$sqlcipher_prefix" ] && command -v brew >/dev/null 2>&1; then
            sqlcipher_prefix="$(brew --prefix sqlcipher 2>/dev/null || true)"
        fi
        if [ -z "$sqlcipher_prefix" ] || [ ! -f "$sqlcipher_prefix/include/sqlcipher/sqlite3.h" ]; then
            missing+=("SQLCipher headers (brew install sqlcipher, or set SQLCIPHER_PREFIX)")
        fi
    fi
    if ((${#missing[@]} > 0)); then
        echo "❌ Missing prerequisites:"
        for item in "${missing[@]}"; do
            echo "   - $item"
        done
        if [ -n "$PREREQ_FINAL_GUIDANCE" ]; then
            echo ""
            echo "Install the above, then re-run. Next steps:"
            printf '%s\n' "$PREREQ_FINAL_GUIDANCE"
        fi
        exit 1
    fi
    echo "✅ All ${RUNBOOK_REPO_NAME} prerequisites present."
    if [ -n "$PREREQ_SUCCESS_GUIDANCE" ]; then
        printf '%s\n' "$PREREQ_SUCCESS_GUIDANCE"
    fi
}

#R030: Install-mode orchestration: print banner, install brew formulas/casks, then run each enabled ensure_* step in order.
run_install_mode() {
    print_header
    ensure_homebrew
    echo ""
    echo "[Tooling] Checking build dependencies..."
    rb_install_brew_formulas "$BREW_FORMULAS"
    local cask
    for cask in $BREW_CASKS; do
        [ -n "$cask" ] || continue
        echo "[cask:${cask}] Installing via Homebrew..."
        brew install --cask "$cask"
    done
    [ "$PREREQ_ENABLE_XCODE_TOOLCHAIN" = "true" ] && ensure_xcode_toolchain
    [ "$PREREQ_ENABLE_XCODE_FIRST_LAUNCH" = "true" ] && ensure_xcode_ready
    [ "$PREREQ_ENABLE_SWIFT" = "true" ] && ensure_swift_tooling
    [ "$PREREQ_ENABLE_ZAP" = "true" ] && ensure_zap_cli
    [ "$PREREQ_ENABLE_1PSA" = "true" ] && ensure_1psa
    [ "$PREREQ_ENABLE_XCODE" = "true" ] && ensure_xcode_ready
    [ "$PREREQ_ENABLE_PG_INSTALL" = "true" ] && ensure_pg_install
    if [ "$PREREQ_ENABLE_PGTAP" = "true" ]; then
        ensure_pgtap_source_install
        ensure_pgtap_sourcehandler
    fi
    if [ -n "$PREREQ_EXTRA_HOOK" ]; then
        local hook="${RUNNER_HOME}/${PREREQ_EXTRA_HOOK}"
        if [ -f "$hook" ]; then
            # shellcheck source=/dev/null
            source "$hook"
        else
            echo "❌ [prereq hook] Not found: ${hook}"
            exit 1
        fi
    fi
    if [ -n "$PREREQ_FINAL_GUIDANCE" ]; then
        echo ""
        printf '%s\n' "$PREREQ_FINAL_GUIDANCE"
    else
        echo ""
        echo "✅ All prerequisites are satisfied!"
    fi
}

#R095: Top-level mode dispatch: route to verify-only or full install based on PREREQ_MODE.
if [ "$PREREQ_MODE" = "verify" ]; then
    run_verify_mode
else
    run_install_mode
fi
