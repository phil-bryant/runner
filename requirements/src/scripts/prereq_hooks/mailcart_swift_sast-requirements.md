# Mailcart Swift SAST Prereq Hook Requirements

## Scope

Applies to `src/scripts/prereq_hooks/mailcart_swift_sast.sh`.

R055  Statement: Ensure the full native-Swift SAST toolchain for `make sast`.
Design: When sourced by the generic install golden, ensure ShellCheck, Semgrep, clang-tidy, and gitleaks are present via the shared Homebrew helpers.
Tests:
- R055-T01: Source the hook with stubbed brew helpers and verify it ensures shellcheck, semgrep, clang-tidy, and gitleaks.

R070  Statement: Ensure clang-tidy availability with a Homebrew llvm fallback.
Design: `ensure_clang_tidy` short-circuits when clang-tidy is on PATH, otherwise resolves the Homebrew `llvm` prefix and installs `llvm`, failing if clang-tidy remains unavailable.
Tests:
- R070-T01: With clang-tidy on PATH, verify `ensure_clang_tidy` reports availability without installing.

R075  Statement: Ensure semgrep is installed and reasonably fresh via Homebrew.
Design: `ensure_semgrep_present` installs semgrep when missing, upgrades it when Homebrew reports it outdated, and fails if it remains absent after install.
Tests:
- R075-T01: With semgrep on PATH and a non-outdated brew stub, verify `ensure_semgrep_present` reports availability without upgrading.
