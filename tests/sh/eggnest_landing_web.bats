#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/prereq_hooks/eggnest_landing_web.sh (landing web prereq hook).

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/prereq_hooks/eggnest_landing_web.sh"
  FAKE_REPO="${BATS_TEST_TMPDIR}/repo"
  mkdir -p "${FAKE_REPO}/landing/node_modules"
  printf '{}\n' > "${FAKE_REPO}/landing/package.json"
  FAKEBIN="${BATS_TEST_TMPDIR}/bin"
  mkdir -p "$FAKEBIN"
  printf '#!/usr/bin/env bash\nexit 0\n' > "${FAKEBIN}/npm"
  printf '#!/usr/bin/env bash\nif [[ "$*" == *"--dry-run"* ]]; then echo "chromium is already installed"; fi\nexit 0\n' > "${FAKEBIN}/npx"
  chmod +x "${FAKEBIN}/npm" "${FAKEBIN}/npx"
}

@test "ensures node, npm dependencies, and the playwright browser when sourced" {
  #R001-T01: Source the hook with stubbed brew/npm helpers and verify it ensures node, npm dependencies, and the Playwright browser.
  run bash -c "PATH='${FAKEBIN}':\"\$PATH\"; RUNBOOK_REPO_ROOT='${FAKE_REPO}'; rb_ensure_brew_formula() { echo \"[\$1] ensured\"; }; source '${SRC}'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"[node] ensured"* ]]
  [[ "$output" == *"[landing npm] node_modules present"* ]]
  [[ "$output" == *"[playwright] Chromium browser already installed"* ]]
}

@test "ensure_landing_node_modules reports presence without installing" {
  #R010-T01: With node_modules present, verify ensure_landing_node_modules reports presence without installing.
  run bash -c "PATH='${FAKEBIN}':\"\$PATH\"; RUNBOOK_REPO_ROOT='${FAKE_REPO}'; rb_ensure_brew_formula() { :; }; source '${SRC}' >/dev/null 2>&1; ensure_landing_node_modules"
  [ "$status" -eq 0 ]
  [[ "$output" == *"node_modules present"* ]]
  [[ "$output" != *"Installing dependencies"* ]]
}

@test "ensure_playwright_chromium reports installed without reinstalling" {
  #R020-T01: With an already-installed dry-run stub, verify ensure_playwright_chromium reports installed without reinstalling.
  run bash -c "PATH='${FAKEBIN}':\"\$PATH\"; RUNBOOK_REPO_ROOT='${FAKE_REPO}'; rb_ensure_brew_formula() { :; }; source '${SRC}' >/dev/null 2>&1; ensure_playwright_chromium"
  [ "$status" -eq 0 ]
  [[ "$output" == *"already installed"* ]]
  [[ "$output" != *"Installing Chromium"* ]]
}
