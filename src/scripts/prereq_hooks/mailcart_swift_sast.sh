#!/usr/bin/env bash
# Reusable prereq hook: mailcart native-Swift SAST toolchain (clang-tidy via llvm,
# semgrep freshness, shellcheck, gitleaks). Sourced by the generic 01 install golden
# when PREREQ_EXTRA_HOOK points here. Relies on rb_ensure_brew_formula from runbook_common.

ensure_clang_tidy() {
    #R070: Ensure clang-tidy is available, including Homebrew llvm fallback.
    echo "[clang-tidy] Checking..."
    if command -v clang-tidy >/dev/null 2>&1; then
        echo "✅ [clang-tidy] Available on PATH"
        return
    fi
    local llvm_prefix llvm_clang_tidy
    llvm_prefix="$(brew --prefix llvm 2>/dev/null || true)"
    llvm_clang_tidy="${llvm_prefix}/bin/clang-tidy"
    if [ -x "$llvm_clang_tidy" ]; then
        echo "✅ [clang-tidy] Available at ${llvm_clang_tidy}"
        echo "ℹ️  Add to PATH for this shell if needed: export PATH=\"${llvm_prefix}/bin:\$PATH\""
        return
    fi
    echo "⚠️  [clang-tidy] Missing; installing llvm with Homebrew..."
    brew install llvm
    llvm_prefix="$(brew --prefix llvm 2>/dev/null || true)"
    llvm_clang_tidy="${llvm_prefix}/bin/clang-tidy"
    if command -v clang-tidy >/dev/null 2>&1 || [ -x "$llvm_clang_tidy" ]; then
        echo "✅ [clang-tidy] Available"
    else
        echo "❌ [clang-tidy] Install completed but clang-tidy is still unavailable"
        exit 1
    fi
}

ensure_semgrep_present() {
    #R075: Ensure semgrep is installed and reasonably fresh via Homebrew.
    echo "[semgrep] Checking..."
    if ! command -v semgrep >/dev/null 2>&1; then
        echo "⚠️  [semgrep] Missing; installing with Homebrew..."
        brew install semgrep
    fi
    if ! command -v semgrep >/dev/null 2>&1; then
        echo "❌ [semgrep] Install completed but command is still missing"
        exit 1
    fi
    if brew outdated --formula semgrep 2>/dev/null | grep -q semgrep; then
        echo "⚠️  [semgrep] Outdated; upgrading with Homebrew..."
        brew upgrade semgrep
    fi
    echo "✅ [semgrep] Available on PATH"
}

#R055: Ensure ShellCheck, Semgrep, clang-tidy, and gitleaks for make sast.
echo ""
rb_ensure_brew_formula "shellcheck"
ensure_semgrep_present
ensure_clang_tidy
rb_ensure_brew_formula "gitleaks"
