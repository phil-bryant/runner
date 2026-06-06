#!/usr/bin/env bats
# Companion tests for 98_destroy_database.sh requirements traceability.
# Each test asserts the implementing tokens physically exist in the source
# without executing any teardown (no psql, 1psa, database, or filesystem side effects).

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/98_destroy_database.sh"
}

@test "runs fail-fast and anchors to the target repo root" {
  #R001-T01: source sets umask 007, set -euo pipefail, and anchors SCRIPT_DIR to RUNBOOK_REPO_ROOT
  grep -q 'umask 007' "$SCRIPT"
  grep -q 'set -euo pipefail' "$SCRIPT"
  grep -q 'SCRIPT_DIR="${RUNBOOK_REPO_ROOT:-$SCRIPT_DIR}"' "$SCRIPT"
}

@test "requires 1psa and resolves the postgres password" {
  #R005-T01: source probes command -v 1psa, reads POSTGRES_PSA_ITEM, and errors on empty password
  grep -q 'command -v 1psa' "$SCRIPT"
  grep -q 'POSTGRES_PSA_ITEM="${POSTGRES_PSA_ITEM:-localhost_postgres_postgres}"' "$SCRIPT"
  grep -q 'Failed to read postgres password from 1psa item' "$SCRIPT"
}

@test "requires explicit destroy confirmation" {
  #R010-T01: source prompts to type destroy and cancels on mismatch
  grep -q "Type 'destroy' to confirm" "$SCRIPT"
  grep -q 'Destruction cancelled' "$SCRIPT"
}

@test "cleans dependent resources before dropping the local database" {
  #R015-T01: source drops the dependent teller view and terminates active backends first
  grep -q 'DROP VIEW IF EXISTS teller.transaction_info_view;' "$SCRIPT"
  grep -q 'pg_terminate_backend' "$SCRIPT"
}

@test "drops database, user, and teller roles idempotently" {
  #R020-T01: source issues idempotent DROP DATABASE/USER/ROLE statements
  grep -q 'DROP DATABASE IF EXISTS' "$SCRIPT"
  grep -q 'DROP USER IF EXISTS teller;' "$SCRIPT"
  grep -q 'DROP ROLE IF EXISTS teller_admin;' "$SCRIPT"
}

@test "prints completion status after teardown" {
  #R025-T01: source prints Cleanup complete! after teardown
  grep -q 'Cleanup complete!' "$SCRIPT"
}

@test "supports sqlite teardown through the destroy entrypoint" {
  #R026-T01: source requires SQLITE_PATH and removes the resolved sqlite artifact
  grep -q 'SQLite destroy requires SQLITE_PATH from db profile export.' "$SCRIPT"
  grep -q 'rm -f "$SQLITE_DB_PATH"' "$SCRIPT"
}

@test "validates the local database identifier before destructive SQL" {
  #R030-T01: source validates LOCAL_DBNAME via is_valid_pg_identifier and refuses invalid ones
  grep -q 'LOCAL_DBNAME="$PG_DBNAME"' "$SCRIPT"
  grep -q 'is_valid_pg_identifier "$LOCAL_DBNAME"' "$SCRIPT"
  grep -q 'Refusing to destroy invalid database identifier:' "$SCRIPT"
}

@test "runs local destroy SQL directly for the validated identifier" {
  #R031-T01: source uses a direct pg_database probe and direct DROP DATABASE (no gexec)
  grep -q "Identifier already validated; use direct SQL compatible with psql -c" "$SCRIPT"
  grep -q "SELECT 1 FROM pg_database WHERE datname = '\${LOCAL_DBNAME}';" "$SCRIPT"
  grep -q 'DROP DATABASE IF EXISTS \\"${LOCAL_DBNAME}\\";' "$SCRIPT"
  ! grep -q '\\gexec' "$SCRIPT"
}

@test "validates the managed schema identifier and refuses protected schemas" {
  #R032-T01: source validates SCHEMA_NAME and refuses protected schemas
  grep -q 'is_valid_pg_identifier "$SCHEMA_NAME"' "$SCRIPT"
  grep -q 'Refusing to destroy invalid schema identifier:' "$SCRIPT"
  grep -q 'Refusing to destroy managed schema' "$SCRIPT"
}

@test "runs managed schema drop directly for the validated identifier" {
  #R033-T01: source drops the managed schema directly via DROP SCHEMA IF EXISTS ... CASCADE (no gexec)
  grep -q "Identifier already validated; execute DROP SCHEMA directly for psql -c compatibility." "$SCRIPT"
  grep -q 'DROP SCHEMA IF EXISTS \\"${SCHEMA_NAME}\\" CASCADE;' "$SCRIPT"
}
