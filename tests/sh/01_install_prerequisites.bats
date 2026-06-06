#!/usr/bin/env bats
# Source-assertion tests for the golden prerequisites installer.
# This installer needs Homebrew/sudo/network/Xcode to actually run, so the tests
# assert that the implementing behavior exists in the source rather than
# executing it. Each @test maps 1:1 to a numbered requirement test case.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/01_install_prerequisites.sh"
  [ -f "$SCRIPT" ]
}

@test "strict bash mode is enabled in the installer" {
  #R001-T01: source enables strict bash mode (set -euo pipefail)
  grep -q 'set -euo pipefail' "$SCRIPT"
}

@test "installer sources the shared runbook contract" {
  #R002-T01: source sources the shared runbook_common contract
  grep -q 'runbook_common.sh' "$SCRIPT"
}

@test "PREREQ_MODE defaults to install" {
  #R003-T01: source defaults PREREQ_MODE to install
  grep -q 'PREREQ_MODE:-install' "$SCRIPT"
}

@test "1psa source repository URL is defined" {
  #R004-T01: source defines the 1psa source repository URL
  grep -q 'ONEPSA_REPO_URL' "$SCRIPT"
}

@test "Homebrew presence is checked" {
  #R005-T01: source checks for the brew command
  grep -q 'command -v brew' "$SCRIPT"
}

@test "ensure_1psa step is defined" {
  #R010-T01: source defines the ensure_1psa step
  grep -q 'ensure_1psa()' "$SCRIPT"
}

@test "sudo credential item knob is defined" {
  #R020-T01: source defines the PSA_INSTALL_SUDO_ITEM credential knob
  grep -q 'PSA_INSTALL_SUDO_ITEM' "$SCRIPT"
}

@test "ensure_pg_install step is defined" {
  #R025-T01: source defines the ensure_pg_install step
  grep -q 'ensure_pg_install()' "$SCRIPT"
}

@test "run_install_mode orchestrator is defined" {
  #R030-T01: source defines the run_install_mode orchestrator
  grep -q 'run_install_mode()' "$SCRIPT"
}

@test "rb_privileged helper is defined" {
  #R045-T01: source defines the rb_privileged helper
  grep -q 'rb_privileged()' "$SCRIPT"
}

@test "run_verify_mode step is defined" {
  #R050-T01: source defines the run_verify_mode step
  grep -q 'run_verify_mode()' "$SCRIPT"
}

@test "swiftc is located via xcrun" {
  #R055-T01: source locates swiftc via xcrun
  grep -q 'xcrun --find swiftc' "$SCRIPT"
}

@test "base Xcode toolchain commands are verified" {
  #R060-T01: source verifies xcodebuild, xcrun, and clang++
  grep -q 'xcodebuild xcrun clang++' "$SCRIPT"
}

@test "Xcode first-launch status is checked" {
  #R065-T01: source checks Xcode first-launch status
  grep -q 'checkFirstLaunchStatus' "$SCRIPT"
}

@test "ZAP CLI is installed via Homebrew cask" {
  #R070-T01: source installs the zap Homebrew cask
  grep -q 'install --cask zap' "$SCRIPT"
}

@test "ensure_pgtap_source_install step is defined" {
  #R085-T01: source defines the ensure_pgtap_source_install step
  grep -q 'ensure_pgtap_source_install()' "$SCRIPT"
}

@test "pgTAP Perl SourceHandler is installed" {
  #R090-T01: source installs TAP::Parser::SourceHandler::pgTAP
  grep -q 'TAP::Parser::SourceHandler::pgTAP' "$SCRIPT"
}

@test "mode dispatch routes on PREREQ_MODE verify" {
  #R095-T01: source dispatches on PREREQ_MODE equal to verify
  grep -q '"$PREREQ_MODE" = "verify"' "$SCRIPT"
}
