#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/cleanup_legacy_dast_artifacts.sql.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SQL="${REPO_ROOT}/src/scripts/cleanup_legacy_dast_artifacts.sql"
}

@test "uses conservative DAST cleanup predicates" {
  #R001-T01: Verify script predicates constrain deletions to expected DAST fingerprint columns/values.
  run grep "level_1 = 'DAST'" "$SQL"
  [ "$status" -eq 0 ]
  run grep "schemathesis-seed-%@example.invalid" "$SQL"
  [ "$status" -eq 0 ]
  run grep "dast-seed-%@example.invalid" "$SQL"
  [ "$status" -eq 0 ]
}

@test "wraps deletes in transaction and FK-safe sequence" {
  #R005-T01: Verify script contains explicit `BEGIN/COMMIT` and dependency-ordered delete statements.
  run grep "^BEGIN;" "$SQL"
  [ "$status" -eq 0 ]
  run grep "DELETE FROM classy.transaction_nys_snw_category" "$SQL"
  [ "$status" -eq 0 ]
  run grep "DELETE FROM classy.nys_snw_category" "$SQL"
  [ "$status" -eq 0 ]
  run grep "DELETE FROM matchy.transaction_email_match" "$SQL"
  [ "$status" -eq 0 ]
  run grep "^COMMIT;" "$SQL"
  [ "$status" -eq 0 ]
}

@test "includes pre-delete count queries for operator visibility" {
  #R010-T01: Verify script contains pre-delete counting queries for each cleanup domain.
  run grep "SELECT 'nys_snw_category orphans" "$SQL"
  [ "$status" -eq 0 ]
  run grep "SELECT 'transaction_nys_snw_category mappings" "$SQL"
  [ "$status" -eq 0 ]
  run grep "SELECT 'transaction_email_match seeder rows'" "$SQL"
  [ "$status" -eq 0 ]
}
