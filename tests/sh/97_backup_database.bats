#!/usr/bin/env bats
# Companion tests for 97_backup_database.sh requirements traceability.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/97_backup_database.sh"
}

@test "strict shell mode and secure umask" {
  #R001-T01: source sets strict shell mode and secure umask
  grep -q 'set -euo pipefail' "$SCRIPT"
  grep -q 'umask 007' "$SCRIPT"
}

@test "requires backup dependencies on PATH" {
  #R005-T01: source checks pg_dump and pg_dumpall presence before dumping
  grep -q 'command -v pg_dump' "$SCRIPT"
  grep -q 'command -v pg_dumpall' "$SCRIPT"
}

@test "resolves local postgres password from configurable 1psa item" {
  #R010-T01: source reads POSTGRES_PSA_ITEM/POSTGRES_PSA_FIELD via 1psa
  grep -q 'POSTGRES_PSA_ITEM' "$SCRIPT"
  grep -q 'POSTGRES_PSA_FIELD' "$SCRIPT"
}

@test "refuses backup when postgres password is empty" {
  #R015-T01: source exits with a clear message on empty password lookup
  grep -q 'Failed to read postgres password' "$SCRIPT"
}

@test "creates backup directory with restricted permissions" {
  #R020-T01: source creates backups dir and chmods it to 700
  grep -q 'mkdir -p "\$BACKUP_DIR"' "$SCRIPT"
  grep -q 'chmod 700 "\$BACKUP_DIR"' "$SCRIPT"
}

@test "writes custom-format timestamped database dump" {
  #R025-T01: source invokes pg_dump in custom format
  grep -q 'pg_dump' "$SCRIPT"
  grep -q -- '-Fc' "$SCRIPT"
}

@test "writes globals-only dump for roles and grants" {
  #R030-T01: source runs pg_dumpall --globals-only into a globals file
  grep -q 'pg_dumpall' "$SCRIPT"
  grep -q -- '--globals-only' "$SCRIPT"
  grep -q '_globals.sql' "$SCRIPT"
}

@test "restricts permissions and prints output paths" {
  #R035-T01: source encrypts artifacts, chmods 600, prints Backup written
  grep -q 'encrypt_artifact' "$SCRIPT"
  grep -q 'chmod 600' "$SCRIPT"
  grep -q 'Backup written:' "$SCRIPT"
}

@test "resolves active DB profile via shared helper" {
  #R040-T01: source invokes db_profile_export.sh and refuses when missing
  grep -q 'db_profile_export.sh' "$SCRIPT"
  grep -q 'DB profile helper is missing' "$SCRIPT"
}

@test "encodes resolved profile into the backup basename" {
  #R040-T02: source builds basename from PROFILE_NAME and TIMESTAMP
  grep -q 'BACKUP_BASENAME="\${PROFILE_NAME}_' "$SCRIPT"
  grep -q 'TIMESTAMP' "$SCRIPT"
}

@test "supports sqlite backups without pg_dump" {
  #R041-T01: source copies SQLITE_PATH file on the sqlite branch
  grep -q 'SQLITE_PATH' "$SCRIPT"
  grep -q 'cp "\$SQLITE_DB_PATH" "\$BACKUP_PATH"' "$SCRIPT"
}

@test "managed target dumps a schema scope against the direct host" {
  #R045-T01: managed branch runs pg_dump with -n PG_SEARCH_PATH
  grep -q 'PROFILE_TARGET:-local}" == "managed"' "$SCRIPT"
  grep -q -- '-n "\$PG_SEARCH_PATH"' "$SCRIPT"
}

@test "managed target skips globals and reports the gap" {
  #R045-T02: managed branch prints Globals skipped and skips pg_dumpall
  grep -q 'Globals skipped:' "$SCRIPT"
}

@test "honors DATABASE_NAME override on local target" {
  #R050-T01: local branch defaults DATABASE_NAME from PG_DBNAME
  grep -q 'DATABASE_NAME="\${DATABASE_NAME:-\$PG_DBNAME}"' "$SCRIPT"
}

@test "emits integrity manifest for full local backups" {
  #R055-T01: source builds a sha256 manifest and chmods it 600
  grep -q 'shasum -a 256' "$SCRIPT"
  grep -q 'manifest.sha256' "$SCRIPT"
  grep -q 'chmod 600 "\$MANIFEST_PATH"' "$SCRIPT"
}

@test "prints manifest path on full local backups" {
  #R055-T02: source prints Manifest written with the manifest path
  grep -q 'Manifest written:' "$SCRIPT"
}

@test "encrypts all backup artifacts with gpg" {
  #R110-T01: source requires gpg, enforces type=gpg, and encrypts artifacts
  grep -q 'command -v gpg' "$SCRIPT"
  grep -q 'type=gpg' "$SCRIPT"
  grep -q 'gpg .*--encrypt' "$SCRIPT"
}
