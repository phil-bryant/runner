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
#R001: function tag for rb_ok
rb_ok() { echo "✅ $*"; }
#R001: function tag for rb_warn
rb_warn() { echo "⚠️  $*"; }
#R001: function tag for rb_err
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
  local spec
  local entry formula command_name
  # Treat an explicit empty argument as a deliberate no-op.
  if [[ "$#" -gt 0 ]]; then
    spec="$1"
  else
    spec="${BREW_FORMULAS:-}"
  fi
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

#R042: Environment/.env fallback for secret resolution mirrors 1psa semantics:
# - Read RB_ENV_FALLBACK_FILE, else ONEPSA_ENV_PATH, else ~/.env.
# - For password lookups, try ITEM.password then ITEM.
# - Normalize item names so lowercase/hyphenated keys still resolve.
rb_env_fallback_file_path() {
  local dotenv_path="${RB_ENV_FALLBACK_FILE:-${ONEPSA_ENV_PATH:-${HOME}/.env}}"
  printf '%s' "$dotenv_path"
}

#R001: function tag for rb_normalize_env_item_name
rb_normalize_env_item_name() {
  local raw="$1"
  local normalized
  normalized="$(printf '%s' "$raw" | tr '[:lower:]' '[:upper:]' | sed -E 's/[^A-Z0-9._]/_/g; s/^_+//; s/_+$//')"
  printf '%s' "$normalized"
}

#R001: function tag for rb_onepsa_env_lookup_keys
rb_onepsa_env_lookup_keys() {
  local item="$1"
  local field="${2:-password}"
  local normalized_item normalized_field candidate
  local seen=$'\n'
  local -a candidates=()

  [[ -n "$item" ]] || return 1
  normalized_item="$(rb_normalize_env_item_name "$item")"
  normalized_field="$(printf '%s' "$field" | tr '[:upper:]' '[:lower:]')"
  normalized_field="${normalized_field//[[:space:]]/}"
  [[ -n "$normalized_field" ]] || normalized_field="password"

  if [[ "$normalized_field" == "password" ]]; then
    candidates+=("${item}.password" "${normalized_item}.password" "$item" "$normalized_item")
  else
    candidates+=("${item}.${normalized_field}" "${normalized_item}.${normalized_field}")
  fi

  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" ]] || continue
    case "$seen" in
      *$'\n'"$candidate"$'\n'*) continue ;;
    esac
    seen+="${candidate}"$'\n'
    printf '%s\n' "$candidate"
  done
}

#R001: function tag for rb_onepsa_env_lookup_keys_csv
rb_onepsa_env_lookup_keys_csv() {
  local item="$1"
  local field="${2:-password}"
  local key joined=""
  while IFS= read -r key; do
    [[ -n "$key" ]] || continue
    if [[ -z "$joined" ]]; then
      joined="$key"
    else
      joined="${joined}, ${key}"
    fi
  done < <(rb_onepsa_env_lookup_keys "$item" "$field")
  printf '%s' "$joined"
}

#R001: function tag for rb_lookup_dotenv_key
rb_lookup_dotenv_key() {
  local key="$1"
  local dotenv_path
  local value=""
  dotenv_path="$(rb_env_fallback_file_path)"
  [[ -r "$dotenv_path" ]] || return 1
  set +e
  value="$(python3 - <<'PY' "$dotenv_path" "$key"
from pathlib import Path
import sys

dotenv_path = Path(sys.argv[1])
target_key = sys.argv[2]

try:
    text = dotenv_path.read_text(encoding="utf-8", errors="replace")
except OSError:
    raise SystemExit(1)

for raw_line in text.splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("export "):
        line = line[7:].lstrip()
    if "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key.strip() != target_key:
        continue
    value = value.strip()
    if len(value) >= 2 and (
        (value[0] == "'" and value[-1] == "'")
        or (value[0] == '"' and value[-1] == '"')
    ):
        value = value[1:-1]
    print(value)
    raise SystemExit(0)

raise SystemExit(1)
PY
)"
  local status=$?
  set -e
  if [[ "$status" -eq 0 ]]; then
    printf '%s' "$value"
    return 0
  fi
  return 1
}

#R001: function tag for rb_lookup_env_fallback
rb_lookup_env_fallback() {
  local item="$1"
  local field="${2:-password}"
  local key value=""
  while IFS= read -r key; do
    [[ -n "$key" ]] || continue
    if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] && [[ -n "${!key:-}" ]]; then
      printf '%s' "${!key}"
      return 0
    fi
    if value="$(rb_lookup_dotenv_key "$key")"; then
      printf '%s' "$value"
      return 0
    fi
  done < <(rb_onepsa_env_lookup_keys "$item" "$field")
  return 1
}

#R040: Resolve 1psa items with a bounded timeout to prevent stuck prompts.
#R041: When 1psa cannot resolve the item for ANY reason (missing CLI, timeout,
# rate limit / auth error, not found), fall back to the matching environment
# variable. Only hard-fail when neither source yields a value.
rb_read_1psa_item() {
  local item="$1"
  local field="${2:-password}"
  local timeout_seconds="${RB_ONEPSA_TIMEOUT_SECONDS:-12}"
  local output=""
  local exit_code=0
  local env_value=""
  local onepsa_empty=false
  local fallback_keys fallback_file
  fallback_keys="$(rb_onepsa_env_lookup_keys_csv "$item" "$field")"
  fallback_file="$(rb_env_fallback_file_path)"
  if ! command -v 1psa >/dev/null 2>&1; then
    if env_value="$(rb_lookup_env_fallback "$item" "$field")"; then
      printf '%s' "$env_value"
      return 0
    fi
    rb_err "1psa is required to resolve item: ${item} (and no environment fallback found; tried ${fallback_keys} in ${fallback_file})"
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
  if [[ "$exit_code" -eq 0 && -n "$output" ]]; then
    printf '%s' "$output"
    return 0
  fi
  if [[ "$exit_code" -eq 0 && -z "$output" ]]; then
    onepsa_empty=true
    exit_code=125
  fi
  # 1psa failed (timeout, rate limit, auth error, not found, ...). Try the
  # environment-variable fallback before giving up.
  if env_value="$(rb_lookup_env_fallback "$item" "$field")"; then
    if [[ "$exit_code" -eq 124 ]]; then
      rb_warn "1psa timed out after ${timeout_seconds}s for item: ${item}; using environment fallback" >&2
    elif [[ "$onepsa_empty" == "true" ]]; then
      rb_warn "1psa returned an empty value for item: ${item}; using environment fallback" >&2
    else
      rb_warn "1psa could not resolve item: ${item}; using environment fallback" >&2
    fi
    printf '%s' "$env_value"
    return 0
  fi
  if [[ "$exit_code" -eq 124 ]]; then
    rb_err "1psa timed out after ${timeout_seconds}s while resolving item: ${item} (and no environment fallback found; tried ${fallback_keys} in ${fallback_file})"
    return 1
  fi
  if [[ "$onepsa_empty" == "true" ]]; then
    rb_err "1psa returned an empty value for item: ${item} (and no environment fallback found; tried ${fallback_keys} in ${fallback_file})"
    return 1
  fi
  rb_err "failed to resolve 1psa item: ${item} (and no environment fallback found; tried ${fallback_keys} in ${fallback_file})"
  return 1
}
