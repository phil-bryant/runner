# 98 destroy database Requirements

## Scope

Applies to `98_destroy_database.sh`. This runner golden tears down a teller database target: it resolves the active DB profile, requires explicit `destroy` confirmation, and removes the database/schema plus teller roles for local PostgreSQL, managed (Supabase) schema, or SQLite targets.

R001  Statement: Run fail-fast with private-default permissions, anchored to the target repo root.
Design: Set `umask 007` and `set -euo pipefail`, then resolve `SCRIPT_DIR="${RUNBOOK_REPO_ROOT:-$SCRIPT_DIR}"` so pointer-driven runs operate on the consuming repo.
Tests:
- R001-T01: Verify source sets `umask 007`, `set -euo pipefail`, and anchors `SCRIPT_DIR` to `RUNBOOK_REPO_ROOT`.

R005  Statement: Require `1psa` and resolve the postgres password from a configurable source, refusing empty results.
Design: Probe `command -v 1psa`, default `POSTGRES_PSA_ITEM`/`POSTGRES_PSA_FIELD`, read via `1psa`, and exit when the lookup is empty.
Tests:
- R005-T01: Verify source probes `command -v 1psa`, reads `POSTGRES_PSA_ITEM`, and errors on an empty password.

R010  Statement: Require explicit destructive confirmation before any teardown.
Design: Prompt the operator to type `destroy`; otherwise print `Destruction cancelled` and exit non-zero.
Tests:
- R010-T01: Verify source prompts to type `destroy` and cancels when confirmation does not match.

R015  Statement: Clean dependent resources before dropping the local database.
Design: When the database exists, drop `teller.transaction_info_view` and run `pg_terminate_backend` against active sessions.
Tests:
- R015-T01: Verify source drops the dependent teller view and terminates active backends before the drop.

R020  Statement: Drop the target database, user, and teller roles idempotently.
Design: Execute `DROP DATABASE IF EXISTS`, `DROP USER IF EXISTS teller`, and `DROP ROLE IF EXISTS` for the teller roles.
Tests:
- R020-T01: Verify source issues idempotent `DROP DATABASE`/`DROP USER`/`DROP ROLE IF EXISTS` statements.

R025  Statement: Print completion status after teardown finishes.
Design: Emit the final `Cleanup complete!` line on each successful teardown path.
Tests:
- R025-T01: Verify source prints `Cleanup complete!` after teardown.

R026  Statement: Support SQLite teardown through the existing destroy entrypoint.
Design: When the dialect/target is `sqlite`, require `SQLITE_PATH`, demand the same `destroy` confirmation, then `rm -f` the resolved SQLite artifact.
Tests:
- R026-T01: Verify source handles the sqlite path: requires `SQLITE_PATH` and removes the resolved artifact.

R030  Statement: Validate the local database identifier before any destructive local SQL.
Design: Assign `LOCAL_DBNAME="$PG_DBNAME"` and reject it via `is_valid_pg_identifier` before existence checks, session termination, and drops.
Tests:
- R030-T01: Verify source validates `LOCAL_DBNAME` with `is_valid_pg_identifier` and refuses invalid identifiers.

R031  Statement: Execute local destroy SQL directly using the pre-validated identifier, compatible with `psql -c`.
Design: Because `LOCAL_DBNAME` is already validated by `is_valid_pg_identifier`, run direct SQL — a `SELECT 1 FROM pg_database WHERE datname = '${LOCAL_DBNAME}'` existence probe and `DROP DATABASE IF EXISTS \"${LOCAL_DBNAME}\"` — via `psql -c` rather than server-side `format('%I', ...) \gexec`.
Tests:
- R031-T01: Verify source uses a direct `pg_database` existence probe and direct `DROP DATABASE` (no `\gexec`) for the validated `LOCAL_DBNAME`.

R032  Statement: Validate the managed schema identifier and refuse protected schemas before managed teardown.
Design: Require managed `SCHEMA_NAME` (from `PG_SEARCH_PATH`) to pass `is_valid_pg_identifier`, and refuse `public`, `pg_catalog`, and `information_schema`.
Tests:
- R032-T01: Verify source validates the managed schema identifier and refuses protected schemas.

R033  Statement: Execute managed `DROP SCHEMA` directly using the pre-validated identifier, compatible with `psql -c`.
Design: Because `SCHEMA_NAME` is already validated, run `DROP SCHEMA IF EXISTS \"${SCHEMA_NAME}\" CASCADE` directly through `run_psql_managed -c` instead of server-side `format('%I', ...) \gexec`.
Tests:
- R033-T01: Verify source drops the managed schema directly via `DROP SCHEMA IF EXISTS ... CASCADE` (no `\gexec`).

## Changelog

- 2026-06-06: Converted from requirements-only to a full traceability doc reconciled to current source.
