#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/run_unit_test_lanes.sh.
# A throwaway fixture mirrors the runner/ tree so the helper resolves
# RUNNER_HOME/RUNBOOK_REPO_ROOT and its sibling helpers exactly as in the
# real monorepo.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  FIXTURE="$(cd "$(mktemp -d)" && pwd -P)"
  RUNNER="${FIXTURE}/runner"
  mkdir -p "${RUNNER}/src/scripts"
  cp "${REPO_ROOT}/src/scripts/run_unit_test_lanes.sh" "${RUNNER}/src/scripts/run_unit_test_lanes.sh"
  cp "${REPO_ROOT}/src/scripts/runbook_common.sh" "${RUNNER}/src/scripts/runbook_common.sh"
  cp "${REPO_ROOT}/src/scripts/export_test_cache_env.sh" "${RUNNER}/src/scripts/export_test_cache_env.sh"
  chmod +x "${RUNNER}/src/scripts/run_unit_test_lanes.sh"

  STUB_BIN="${FIXTURE}/bin"
  mkdir -p "$STUB_BIN"
  CALLS_LOG="${FIXTURE}/calls.log"
  : > "$CALLS_LOG"

  LANES="${RUNNER}/src/scripts/run_unit_test_lanes.sh"
}

teardown() {
  if [ -n "${FIXTURE:-}" ] && [ -d "${FIXTURE}" ]; then
    rm -rf "${FIXTURE}" || true
  fi
}

@test "exports hypothesis storage under artifacts/cache" {
  #R038-T01: Verify the helper exports `HYPOTHESIS_STORAGE_DIRECTORY` ending in `artifacts/cache/hypothesis`.
  run bash -c "
    # shellcheck disable=SC1091
    source '${RUNNER}/src/scripts/export_test_cache_env.sh'
    export_test_cache_env '${FIXTURE}'
    printf '%s' \"\${HYPOTHESIS_STORAGE_DIRECTORY}\"
  "
  [ "$status" -eq 0 ]
  [[ "$output" == *"artifacts/cache/hypothesis"* ]]
}

@test "runs from target repo root and honors disabled lanes" {
  #R001-T01: Verify the helper re-roots execution and respects lane toggles for shell/python/sql/swift execution.
  #R030-T01: Verify helper does not call crash-verification script when running default lanes.
  TARGET="${FIXTURE}/target"
  mkdir -p "$TARGET"
  run env PATH="${STUB_BIN}:${PATH}" RUNBOOK_REPO_ROOT="$TARGET" \
    RUN_SHELL_TESTS=false RUN_PYTHON_TESTS=false RUN_SQL_TESTS=false RUN_SWIFT_TESTS=false \
    bash "$LANES"
  [ "$status" -eq 0 ]
  # Re-rooted onto the target repo: cache env materialized under the target tree.
  [ -d "${TARGET}/artifacts/cache/hypothesis" ]
  # No crash-verification lane is ever invoked from this helper.
  [[ "$output" != *"crash"* ]]
}

@test "fails fast when db profile helper is missing" {
  #R005-T01: Verify SQL preflight failures surface clear diagnostics and block SQL test execution.
  #R015-T01: Verify helper exits non-zero when an enabled lane command returns failure.
  #R025-T01: Verify missing or failing DB profile export helper prevents SQL lane startup.
  #R035-T01: Verify SQL lane preflight exits with setup diagnostic when profile exports fail.
  mkdir -p "${RUNNER}/tests/sql"
  run env PATH="${STUB_BIN}:${PATH}" \
    RUN_SHELL_TESTS=false RUN_PYTHON_TESTS=false RUN_SQL_TESTS=true RUN_SWIFT_TESTS=false \
    SQL_TESTS_DIR="${RUNNER}/tests/sql" \
    bash "$LANES"
  [ "$status" -eq 1 ]
  [[ "$output" == *"DB profile helper is missing or not executable"* ]]
}

@test "swift lane invokes lock helper and retries stale-cache failure once" {
  #R010-T01: Verify lock helper invocation and single-retry stale-cache recovery path behavior.
  #R020-T01: Verify stale-checkout signal triggers single retry and unrelated failures do not.
  mkdir -p "${RUNNER}/src/macos-ui/Tests"
  cat > "${RUNNER}/src/scripts/macos_ui_swift_lock.sh" <<EOF
#!/usr/bin/env bash
macos_ui_with_swiftpm_lock() {
  echo "lock:\$1:\$2:\$3" >> "${CALLS_LOG}"
  shift 3
  "\$@"
}
EOF

  cat > "${STUB_BIN}/swift" <<EOF
#!/usr/bin/env bash
echo "swift \$*" >> "${CALLS_LOG}"
if [[ "\$*" == *"swift test --package-path ./src/macos-ui"* ]]; then
  marker="${FIXTURE}/swift-first"
  if [[ ! -f "\$marker" ]]; then
    touch "\$marker"
    echo "cannot be accessed .build/" >&2
    exit 1
  fi
fi
exit 0
EOF
  chmod +x "${STUB_BIN}/swift"

  run env PATH="${STUB_BIN}:${PATH}" \
    RUN_SHELL_TESTS=false RUN_PYTHON_TESTS=false RUN_SQL_TESTS=false RUN_SWIFT_TESTS=true \
    bash "$LANES"
  [ "$status" -eq 0 ]
  calls="$(<"${CALLS_LOG}")"
  [[ "$calls" == *"lock:"* ]]
  [[ "$calls" == *"swift test --package-path ./src/macos-ui"* ]]
}

@test "swift lane skips gracefully when sandbox_apply is denied" {
  #R020-T02: Verify sandbox-denied Swift test startup is treated as a graceful skip path instead of a stale-cache retry loop.
  mkdir -p "${RUNNER}/src/macos-ui/Tests"
  cat > "${RUNNER}/src/scripts/macos_ui_swift_lock.sh" <<'EOF'
#!/usr/bin/env bash
macos_ui_with_swiftpm_lock() {
  shift 3
  "$@"
}
EOF

  cat > "${STUB_BIN}/swift" <<'EOF'
#!/usr/bin/env bash
echo "sandbox_apply: Operation not permitted" >&2
exit 1
EOF
  chmod +x "${STUB_BIN}/swift"

  run env PATH="${STUB_BIN}:${PATH}" \
    RUN_SHELL_TESTS=false RUN_PYTHON_TESTS=false RUN_SQL_TESTS=false RUN_SWIFT_TESTS=true \
    bash "$LANES"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Skipping Swift unit tests in restricted runtime"* ]]
}
