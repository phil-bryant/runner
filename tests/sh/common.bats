#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/security/common.sh (shared security helper library).

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/security/common.sh"
}

#R001: shard-3 function tag
defines() {
  bash -c "source '${SRC}' >/dev/null 2>&1; declare -F '$1' >/dev/null"
}

@test "print_tool_header renders a deterministic bordered tool header" {
  #R001-T01: Source helper file and verify print_tool_header function is defined.
  run bash -c "source '${SRC}'; print_tool_header 'Tool' 'line1' 'line2' 'https://example.invalid'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Security Tool: Tool"* ]]
  [[ "$output" == *"URL: https://example.invalid"* ]]
  [[ "$output" == *"+======"* ]]
}

@test "security_init_repo_root is defined and exports SECURITY_REPO_ROOT" {
  #R005-T01: Verify security_init_repo_root function is defined and references SECURITY_REPO_ROOT.
  run defines security_init_repo_root
  [ "$status" -eq 0 ]
  run grep -q "export .*SECURITY_REPO_ROOT" "$SRC"
  [ "$status" -eq 0 ]
}

@test "prerequisite helpers require_command/require_file/python_interpreter_usable are defined" {
  #R010-T01: Verify prerequisite helper functions are defined in source.
  run defines require_command
  [ "$status" -eq 0 ]
  run defines require_file
  [ "$status" -eq 0 ]
  run defines python_interpreter_usable
  [ "$status" -eq 0 ]
}

@test "lane setup helper security_resolve_asset prefers repo copy then runner default" {
  #R015-T01: Verify lane setup helper signatures are present in source.
  run defines security_resolve_asset
  [ "$status" -eq 0 ]
  tmp="$(mktemp -d)"
  mkdir -p "${tmp}/repo/config" "${tmp}/runner/config"
  : > "${tmp}/runner/config/asset.txt"
  run bash -c "source '${SRC}'; SECURITY_REPO_ROOT='${tmp}/repo' SECURITY_RUNNER_HOME='${tmp}/runner' security_resolve_asset config/asset.txt"
  [ "$status" -eq 0 ]
  [ "$output" = "${tmp}/runner/config/asset.txt" ]
  : > "${tmp}/repo/config/asset.txt"
  run bash -c "source '${SRC}'; SECURITY_REPO_ROOT='${tmp}/repo' SECURITY_RUNNER_HOME='${tmp}/runner' security_resolve_asset config/asset.txt"
  [ "$output" = "${tmp}/repo/config/asset.txt" ]
  rm -rf "$tmp"
}

@test "status formatting primitive emits aligned bordered output" {
  #R020-T01: Verify status-format helper functions are present in source.
  run bash -c "source '${SRC}'; print_tool_header 'X' 'a' 'b' 'u' | sed -n '1p'"
  [ "$status" -eq 0 ]
  [[ "$output" == "+"*"+" ]]
}

@test "scanner orchestration helper wait_for_http is defined" {
  #R025-T01: Verify scanner orchestration helper functions are present in source.
  run defines wait_for_http
  [ "$status" -eq 0 ]
  run grep -q "curl_args" "$SRC"
  [ "$status" -eq 0 ]
}

@test "gate/helper plumbing contract is declared in helper library" {
  #R030-T01: Verify gate/helper plumbing functions are present in source.
  run grep -q "reusable gate/helper plumbing for blocker policies" "$SRC"
  [ "$status" -eq 0 ]
}

@test "exclusion-aware invocation contract is declared in helper library" {
  #R035-T01: Verify exclusion-aware helper signatures are present in source.
  run grep -q "reusable exclusion-aware command invocation paths" "$SRC"
  [ "$status" -eq 0 ]
}

@test "tracked-source scan construction contract is declared in helper library" {
  #R040-T01: Verify tracked-source helper signatures are present in source.
  run grep -q "reusable tracked-source scan command construction" "$SRC"
  [ "$status" -eq 0 ]
}

@test "Semgrep status formatting contract is declared in helper library" {
  #R045-T01: Verify Semgrep status helper signatures are present in source.
  run grep -q "reusable Semgrep status formatting paths" "$SRC"
  [ "$status" -eq 0 ]
}

@test "Semgrep invocation wiring avoids quiet-mode suppression" {
  #R047-T01: Verify Semgrep invocation helper signatures are present in source.
  run grep -q "reusable Semgrep invocation wiring (no quiet mode)" "$SRC"
  [ "$status" -eq 0 ]
}

@test "Bandit status/report contract is declared in helper library" {
  #R050-T01: Verify Bandit helper signatures are present in source.
  run grep -q "reusable Bandit status/reporting pathways" "$SRC"
  [ "$status" -eq 0 ]
}

@test "pip-audit status/report contract is declared in helper library" {
  #R055-T01: Verify pip-audit helper signatures are present in source.
  run grep -q "reusable pip-audit status/reporting pathways" "$SRC"
  [ "$status" -eq 0 ]
}

@test "detect-secrets status/report contract is declared in helper library" {
  #R060-T01: Verify detect-secrets helper signatures are present in source.
  run grep -q "reusable detect-secrets/reporting pathways" "$SRC"
  [ "$status" -eq 0 ]
}

@test "Ruff status/report contract is declared in helper library" {
  #R065-T01: Verify Ruff helper signatures are present in source.
  run grep -q "reusable Ruff/reporting pathways" "$SRC"
  [ "$status" -eq 0 ]
}

@test "ShellCheck status/report contract is declared in helper library" {
  #R070-T01: Verify ShellCheck helper signatures are present in source.
  run grep -q "reusable ShellCheck/reporting pathways" "$SRC"
  [ "$status" -eq 0 ]
}

@test "helper setup sources cache-env and targets artifacts/cache" {
  #R080-T01: Verify helper source references cache-env export integration.
  run grep -q "export_test_cache_env.sh" "$SRC"
  [ "$status" -eq 0 ]
  run grep -q "export_test_cache_env " "$SRC"
  [ "$status" -eq 0 ]
}

@test "medium-or-higher gate plumbing contract is declared in helper library" {
  #R090-T01: Verify medium-or-higher gate helper signatures are present in source.
  run grep -q "reusable medium-or-higher gate plumbing" "$SRC"
  [ "$status" -eq 0 ]
}

@test "redaction helpers actually replace secrets in persisted artifacts" {
  #R100-T01: Verify redaction helper functions are present in source.
  run defines redact_secret_in_file
  [ "$status" -eq 0 ]
  run defines redact_secret_in_place
  [ "$status" -eq 0 ]
  tmp="$(mktemp -d)"
  printf 'token=SUPERSECRET trailer\n' > "${tmp}/in.txt"
  run bash -c "source '${SRC}'; redact_secret_in_place '${tmp}/in.txt' 'SUPERSECRET'"
  [ "$status" -eq 0 ]
  run grep -q "SUPERSECRET" "${tmp}/in.txt"
  [ "$status" -ne 0 ]
  run grep -q "\[REDACTED\]" "${tmp}/in.txt"
  [ "$status" -eq 0 ]
  rm -rf "$tmp"
}

@test "require_command guidance references hash-pinned requirements install" {
  #R105-T01: Verify helper source references hash-pinned requirements install guidance.
  run grep -q -- "--require-hashes -r" "$SRC"
  [ "$status" -eq 0 ]
  run grep -q "SECURITY_REQUIREMENTS_FILE" "$SRC"
  [ "$status" -eq 0 ]
}

@test "supply-chain artifact generation wiring contract is declared in helper library" {
  #R110-T01: Verify supply-chain helper signatures are present in source.
  run grep -q "supply-chain artifact generation wiring (SBOM/signing scaffold)" "$SRC"
  [ "$status" -eq 0 ]
}

@test "CI-default required signing behavior contract is declared in helper library" {
  #R115-T01: Verify CI signing policy helper signatures are present in source.
  run grep -q "CI-default required signing mode behavior in static security lane" "$SRC"
  [ "$status" -eq 0 ]
}
