# 99 restore database Requirements

## Scope

Applies to `99_restore_database.sh`. Profile-aware PostgreSQL/SQLite restore entrypoint that resolves the active DB profile via the shared db_profile_export helper, selects the newest gpg-encrypted dump (or an explicit `--from` source), verifies a sha256 integrity manifest, decrypts artifacts to secure temp files, and replays globals plus a full `pg_restore` for local targets while supporting `--table` scoped restore for managed targets, with post-restore teller credential re-sync and invariant repair.

R001  Statement: Run in strict shell mode with private-default file permissions and operate on the resolved target repo root.
Design: Set `umask 007` and `set -euo pipefail`, then resolve `SCRIPT_DIR` honoring `RUNBOOK_REPO_ROOT` so pointer-driven runs operate on the target repo.
Tests:
- R001-T01: Verify the script sets `umask 007` and strict `set -euo pipefail`.

R005  Statement: Accept an optional backup source path and default to the newest local backup.
Design: Parse `--from`; otherwise `latest_backup_path` selects the newest encrypted `*.dump.gpg` in `backups/`, falling back to legacy plaintext `*.dump` only when no encrypted artifact exists.
Tests:
- R005-T01: Verify `latest_backup_path` selects the newest `*.dump.gpg` from the backups directory.
- R005-T02: Verify `--from` overrides default selection by setting `BACKUP_PATH`.

R010  Statement: Require restore dependencies before running restore operations.
Design: Validate that `1psa`, `pg_restore`, `psql`, and `gpg` are available on PATH and exit with a clear message when any is missing.
Tests:
- R010-T01: Verify the script requires `pg_restore` on PATH with a clear failure message.

R015  Statement: Resolve the postgres admin password from a configurable 1psa source.
Design: Read via `1psa -p` for the default `password` field or `1psa -f` for an override field from `POSTGRES_PSA_ITEM`, then refuse to proceed when the lookup is empty.
Tests:
- R015-T01: Verify the script refuses restore when the postgres password lookup is empty.

R020  Statement: Require the backup dump (and matching globals for full restore) to exist.
Design: Validate the selected backup path always; for full restore (no `--table`) require the sibling `_globals.sql.gpg` (or `_globals.sql` for legacy plaintext), and skip the globals requirement for `--table` scoped restore.
Tests:
- R020-T01: Verify full restore refuses when the matching globals backup is missing.
- R020-T02: Verify the globals requirement is gated on full-restore (no `--table`) mode.

R025  Statement: Refuse full restore into a database that already contains the teller schema unless a table scope is provided.
Design: Query the target database for schema `teller` and abort with guidance only when it exists and `--table` is not provided.
Tests:
- R025-T01: Verify full restore is refused when the teller schema already exists.
- R025-T02: Verify the refusal guidance points to `--table` for scoped restore into the existing schema.

R030  Statement: For full restore, replay globals first, then restore the database dump.
Design: Run the globals SQL via `psql -f` (with duplicate-role retry in non-stop mode), then run `pg_restore -U postgres -d postgres --clean --if-exists --create`; for `--table` restore skip globals replay entirely.
Tests:
- R030-T01: Verify full restore runs `pg_restore --clean --if-exists --create` after globals replay.
- R030-T02: Verify table-scoped restore uses `pg_restore` with `RESTORE_TABLE_ARGS` instead of globals replay.

R035  Statement: Provide fail-fast target SQL execution and print a completion line.
Design: Provide a `run_psql_target` helper bound to the target DB with `psql -v ON_ERROR_STOP=1` for repair SQL, and emit a final `Restore complete from:` message with the selected dump path.
Tests:
- R035-T01: Verify `run_psql_target` executes target SQL with `ON_ERROR_STOP=1`.
- R035-T02: Verify a successful run prints the `Restore complete from:` completion line.

R040  Statement: Accept an optional table-scoped restore selection with validated identifiers.
Design: Parse `--table <table_name|schema.table_name>`, split into schema/relation (defaulting bare names to schema `teller`), validate both via `is_valid_pg_identifier`, and build `RESTORE_TABLE_ARGS`.
Tests:
- R040-T01: Verify `--table` is parsed into `TABLE_NAME` for scoped restore.
- R040-T02: Verify a bare table name defaults to the `teller` schema.

R045  Statement: Support combining an explicit backup source with table-scoped restore.
Design: Allow `--from` and `--table` together so the scoped restore applies `RESTORE_TABLE_ARGS` against the selected `BACKUP_INPUT_PATH`.
Tests:
- R045-T01: Verify scoped restore applies `RESTORE_TABLE_ARGS` to the selected backup input.

R050  Statement: Reapply deploy-time invariants after table-scoped restore for teller schema tables.
Design: After `pg_restore --table`, run `repair_scoped_table_restore`, which is a no-op unless the resolved target is in schema `teller`.
Tests:
- R050-T01: Verify `repair_scoped_table_restore` runs after scoped restore.
- R050-T02: Verify the repair hook is skipped for non-`teller` schema targets.

R055  Statement: Ensure the shared `updated_at` trigger function exists during scoped teller restore repair.
Design: Recreate `teller.update_updated_at()` idempotently with `CREATE OR REPLACE FUNCTION` before per-table trigger repair.
Tests:
- R055-T01: Verify scoped repair recreates `teller.update_updated_at()`.

R060  Statement: Recreate the per-table `updated_at` trigger only when the restored teller table has that column.
Design: Detect the `updated_at` column via `information_schema.columns`; when present, drop and recreate `update_<table>_updated_at` via `CREATE TRIGGER`.
Tests:
- R060-T01: Verify the repair recreates the per-table trigger with `CREATE TRIGGER`.
- R060-T02: Verify trigger recreation is conditional on detecting the `updated_at` column.

R065  Statement: Reapply known table-specific DDL fixups after scoped restore.
Design: For `teller.transaction_nys_snw_category`, recreate the transaction foreign key with `ON DELETE CASCADE` to match the deploy invariant.
Tests:
- R065-T01: Verify scoped repair reapplies the `transaction_nys_snw_category` FK with `ON DELETE CASCADE`.

R070  Statement: Resolve the teller password from a configurable 1psa source for full-restore re-sync.
Design: Read the teller password via `TELLER_PSA_ITEM`/`TELLER_PSA_FIELD` (default item `localhost_postgres_teller`) and refuse to proceed when empty.
Tests:
- R070-T01: Verify the script refuses restore when the teller password lookup is empty.

R075  Statement: Re-sync the teller role credential to the current 1psa secret after full restore.
Design: In full restore mode, after globals replay and database restore, run `ALTER USER teller WITH PASSWORD` using the resolved (single-quote-escaped) teller secret.
Tests:
- R075-T01: Verify full restore runs `ALTER USER teller WITH PASSWORD` to re-sync the credential.

R080  Statement: Verify teller authentication succeeds after the full-restore credential re-sync.
Design: After the password reset, perform a `psql -U teller` login against the target database and fail restore if authentication does not succeed.
Tests:
- R080-T01: Verify restore fails when post-restore teller authentication does not succeed.

R085  Statement: Resolve the active DB profile via the shared helper and refuse when it is missing.
Design: Resolve `db_profile_export.sh`, refuse with an error when the helper is missing or not executable, and source whitelisted `PROFILE_*`/`PG_*` exports before any restore action.
Tests:
- R085-T01: Verify the script refuses to run when the `db_profile_export.sh` helper is missing or not executable.

R086  Statement: Support SQLite restore through the existing restore entrypoint.
Design: When the profile dialect/target is `sqlite`, decrypt if needed and copy the resolved backup to `SQLITE_PATH`, rejecting `--table` scoped restore for sqlite targets.
Tests:
- R086-T01: Verify sqlite restore copies the backup to `SQLITE_PATH` and rejects `--table` scope.

R090  Statement: Managed-target restore refuses full restore and supports only `--table` scoped restore against the direct host.
Design: For `PROFILE_TARGET=managed` without `--table`, exit non-zero with guidance; otherwise re-resolve via the `supabase_direct` profile, read the password from `PG_ONEPSA_ITEM` (with `TELLER_DB_PASSWORD` override), and invoke `pg_restore -h/-p/-U/-d --clean --if-exists` with the scoped table args.
Tests:
- R090-T01: Verify managed-target restore without `--table` refuses with explicit guidance.
- R090-T02: Verify managed restore re-resolves credentials via the `supabase_direct` profile.
- R090-T03: Verify managed scoped restore invokes `pg_restore` against the resolved managed host/user/database.

R095  Statement: Honor an existing `DATABASE_NAME` env override on local-target runs while defaulting to the profile-resolved DB.
Design: Set `DATABASE_NAME="${DATABASE_NAME:-$PG_DBNAME}"` so legacy callers keep working while default runs adopt the resolved profile database.
Tests:
- R095-T01: Verify `DATABASE_NAME` defaults to the profile-resolved `PG_DBNAME` when unset.

R100  Statement: Validate the full-restore database target identifier before destructive checks.
Design: Require the resolved `DATABASE_NAME` to satisfy `is_valid_pg_identifier` before any database existence checks or restore commands run.
Tests:
- R100-T01: Verify restore exits when the resolved `DATABASE_NAME` is not a valid PostgreSQL identifier.

R101  Statement: Validate scoped restore schema/table identifiers before repair SQL.
Design: Reject invalid `--table` schema and relation identifiers via `is_valid_pg_identifier` before building restore args or running repair SQL.
Tests:
- R101-T01: Verify an invalid `--table` schema identifier is rejected.
- R101-T02: Verify an invalid `--table` relation identifier is rejected.

R102  Statement: Require and verify the backup integrity manifest before full-restore globals replay.
Design: In full restore mode, require the sibling `*.manifest.sha256` and verify the dump/globals pair with `shasum -a 256 -c` via `verify_backup_manifest` before globals replay.
Tests:
- R102-T01: Verify full restore aborts when the integrity manifest is missing.
- R102-T02: Verify the manifest checksum verification failure aborts restore.

R110  Statement: Resolve backup decryption configuration and decrypt encrypted artifacts to secure temp files.
Design: For `.gpg` artifacts read `type`/`gpg_private_key`/`gpg_private_key_passphrase` from `POSTGRES_BACKUP_ENCRYPTION` (with env fallback), require `type=gpg`, and decrypt to mode-600 `mktemp` files via `decrypt_backup_artifact`, cleaned up via `trap`.
Tests:
- R110-T01: Verify encrypted artifacts are decrypted via `decrypt_backup_artifact` using `gpg --decrypt`.

## Changelog

- 2026-06-06: Converted from requirements-only to a full traceability doc reconciled to current source.
- 2026-05-31: Added R110 for encrypted restore decryption contract and updated R005/R010/R020/R102 for encrypted backup defaults and verification semantics.
- 2026-05-30: Added R086 for SQLite restore behavior, and R100-R102 for identifier validation, scoped repair SQL parameterization, and full-restore manifest integrity verification.
- 2026-05-26: Added R085/R090/R095 for profile-aware restore behavior; managed-target restore is `--table`-only with profile-resolved credentials.
- 2026-05-09: Added R070/R075/R080 for full-restore teller credential re-sync and auth verification against current 1psa secret.
- 2026-04-24: Added R050/R055/R060/R065 for post-scoped-restore invariant repair; refined R035 for fail-fast target SQL helper coverage.
- 2026-04-21: Added R040/R045 for optional `--table` restore scope and `--from` composition; refined R020/R025/R030 for table mode.
- 2026-04-19: Initial reverse-engineered requirements for `99_restore_database.sh`.
