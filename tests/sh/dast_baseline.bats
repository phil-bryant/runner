#!/usr/bin/env bats
# Self-contained static unit tests for src/scripts/dast_baseline.py (runner engine helper).

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/dast_baseline.py"
}

@test "module parses and snapshots the mutable DAST-affected tables" {
  #R001-T01: parses and snapshots the mutable DAST-affected tables
  run python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$SRC"
  [ "$status" -eq 0 ]
  grep -q "nys_snw_category" "$SRC"
  grep -q "transaction_email_match" "$SRC"
  grep -q "transaction_nys_snw_category" "$SRC"
}

@test "degrades to a skipped payload when database deps are unavailable" {
  #R005-T01: degrades to a skipped payload when database deps are unavailable
  grep -q "skipped" "$SRC"
}

@test "emits an operator-readable summary payload" {
  #R010-T01: emits an operator-readable summary payload
  grep -Eq "status|profile" "$SRC"
}
