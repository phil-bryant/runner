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
