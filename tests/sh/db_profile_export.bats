#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/db_profile_export.sh.
# A throwaway fixture mirrors the repo layout and stubs python3 so the helper's
# argument handling, output filtering, and failure propagation are exercised
# without a real teller venv or 1Password access.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  FIXTURE="$(cd "$(mktemp -d)" && pwd -P)"
  REPO="${FIXTURE}/repo"
  mkdir -p "${REPO}/src/scripts"
  cp "${REPO_ROOT}/src/scripts/db_profile_export.sh" "${REPO}/src/scripts/db_profile_export.sh"
  chmod +x "${REPO}/src/scripts/db_profile_export.sh"

  STUB_BIN="${FIXTURE}/bin"
  mkdir -p "$STUB_BIN"
  HELPER="${REPO}/src/scripts/db_profile_export.sh"
}

teardown() {
  if [ -n "${FIXTURE:-}" ] && [ -d "${FIXTURE}" ]; then
    rm -rf "${FIXTURE}" || true
  fi
}

@test "prints expected export keys and filters non-export noise" {
  #R001-T01: Verify successful execution prints required export keys with shell-quoted values and filters non-export noise.
  cat > "${STUB_BIN}/python3" <<'EOF'
#!/usr/bin/env bash
cat <<'OUT'
# resolving profile (this noise line must be filtered out)
DB_DIALECT=postgresql
PROFILE_NAME=local
PROFILE_TARGET=local
PG_HOST=localhost
PG_PORT=5432
PG_DBNAME=prod
PG_USER=teller
PG_SSLMODE=disable
PG_SEARCH_PATH='teller,public'
PG_RUNTIME_ROLE=teller_write
PG_ONEPSA_ITEM=localhost_postgres_teller
OUT
EOF
  chmod +x "${STUB_BIN}/python3"

  run env PATH="${STUB_BIN}:${PATH}" bash -c "cd '${REPO}' && ./src/scripts/db_profile_export.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"DB_DIALECT=postgresql"* ]]
  [[ "$output" == *"PROFILE_NAME=local"* ]]
  [[ "$output" == *"PG_DBNAME=prod"* ]]
  [[ "$output" == *"PG_ONEPSA_ITEM=localhost_postgres_teller"* ]]
  [[ "$output" == *"PG_SEARCH_PATH='teller,public'"* ]]
  [[ "$output" != *"this noise line"* ]]
}

@test "supports profile override and rejects unknown args" {
  #R005-T01: Verify profile override is propagated and unknown flags fail with an explicit error.
  cat > "${STUB_BIN}/python3" <<'EOF'
#!/usr/bin/env bash
echo "PROFILE_NAME=${TELLER_DB_PROFILE:-unset}"
echo "PG_DBNAME=prod"
EOF
  chmod +x "${STUB_BIN}/python3"

  run env PATH="${STUB_BIN}:${PATH}" bash -c "cd '${REPO}' && ./src/scripts/db_profile_export.sh --profile test-profile"
  [ "$status" -eq 0 ]
  [[ "$output" == *"PROFILE_NAME=test-profile"* ]]

  run env PATH="${STUB_BIN}:${PATH}" bash -c "cd '${REPO}' && ./src/scripts/db_profile_export.sh --bad-flag"
  [ "$status" -eq 2 ]
  [[ "$output" == *"unknown arg"* ]]
}

@test "fails clearly when profile resolver errors" {
  #R010-T01: Simulate profile-resolution failure and verify stderr guidance plus failing exit status.
  cat > "${STUB_BIN}/python3" <<'EOF'
#!/usr/bin/env bash
echo "profile resolution failed" >&2
exit 1
EOF
  chmod +x "${STUB_BIN}/python3"

  run env PATH="${STUB_BIN}:${PATH}" bash -c "cd '${REPO}' && ./src/scripts/db_profile_export.sh"
  [ "$status" -eq 1 ]
  [[ "$output" == *"profile resolution failed"* ]]
}
