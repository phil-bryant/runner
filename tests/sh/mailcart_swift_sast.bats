#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/prereq_hooks/mailcart_swift_sast.sh (native-Swift SAST prereq hook).

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/prereq_hooks/mailcart_swift_sast.sh"
  FAKEBIN="${BATS_TEST_TMPDIR}/bin"
  mkdir -p "$FAKEBIN"
  for tool in clang-tidy semgrep shellcheck gitleaks; do
    printf '#!/usr/bin/env bash\nexit 0\n' > "${FAKEBIN}/${tool}"
    chmod +x "${FAKEBIN}/${tool}"
  done
}

@test "ensures the full swift SAST toolchain when sourced" {
  #R055-T01: Source the hook with stubbed brew helpers and verify it ensures shellcheck, semgrep, clang-tidy, and gitleaks.
  run bash -c "PATH='${FAKEBIN}:\$PATH'; rb_ensure_brew_formula() { echo \"[\$1] ensured\"; }; brew() { return 0; }; source '${SRC}'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"[shellcheck] ensured"* ]]
  [[ "$output" == *"[gitleaks] ensured"* ]]
  [[ "$output" == *"[semgrep] Available on PATH"* ]]
  [[ "$output" == *"[clang-tidy] Available on PATH"* ]]
}

@test "ensure_clang_tidy reports availability without installing when on PATH" {
  #R070-T01: With clang-tidy on PATH, verify ensure_clang_tidy reports availability without installing.
  run bash -c "PATH='${FAKEBIN}:\$PATH'; rb_ensure_brew_formula() { :; }; brew() { return 0; }; source '${SRC}' >/dev/null 2>&1; ensure_clang_tidy"
  [ "$status" -eq 0 ]
  [[ "$output" == *"[clang-tidy] Available on PATH"* ]]
}

@test "ensure_semgrep_present reports availability without upgrading when fresh" {
  #R075-T01: With semgrep on PATH and a non-outdated brew stub, verify ensure_semgrep_present reports availability without upgrading.
  run bash -c "PATH='${FAKEBIN}:\$PATH'; rb_ensure_brew_formula() { :; }; brew() { return 0; }; source '${SRC}' >/dev/null 2>&1; ensure_semgrep_present"
  [ "$status" -eq 0 ]
  [[ "$output" == *"[semgrep] Available on PATH"* ]]
  [[ "$output" != *"upgrading"* ]]
}
