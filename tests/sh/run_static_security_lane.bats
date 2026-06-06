#!/usr/bin/env bats
# Self-contained static-inspection unit tests for src/scripts/security/run_static_security_lane.sh.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/security/run_static_security_lane.sh"
}

@test "static lane is shell-parseable and defines a banner helper" {
  #R001-T01: Verify the lane defines a print_tool_header banner helper.
  run bash -n "$SRC"
  [ "$status" -eq 0 ]
  run grep -q '^print_tool_header() {' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane runs strict mode and resolves repo root" {
  #R005-T01: Verify strict-mode shell settings and security_init_repo_root invocation.
  run grep -q '^set -euo pipefail' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'security_init_repo_root "$SCRIPT_PATH"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane bootstraps an isolated security venv" {
  #R010-T01: Verify the lane creates an isolated security venv before scanning.
  run grep -q 'ensure_security_venv() {' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'python3 -m venv "$SECURITY_VENV_DIR"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane defaults to SAST-on, DAST-off" {
  #R015-T01: Verify the RUN_SAST/RUN_DAST default toggles.
  run grep -q 'RUN_SAST="${RUN_SAST:-true}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'RUN_DAST="${RUN_DAST:-false}"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane prints completion marker with report path" {
  #R020-T01: Verify the lane prints a completion marker with the report path.
  run grep -q 'Security checks completed. Reports: ${REPORT_DIR}' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane runs Ruff and persists its report" {
  #R025-T01: Verify the lane runs Ruff and persists its report.
  run grep -q 'run_ruff_sast() {' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'ruff check' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q '. > "$ruff_report"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane feeds findings into the consolidated SAST gate" {
  #R030-T01: Verify the lane invokes the consolidated SAST summary gate.
  run grep -q 'sast_summary_gate.py' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane excludes generated cache paths from secret scanning" {
  #R035-T01: Verify generated cache paths are excluded from secret-scan input.
  run grep -q '"$tracked_file" == .ruff_cache/\*' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q '"$tracked_file" == __pycache__/\*' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane runs gitleaks against a tracked-source snapshot" {
  #R040-T01: Verify gitleaks runs against a tracked-source snapshot directory.
  run grep -q 'gitleaks detect' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q -- '--source "$gitleaks_source_dir"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane prints detailed Semgrep status" {
  #R045-T01: Verify the lane prints a detailed Semgrep status line.
  run grep -q 'Semgrep detailed status:' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane invokes Semgrep without a --quiet suppression flag" {
  #R047-T01: Verify the Semgrep invocation omits a --quiet suppression flag.
  run python3 - "$SRC" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"semgrep scan(.*?)\n\n", text, flags=re.DOTALL)
if m is None:
    raise SystemExit("semgrep scan invocation not found")
if "--quiet" in m.group(1):
    raise SystemExit("semgrep scan must not pass --quiet")
PY
  [ "$status" -eq 0 ]
}

@test "static lane prints detailed Bandit status" {
  #R050-T01: Verify the lane prints a detailed Bandit status line.
  run grep -q 'Bandit detailed status:' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane prints detailed pip-audit status" {
  #R055-T01: Verify the lane prints a detailed pip-audit status line.
  run grep -q 'pip-audit detailed status:' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane prints detailed detect-secrets status" {
  #R060-T01: Verify the lane prints a detailed detect-secrets status line.
  run grep -q 'detect-secrets detailed status:' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane prints detailed Ruff status" {
  #R065-T01: Verify the lane prints a detailed Ruff status line.
  run grep -q 'Ruff detailed status:' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane prints detailed ShellCheck status" {
  #R070-T01: Verify the lane prints a detailed ShellCheck status line.
  run grep -q 'ShellCheck detailed status:' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane treats artifacts/cache and __pycache__ as generated" {
  #R080-T01: Verify cache paths under artifacts/cache and __pycache__ are treated as generated.
  run grep -q '"$tracked_file" == artifacts/cache/\*' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q '__pycache__' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane enforces a medium-or-higher blocking threshold" {
  #R090-T01: Verify the lane enforces a medium-or-higher blocking threshold.
  run grep -q '"${FAIL_ON_MEDIUM_OR_HIGHER}"     "medium"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane redacts token-bearing artifacts before persistence" {
  #R100-T01: Verify token-bearing artifacts are redacted before persistence.
  run grep -q 'redact_secret_in_file' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane installs the toolchain with hash-pinned requirements" {
  #R105-T01: Verify toolchain install uses --require-hashes.
  run grep -q -- '--require-hashes -r "$SECURITY_REQUIREMENTS_FILE"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane generates supply-chain SBOM/signing artifacts" {
  #R110-T01: Verify the lane invokes supply-chain artifact generation.
  run grep -q 'generate_supply_chain_artifacts' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane defaults CI signing mode to required" {
  #R115-T01: Verify the CI default sets the signing mode to required.
  run grep -q 'SUPPLY_CHAIN_SIGNING_MODE="required"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "static lane enforces a secure pip baseline before pip-audit" {
  #R120-T01: Verify the lane enforces a secure pip baseline before pip-audit.
  run grep -q 'enforce_pip_audit_secure_baseline() {' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'PIP_AUDIT_MIN_SECURE_PIP_VERSION' "$SRC"
  [ "$status" -eq 0 ]
}
