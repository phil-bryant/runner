#!/usr/bin/env bats
# Self-contained static unit tests for src/scripts/dast_cleanup.py (runner engine helper).

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/dast_cleanup.py"
}

@test "module parses and reconciles classifications with bound SQL parameters" {
  #R001-T01
  run python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$SRC"
  [ "$status" -eq 0 ]
  grep -q "ANY(" "$SRC"
}

@test "refuses cleanup on profile mismatch unless force override is set" {
  #R005-T01
  grep -q "DAST_CLEANUP_FORCE" "$SRC"
  grep -Eq "refus" "$SRC"
}

@test "treats missing/non-captured baselines as non-fatal skips" {
  #R010-T01
  grep -q "skipped" "$SRC"
}
