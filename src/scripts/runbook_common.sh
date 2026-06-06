#!/usr/bin/env bash
# runbook_common.sh - shared contract for genericized runner golden scripts.
#
# Sourced by golden scripts in runner/ (and runner/tests/). Establishes the two
# locations that golden scripts must keep distinct:
#
#   RUNNER_HOME        - where the golden scripts + shared helpers physically live
#                        (always the runner/ tree). Use for CODE/helper lookups.
#   RUNBOOK_REPO_ROOT  - the repository the golden operates ON (venv, src/, config/,
#                        tests/). Defaults to RUNNER_HOME for backward-compatible
#                        direct runs; thin rNN_ pointers override it per repo.
#
# Thin pointers set RUNBOOK_REPO_ROOT and any profile knobs (sourced from
# runner/config/runbook/<repo>.env), then exec the golden.

#R001: Resolve RUNNER_HOME from this file's own location (runner/src/scripts).
RUNBOOK_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_HOME="$(cd "${RUNBOOK_COMMON_DIR}/../.." && pwd)"
export RUNNER_HOME

#R005: Default the target repo to RUNNER_HOME so direct golden runs are unchanged.
RUNBOOK_REPO_ROOT="${RUNBOOK_REPO_ROOT:-$RUNNER_HOME}"
RUNBOOK_REPO_ROOT="$(cd "$RUNBOOK_REPO_ROOT" && pwd)"
export RUNBOOK_REPO_ROOT

#R010: Derive the repo display name and conventional venv directory name.
RUNBOOK_REPO_NAME="${RUNBOOK_REPO_NAME:-$(basename "$RUNBOOK_REPO_ROOT")}"
VENV_NAME="${VENV_NAME:-${RUNBOOK_REPO_NAME}-venv}"
export RUNBOOK_REPO_NAME VENV_NAME

#R012: Shared traceability/test asset roots can live in runner while execution
# still targets RUNBOOK_REPO_ROOT scripts.
TRACEABILITY_REQUIREMENTS_ROOTS="${TRACEABILITY_REQUIREMENTS_ROOTS:-${RUNBOOK_REPO_ROOT}/requirements}"
TRACEABILITY_TEST_ROOTS="${TRACEABILITY_TEST_ROOTS:-${RUNBOOK_REPO_ROOT}/tests/sh}"
#R013: Shell lane discovery defaults to the same roots traceability uses for
# requirements-to-test mapping.
SHELL_BATS_ROOTS="${SHELL_BATS_ROOTS:-${TRACEABILITY_TEST_ROOTS}}"
export TRACEABILITY_REQUIREMENTS_ROOTS TRACEABILITY_TEST_ROOTS SHELL_BATS_ROOTS

#R015: Operate from the target repository root by default.
runbook_cd_repo() {
  cd "$RUNBOOK_REPO_ROOT"
}

#R020: Status helpers keep output uniform across goldens.
rb_info() { echo "$*"; }
rb_ok() { echo "✅ $*"; }
rb_warn() { echo "⚠️  $*"; }
rb_err() { echo "❌ $*" >&2; }

#R025: Ensure a Homebrew formula is present; install it when missing.
# Usage: rb_ensure_brew_formula <formula> [command-name]
rb_ensure_brew_formula() {
  local formula="$1"
  local command_name="${2:-$1}"
  if command -v "$command_name" >/dev/null 2>&1; then
    rb_ok "[$formula] Available on PATH"
    return 0
  fi
  rb_warn "[$formula] Missing on PATH"
  rb_info "[$formula] Installing via Homebrew..."
  brew install "$formula"
  if command -v "$command_name" >/dev/null 2>&1; then
    rb_ok "[$formula] Installed and available"
  else
    rb_err "[$formula] Install completed but command still unavailable"
    return 1
  fi
}

#R030: Iterate a newline/space separated BREW_FORMULAS spec. Each entry is
# "formula" or "formula:command" (command used for the PATH probe).
rb_install_brew_formulas() {
  local spec="${1:-${BREW_FORMULAS:-}}"
  local entry formula command_name
  [[ -n "$spec" ]] || return 0
  while IFS= read -r entry; do
    entry="$(echo "$entry" | xargs)"
    [[ -n "$entry" ]] || continue
    formula="${entry%%:*}"
    if [[ "$entry" == *:* ]]; then
      command_name="${entry##*:}"
    else
      command_name="$formula"
    fi
    rb_ensure_brew_formula "$formula" "$command_name"
  done <<< "${spec//[[:space:]]/$'\n'}"
}

#R035: Resolve a usable python interpreter for the target repo's venv.
rb_repo_python() {
  local venv_python="${RUNBOOK_REPO_ROOT}/${VENV_NAME}/bin/python3"
  if [[ -x "$venv_python" ]] && "$venv_python" -c "import site" >/dev/null 2>&1; then
    printf '%s\n' "$venv_python"
    return 0
  fi
  command -v python3
}

#R042: Environment-variable fallback for secret resolution. The db-profiles
# "1psa_or_env_item" value (and the *_PSA_ITEM knobs) double as the env var name
# that supplies the secret when 1Password is unreachable (rate limit, auth error,
# offline, etc). Try the item name verbatim, then an uppercased variant so that
# lowercase defaults like "localhost_postgres_teller" also resolve from
# LOCALHOST_POSTGRES_TELLER. Emits only the value on stdout.
rb_lookup_env_fallback() {
  local name="$1"
  local upper
  if [[ -n "${!name:-}" ]]; then
    printf '%s' "${!name}"
    return 0
  fi
  upper="$(printf '%s' "$name" | tr '[:lower:]' '[:upper:]')"
  if [[ "$upper" != "$name" && -n "${!upper:-}" ]]; then
    printf '%s' "${!upper}"
    return 0
  fi
  return 1
}

#R040: Resolve 1psa items with a bounded timeout to prevent stuck prompts.
#R041: When 1psa cannot resolve the item for ANY reason (missing CLI, timeout,
# rate limit / auth error, not found), fall back to the matching environment
# variable. Only hard-fail when neither source yields a value.
rb_read_1psa_item() {
  local item="$1"
  local timeout_seconds="${RB_ONEPSA_TIMEOUT_SECONDS:-12}"
  local output=""
  local exit_code=0
  local env_value=""
  if ! command -v 1psa >/dev/null 2>&1; then
    if env_value="$(rb_lookup_env_fallback "$item")"; then
      printf '%s' "$env_value"
      return 0
    fi
    rb_err "1psa is required to resolve item: ${item} (and no environment fallback found)"
    return 1
  fi
  set +e
  output="$(python3 - <<'PY' "$item" "$timeout_seconds"
import subprocess
import sys

item = sys.argv[1]
timeout_seconds = int(sys.argv[2])
try:
    result = subprocess.run(["1psa", "-p", item], check=False, capture_output=True, text=True, timeout=timeout_seconds)
except subprocess.TimeoutExpired:
    print(f"timeout:{item}:{timeout_seconds}", file=sys.stderr)
    raise SystemExit(124)
if result.returncode != 0:
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    raise SystemExit(result.returncode)
print(result.stdout.strip())
PY
)"
  exit_code=$?
  set -e
  if [[ "$exit_code" -eq 0 ]]; then
    printf '%s' "$output"
    return 0
  fi
  # 1psa failed (timeout, rate limit, auth error, not found, ...). Try the
  # environment-variable fallback before giving up.
  if env_value="$(rb_lookup_env_fallback "$item")"; then
    if [[ "$exit_code" -eq 124 ]]; then
      rb_warn "1psa timed out after ${timeout_seconds}s for item: ${item}; using environment fallback" >&2
    else
      rb_warn "1psa could not resolve item: ${item}; using environment fallback" >&2
    fi
    printf '%s' "$env_value"
    return 0
  fi
  if [[ "$exit_code" -eq 124 ]]; then
    rb_err "1psa timed out after ${timeout_seconds}s while resolving item: ${item} (and no environment fallback found)"
    return 1
  fi
  rb_err "failed to resolve 1psa item: ${item} (and no environment fallback found)"
  return 1
}
