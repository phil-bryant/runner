#!/usr/bin/env bats
# Companion tests for tests/t07_run_mutation_tests.sh requirements traceability.

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd -P)"
  SCRIPT="${REPO_ROOT}/tests/t07_run_mutation_tests.sh"
}

@test "documents CLI preflight/cache flags and help output" {
  #R001-T01: Verify usage text documents preflight/cache flags.
  grep -q '\-\-slow|\-\-preflight' "$SCRIPT"
  grep -q '\-\-fast|\-\-skip-preflight' "$SCRIPT"
  grep -q '\-\-cache-smart|\-\-cache-fresh|\-\-cache-force' "$SCRIPT"
  grep -q '\-h, \-\-help' "$SCRIPT"
}

@test "parses preflight and cache switches and rejects unknown args" {
  #R001-T02: Verify argument parser handles preflight/cache switches and rejects unknown args.
  grep -q -- '--slow|--preflight' "$SCRIPT"
  grep -q -- '--fast|--skip-preflight' "$SCRIPT"
  grep -q -- '--cache-smart' "$SCRIPT"
  grep -q -- '--cache-fresh' "$SCRIPT"
  grep -q -- '--cache-force' "$SCRIPT"
  grep -q 'unknown argument' "$SCRIPT"
}

@test "defaults to fast preflight mode and smart cache mode" {
  #R005-T01: Verify source defaults set skip-preflight + smart-cache mode.
  grep -q 'MUTATION_CACHE_MODE="smart"' "$SCRIPT"
  grep -q 'MUTATION_RUN_PREFLIGHT=false' "$SCRIPT"
}

@test "defines fingerprint helpers and metadata path for cache state" {
  #R010-T01: Verify source defines fingerprint build/read/write helpers and cache metadata path.
  grep -q 'CACHE_META_PATH="' "$SCRIPT"
  grep -q 'build_cache_fingerprint()' "$SCRIPT"
  grep -q 'read_cache_fingerprint()' "$SCRIPT"
  grep -q 'write_cache_metadata()' "$SCRIPT"
}

@test "smart-mode cache reuse requires existing cache plus fingerprint match" {
  #R010-T02: Verify smart-mode reuse gate requires both existing cache + matching saved fingerprint.
  grep -q '\[\[ -d "\${MUTANTS_DIR}" && -f "\${CACHE_META_PATH}" \]\]' "$SCRIPT"
  grep -q 'saved_cache_fingerprint' "$SCRIPT"
  grep -q '"\${saved_cache_fingerprint}" == "\${current_cache_fingerprint}"' "$SCRIPT"
}

@test "rotates stale cache through trash-safe cleanup before link recreation" {
  #R015-T01: Verify source routes stale cache cleanup through safe_move_to_trash before link recreation.
  grep -q 'safe_move_to_trash "\${ROOT_MUTANTS_LINK}"' "$SCRIPT"
  grep -q 'safe_move_to_trash "\${MUTANTS_DIR}"' "$SCRIPT"
  grep -q 'ln -s "\$MUTANTS_DIR" "\$ROOT_MUTANTS_LINK"' "$SCRIPT"
}

@test "prints explicit default-skip and preflight-enabled messages" {
  #R020-T01: Verify source prints explicit default skip message and explicit preflight-enabled message.
  grep -q 'Preflight: skipped by default' "$SCRIPT"
  grep -q 'Preflight: running pytest on tests/py (--preflight enabled).' "$SCRIPT"
}

@test "computes mutator-coverage gate from parsed threshold values" {
  #R022-T01: Verify source computes coverage gate status from parsed mutator coverage and threshold values.
  grep -q 'mutator_coverage = (verdict_pool / total \* 100.0) if total > 0 else 0.0' "$SCRIPT"
  grep -q 'coverage_failed = total == 0 or mutator_coverage < coverage_threshold' "$SCRIPT"
}

@test "defines optional exclusion input and forwards it to summary parser" {
  #R025-T01: Verify source defines MUTATION_EXCLUDE_FILES and forwards it into summary generation arguments.
  grep -q 'MUTATION_EXCLUDE_FILES=' "$SCRIPT"
  grep -q '"\$MUTATION_EXCLUDE_FILES"' "$SCRIPT"
}

@test "defines and writes machine-readable mutation summary output" {
  #R030-T01: Verify source defines MUTATION_SUMMARY and writes JSON summary data.
  grep -q 'MUTATION_SUMMARY=' "$SCRIPT"
  grep -q 'summary_path.write_text(json.dumps(summary, indent=2)' "$SCRIPT"
}

@test "contains explicit mutation completion and failure messaging" {
  #R035-T01: Verify source includes explicit mutation lane completion and failure messaging.
  grep -q 'Mutation testing completed. Report:' "$SCRIPT"
  grep -q '❌ FAIL: Mutation score' "$SCRIPT"
}

@test "wraps mutmut execution with timeout helper and timeout branch" {
  #R040-T01: Verify source defines the timeout wrapper and timeout handling branch.
  grep -q 'run_with_timeout()' "$SCRIPT"
  grep -q 'Mutation testing timed out after' "$SCRIPT"
  grep -q 'raise SystemExit(124)' "$SCRIPT"
}

@test "carries history and trend artifact paths through summary processing" {
  #R045-T01: Verify source carries history/trend paths and appends trend processing logic.
  grep -q 'MUTATION_HISTORY_PATH=' "$SCRIPT"
  grep -q 'MUTATION_TREND_PATH=' "$SCRIPT"
  grep -q 'history_path.open("a"' "$SCRIPT"
  grep -q 'trend_path.write_text' "$SCRIPT"
}

@test "includes CI strict-mode failure branch for runtime skip path" {
  #R050-T01: Verify source includes CI strict-mode failure branch for mutation-skip path.
  grep -q 'if \[\[ "\$IS_CI" == "true" \]\]' "$SCRIPT"
  grep -q 'CI strict mode' "$SCRIPT"
  grep -q 'exit 1' "$SCRIPT"
}

@test "includes survivor budget fields in mutation summary payload" {
  #R055-T01: Verify source includes survivor-budget and survivor-budget-failed summary fields.
  grep -q '"survivor_budget": survivor_budget' "$SCRIPT"
  grep -q '"survivor_budget_failed": survivor_budget_failed' "$SCRIPT"
}

@test "supports equivalents file scoring exclusions" {
  #R060-T01: Verify source references MUTATION_EQUIVALENTS_FILE and equivalent-mutant scoring exclusions.
  grep -q 'MUTATION_EQUIVALENTS_FILE' "$SCRIPT"
  grep -q 'Excluded {equivalent} proven-equivalent mutant' "$SCRIPT"
}

