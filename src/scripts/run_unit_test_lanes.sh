#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/runbook_common.sh"
REPO_ROOT="$RUNBOOK_REPO_ROOT"
#R001: Run tests from the target repository root regardless of caller working directory.
cd "$REPO_ROOT"

#R038: Keep Hypothesis and other Python tool caches out of the repository root.
# shellcheck disable=SC1091
source "${RUNNER_HOME}/src/scripts/export_test_cache_env.sh"
export_test_cache_env "$REPO_ROOT"

# Optional runner controls for local development.
RUN_SHELL_TESTS="${RUN_SHELL_TESTS:-true}"
RUN_PYTHON_TESTS="${RUN_PYTHON_TESTS:-true}"
RUN_SQL_TESTS="${RUN_SQL_TESTS:-true}"
RUN_SWIFT_TESTS="${RUN_SWIFT_TESTS:-true}"
RUN_MACOS_UI_REGRESSION_TESTS="${RUN_MACOS_UI_REGRESSION_TESTS:-false}"
MACOS_UI_SWIFTPM_LOCK="${MACOS_UI_SWIFTPM_LOCK:-./src/macos-ui/.swiftpm-run.lock}"
MACOS_UI_SWIFT_LOCK_TIMEOUT_SECONDS="${MACOS_UI_SWIFT_LOCK_TIMEOUT_SECONDS:-600}"
#R030: Keep crash-reporter verification isolated to dedicated script 14.
BATS_FILTER="${BATS_FILTER:-}"
RUN_SHELL_COVERAGE="${RUN_SHELL_COVERAGE:-false}"
SHELL_COVERAGE_TOOL="${SHELL_COVERAGE_TOOL:-kcov}"
SHELL_COVERAGE_KCOV_CONFIG="${SHELL_COVERAGE_KCOV_CONFIG:-bash-use-basic-parser=1}"
SHELL_COVERAGE_STRICT="${SHELL_COVERAGE_STRICT:-false}"
SHELL_COVERAGE_TIMEOUT_SECONDS="${SHELL_COVERAGE_TIMEOUT_SECONDS:-120}"
SHELL_COVERAGE_INCLUDE_PATHS="${SHELL_COVERAGE_INCLUDE_PATHS:-}"
SQL_TESTS_DIR="${SQL_TESTS_DIR:-}"
RUN_PYTEST_COVERAGE="${RUN_PYTEST_COVERAGE:-true}"
COVERAGE_REPORT_DIR="${COVERAGE_REPORT_DIR:-./artifacts/coverage}"
COVERAGE_SOURCE_DIRS="${COVERAGE_SOURCE_DIRS:-${PYTHON_SRC_DIRS:-}}"
COVERAGE_FAIL_UNDER="${COVERAGE_FAIL_UNDER:-}"
SHELL_COVERAGE_REPORT_DIR="${SHELL_COVERAGE_REPORT_DIR:-${COVERAGE_REPORT_DIR}/shell}"

if [[ "$RUN_SQL_TESTS" == "true" && -z "$SQL_TESTS_DIR" ]]; then
  if [[ ! -d "./tests/sql" && ! -d "./tests/sql/sqlite" ]]; then
    echo "ℹ️  Skipping SQL unit tests: ./tests/sql and ./tests/sql/sqlite not found."
    RUN_SQL_TESTS="false"
  fi
fi

#R025: Resolve DB connection settings from the active profile (1psa+~/.env via the helper).
DB_PROFILE_HELPER="${RUNNER_HOME}/src/scripts/db_profile_export.sh"
PG_HOST=""
PG_PORT=""
PG_DBNAME=""
PG_USER=""
PG_SSLMODE="disable"
PG_ONEPSA_ITEM=""
#R025: Only resolve a DB profile when the SQL lane will actually run (keeps non-DB repos working).
if [[ "$RUN_SQL_TESTS" == "true" ]]; then
if [[ ! -x "$DB_PROFILE_HELPER" ]]; then
  echo "❌ DB profile helper is missing or not executable: ${DB_PROFILE_HELPER}"
  exit 1
fi
#R001: function tag for load_profile_exports_from_file
load_profile_exports_from_file() {
  local exports_file="$1"
  local invalid_lines=""
  invalid_lines="$(awk '
    !/^(export )?[A-Za-z_][A-Za-z0-9_]*=.*/ { print; next }
    {
      key=$0
      sub(/^export[[:space:]]+/, "", key)
      sub(/=.*/, "", key)
      if (key !~ /^(DB_DIALECT|PROFILE_NAME|PROFILE_TARGET|PG_HOST|PG_PORT|PG_DBNAME|PG_USER|PG_SSLMODE|PG_SEARCH_PATH|PG_RUNTIME_ROLE|PG_ONEPSA_ITEM|SQLITE_PATH|SQLCIPHER_KEY)$/) {
        print
      }
    }
  ' "$exports_file")"
  if [[ -n "$invalid_lines" ]]; then
    echo "❌ Refusing to load unexpected profile export lines:"
    printf '%s\n' "$invalid_lines"
    return 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$exports_file"
  set +a
}

profile_exports_file="$(mktemp "${TMPDIR:-/tmp}/runbook-profile-exports.XXXXXX")"
if ! "$DB_PROFILE_HELPER" >"$profile_exports_file"; then
  #R035: Refuse SQL lane preflight when DB profile setup is missing.
  rm -f "$profile_exports_file"
  exit 1
fi
if ! load_profile_exports_from_file "$profile_exports_file"; then
  rm -f "$profile_exports_file"
  exit 1
fi
rm -f "$profile_exports_file"
fi

SQL_TEST_DATABASE="${SQL_TEST_DATABASE:-${TELLER_DB_NAME:-${PG_DBNAME:-}}}"
PG_PROVE_BIN="${PG_PROVE_BIN:-}"
DB_HOST="${TELLER_DB_HOST:-${PG_HOST:-localhost}}"
DB_PORT="${TELLER_DB_PORT:-${PG_PORT:-5432}}"
DB_USER="${TELLER_DB_USER:-${PG_USER:-teller}}"
DB_PASSWORD="${TELLER_DB_PASSWORD:-${DB_PASSWORD:-}}"
DB_DIALECT="${DB_DIALECT:-postgresql}"
SQLITE_PATH="${TELLER_DB_SQLITE_PATH:-${SQLITE_PATH:-}}"
SQLCIPHER_KEY="${TELLER_DB_SQLCIPHER_KEY:-${SQLCIPHER_KEY:-}}"
if [[ -z "$SQL_TESTS_DIR" ]]; then
  if [[ "$DB_DIALECT" == "sqlite" || "${PROFILE_TARGET:-local}" == "sqlite" ]]; then
    SQL_TESTS_DIR="./tests/sql/sqlite"
  else
    SQL_TESTS_DIR="./tests/sql"
  fi
fi

#R001: function tag for python_interpreter_usable
python_interpreter_usable() {
  local candidate="$1"
  [[ -x "$candidate" ]] || return 1
  "$candidate" -c "import site" >/dev/null 2>&1
}

#R001: function tag for resolve_bats_jobs
resolve_bats_jobs() {
  local default_jobs cap
  default_jobs="$(sysctl -n hw.ncpu 2>/dev/null || echo 8)"
  if [[ "${PARALLEL_LANES:-1}" =~ ^[0-9]+$ ]] && [[ "${PARALLEL_LANES:-1}" -gt 1 ]]; then
    default_jobs=$(( default_jobs / PARALLEL_LANES ))
    if [[ "$default_jobs" -lt 1 ]]; then
      default_jobs=1
    fi
  fi
  BATS_JOBS_RESOLVED="${BATS_JOBS:-$default_jobs}"
  cap="${BATS_JOBS_CAP:-8}"
  if [[ "$cap" =~ ^[0-9]+$ ]] && [[ "$cap" -gt 0 ]] && [[ "$BATS_JOBS_RESOLVED" -gt "$cap" ]]; then
    BATS_JOBS_RESOLVED="$cap"
  fi
}

#R001: function tag for run_single_bats_file
run_single_bats_file() {
  local bats_file="$1"
  local -a bats_env_unsets=(
    -u TELLER_DB_PASSWORD
    -u DB_PASSWORD
    -u DB_DIALECT
    -u PROFILE_NAME
    -u PROFILE_TARGET
    -u PG_HOST
    -u PG_PORT
    -u PG_DBNAME
    -u PG_USER
    -u PG_SSLMODE
    -u PG_SEARCH_PATH
    -u PG_RUNTIME_ROLE
    -u PG_ONEPSA_ITEM
    -u SQLITE_PATH
    -u SQLCIPHER_KEY
    -u TELLER_DB_HOST
    -u TELLER_DB_PORT
    -u TELLER_DB_NAME
    -u TELLER_DB_USER
    -u TELLER_DB_SQLITE_PATH
    -u TELLER_DB_SQLCIPHER_KEY
  )
  if [[ -n "$BATS_FILTER" ]]; then
    env "${bats_env_unsets[@]}" bats --filter "$BATS_FILTER" "$bats_file"
  else
    env "${bats_env_unsets[@]}" bats "$bats_file"
  fi
}

#R001: function tag for shell_coverage_label_for_bats_file
shell_coverage_label_for_bats_file() {
  local bats_file="$1"
  local relative_path
  if [[ "$bats_file" == "$RUNBOOK_REPO_ROOT/"* ]]; then
    relative_path="${bats_file#"${RUNBOOK_REPO_ROOT}"/}"
  elif [[ "$bats_file" == "$RUNNER_HOME/"* ]]; then
    relative_path="runner/${bats_file#"${RUNNER_HOME}"/}"
  else
    relative_path="$(basename "$bats_file")"
  fi
  printf '%s' "$relative_path" | sed -E 's#[^A-Za-z0-9._-]+#_#g; s#_+#_#g; s#^_##; s#_$##'
}

#R001: function tag for run_single_bats_file_with_coverage
run_single_bats_file_with_coverage() {
  local bats_file="$1"
  local coverage_prefix="$2"
  local coverage_label coverage_output_dir coverage_stderr_log coverage_output_log
  local -a coverage_tool_args=()
  local -a coverage_cmd=()
  local -a coverage_exec_cmd=()
  local -a bats_env_unsets=(
    -u TELLER_DB_PASSWORD
    -u DB_PASSWORD
    -u DB_DIALECT
    -u PROFILE_NAME
    -u PROFILE_TARGET
    -u PG_HOST
    -u PG_PORT
    -u PG_DBNAME
    -u PG_USER
    -u PG_SSLMODE
    -u PG_SEARCH_PATH
    -u PG_RUNTIME_ROLE
    -u PG_ONEPSA_ITEM
    -u SQLITE_PATH
    -u SQLCIPHER_KEY
    -u TELLER_DB_HOST
    -u TELLER_DB_PORT
    -u TELLER_DB_NAME
    -u TELLER_DB_USER
    -u TELLER_DB_SQLITE_PATH
    -u TELLER_DB_SQLCIPHER_KEY
  )
  coverage_label="$(shell_coverage_label_for_bats_file "$bats_file")"
  coverage_output_dir="${SHELL_COVERAGE_REPORT_DIR}/${coverage_prefix}_${coverage_label}"
  if [[ "$(basename "$SHELL_COVERAGE_TOOL")" == "kcov" && -n "${SHELL_COVERAGE_KCOV_CONFIG:-}" ]]; then
    coverage_tool_args+=( --configure "$SHELL_COVERAGE_KCOV_CONFIG" )
  fi
  coverage_cmd=(
    "$SHELL_COVERAGE_TOOL"
    "${coverage_tool_args[@]}"
    --clean
  )
  if [[ -n "${SHELL_COVERAGE_INCLUDE_PATHS_RESOLVED:-}" ]]; then
    coverage_cmd+=( --include-path "$SHELL_COVERAGE_INCLUDE_PATHS_RESOLVED" )
  fi
  coverage_cmd+=(
    "$coverage_output_dir"
    bats
  )
  if [[ -n "$BATS_FILTER" ]]; then
    coverage_cmd+=( --filter "$BATS_FILTER" )
  fi
  coverage_cmd+=( "$bats_file" )
  coverage_exec_cmd=( env "${bats_env_unsets[@]}" "${coverage_cmd[@]}" )
  coverage_stderr_log="${coverage_output_dir}.kcov.stderr.log"
  coverage_output_log="${coverage_output_dir}.kcov.output.log"
  SHELL_COVERAGE_LAST_STDERR_LOG="$coverage_stderr_log"
  SHELL_COVERAGE_LAST_OUTPUT_LOG="$coverage_output_log"
  export SHELL_COVERAGE_LAST_STDERR_LOG
  export SHELL_COVERAGE_LAST_OUTPUT_LOG
  if [[ "$SHELL_COVERAGE_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] && [[ "$SHELL_COVERAGE_TIMEOUT_SECONDS" -gt 0 ]]; then
    if ! python3 - "$coverage_output_log" "$SHELL_COVERAGE_TIMEOUT_SECONDS" "${coverage_exec_cmd[@]}" <<'PY'
import subprocess
import sys

output_path = sys.argv[1]
timeout_seconds = int(sys.argv[2])
command = sys.argv[3:]

with open(output_path, "wb") as stream:
    try:
        completed = subprocess.run(
            command,
            stdout=stream,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        stream.write(
            f"\n⚠️ Shell coverage command timed out after {timeout_seconds}s.\n".encode("utf-8")
        )
        sys.exit(124)

sys.exit(completed.returncode)
PY
    then
      cp "$coverage_output_log" "$coverage_stderr_log" 2>/dev/null || true
      return 1
    fi
  else
    if ! "${coverage_exec_cmd[@]}" >"$coverage_output_log" 2>&1; then
      cp "$coverage_output_log" "$coverage_stderr_log" 2>/dev/null || true
      return 1
    fi
  fi
}

#R001: function tag for resolve_shell_coverage_include_paths
resolve_shell_coverage_include_paths() {
  local spec normalized root bats_bin bats_root
  local seen=$'\n'
  local -a roots=()
  spec="${SHELL_COVERAGE_INCLUDE_PATHS:-}"
  if [[ -z "${spec// }" ]]; then
    spec="${RUNBOOK_REPO_ROOT},${RUNNER_HOME}"
    if bats_bin="$(command -v bats 2>/dev/null)"; then
      bats_root="$(python3 - <<'PY' "$bats_bin"
import os
import sys

path = os.path.realpath(sys.argv[1])
print(os.path.realpath(os.path.join(os.path.dirname(path), "..")))
PY
)"
      if [[ -n "$bats_root" ]]; then
        spec="${spec},${bats_root}"
      fi
    fi
  fi
  normalized="${spec//:/ }"
  normalized="${normalized//,/ }"
  for root in $normalized; do
    [[ -n "$root" ]] || continue
    if [[ "$root" != /* ]]; then
      root="${REPO_ROOT}/${root#./}"
    fi
    if [[ ! -d "$root" ]]; then
      continue
    fi
    root="$(cd "$root" && pwd -P)"
    case "$seen" in
      *$'\n'"$root"$'\n'*) continue ;;
    esac
    seen+="${root}"$'\n'
    roots+=("$root")
  done
  if [[ "${#roots[@]}" -eq 0 ]]; then
    SHELL_COVERAGE_INCLUDE_PATHS_RESOLVED=""
  else
    SHELL_COVERAGE_INCLUDE_PATHS_RESOLVED="$(IFS=,; echo "${roots[*]}")"
  fi
  export SHELL_COVERAGE_INCLUDE_PATHS_RESOLVED
}

#R001: function tag for collect_bats_files
collect_bats_files() {
  local roots_spec normalized root candidate
  local seen=$'\n'
  bats_files=()
  roots_spec="${SHELL_BATS_ROOTS:-./tests/sh}"
  normalized="${roots_spec//:/ }"
  normalized="${normalized//,/ }"
  for root in $normalized; do
    [[ -n "$root" ]] || continue
    if [[ "$root" != /* ]]; then
      root="${REPO_ROOT}/${root#./}"
    fi
    [[ -d "$root" ]] || continue
    shopt -s nullglob
    for candidate in "$root"/*.bats; do
      case "$seen" in
        *$'\n'"$candidate"$'\n'*) continue ;;
      esac
      seen+="${candidate}"$'\n'
      bats_files+=("$candidate")
    done
    shopt -u nullglob
  done
}

#R001: function tag for swiftpm_state_looks_stale
swiftpm_state_looks_stale() {
  local output_text="$1"
  [[ "$output_text" == *"cannot be accessed"* && "$output_text" == *".build/"* ]] && return 0
  [[ "$output_text" == *"was compiled with module cache path"* ]] && return 0
  [[ "$output_text" == *"is defined in both"* && "$output_text" == *"ModuleCache"* ]] && return 0
  return 1
}

#R001: function tag for clear_conflicting_swiftpm_build_dirs
clear_conflicting_swiftpm_build_dirs() {
  local output_text="$1"
  local cache_roots=""
  cache_roots="$(
    python3 - <<'PY' "$output_text"
import re
import sys

text = sys.argv[1]
roots = sorted(set(re.findall(r"(/[^'\s]+/src/macos-ui)/\.build", text)))
for root in roots:
    print(root)
PY
  )"
  if [[ -n "$cache_roots" ]]; then
    while IFS= read -r cache_root; do
      [[ -n "$cache_root" ]] || continue
      if [[ -d "$cache_root/.build" ]]; then
        rm -rf "$cache_root/.build"
      fi
    done <<< "$cache_roots"
  fi
  rm -rf ./src/macos-ui/.build
}

#R005: Prefer project venv when available.
if [[ -d "./${VENV_NAME}" ]] && [[ -f "./${VENV_NAME}/bin/activate" ]]; then
  if ! python_interpreter_usable "./${VENV_NAME}/bin/python"; then
    echo "⚠️  Skipping ${VENV_NAME} activation because its interpreter is not usable."
  else
  # shellcheck disable=SC1090,SC1091
    source "./${VENV_NAME}/bin/activate"
  fi
fi

if [[ "$RUN_SHELL_TESTS" == "true" ]]; then
  if ! command -v bats >/dev/null 2>&1; then
    echo "❌ bats is required for shell unit tests. Install bats-core and rerun."
    exit 1
  fi
  if [[ "$RUN_SHELL_COVERAGE" == "true" ]]; then
    if ! command -v "$SHELL_COVERAGE_TOOL" >/dev/null 2>&1; then
      echo "❌ ${SHELL_COVERAGE_TOOL} is required when RUN_SHELL_COVERAGE=true."
      echo "Install ${SHELL_COVERAGE_TOOL} and rerun (for Homebrew: brew install ${SHELL_COVERAGE_TOOL})."
      exit 1
    fi
    resolve_shell_coverage_include_paths
  fi
  collect_bats_files
  if [[ "${#bats_files[@]}" -eq 0 ]]; then
    echo "ℹ️  Skipping shell unit tests: no *.bats files found in SHELL_BATS_ROOTS='${SHELL_BATS_ROOTS:-./tests/sh}'."
  elif [[ "$RUN_SHELL_COVERAGE" == "true" ]]; then
    mkdir -p "$SHELL_COVERAGE_REPORT_DIR"
    echo "▶ Running shell unit tests (bats + ${SHELL_COVERAGE_TOOL}, serial coverage mode)..."
    coverage_index=0
    for bats_file in "${bats_files[@]}"; do
      run_single_bats_file "$bats_file"
      coverage_index=$((coverage_index + 1))
      coverage_prefix="$(printf '%03d' "$coverage_index")"
      if ! run_single_bats_file_with_coverage "$bats_file" "$coverage_prefix"; then
        if [[ "$SHELL_COVERAGE_STRICT" == "true" ]]; then
          if [[ -s "${SHELL_COVERAGE_LAST_STDERR_LOG:-}" ]]; then
            cat "${SHELL_COVERAGE_LAST_STDERR_LOG}" >&2
          fi
          echo "❌ Shell coverage collection failed for ${bats_file}."
          exit 1
        fi
        echo "⚠️  Shell coverage collection failed for ${bats_file}; continuing (set SHELL_COVERAGE_STRICT=true to fail)."
        if [[ -n "${SHELL_COVERAGE_LAST_STDERR_LOG:-}" ]]; then
          echo "   Coverage stderr log: ${SHELL_COVERAGE_LAST_STDERR_LOG}"
        fi
      fi
    done
    echo "Shell coverage reports: ${SHELL_COVERAGE_REPORT_DIR}"
  else
    resolve_bats_jobs
    if [[ "$BATS_JOBS_RESOLVED" -le 1 || "${#bats_files[@]}" -le 1 ]]; then
      echo "▶ Running shell unit tests (bats, serial)..."
      for bats_file in "${bats_files[@]}"; do
        run_single_bats_file "$bats_file"
      done
    else
      echo "▶ Running shell unit tests (bats, parallel by file; jobs=${BATS_JOBS_RESOLVED})..."
      printf '%s\0' "${bats_files[@]}" | \
        BATS_FILTER="$BATS_FILTER" \
        xargs -0 -P "$BATS_JOBS_RESOLVED" -I {} bash -c '
          set -euo pipefail
          file="$1"
          bats_env_unsets=(
            -u TELLER_DB_PASSWORD
            -u DB_PASSWORD
            -u DB_DIALECT
            -u PROFILE_NAME
            -u PROFILE_TARGET
            -u PG_HOST
            -u PG_PORT
            -u PG_DBNAME
            -u PG_USER
            -u PG_SSLMODE
            -u PG_SEARCH_PATH
            -u PG_RUNTIME_ROLE
            -u PG_ONEPSA_ITEM
            -u SQLITE_PATH
            -u SQLCIPHER_KEY
            -u TELLER_DB_HOST
            -u TELLER_DB_PORT
            -u TELLER_DB_NAME
            -u TELLER_DB_USER
            -u TELLER_DB_SQLITE_PATH
            -u TELLER_DB_SQLCIPHER_KEY
          )
          if [[ -n "${BATS_FILTER:-}" ]]; then
            env "${bats_env_unsets[@]}" bats --filter "$BATS_FILTER" "$file"
          else
            env "${bats_env_unsets[@]}" bats "$file"
          fi
        ' _ {}
    fi
  fi
fi

#R010: Run Python unit lane through pytest as the single runner semantic.
#R015: Propagate python-suite failures.
if [[ "$RUN_PYTHON_TESTS" == "true" ]]; then
  echo "▶ Running Python unit tests (pytest)..."
  PYTEST_DIR="${PYTEST_DIR:-tests/py}"
  UNITTEST_PYTHON="python3"
  coverage_sources_csv=""
  if [[ -n "${COVERAGE_SOURCE_DIRS// }" ]]; then
    coverage_sources_csv="$(printf '%s\n' "$COVERAGE_SOURCE_DIRS" | tr ',:' '  ' | xargs)"
    coverage_sources_csv="${coverage_sources_csv// /,}"
  elif [[ -d "./src" ]]; then
    coverage_sources_csv="src"
  fi
  if [[ -n "${PYTHONPATH:-}" ]]; then
    UNITTEST_PYTHONPATH="./src:${PYTHONPATH}"
  else
    UNITTEST_PYTHONPATH="./src"
  fi
  if python_interpreter_usable "./${VENV_NAME}/bin/python3"; then
    UNITTEST_PYTHON="./${VENV_NAME}/bin/python3"
  elif [[ -d "./${VENV_NAME}/lib" ]]; then
    python_minor_version="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
    preferred_site_packages_dir="./${VENV_NAME}/lib/python${python_minor_version}/site-packages"
    if [[ -d "$preferred_site_packages_dir" ]]; then
      preferred_site_packages_dir_abs="$(cd "$preferred_site_packages_dir" && pwd)"
      if [[ -n "$UNITTEST_PYTHONPATH" ]]; then
        UNITTEST_PYTHONPATH="${preferred_site_packages_dir_abs}:${UNITTEST_PYTHONPATH}"
      else
        UNITTEST_PYTHONPATH="${preferred_site_packages_dir_abs}"
      fi
    fi
  fi
  if [[ "$RUN_PYTEST_COVERAGE" == "true" ]] && PYTHONPATH="$UNITTEST_PYTHONPATH" "$UNITTEST_PYTHON" -m coverage --version >/dev/null 2>&1; then
    mkdir -p "$COVERAGE_REPORT_DIR"
    coverage_data_file="${COVERAGE_REPORT_DIR}/.coverage"
    coverage_run_cmd=( "$UNITTEST_PYTHON" -m coverage run "--data-file=${coverage_data_file}" )
    if [[ -n "$coverage_sources_csv" ]]; then
      coverage_run_cmd+=( "--source=${coverage_sources_csv}" )
    fi
    coverage_report_cmd=( "$UNITTEST_PYTHON" -m coverage report "--data-file=${coverage_data_file}" )
    if [[ -n "$COVERAGE_FAIL_UNDER" ]]; then
      coverage_report_cmd+=( "--fail-under=${COVERAGE_FAIL_UNDER}" )
    fi
    echo "▶ Collecting Python line coverage..."
    set +e
    PYTHONPATH="$UNITTEST_PYTHONPATH" "${coverage_run_cmd[@]}" -m pytest "$PYTEST_DIR" -q
    pytest_exit=$?
    set -e
    coverage_report_exit=0
    coverage_xml_exit=0
    coverage_json_exit=0
    if [[ -f "$coverage_data_file" ]]; then
      set +e
      "${coverage_report_cmd[@]}"
      coverage_report_exit=$?
      "$UNITTEST_PYTHON" -m coverage xml "--data-file=${coverage_data_file}" -o "${COVERAGE_REPORT_DIR}/coverage.xml"
      coverage_xml_exit=$?
      "$UNITTEST_PYTHON" -m coverage json "--data-file=${coverage_data_file}" -o "${COVERAGE_REPORT_DIR}/coverage.json"
      coverage_json_exit=$?
      set -e
      "$UNITTEST_PYTHON" - "${COVERAGE_REPORT_DIR}/coverage.json" "${COVERAGE_REPORT_DIR}/coverage-summary.json" <<'PY'
import json
import sys
from pathlib import Path

coverage_json = Path(sys.argv[1])
summary_json = Path(sys.argv[2])
payload = json.loads(coverage_json.read_text(encoding="utf-8"))
totals = payload.get("totals", {})
percent_covered = float(totals.get("percent_covered", 0.0))
summary = {
    "percent_covered": round(percent_covered, 2),
    "line_rate": round(percent_covered / 100.0, 4),
    "covered_lines": int(totals.get("covered_lines", 0)),
    "missing_lines": int(totals.get("missing_lines", 0)),
    "excluded_lines": int(totals.get("excluded_lines", 0)),
    "num_statements": int(totals.get("num_statements", 0)),
}
summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
PY
      echo "Coverage reports: ${COVERAGE_REPORT_DIR}/coverage.{xml,json}"
    fi
    if [[ "$pytest_exit" -ne 0 ]]; then
      exit "$pytest_exit"
    fi
    if [[ "$coverage_report_exit" -ne 0 || "$coverage_xml_exit" -ne 0 || "$coverage_json_exit" -ne 0 ]]; then
      exit 1
    fi
  else
    if [[ "$RUN_PYTEST_COVERAGE" == "true" ]]; then
      echo "⚠️  coverage.py not available in active environment; running pytest without coverage."
    fi
    PYTHONPATH="$UNITTEST_PYTHONPATH" "$UNITTEST_PYTHON" -m pytest "$PYTEST_DIR" -q
  fi
fi

#R025: Run pgTAP SQL unit tests.
#R015: Stop SQL suite on first failure.
if [[ "$RUN_SQL_TESTS" == "true" ]]; then
  if [[ -d "$SQL_TESTS_DIR" ]]; then
    if [[ "$DB_DIALECT" == "sqlite" || "${PROFILE_TARGET:-local}" == "sqlite" ]]; then
      if [[ -z "$SQLITE_PATH" ]]; then
        echo "❌ SQLite SQL lane requires SQLITE_PATH from profile export."
        exit 1
      fi
      if [[ -z "$SQLCIPHER_KEY" ]]; then
        echo "❌ SQLite SQL lane requires SQLCIPHER_KEY from profile export."
        exit 1
      fi
      if ! command -v sqlcipher >/dev/null 2>&1; then
        echo "❌ sqlcipher is required for SQLite SQL unit tests."
        exit 1
      fi
      shopt -s nullglob
      sql_test_files=("$SQL_TESTS_DIR"/*.sql)
      shopt -u nullglob
      if [[ "${#sql_test_files[@]}" -eq 0 ]]; then
        echo "ℹ️  Skipping SQL unit tests: no *.sql files found in ${SQL_TESTS_DIR}."
      else
        echo "▶ Running SQL unit tests (sqlcipher)..."
        SQLITE_ESCAPED_KEY="$(printf "%s" "$SQLCIPHER_KEY" | sed "s/'/''/g")"
        for sql_test_file in "${sql_test_files[@]}"; do
          sqlcipher "$SQLITE_PATH" <<SQL
.bail on
PRAGMA key='${SQLITE_ESCAPED_KEY}';
.read "${sql_test_file}"
SQL
        done
      fi
    else
    echo "▶ Preparing SQL unit tests (pgTAP)..."
    if [[ -z "$PG_PROVE_BIN" ]]; then
      if [[ -x "/opt/homebrew/bin/pg_prove" ]]; then
        PG_PROVE_BIN="/opt/homebrew/bin/pg_prove"
      elif [[ -x "/usr/local/bin/pg_prove" ]]; then
        PG_PROVE_BIN="/usr/local/bin/pg_prove"
      elif command -v pg_prove >/dev/null 2>&1; then
        PG_PROVE_BIN="$(command -v pg_prove)"
      elif [[ -x "${HOME}/perl5/bin/pg_prove" ]]; then
        PG_PROVE_BIN="${HOME}/perl5/bin/pg_prove"
      fi
    fi
    if [[ -z "$PG_PROVE_BIN" ]]; then
      echo "❌ pg_prove is required for pgTAP SQL unit tests. Install pgTAP tools and rerun."
      exit 1
    fi
    if [[ -z "$DB_PASSWORD" ]]; then
      DB_PASSWORD="$(rb_read_1psa_item "${TELLER_PSA_ITEM:-${PG_ONEPSA_ITEM:-localhost_postgres_teller}}" "password")"
    fi
    if [[ -z "$DB_PASSWORD" ]]; then
      echo "❌ failed to resolve teller DB password for SQL unit tests."
      exit 1
    fi
    # Some local DB profiles run SQL tests as restricted roles; pgTAP helper
    # objects require elevated privileges. Prefer postgres role when available.
    if [[ "${SQL_TESTS_USE_ADMIN_ROLE:-true}" == "true" && "$DB_USER" != "postgres" ]]; then
      admin_password="${POSTGRES_ADMIN_PASSWORD:-}"
      if [[ -z "$admin_password" ]]; then
        admin_password="$(rb_read_1psa_item "${POSTGRES_PSA_ITEM:-localhost_postgres_postgres}" "password" 2>/dev/null || true)"
      fi
      if [[ -n "$admin_password" ]]; then
        echo "ℹ️  Using postgres admin role for pgTAP execution."
        DB_USER="postgres"
        DB_PASSWORD="$admin_password"
      fi
    fi
    if [[ -z "$SQL_TEST_DATABASE" ]]; then
      echo "❌ Resolved profile is missing PG_DBNAME and SQL_TEST_DATABASE/TELLER_DB_NAME are unset."
      exit 1
    fi
    if ! command -v psql >/dev/null 2>&1; then
      echo "❌ psql is required to verify pgTAP extension availability. Install PostgreSQL client tools and rerun."
      exit 1
    fi

    if ! pgtap_installed="$(
      PGPASSWORD="${DB_PASSWORD}" PGSSLMODE="${PG_SSLMODE:-disable}" psql -w -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -v ON_ERROR_STOP=1 -d "$SQL_TEST_DATABASE" -Atqc \
        "SELECT 1 FROM pg_extension WHERE extname = 'pgtap' LIMIT 1;" 2>&1
    )"; then
      echo "❌ failed to query '${SQL_TEST_DATABASE}' for pgtap extension availability."
      echo "$pgtap_installed"
      exit 1
    fi

    if [[ "$pgtap_installed" != "1" ]]; then
      echo "❌ pgtap extension is required in database '${SQL_TEST_DATABASE}'. Run: CREATE EXTENSION pgtap;"
      exit 1
    fi

    shopt -s nullglob
    sql_test_files=("$SQL_TESTS_DIR"/*.sql)
    shopt -u nullglob

    if [[ "${#sql_test_files[@]}" -eq 0 ]]; then
      echo "ℹ️  Skipping SQL unit tests: no *.sql files found in ${SQL_TESTS_DIR}."
    else
      echo "▶ Running SQL unit tests (pgTAP via pg_prove)..."
      for sql_test_file in "${sql_test_files[@]}"; do
        if ! PGHOST="$DB_HOST" PGPORT="$DB_PORT" PGUSER="$DB_USER" PGPASSWORD="$DB_PASSWORD" PGSSLMODE="${PG_SSLMODE:-disable}" \
          PGOPTIONS="-c search_path=public,teller" \
          "$PG_PROVE_BIN" --dbname "$SQL_TEST_DATABASE" "$sql_test_file"; then
          if [[ "$PG_PROVE_BIN" == "${HOME}/perl5/bin/pg_prove" ]]; then
            brew_perl_bin="/opt/homebrew/bin/perl"
            if [[ ! -x "$brew_perl_bin" ]]; then
              brew_perl_prefix="$(brew --prefix perl 2>/dev/null || true)"
              if [[ -n "$brew_perl_prefix" ]]; then
                brew_perl_bin="${brew_perl_prefix}/bin/perl"
              fi
            fi
            if [[ -x "$brew_perl_bin" ]]; then
              echo "ℹ️  Retrying user-local pg_prove with Homebrew perl..."
              PGHOST="$DB_HOST" PGPORT="$DB_PORT" PGUSER="$DB_USER" PGPASSWORD="$DB_PASSWORD" PGSSLMODE="${PG_SSLMODE:-disable}" \
                PGOPTIONS="-c search_path=public,teller" \
                "$brew_perl_bin" "$PG_PROVE_BIN" --dbname "$SQL_TEST_DATABASE" "$sql_test_file"
              continue
            fi
          fi
          exit 1
        fi
      done
    fi
    fi
  else
    echo "ℹ️  Skipping SQL unit tests: ${SQL_TESTS_DIR} not found."
  fi
fi

#R020: Run Swift package tests under bounded stale-cache retry recovery.
#R015: Propagate Swift suite failures by exiting on non-zero status.
if [[ "$RUN_SWIFT_TESTS" == "true" ]]; then
  if [[ -d "./src/macos-ui/Tests" ]]; then
    if ! command -v swift >/dev/null 2>&1; then
      echo "❌ swift is required for Swift unit tests. Install Xcode command line tools and rerun."
      exit 1
    fi
    echo "▶ Running Swift unit tests (swift test)..."
    MACOS_UI_SWIFT_LOCK_HELPER="./src/scripts/macos_ui_swift_lock.sh"
    if [[ ! -f "$MACOS_UI_SWIFT_LOCK_HELPER" ]]; then
      echo "❌ macOS UI SwiftPM lock helper not found at ${MACOS_UI_SWIFT_LOCK_HELPER}."
      exit 1
    fi
    # shellcheck disable=SC1090
    source "$MACOS_UI_SWIFT_LOCK_HELPER"
    #R001: function tag for run_swift_tests_with_lock
    run_swift_tests_with_lock() {
      macos_ui_with_swiftpm_lock "$MACOS_UI_SWIFTPM_LOCK" "$MACOS_UI_SWIFT_LOCK_TIMEOUT_SECONDS" "run_unit_test_lanes:swift-test" \
        swift test --package-path ./src/macos-ui 2>&1
    }
    set +e
    swift_test_output="$(run_swift_tests_with_lock)"
    swift_test_exit=$?
    set -e
    printf '%s\n' "$swift_test_output"
    if [[ "$swift_test_exit" -ne 0 ]]; then
      if [[ "$swift_test_output" == *"sandbox_apply: Operation not permitted"* ]]; then
        echo "⚠️  Skipping Swift unit tests in restricted runtime (swift sandbox apply permission denied)."
      elif swiftpm_state_looks_stale "$swift_test_output"; then
        #R020: Recover only on stale-cache/moved-worktree style errors instead of deleting .build preemptively.
        echo "ℹ️  Detected stale SwiftPM cache state; clearing ./src/macos-ui/.build and retrying swift test once..."
        if ! clear_conflicting_swiftpm_build_dirs "$swift_test_output"; then
          echo "⚠️  Unable to fully clear ./src/macos-ui/.build in restricted runtime; continuing with original failure."
          exit "$swift_test_exit"
        fi
        set +e
        swift_test_output="$(run_swift_tests_with_lock)"
        swift_test_exit=$?
        set -e
        printf '%s\n' "$swift_test_output"
        if [[ "$swift_test_exit" -ne 0 ]]; then
          exit "$swift_test_exit"
        fi
      else
        exit "$swift_test_exit"
      fi
    fi
  else
    echo "ℹ️  Skipping Swift unit tests: ./src/macos-ui/Tests not found."
  fi
fi

if [[ "$RUN_MACOS_UI_REGRESSION_TESTS" == "true" ]]; then
  echo "▶ Running macOS UI regression test lane..."
  # Resolve the lane by content so repo renumbers/relocations stay safe.
  ui_regression_lane="$(ls ./tests/t*_run_macos_ui_regression_tests.sh 2>/dev/null | sort -V | head -n1)"
  if [[ -z "$ui_regression_lane" ]]; then
    echo "❌ macOS UI regression lane (tests/t*_run_macos_ui_regression_tests.sh) not found." >&2
    exit 1
  fi
  "$ui_regression_lane"
fi
