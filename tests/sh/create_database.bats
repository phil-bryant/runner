#!/usr/bin/env bats
# Self-contained shell unit tests for src/sql/sqlite/create_database.sql.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SQL="${REPO_ROOT}/src/sql/sqlite/create_database.sql"
}

@test "sqlite schema sets foreign key pragma" {
  #R001-T01: Parse create_database.sql and verify the foreign-key pragma is present.
  run grep -n "PRAGMA foreign_keys = ON;" "$SQL"
  [ "$status" -eq 0 ]
}

@test "sqlite schema defines ingest graph tables" {
  #R005-T01: Parse create_database.sql and verify core ingest table names are declared.
  run grep -En "CREATE TABLE IF NOT EXISTS (institution|account|identity)" "$SQL"
  [ "$status" -eq 0 ]
}

@test "sqlite schema defines classification and match tables" {
  #R010-T01: Parse create_database.sql and verify classification + match-review table declarations exist.
  run grep -En 'CREATE TABLE IF NOT EXISTS ("transaction"|nys_snw_category|transaction_nys_snw_category|transaction_email_match)' "$SQL"
  [ "$status" -eq 0 ]
}

@test "sqlite schema defines transaction info view" {
  #R015-T01: Parse create_database.sql and verify transaction_info_view DDL is present.
  run grep -n "CREATE VIEW IF NOT EXISTS transaction_info_view AS" "$SQL"
  [ "$status" -eq 0 ]
}
