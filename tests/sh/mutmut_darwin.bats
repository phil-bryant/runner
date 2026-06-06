#!/usr/bin/env bats
# Self-contained static unit tests for src/scripts/mutmut_darwin.py + mutmut_darwin_stub.py (runner engine helpers).

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/mutmut_darwin.py"
  STUB="${REPO_ROOT}/src/scripts/mutmut_darwin_stub.py"
}

@test "driver parses and splits prepare/execute phases" {
  #R001-T01: driver parses and splits prepare/execute phases
  run python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$SRC"
  [ "$status" -eq 0 ]
  grep -q "prepare" "$SRC"
  grep -q "execute" "$SRC"
}

@test "driver configures a deterministic subprocess pytest environment" {
  #R005-T01: driver configures a deterministic subprocess pytest environment
  grep -q "root / \"mutants\" / \"src\"" "$SRC"
  grep -q "PYTHONPATH" "$SRC"
  grep -q "MUTATION_WORKERS" "$SRC"
  grep -q "MUTATION_FULL_SUITE_ESCALATION" "$SRC"
  grep -q "MUTATION_IMPORT_PREPEND" "$SRC"
  grep -q "pytest.main(sys.argv\\[1:\\])" "$SRC"
  grep -q "cwd=root" "$SRC"
}

@test "stub module installs a callable setproctitle symbol" {
  #R010-T01: stub module installs a callable setproctitle symbol
  run python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$STUB"
  [ "$status" -eq 0 ]
  grep -q "setproctitle" "$STUB"
}
