# 06 deploy database Requirements

## Scope

These requirements govern `06_deploy_database.sh`, the shared runner golden that
deploys the teller database schema. The script resolves the active DB profile
through a shared export helper, then applies SQL DDL to one of three targets:
a managed Postgres instance (direct, non-pooler connection), a local Postgres
instance bootstrapped as the `postgres` superuser, or an encrypted SQLite
database via sqlcipher. Every requirement below maps 1:1 to a scoped `#Rxxx:`
tag in the script and is exercised by source-assertion tests in
`tests/sh/06_deploy_database.bats` that confirm the implementing code exists
without contacting a database, 1Password, or the network.

R001  Statement: The script runs in fail-fast strict shell mode with a private umask and operates on the target repository root rather than the caller's working directory.
Design: It sets `umask 007` and `set -euo pipefail` before any logic, then resolves `SCRIPT_DIR` from `RUNBOOK_REPO_ROOT` (set by the rNN_ pointer) so all paths are anchored to the target repo, defaulting to the script's own directory.
Tests:
- R001-T01: Assert the source sets `umask 007`, enables `set -euo pipefail`, and anchors `SCRIPT_DIR` to `RUNBOOK_REPO_ROOT`.

R005  Statement: The script requires the `1psa` credential helper to be installed before performing any 1Password-backed credential lookups.
Design: Before reading local Postgres credentials it probes `command -v 1psa` and exits non-zero with a "1psa is required" message when the helper is absent.
Tests:
- R005-T01: Assert the source probes `command -v 1psa` and errors when it is missing.

R006  Statement: The script makes psql fail fast on the first SQL error so a broken DDL statement aborts the deploy instead of continuing.
Design: It builds a shared `PSQL_OPTS` array containing `-v ON_ERROR_STOP=1` that every psql invocation reuses.
Tests:
- R006-T01: Assert the source defines `PSQL_OPTS` with `ON_ERROR_STOP=1`.

R007  Statement: The script provides a helper that runs SQL as the local `postgres` superuser with the fail-fast psql options.
Design: It defines `run_psql_postgres()`, which exports `PGPASSWORD`/`PGSSLMODE` and invokes `psql "${PSQL_OPTS[@]}" -U postgres`.
Tests:
- R007-T01: Assert the source defines `run_psql_postgres()` connecting as `-U postgres`.

R008  Statement: The script provides a helper that runs SQL as the resolved teller role against the resolved database with the fail-fast psql options.
Design: It defines `run_psql_teller()`, which exports the teller password and invokes `psql "${PSQL_OPTS[@]}" -U "$PG_USER" -d "$PG_DBNAME"`.
Tests:
- R008-T01: Assert the source defines `run_psql_teller()` connecting as `-U "$PG_USER"`.

R010  Statement: The script reads the local Postgres admin password from a configurable 1Password item and field so consuming profiles can override the source.
Design: It defaults `POSTGRES_PSA_ITEM`/`POSTGRES_PSA_FIELD` to `localhost_postgres_postgres`/`password` and resolves `POSTGRES_PASSWORD` via `1psa -p` (password field) or `1psa -f` (other fields).
Tests:
- R010-T01: Assert the source defines `POSTGRES_PSA_ITEM`/`POSTGRES_PSA_FIELD` defaults and resolves the password via `1psa`.

R015  Statement: The script reads the local teller user password from a configurable 1Password item and field so consuming profiles can override the source.
Design: It defaults `TELLER_PSA_ITEM`/`TELLER_PSA_FIELD` to `localhost_postgres_teller`/`password` and resolves `TELLER_PASSWORD` via `1psa -p` or `1psa -f`.
Tests:
- R015-T01: Assert the source defines `TELLER_PSA_ITEM`/`TELLER_PSA_FIELD` defaults and resolves the password via `1psa`.

R020  Statement: The script refuses to deploy when either resolved local password is empty so it never runs DDL with missing credentials.
Design: After resolving each credential it checks `[ -z "$POSTGRES_PASSWORD" ]` and `[ -z "$TELLER_PASSWORD" ]`, printing a "Failed to read ... password" message and exiting non-zero.
Tests:
- R020-T01: Assert the source rejects empty postgres and teller passwords before deploying.

R025  Statement: The script runs the admin bootstrap SQL that configures the database, roles, and privileges in the required order.
Design: As the `postgres` superuser it applies `configure_database.sql` with the resolved db name, teller user, and teller password bound as psql variables.
Tests:
- R025-T01: Assert the source applies `configure_database.sql` with the bootstrap variables.

R030  Statement: The script builds local Teller/Classy/Matchy schema objects by applying SQL files in declared dependency order.
Design: As the teller role it runs `run_psql_teller -f` over ordered files beginning with `teller_enums.sql`, then `classy_*.sql`, `matchy_enums.sql`, and `matchy_*.sql`.
Tests:
- R030-T01: Assert the source applies ordered schema files including `teller_enums.sql` and `matchy_enums.sql` as the teller role.

R035  Statement: The script resolves the SQL source directories relative to the resolved script location rather than the caller's path.
Design: It sets `SQL_DIR` to `${SCRIPT_DIR}/src/sql/postgres` and `SQLITE_SQL_DIR` to `${SCRIPT_DIR}/src/sql/sqlite`.
Tests:
- R035-T01: Assert the source resolves `SQL_DIR` under `${SCRIPT_DIR}/src/sql/postgres`.

R040  Statement: The script attaches the updated_at triggers only after every table that the triggers reference already exists.
Design: It applies `create_triggers.sql` after all `teller_*` table files have been created.
Tests:
- R040-T01: Assert the source applies `create_triggers.sql`.

R045  Statement: The script repairs the transaction-classification foreign key so deleting a transaction cascades to its NYS SNW category rows.
Design: It runs an `ALTER TABLE classy.transaction_nys_snw_category` that drops and re-adds `transaction_nys_snw_category_transaction_id_fkey` with `ON DELETE CASCADE`.
Tests:
- R045-T01: Assert the source rebuilds the classification FK with `ON DELETE CASCADE`.

R050  Statement: The script ensures the pgTAP extension exists in the resolved local database so SQL unit tests can run.
Design: As the `postgres` superuser it runs `CREATE EXTENSION IF NOT EXISTS pgtap;` against the resolved database.
Tests:
- R050-T01: Assert the source creates the `pgtap` extension when deploying locally.

R055  Statement: The script applies the explicit reconcile/audit grants required by the runtime ingest role.
Design: As the teller role it applies `grant_ingest_reconcile_privileges.sql` as the final local deploy step.
Tests:
- R055-T01: Assert the source applies `grant_ingest_reconcile_privileges.sql`.

R060  Statement: The script resolves the active DB profile through the shared export helper, prints the resolved deploy target, and forces the direct (non-pooler) profile for managed DDL.
Design: It locates `db_profile_export.sh`, sources its exports, echoes the resolved `profile/target/dialect`, and for managed targets re-resolves with `--profile supabase_direct` so DDL never goes through the transaction pooler.
Tests:
- R060-T01: Assert the source resolves the profile via `db_profile_export.sh`, prints the deploy target, and forces `supabase_direct` for managed DDL.

R065  Statement: The script resolves the managed-target password from the profile's 1Password item while still allowing an environment override.
Design: For managed deploys it uses `TELLER_DB_PASSWORD` when set, otherwise requires `PG_ONEPSA_ITEM` and resolves the password via `1psa -p "$PG_ONEPSA_ITEM"`, failing if the result is empty.
Tests:
- R065-T01: Assert the source resolves the managed password from `PG_ONEPSA_ITEM` with a `TELLER_DB_PASSWORD` override.

R070  Statement: The script applies the managed schema using the profile's connection user, creating product schemas first and then ordered schema files.
Design: It defines `run_psql_managed()` against the resolved host/port/db/user, runs `CREATE SCHEMA IF NOT EXISTS teller/classy/matchy;`, then applies ordered `teller_*.sql`, `classy_*.sql`, `matchy_enums.sql`, and `matchy_*.sql` files.
Tests:
- R070-T01: Assert the source defines `run_psql_managed()` and creates the teller/classy/matchy schemas before applying managed schema files.

R071  Statement: The script deploys the SQLite dialect through sqlcipher when the profile selects a SQLite target.
Design: When the dialect or target is `sqlite` it validates `SQLITE_PATH` and the cipher key, requires `sqlcipher` on PATH, and applies the SQLite `create_database.sql` from `SQLITE_SQL_DIR` keyed with `PRAGMA key`.
Tests:
- R071-T01: Assert the source applies the SQLite schema via `sqlcipher` from `SQLITE_SQL_DIR`.

R072  Statement: The script supports helpers that omit `SQLCIPHER_KEY` from default profile exports by resolving it explicitly only when needed.
Design: In the SQLite branch, when `SQLCIPHER_KEY` and `TELLER_DB_SQLCIPHER_KEY` are empty, probe the profile helper for `--print-sqlcipher-key` support and use that output as the cipher key.
Tests:
- R072-T01: Assert the source conditionally resolves `SQLCIPHER_KEY` via `db_profile_export.sh --print-sqlcipher-key` when default exports omit it.

R075  Statement: The script intentionally skips pgTAP extension creation on managed targets because the extension is not allow-listed there.
Design: The managed branch exits before any pgTAP creation and documents the deliberate skip inline.
Tests:
- R075-T01: Assert the source documents skipping pgTAP creation on managed targets.

R080  Statement: The script intentionally skips the teller_write ingest grants on managed targets because no teller_write role exists there.
Design: The managed branch exits before applying any teller_write grants and documents the deliberate skip inline.
Tests:
- R080-T01: Assert the source documents skipping teller_write grants on managed targets.

R085  Statement: The script skips creating the local database when the resolved database already exists so re-runs against an existing DB do not error.
Design: It queries `pg_database` for the resolved `PG_DBNAME` and only runs `create_database.sql` when the existence check (`prod_exists`) comes back empty.
Tests:
- R085-T01: Assert the source guards `create_database.sql` behind an empty `prod_exists` existence check.

R090  Statement: The script refuses to deploy when DB profile resolution fails, with no implicit fallback to a local target.
Design: It exits non-zero when the profile helper is missing or non-executable and when the helper invocation or export load fails.
Tests:
- R090-T01: Assert the source aborts when the profile helper is missing or not executable.

R095  Statement: The script validates the profile-resolved database and user identifiers before using them in SQL execution.
Design: It defines `is_valid_pg_identifier()` and rejects a `PG_DBNAME` or `PG_USER` that is missing or not a valid PostgreSQL identifier.
Tests:
- R095-T01: Assert the source validates `PG_DBNAME`/`PG_USER` via `is_valid_pg_identifier`.

R096  Statement: The script uses a directly interpolated SQL existence check for the already-validated database name to stay compatible with `psql -c`.
Design: Because the identifier is pre-validated, it builds the `SELECT 1 FROM pg_database WHERE datname = '...'` probe by direct substitution rather than a bound psql variable.
Tests:
- R096-T01: Assert the source runs the direct `SELECT 1 FROM pg_database` existence probe for the validated identifier.
