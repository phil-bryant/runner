#!/usr/bin/env bash

#R001: Shared security helpers support explicit lane startup messaging contracts.
#R005: Shared helpers resolve repo root and enforce deterministic execution context.
#R010: Shared helpers provide command/file/toolchain precondition utilities.
#R015: Shared helpers support default lane toggle handling in caller scripts.
#R020: Shared helpers provide common output/status formatting primitives.
#R025: Shared helpers provide reusable scanner orchestration support primitives.
#R030: Shared helpers provide reusable gate/helper plumbing for blocker policies.
#R035: Shared helpers support reusable exclusion-aware command invocation paths.
#R040: Shared helpers support reusable tracked-source scan command construction.
#R045: Shared helpers support reusable Semgrep status formatting paths.
#R047: Shared helpers support reusable Semgrep invocation wiring (no quiet mode).
#R050: Shared helpers support reusable Bandit status/reporting pathways.
#R055: Shared helpers support reusable pip-audit status/reporting pathways.
#R060: Shared helpers support reusable detect-secrets/reporting pathways.
#R065: Shared helpers support reusable Ruff/reporting pathways.
#R070: Shared helpers support reusable ShellCheck/reporting pathways.
#R080: Shared helpers export Python bytecode cache path under artifacts/cache.
#R090: Shared helpers support reusable medium-or-higher gate plumbing.
#R100: Shared helpers provide reusable secret redaction for persisted Schemathesis artifacts.
#R105: Shared helpers support hash-pinned requirements enforcement for security toolchains.
#R110: Shared helpers support supply-chain artifact generation wiring (SBOM/signing scaffold).
#R115: Shared helpers support CI-default required signing mode behavior in static security lane.
security_init_repo_root() {
  local script_path="${1:-${BASH_SOURCE[0]-$0}}"
  local script_dir
  script_dir="$(cd "$(dirname "$script_path")" && pwd)"
  #R005: Engine home (where security lane code lives). Used for runner-owned code/config defaults.
  local runner_home="$script_dir"
  if [[ "$script_dir" == */src/scripts/security ]]; then
    runner_home="$(cd "${script_dir}/../../.." && pwd)"
  elif [[ "$(basename "$script_dir")" == "tests" ]]; then
    runner_home="$(cd "${script_dir}/.." && pwd)"
  fi
  SECURITY_RUNNER_HOME="${RUNNER_HOME:-$runner_home}"
  #R005: Target repo to scan (an NN_/tNN_ pointer sets RUNBOOK_REPO_ROOT); default to engine home.
  local repo_root="${RUNBOOK_REPO_ROOT:-$SECURITY_RUNNER_HOME}"
  repo_root="$(cd "$repo_root" && pwd)"
  cd "$repo_root"
  # shellcheck disable=SC1091
  source "${SECURITY_RUNNER_HOME}/src/scripts/export_test_cache_env.sh"
  export_test_cache_env "$repo_root"
  SECURITY_REPO_ROOT="$repo_root"
  VENV_NAME="${VENV_NAME:-$(basename "$repo_root")-venv}"
  export SECURITY_RUNNER_HOME SECURITY_REPO_ROOT VENV_NAME
}

#R005: Layered asset resolution: prefer the target repo's copy, else the runner-owned default.
security_resolve_asset() {
  local rel="$1"
  if [[ -e "${SECURITY_REPO_ROOT}/${rel}" ]]; then
    printf '%s\n' "${SECURITY_REPO_ROOT}/${rel}"
  else
    printf '%s\n' "${SECURITY_RUNNER_HOME}/${rel}"
  fi
}

python_interpreter_usable() {
  local candidate="$1"
  [[ -x "$candidate" ]] || return 1
  "$candidate" -c "import site" >/dev/null 2>&1
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    local requirements_file="${SECURITY_REQUIREMENTS_FILE:-./requirements/security/requirements-security.txt}"
    echo "❌ Missing required command: $1"
    echo "Install prerequisites with ./01_install_prerequisites.sh, then run ./03_prepare_supply_chain_integrity.sh and pip install --require-hashes -r ${requirements_file}"
    exit 1
  fi
}

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "❌ Missing required file: $1"
    exit 1
  fi
}

# Environment/.env fallback for secret resolution mirrors 1psa semantics:
# - Read RB_ENV_FALLBACK_FILE, else ONEPSA_ENV_PATH, else ~/.env.
# - For password lookups, try ITEM.password then ITEM.
# - Normalize item names so lowercase/hyphenated keys still resolve.
rb_env_fallback_file_path() {
  local dotenv_path="${RB_ENV_FALLBACK_FILE:-${ONEPSA_ENV_PATH:-${HOME}/.env}}"
  printf '%s' "$dotenv_path"
}

rb_normalize_env_item_name() {
  local raw="$1"
  local normalized
  normalized="$(printf '%s' "$raw" | tr '[:lower:]' '[:upper:]' | sed -E 's/[^A-Z0-9._]/_/g; s/^_+//; s/_+$//')"
  printf '%s' "$normalized"
}

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

# Resolve a 1psa item, falling back to the matching environment variable when
# 1psa cannot resolve it for ANY reason (missing CLI, timeout, rate limit / auth
# error, not found). Only hard-fail when neither source yields a value.
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
    echo "❌ Missing required command: 1psa (and no environment fallback for item: ${item}; tried ${fallback_keys} in ${fallback_file})" >&2
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
      echo "⚠️  1psa timed out after ${timeout_seconds}s for item: ${item}; using environment fallback" >&2
    elif [[ "$onepsa_empty" == "true" ]]; then
      echo "⚠️  1psa returned an empty value for item: ${item}; using environment fallback" >&2
    else
      echo "⚠️  1psa could not resolve item: ${item}; using environment fallback" >&2
    fi
    printf '%s' "$env_value"
    return 0
  fi
  if [[ "$exit_code" -eq 124 ]]; then
    echo "❌ 1psa timed out after ${timeout_seconds}s while resolving item: ${item} (and no environment fallback found; tried ${fallback_keys} in ${fallback_file})" >&2
    return 1
  fi
  if [[ "$onepsa_empty" == "true" ]]; then
    echo "❌ 1psa returned an empty value for item: ${item} (and no environment fallback found; tried ${fallback_keys} in ${fallback_file})" >&2
    return 1
  fi
  echo "❌ failed to resolve 1psa item: ${item} (and no environment fallback found; tried ${fallback_keys} in ${fallback_file})" >&2
  return 1
}

print_tool_header() {
  local tool_name="$1"
  local explainer_line_1="$2"
  local explainer_line_2="$3"
  local tool_url="$4"
  local border="+==============================================================================+"
  printf '%s\n' "$border"
  printf '| %-76s |\n' "Security Tool: ${tool_name}"
  printf '| %-76s |\n' "${explainer_line_1}"
  printf '| %-76s |\n' "${explainer_line_2}"
  printf '| %-76s |\n' "URL: ${tool_url}"
  printf '%s\n' "$border"
}

wait_for_http() {
  local url="$1"
  local timeout_seconds="${2:-30}"
  local curl_args=(-fsS)
  local https_localhost_pattern='^https://(localhost|127\.0\.0\.1|\[::1\]|[A-Za-z0-9.-]+\.localhost)(:[0-9]+)?($|/)'
  if [[ "$url" =~ $https_localhost_pattern ]]; then
    curl_args+=(-k)
  fi
  local start_ts
  start_ts="$(date +%s)"
  while true; do
    if curl "${curl_args[@]}" "$url" >/dev/null 2>&1; then
      return 0
    fi
    if (( "$(date +%s)" - start_ts >= timeout_seconds )); then
      echo "❌ Timed out waiting for ${url}"
      return 1
    fi
    sleep 1
  done
}

redact_secret_in_file() {
  local input_path="$1"
  local output_path="$2"
  local secret="${3:-}"
  python3 - <<'PY' "$input_path" "$output_path" "$secret"
import pathlib
import sys

input_path = pathlib.Path(sys.argv[1])
output_path = pathlib.Path(sys.argv[2])
secret = sys.argv[3]

content = input_path.read_text(encoding="utf-8", errors="replace")
if secret:
    content = content.replace(secret, "[REDACTED]")
output_path.write_text(content, encoding="utf-8")
print(content, end="")
PY
}

redact_secret_in_place() {
  local path="$1"
  local secret="${2:-}"
  local tmp_path="${path}.redacted"
  redact_secret_in_file "$path" "$tmp_path" "$secret" >/dev/null
  mv "$tmp_path" "$path"
}
