#!/usr/bin/env bats
# Source-assertion unit tests for 06_deploy_database.sh (runner golden DB deploy).
# These tests verify that the implementing code for each requirement physically
# exists in the script without executing any deploy (no psql, sqlcipher, 1psa,
# database, or network side effects).

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/06_deploy_database.sh"
}

@test "script runs fail-fast and anchors to the target repo root" {
  #R001-T01: source sets umask 007, set -euo pipefail, and anchors SCRIPT_DIR to RUNBOOK_REPO_ROOT
  grep -q 'umask 007' "$SCRIPT"
  grep -q 'set -euo pipefail' "$SCRIPT"
  grep -q 'SCRIPT_DIR="${RUNBOOK_REPO_ROOT:-$SCRIPT_DIR}"' "$SCRIPT"
}

@test "script requires the 1psa helper before credential lookups" {
  #R005-T01: source probes command -v 1psa and errors when missing
  grep -q 'command -v 1psa' "$SCRIPT"
  grep -q '1psa is required but was not found on PATH' "$SCRIPT"
}

@test "script makes psql fail fast on the first SQL error" {
  #R006-T01: source defines PSQL_OPTS with ON_ERROR_STOP=1
  grep -q 'PSQL_OPTS=(-v ON_ERROR_STOP=1)' "$SCRIPT"
}

@test "script defines the postgres superuser psql helper" {
  #R007-T01: source defines run_psql_postgres() connecting as -U postgres
  grep -q 'run_psql_postgres()' "$SCRIPT"
  grep -q 'psql "${PSQL_OPTS\[@\]}" -U postgres' "$SCRIPT"
}

@test "script defines the teller-role psql helper" {
  #R008-T01: source defines run_psql_teller() connecting as the resolved teller user/db
  grep -q 'run_psql_teller()' "$SCRIPT"
  grep -q '\-U "$PG_USER" -d "$PG_DBNAME"' "$SCRIPT"
}

@test "script reads the postgres admin password from a configurable 1psa source" {
  #R010-T01: source defines POSTGRES_PSA_ITEM/FIELD defaults and resolves via 1psa
  grep -q 'POSTGRES_PSA_ITEM="${POSTGRES_PSA_ITEM:-localhost_postgres_postgres}"' "$SCRIPT"
  grep -q 'POSTGRES_PSA_FIELD="${POSTGRES_PSA_FIELD:-password}"' "$SCRIPT"
  grep -q 'POSTGRES_PASSWORD="$(1psa' "$SCRIPT"
}

@test "script reads the teller password from a configurable 1psa source" {
  #R015-T01: source defines TELLER_PSA_ITEM/FIELD defaults and resolves via 1psa
  grep -q 'TELLER_PSA_ITEM="${TELLER_PSA_ITEM:-localhost_postgres_teller}"' "$SCRIPT"
  grep -q 'TELLER_PSA_FIELD="${TELLER_PSA_FIELD:-password}"' "$SCRIPT"
  grep -q 'TELLER_PASSWORD="$(1psa' "$SCRIPT"
}

@test "script refuses to deploy with empty local passwords" {
  #R020-T01: source rejects empty postgres and teller passwords
  grep -q 'Failed to read postgres password from 1psa item' "$SCRIPT"
  grep -q 'Failed to read teller password from 1psa item' "$SCRIPT"
}

@test "script runs the admin bootstrap configure_database SQL" {
  #R025-T01: source applies configure_database.sql with bootstrap variables
  grep -q 'configure_database.sql' "$SCRIPT"
  grep -q 'teller_password="$TELLER_PASSWORD"' "$SCRIPT"
}

@test "script builds the local teller schema in dependency order" {
  #R030-T01: source applies ordered teller schema files starting with teller_enums.sql as teller
  grep -q 'run_psql_teller -f "${SQL_DIR}/teller_enums.sql"' "$SCRIPT"
}

@test "script resolves SQL directories relative to the script location" {
  #R035-T01: source resolves SQL_DIR under ${SCRIPT_DIR}/src/sql/postgres
  grep -q 'SQL_DIR="${SCRIPT_DIR}/src/sql/postgres"' "$SCRIPT"
}

@test "script attaches updated_at triggers after tables exist" {
  #R040-T01: source applies create_triggers.sql
  grep -q 'create_triggers.sql' "$SCRIPT"
}

@test "script repairs the classification FK with cascade delete" {
  #R045-T01: source rebuilds the classification FK with ON DELETE CASCADE
  grep -q 'transaction_nys_snw_category_transaction_id_fkey' "$SCRIPT"
  grep -q 'ON DELETE CASCADE' "$SCRIPT"
}

@test "script ensures the pgtap extension exists locally" {
  #R050-T01: source creates the pgtap extension when deploying locally
  grep -q 'CREATE EXTENSION IF NOT EXISTS pgtap;' "$SCRIPT"
}

@test "script applies the reconcile/audit ingest grants" {
  #R055-T01: source applies grant_ingest_reconcile_privileges.sql
  grep -q 'grant_ingest_reconcile_privileges.sql' "$SCRIPT"
}

@test "script resolves the profile, prints the target, and forces supabase_direct" {
  #R060-T01: source resolves via db_profile_export.sh, prints target, forces supabase_direct
  grep -q 'db_profile_export.sh' "$SCRIPT"
  grep -q 'Deploying database via profile=' "$SCRIPT"
  grep -q -- '--profile supabase_direct' "$SCRIPT"
}

@test "script resolves the managed password from PG_ONEPSA_ITEM with override" {
  #R065-T01: source resolves managed password from PG_ONEPSA_ITEM, env override wins
  grep -q 'MANAGED_PASSWORD="${TELLER_DB_PASSWORD:-}"' "$SCRIPT"
  grep -q '1psa -p "$PG_ONEPSA_ITEM"' "$SCRIPT"
}

@test "script applies managed schema via run_psql_managed after creating the schema" {
  #R070-T01: source defines run_psql_managed() and creates teller schema before applying files
  grep -q 'run_psql_managed()' "$SCRIPT"
  grep -q 'CREATE SCHEMA IF NOT EXISTS teller;' "$SCRIPT"
}

@test "script deploys the sqlite dialect via sqlcipher" {
  #R071-T01: source applies SQLite schema via sqlcipher from SQLITE_SQL_DIR
  grep -q 'sqlcipher' "$SCRIPT"
  grep -q 'SQLITE_SQL_DIR' "$SCRIPT"
}

@test "script documents skipping pgtap creation on managed targets" {
  #R075-T01: source documents skipping pgTAP creation on managed targets
  grep -q 'Skip pgtap extension creation on managed targets' "$SCRIPT"
}

@test "script documents skipping teller_write grants on managed targets" {
  #R080-T01: source documents skipping teller_write grants on managed targets
  grep -q 'Skip teller_write ingest grants on managed targets' "$SCRIPT"
}

@test "script skips create_database when the database already exists" {
  #R085-T01: source guards create_database.sql behind an empty prod_exists check
  grep -q 'prod_exists' "$SCRIPT"
  grep -q 'if \[ -z "$prod_exists" \]' "$SCRIPT"
  grep -q 'create_database.sql' "$SCRIPT"
}

@test "script aborts when the profile helper is unavailable" {
  #R090-T01: source aborts when the profile helper is missing or not executable
  grep -q 'if \[\[ ! -x "$DB_PROFILE_HELPER" \]\]' "$SCRIPT"
  grep -q 'DB profile helper is missing or not executable' "$SCRIPT"
}

@test "script validates resolved postgres identifiers before SQL" {
  #R095-T01: source validates PG_DBNAME/PG_USER via is_valid_pg_identifier
  grep -q 'is_valid_pg_identifier()' "$SCRIPT"
  grep -q 'is_valid_pg_identifier "$PG_DBNAME"' "$SCRIPT"
  grep -q 'is_valid_pg_identifier "$PG_USER"' "$SCRIPT"
}

@test "script uses a direct existence probe for the validated identifier" {
  #R096-T01: source runs the direct SELECT 1 FROM pg_database existence probe
  grep -q "SELECT 1 FROM pg_database WHERE datname = '\${PG_DBNAME}'" "$SCRIPT"
}
