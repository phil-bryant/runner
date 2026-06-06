# 01 install prerequisites Requirements

## Scope

This document specifies the behavior of the shared golden prerequisites
installer `01_install_prerequisites.sh`. The script is a profile-driven macOS
setup entrypoint that prepares a runbook repository for development and testing.
Driven entirely by `PREREQ_*` environment knobs, it runs in one of two modes:
an install mode that checks for Homebrew, installs the configured Homebrew
formulas and casks, builds/installs sibling tooling (1psa, pg_install, pgTAP
plus its Perl SourceHandler), installs the OWASP ZAP CLI cask, and verifies the
Xcode toolchain / first-launch / Swift compiler state; and a verify-only mode
that asserts a list of required commands (and optionally SQLCipher headers) are
present without performing any installs. Privileged operations are performed via
sudo, optionally piping the sudo password from a 1psa-managed credential.

R001  Statement: The installer runs under bash with a secure umask and fails fast on unrecoverable errors.
Design: Sets `umask 007` and enables `set -euo pipefail` so unset variables, command failures, and broken pipes abort the run.
Tests:
- R001-T01: source enables strict bash mode (set -euo pipefail)

R002  Statement: The installer establishes the RUNNER_HOME (engine) and RUNBOOK_REPO_ROOT (target repo) contract before doing any work.
Design: Resolves its own directory and sources `src/scripts/runbook_common.sh` to populate the shared runbook environment contract.
Tests:
- R002-T01: source sources the shared runbook_common contract

R003  Statement: Behavior is configured through PREREQ_* profile knobs whose defaults reproduce the full installer.
Design: Reads PREREQ_MODE, banner text, brew formula/cask lists, and per-feature enable flags from the environment with install-oriented defaults.
Tests:
- R003-T01: source defaults PREREQ_MODE to install

R004  Statement: Sibling tooling clones (1psa, pg_install, pgtap) are located beside the target repository.
Design: Derives PARENT_DIR from RUNBOOK_REPO_ROOT and computes default clone directories and source URLs for each tooling repository.
Tests:
- R004-T01: source defines the 1psa source repository URL

R005  Statement: Homebrew must be present before any package actions are attempted.
Design: `ensure_homebrew` checks for the `brew` command and exits with installation guidance when it is missing.
Tests:
- R005-T01: source checks for the brew command

R010  Statement: The 1psa secrets helper is made available on PATH, with an advisory-only escape hatch.
Design: `ensure_1psa` returns early when 1psa is present or advisory mode is set, otherwise clones, builds, and privilege-installs it from source.
Tests:
- R010-T01: source defines the ensure_1psa step

R020  Statement: A default sudo credential item is used for privileged operations and is overridable via environment.
Design: Sets `PSA_INSTALL_SUDO_ITEM` (default `odus`) used as the 1psa item/field name when fetching the sudo password.
Tests:
- R020-T01: source defines the PSA_INSTALL_SUDO_ITEM credential knob

R025  Statement: The pg_install repository is present and verifiable before PostgreSQL tooling is used.
Design: `ensure_pg_install` validates an existing git checkout, errors on a non-repo path, or clones the repository into the parent directory.
Tests:
- R025-T01: source defines the ensure_pg_install step

R030  Statement: Install mode orchestrates the full prerequisite sequence in a deterministic order.
Design: `run_install_mode` prints the banner, installs brew formulas/casks, then invokes each enabled ensure_* step and optional hook.
Tests:
- R030-T01: source defines the run_install_mode orchestrator

R045  Statement: Privileged commands may be run with the sudo password fed from 1psa.
Design: `rb_privileged` pipes the 1psa credential into `sudo -S` when configured, otherwise falls back to a plain `sudo` invocation.
Tests:
- R045-T01: source defines the rb_privileged helper

R050  Statement: Verify-only mode checks required commands and headers without performing installs.
Design: `run_verify_mode` iterates PREREQ_VERIFY_COMMANDS, optionally checks SQLCipher headers, and reports any missing prerequisites.
Tests:
- R050-T01: source defines the run_verify_mode step

R055  Statement: The Swift compiler must be discoverable via xcrun when Swift tooling is enabled.
Design: `ensure_swift_tooling` confirms `xcrun --find swiftc` succeeds and otherwise instructs the user to install full Xcode.
Tests:
- R055-T01: source locates swiftc via xcrun

R060  Statement: The base Xcode toolchain commands must be available when the toolchain check is enabled.
Design: `ensure_xcode_toolchain` verifies xcodebuild, xcrun, and clang++ are on PATH and exits with guidance when any are missing.
Tests:
- R060-T01: source verifies xcodebuild, xcrun, and clang++

R065  Statement: Xcode first-launch and license setup must be completed when the Xcode readiness check is enabled.
Design: `ensure_xcode_ready` runs `xcodebuild -runFirstLaunch` and accepts the license via privileged invocation until first-launch status is configured.
Tests:
- R065-T01: source checks Xcode first-launch status

R070  Statement: The local OWASP ZAP CLI is installed via a Homebrew cask when missing.
Design: `ensure_zap_cli` returns early when the CLI wrapper exists, otherwise installs the `zap` cask and re-verifies the wrapper path.
Tests:
- R070-T01: source installs the zap Homebrew cask

R085  Statement: pgTAP is installed from source when pg_prove is not already available.
Design: `ensure_pgtap_source_install` clones the pgTAP source, then builds and installs it via make when pg_prove is missing.
Tests:
- R085-T01: source defines the ensure_pgtap_source_install step

R090  Statement: The pgTAP Perl SourceHandler is installed with a user-local cpanm.
Design: `ensure_pgtap_sourcehandler` installs TAP::Parser::SourceHandler::pgTAP into ~/perl5 via cpanm when pg_prove is unavailable.
Tests:
- R090-T01: source installs TAP::Parser::SourceHandler::pgTAP

R095  Statement: The script dispatches to verify-only or full install based on PREREQ_MODE.
Design: The top-level dispatch runs `run_verify_mode` when PREREQ_MODE is `verify`, otherwise runs `run_install_mode`.
Tests:
- R095-T01: source dispatches on PREREQ_MODE equal to verify
