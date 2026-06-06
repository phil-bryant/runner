# 97 backup database Requirements

## Scope

Applies to `97_backup_database.sh`. This script produces encrypted, profile-aware backups of the active database: it resolves the active DB profile via the shared db_profile_export helper, dumps the local/managed Postgres database (or copies the SQLite file), encrypts every artifact with GPG, and emits an integrity manifest for full local backups.

R001  Statement: Run in strict shell mode with private-default file permissions and operate from the resolved target repo root.
Design: Set `umask 007` and `set -euo pipefail`; resolve `SCRIPT_DIR` and override it with `RUNBOOK_REPO_ROOT` when set so backups land under the target repo's `backups/` directory.
Tests:
- R001-T01: Verify the script sets `set -euo pipefail` and `umask 007`.

R005  Statement: Require backup dependencies before running any dump operation.
Design: Verify `1psa`, `pg_dump`, and `pg_dumpall` are present on PATH via `command -v`, exiting with a clear message if any is missing.
Tests:
- R005-T01: Verify the script checks `command -v pg_dump` and `pg_dumpall` and fails when missing.

R010  Statement: Resolve the local postgres password from a configurable 1psa item and field.
Design: Use `POSTGRES_PSA_ITEM`/`POSTGRES_PSA_FIELD` (defaulting to `localhost_postgres_postgres`/`password`); read via `1psa -p` for the default password field or `1psa -f` for an override field.
Tests:
- R010-T01: Verify the script reads `POSTGRES_PSA_ITEM`/`POSTGRES_PSA_FIELD` and resolves the password via `1psa`.

R015  Statement: Refuse backup when the postgres password resolves empty.
Design: After the 1psa lookup, validate the password is non-empty and exit non-zero with `Failed to read postgres password` otherwise.
Tests:
- R015-T01: Verify an empty password triggers the `Failed to read postgres password` exit path.

R020  Statement: Create the backup output directory with restricted permissions.
Design: Run `mkdir -p "$BACKUP_DIR"` then `chmod 700 "$BACKUP_DIR"` so the directory is owner-only.
Tests:
- R020-T01: Verify the script creates `backups/` with `mkdir -p` and applies mode `700`.

R025  Statement: Write the database dump in custom format with create-database metadata.
Design: Run `pg_dump -Fc` (with `-C` for local targets) into a timestamped `<profile>_<db>_<timestamp>.dump` file.
Tests:
- R025-T01: Verify the script invokes `pg_dump -Fc` writing a timestamped `.dump` artifact.

R030  Statement: Write a globals-only dump for roles and grants on local backups.
Design: Run `pg_dumpall --globals-only` (adding `--no-role-passwords` unless `BACKUP_INCLUDE_ROLE_AUTH_DATA=true`) into a matching `_globals.sql` file.
Tests:
- R030-T01: Verify the script runs `pg_dumpall --globals-only` into a `_globals.sql` file.

R035  Statement: Restrict backup file permissions and print resulting output paths.
Design: Encrypt artifacts to `.gpg` via `encrypt_artifact`, apply mode `600` to encrypted output, and print `Backup written:` (and globals) lines for the operator.
Tests:
- R035-T01: Verify `encrypt_artifact` applies `chmod 600` and the script prints `Backup written:`.

R040  Statement: Resolve the active DB profile via the shared helper and refuse to back up when the helper is missing.
Design: Source whitelisted `PROFILE_NAME`/`PROFILE_TARGET`/`PG_*` exports from `src/scripts/db_profile_export.sh`; require non-empty `PROFILE_NAME`/`PROFILE_TARGET`; encode the resolved profile name into the backup basename so dumps across targets do not collide.
Tests:
- R040-T01: Verify the script invokes the `db_profile_export.sh` helper and refuses when it is missing.
- R040-T02: Verify the backup basename encodes `${PROFILE_NAME}_..._${TIMESTAMP}` from the resolved profile.

R041  Statement: Support SQLite backups through the existing backup entrypoint.
Design: When `DB_DIALECT=sqlite` or `PROFILE_TARGET=sqlite`, copy the resolved `SQLITE_PATH` file, encrypt it, and emit a completion line without invoking `pg_dump`/`pg_dumpall`.
Tests:
- R041-T01: Verify the sqlite branch uses `SQLITE_PATH` and copies the database file instead of running `pg_dump`.

R045  Statement: Managed-target backup uses the profile connection user against the direct host and skips globals.
Design: When `PROFILE_TARGET=managed`, re-resolve via the `supabase_direct` profile, read the password from `PG_ONEPSA_ITEM` via `1psa` (with `TELLER_DB_PASSWORD` override), run a schema-scoped `pg_dump -Fc -n "$PG_SEARCH_PATH"`, skip `pg_dumpall`, and print a `Globals skipped:` line.
Tests:
- R045-T01: Verify the managed branch runs `pg_dump` with `-n "$PG_SEARCH_PATH"` against the direct host.
- R045-T02: Verify the managed branch prints `Globals skipped:` and does not run `pg_dumpall`.

R050  Statement: Honor an existing `DATABASE_NAME` env override for backward compatibility on local-target runs.
Design: For local-target runs set `DATABASE_NAME="${DATABASE_NAME:-$PG_DBNAME}"` so pinned callers keep working while others default to the profile-resolved DB.
Tests:
- R050-T01: Verify the local branch defaults `DATABASE_NAME` from `PG_DBNAME` when no override is set.

R055  Statement: Emit an integrity manifest for full local backup dump/globals pairs.
Design: After encrypting the local `.dump` and `_globals.sql` artifacts, run `shasum -a 256` over both encrypted files into a sibling `*.manifest.sha256`, restrict it to mode `600`, and print a `Manifest written:` line.
Tests:
- R055-T01: Verify the script runs `shasum -a 256` to build a `manifest.sha256` and applies mode `600`.
- R055-T02: Verify the script prints a `Manifest written:` line with the manifest path.

R110  Statement: Resolve backup encryption configuration and encrypt all backup outputs at rest with GPG.
Design: Require `gpg` on PATH; read `type`/`gpg_recipient`/`gpg_public_key` via `read_backup_encryption_field` (`1psa -f POSTGRES_BACKUP_ENCRYPTION <field>` with `POSTGRES_BACKUP_ENCRYPTION_<FIELD>` env fallback); require `type=gpg`, import the public key into a temp `GPG_HOME`, encrypt each artifact, remove plaintext, and report `.gpg` output paths.
Tests:
- R110-T01: Verify the script requires `gpg`, enforces `type=gpg`, and encrypts artifacts via `gpg --encrypt`.

## Changelog

- 2026-06-06: Converted from requirements-only to a full traceability doc reconciled to current source.
