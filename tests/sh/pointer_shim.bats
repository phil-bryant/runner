#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/pointer_shim.sh (runner engine helper).
# A throwaway fixture mirrors the runner/<repo> layout so the shim resolves paths
# exactly as it does in the real monorepo.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SHIM_SRC="${REPO_ROOT}/src/scripts/pointer_shim.sh"
  FIXTURE="$(cd "$(mktemp -d)" && pwd -P)"
  # Keep shim behavior tests deterministic even when parent runners export shim state.
  unset POINTER_SHIM_PROFILE_LOADED RUNBOOK_PROFILE

  mkdir -p "${FIXTURE}/runner/src/scripts" "${FIXTURE}/runner/config/runbook"
  cp "$SHIM_SRC" "${FIXTURE}/runner/src/scripts/pointer_shim.sh"
  printf 'export DEMO_PROFILE_VAR=ok\n' > "${FIXTURE}/runner/config/runbook/demo.env"
  cat > "${FIXTURE}/runner/golden.sh" <<'GOLD'
#!/usr/bin/env bash
echo "golden args: $*"
echo "golden repo_root: ${RUNBOOK_REPO_ROOT}"
echo "golden demo: ${DEMO_PROFILE_VAR:-unset}"
GOLD
  chmod +x "${FIXTURE}/runner/golden.sh"
  mkdir -p "${FIXTURE}/runner/tests"
  cat > "${FIXTURE}/runner/tests/nested_golden.sh" <<'GOLD'
#!/usr/bin/env bash
echo "nested golden args: $*"
GOLD
  chmod +x "${FIXTURE}/runner/tests/nested_golden.sh"

  mkdir -p "${FIXTURE}/demo/tests"
}

teardown() {
  if [ -n "${FIXTURE:-}" ] && [ -d "${FIXTURE}" ]; then
    mv "${FIXTURE}" "${BATS_TEST_TMPDIR:-${TMPDIR:-/tmp}}/used.$$.$RANDOM" || true
  fi
}

# Writes a top-level pointer at demo/<name> that sources the shim and runs <body>.
write_top_pointer() {
  local name="$1" profile="$2" body="$3"
  {
    echo '#!/usr/bin/env bash'
    [ -n "$profile" ] && echo "RUNBOOK_PROFILE=\"${profile}\""
    echo 'source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../runner/src/scripts" && pwd -P)/pointer_shim.sh"'
    echo "$body"
  } > "${FIXTURE}/demo/${name}"
  chmod +x "${FIXTURE}/demo/${name}"
}

# Writes a tests/ pointer at demo/tests/<name> that sources the shim and runs <body>.
write_tests_pointer() {
  local name="$1" profile="$2" body="$3"
  {
    echo '#!/usr/bin/env bash'
    [ -n "$profile" ] && echo "RUNBOOK_PROFILE=\"${profile}\""
    echo 'source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../runner/src/scripts" && pwd -P)/pointer_shim.sh"'
    echo "$body"
  } > "${FIXTURE}/demo/tests/${name}"
  chmod +x "${FIXTURE}/demo/tests/${name}"
}

@test "pointer sourcing the shim runs with secure umask and strict shell mode" {
  #R001-T01: pointer runs with secure umask and strict shell mode
  write_top_pointer "p.sh" "demo" 'printf "umask=%s flags=%s\n" "$(umask)" "$-"; set -o | grep -q "pipefail.*on" && echo "pipefail=on"'
  run bash "${FIXTURE}/demo/p.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"umask=0007"* ]]
  [[ "$output" == *"flags="*"e"* ]]
  [[ "$output" == *"flags="*"u"* ]]
  [[ "$output" == *"pipefail=on"* ]]
}

@test "shim exports RUNNER_HOME pointed at the runner tree" {
  #R005-T01: shim exports RUNNER_HOME pointed at the runner tree
  write_top_pointer "p.sh" "demo" 'printf "RUNNER_HOME=%s\n" "$RUNNER_HOME"'
  run bash "${FIXTURE}/demo/p.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RUNNER_HOME=${FIXTURE}/runner"* ]]
}

@test "top-level pointer resolves RUNBOOK_REPO_ROOT to its repo directory" {
  #R010-T01: top-level pointer resolves RUNBOOK_REPO_ROOT to its repo dir
  write_top_pointer "p.sh" "demo" 'printf "REPO_ROOT=%s\n" "$RUNBOOK_REPO_ROOT"'
  run bash "${FIXTURE}/demo/p.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"REPO_ROOT=${FIXTURE}/demo"* ]]
}

@test "tests/ pointer resolves RUNBOOK_REPO_ROOT to the repo root, not tests dir" {
  #R010-T02: tests/ pointer resolves RUNBOOK_REPO_ROOT to repo root, not tests dir
  write_tests_pointer "tp.sh" "demo" 'printf "REPO_ROOT=%s\n" "$RUNBOOK_REPO_ROOT"'
  run bash "${FIXTURE}/demo/tests/tp.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"REPO_ROOT=${FIXTURE}/demo"* ]]
  [[ "$output" != *"REPO_ROOT=${FIXTURE}/demo/tests"* ]]
}

@test "shim sources the selected runbook profile" {
  #R015-T01: shim sources the selected runbook profile
  write_top_pointer "p.sh" "" 'select_runbook_profile "demo"; printf "DEMO=%s\n" "${DEMO_PROFILE_VAR:-unset}"'
  run bash "${FIXTURE}/demo/p.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"DEMO=ok"* ]]
}

@test "shim aborts when select_runbook_profile argument is unset" {
  #R015-T02: shim aborts when select_runbook_profile argument is unset
  write_top_pointer "p.sh" "" 'select_runbook_profile "${UNSET_PROFILE:-}"; printf "should-not-run\n"'
  run bash "${FIXTURE}/demo/p.sh"
  [ "$status" -ne 0 ]
  [[ "$output" == *"select_runbook_profile requires a profile argument"* ]]
  [[ "$output" != *"should-not-run"* ]]
}

@test "delegate_golden execs the resolved golden with argument passthrough" {
  #R020-T01: delegate_golden execs the resolved golden with arg passthrough
  write_top_pointer "p.sh" "demo" 'delegate_golden "golden.sh" "$@"'
  run bash "${FIXTURE}/demo/p.sh" alpha beta
  [ "$status" -eq 0 ]
  [[ "$output" == *"golden args: alpha beta"* ]]
  [[ "$output" == *"golden repo_root: ${FIXTURE}/demo"* ]]
}

@test "delegate_golden auto-loads RUNBOOK_PROFILE for legacy pointers" {
  #R016-T01: delegate_golden auto-loads RUNBOOK_PROFILE for legacy pointers
  write_top_pointer "p.sh" "demo" 'delegate_golden "golden.sh" "$@"'
  run bash "${FIXTURE}/demo/p.sh" legacy
  [ "$status" -eq 0 ]
  [[ "$output" == *"golden args: legacy"* ]]
  [[ "$output" == *"golden demo: ok"* ]]
}

@test "delegate_golden resolves nested golden paths" {
  #R020-T01: delegate_golden resolves nested golden paths
  write_tests_pointer "tp.sh" "demo" 'delegate_golden "tests/nested_golden.sh" "$@"'
  run bash "${FIXTURE}/demo/tests/tp.sh" gamma
  [ "$status" -eq 0 ]
  [[ "$output" == *"nested golden args: gamma"* ]]
}
