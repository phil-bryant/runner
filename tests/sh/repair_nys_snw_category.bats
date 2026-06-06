#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/repair_nys_snw_category.sql.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SQL="${REPO_ROOT}/src/scripts/repair_nys_snw_category.sql"
}

@test "normalizes hierarchy fields before constraints" {
  #R001-T01: Verify the SQL script contains normalization updates for all targeted mutable hierarchy fields.
  run grep "REGEXP_REPLACE(level_1" "$SQL"
  [ "$status" -eq 0 ]
  run grep "REGEXP_REPLACE(level_4" "$SQL"
  [ "$status" -eq 0 ]
  run grep "REGEXP_REPLACE(categorization" "$SQL"
  [ "$status" -eq 0 ]
}

@test "contains guard block for empty hierarchy rows" {
  #R005-T01: Verify the guard block checks emptiness and raises a descriptive exception for non-compliant data.
  run grep "Cannot enforce nys_snw_category constraints" "$SQL"
  [ "$status" -eq 0 ]
  run grep "COALESCE(" "$SQL"
  [ "$status" -eq 0 ]
}

@test "recreates and validates both constraints" {
  #R010-T01: Verify DDL includes drop/add/validate sequence for both named constraints.
  run grep "DROP CONSTRAINT IF EXISTS nys_snw_category_non_empty_hierarchy_chk" "$SQL"
  [ "$status" -eq 0 ]
  run grep "ADD CONSTRAINT nys_snw_category_non_empty_hierarchy_chk" "$SQL"
  [ "$status" -eq 0 ]
  run grep "VALIDATE CONSTRAINT nys_snw_category_no_control_chars_chk" "$SQL"
  [ "$status" -eq 0 ]
}
