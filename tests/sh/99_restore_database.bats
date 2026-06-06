#!/usr/bin/env bats
# Companion tests for 99_restore_database.sh requirements traceability.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/99_restore_database.sh"
}

@test "strict shell mode and secure umask" {
  #R001-T01: source sets secure umask and strict shell mode
  grep -q 'umask 007' "$SCRIPT"
  grep -q 'set -euo pipefail' "$SCRIPT"
}

@test "backup source selection and --from override" {
  #R005-T01: latest_backup_path selects newest encrypted dump from backups dir
  grep -q 'latest_backup_path()' "$SCRIPT"
  grep -q '"\$BACKUP_DIR"/\*\.dump\.gpg' "$SCRIPT"
  #R005-T02: --from argument sets BACKUP_PATH
  grep -q -- '--from)' "$SCRIPT"
  grep -q 'BACKUP_PATH="\$2"' "$SCRIPT"
}

@test "requires restore dependencies on PATH" {
  #R010-T01: pg_restore is required before restore operations
  grep -q 'command -v pg_restore' "$SCRIPT"
  grep -q 'pg_restore is required but was not found on PATH' "$SCRIPT"
}

@test "postgres password resolved from 1psa and validated" {
  #R015-T01: empty postgres password lookup refuses restore
  grep -q 'POSTGRES_PSA_ITEM' "$SCRIPT"
  grep -q 'Failed to read postgres password from 1psa item' "$SCRIPT"
}

@test "requires globals dump only for full restore" {
  #R020-T01: full restore refuses when matching globals backup is missing
  grep -q 'Matching globals backup is missing' "$SCRIPT"
  #R020-T02: globals requirement is gated on full-restore (no --table) mode
  grep -q 'if \[ -z "\$TABLE_NAME" \]; then' "$SCRIPT"
}

@test "refuses full restore into existing teller schema" {
  #R025-T01: refuse full restore when teller schema already exists
  grep -q 'Schema teller already exists in' "$SCRIPT"
  #R025-T02: guidance points to --table scoped restore
  grep -q 'Pass --table schema.table_name to run table-scoped restore' "$SCRIPT"
}

@test "full restore replays globals then restores dump" {
  #R030-T01: full restore runs pg_restore --create after globals replay
  grep -q 'pg_restore -U postgres -d postgres --clean --if-exists --create' "$SCRIPT"
  #R030-T02: table-scoped restore uses RESTORE_TABLE_ARGS instead of globals replay
  grep -q 'pg_restore -U postgres -d "\$DATABASE_NAME" --clean --if-exists "\${RESTORE_TABLE_ARGS\[@\]}"' "$SCRIPT"
}

@test "fail-fast target SQL helper and completion output" {
  #R035-T01: run_psql_target executes target SQL with ON_ERROR_STOP=1
  grep -q 'run_psql_target()' "$SCRIPT"
  grep -q 'psql -v ON_ERROR_STOP=1 -U postgres -d "\$DATABASE_NAME"' "$SCRIPT"
  #R035-T02: successful run prints completion line with backup path
  grep -q 'Restore complete from:' "$SCRIPT"
}

@test "table scope parsing and schema defaulting" {
  #R040-T01: --table parsed into TABLE_NAME
  grep -q -- '--table)' "$SCRIPT"
  grep -q 'TABLE_NAME="\$2"' "$SCRIPT"
  #R040-T02: bare table name defaults to teller schema
  grep -q 'TABLE_SCHEMA="teller"' "$SCRIPT"
}

@test "combine explicit source with scoped restore" {
  #R045-T01: scoped restore applies RESTORE_TABLE_ARGS to selected backup input
  grep -q '"\${RESTORE_TABLE_ARGS\[@\]}" "\$BACKUP_INPUT_PATH"' "$SCRIPT"
}

@test "scoped restore repair hook for teller tables" {
  #R050-T01: repair_scoped_table_restore runs after scoped restore
  grep -q 'repair_scoped_table_restore' "$SCRIPT"
  #R050-T02: repair hook skipped for non-teller schema targets
  grep -q 'if \[ "\${TABLE_SCHEMA}" != "teller" \]' "$SCRIPT"
}

@test "scoped repair ensures shared trigger function" {
  #R055-T01: scoped repair recreates teller.update_updated_at()
  grep -q 'CREATE OR REPLACE FUNCTION teller.update_updated_at()' "$SCRIPT"
}

@test "per-table updated_at trigger recreation" {
  #R060-T01: repair recreates per-table trigger via CREATE TRIGGER
  grep -q 'CREATE TRIGGER' "$SCRIPT"
  #R060-T02: trigger recreation conditional on detecting updated_at column
  grep -q "column_name = 'updated_at'" "$SCRIPT"
}

@test "table-specific DDL fixup after scoped restore" {
  #R065-T01: reapply transaction_nys_snw_category FK with ON DELETE CASCADE
  grep -q 'transaction_nys_snw_category' "$SCRIPT"
  grep -q 'ON DELETE CASCADE' "$SCRIPT"
}

@test "teller password resolved from 1psa and validated" {
  #R070-T01: empty teller password lookup refuses restore
  grep -q 'TELLER_PSA_ITEM' "$SCRIPT"
  grep -q 'Failed to read teller password from 1psa item' "$SCRIPT"
}

@test "re-sync teller role credential after full restore" {
  #R075-T01: full restore runs ALTER USER teller WITH PASSWORD
  grep -q 'ALTER USER teller WITH PASSWORD' "$SCRIPT"
}

@test "verify teller authentication after re-sync" {
  #R080-T01: restore fails when post-restore teller authentication fails
  grep -q 'psql -w -v ON_ERROR_STOP=1 -U teller' "$SCRIPT"
  grep -q 'teller authentication failed' "$SCRIPT"
}

@test "resolve active DB profile via shared helper" {
  #R085-T01: refuse when db_profile_export.sh helper is missing or not executable
  grep -q 'db_profile_export.sh' "$SCRIPT"
  grep -q 'DB profile helper is missing or not executable' "$SCRIPT"
}

@test "sqlite restore through existing entrypoint" {
  #R086-T01: sqlite restore copies backup to SQLITE_PATH and rejects --table
  grep -q 'SQLITE_PATH' "$SCRIPT"
  grep -q -- '--table scoped restore is not supported for sqlite targets' "$SCRIPT"
}

@test "managed target restore behavior" {
  #R090-T01: managed restore without --table refuses with guidance
  grep -q 'Refusing full restore against managed target' "$SCRIPT"
  #R090-T02: managed restore re-resolves credentials via supabase_direct profile
  grep -q 'supabase_direct' "$SCRIPT"
  grep -q 'PG_ONEPSA_ITEM' "$SCRIPT"
  #R090-T03: managed scoped restore invokes pg_restore against resolved host/user/db
  grep -q '\-h "\$PG_HOST" -p "\$PG_PORT" -U "\$PG_USER" -d "\$PG_DBNAME"' "$SCRIPT"
}

@test "DATABASE_NAME env override defaulting" {
  #R095-T01: DATABASE_NAME defaults to profile-resolved PG_DBNAME when unset
  grep -q 'DATABASE_NAME="\${DATABASE_NAME:-\$PG_DBNAME}"' "$SCRIPT"
}

@test "validate full-restore database identifier" {
  #R100-T01: invalid resolved DATABASE_NAME aborts before SQL checks
  grep -q 'Resolved DATABASE_NAME is not a valid PostgreSQL identifier' "$SCRIPT"
}

@test "validate scoped restore identifiers" {
  #R101-T01: invalid --table schema identifier rejected
  grep -q 'Invalid schema identifier supplied to --table' "$SCRIPT"
  #R101-T02: invalid --table relation identifier rejected
  grep -q 'Invalid table identifier supplied to --table' "$SCRIPT"
}

@test "verify integrity manifest before globals replay" {
  #R102-T01: full restore aborts when integrity manifest is missing
  grep -q 'Backup integrity manifest is missing' "$SCRIPT"
  #R102-T02: checksum verification failure aborts restore
  grep -q 'shasum -a 256 -c' "$SCRIPT"
  grep -q 'Backup integrity check failed' "$SCRIPT"
}

@test "decrypt encrypted backup artifacts to secure temp files" {
  #R110-T01: encrypted artifacts decrypted via decrypt_backup_artifact using gpg --decrypt
  grep -q 'decrypt_backup_artifact' "$SCRIPT"
  grep -q 'gpg --batch --yes --homedir "\$GPG_HOME"' "$SCRIPT"
  grep -q -- '--decrypt' "$SCRIPT"
}
