#!/usr/bin/env bash
# pointer_shim.sh - shared boilerplate for thin runbook pointer scripts.
#
# Each sibling repo (teller/classy/matchy/mailcart), the eggnest workspace root,
# and runner's own self-run pointer ship a thin pointer that delegates into the
# runner "golden" scripts. Every pointer used to repeat the same boilerplate:
# secure umask, strict shell mode, RUNNER_HOME + RUNBOOK_REPO_ROOT resolution,
# and sourcing runner/config/runbook/<profile>.env. This shim centralizes all of
# it so each pointer collapses to a profile declaration plus a single
# delegate_golden call.
#
# Contract for callers (pointers):
#   - Source this file via a path resolved relative to the pointer, e.g.
#       source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../runner/src/scripts" \
#         && pwd -P)/pointer_shim.sh"
#   - Prefer selecting an explicit profile after sourcing:
#       select_runbook_profile "<repo>"
#     Backward compatibility: if the pointer exports RUNBOOK_PROFILE and calls
#     delegate_golden directly, delegate_golden will auto-load that profile.
#   - Call: delegate_golden "<target-relative-to-RUNNER_HOME>" "$@"

#R001: Enable secure umask and strict shell mode for every pointer before delegation.
umask 007
set -euo pipefail

#R005: Resolve RUNNER_HOME from this shim's own physical location
# (runner/src/scripts -> runner), independent of which repo's pointer sourced it.
POINTER_SHIM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
RUNNER_HOME="$(cd "${POINTER_SHIM_DIR}/../.." && pwd -P)"
export RUNNER_HOME

#R010: Resolve RUNBOOK_REPO_ROOT from the sourcing pointer's own physical directory.
# Pointers in a repo's tests/ subdir still resolve to the repo root (not tests/),
# preserving the pre-shim behavior exactly.
POINTER_PATH="${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}"
POINTER_DIR="$(cd "$(dirname "${POINTER_PATH}")" && pwd -P)"
if [[ "$(basename "${POINTER_DIR}")" == "tests" ]]; then
  RUNBOOK_REPO_ROOT="$(cd "${POINTER_DIR}/.." && pwd -P)"
else
  RUNBOOK_REPO_ROOT="${POINTER_DIR}"
fi
export RUNBOOK_REPO_ROOT

#R015: Load the repo-specific runbook profile selected explicitly by the pointer.
select_runbook_profile() {
  local runbook_profile="${1:-}"
  if [[ -z "${runbook_profile}" ]]; then
    echo "❌ pointer_shim: select_runbook_profile requires a profile argument." >&2
    return 1
  fi

  local runbook_profile_env="${RUNNER_HOME}/config/runbook/${runbook_profile}.env"
  if [[ ! -f "${runbook_profile_env}" ]]; then
    echo "❌ pointer_shim: runbook profile not found: ${runbook_profile_env}" >&2
    return 1
  fi

  export RUNBOOK_PROFILE="${runbook_profile}"
  export POINTER_SHIM_PROFILE_LOADED="1"
  # shellcheck source=/dev/null
  source "${runbook_profile_env}"
}

#R020: Delegate to the mapped runner golden under RUNNER_HOME with argument passthrough.
delegate_golden() {
  local target="$1"
  shift
  # Backward-compat mode for pointers that set RUNBOOK_PROFILE but do not call
  # select_runbook_profile explicitly.
  if [[ -n "${RUNBOOK_PROFILE:-}" && "${POINTER_SHIM_PROFILE_LOADED:-}" != "1" ]]; then
    select_runbook_profile "${RUNBOOK_PROFILE}"
  fi
  exec "${RUNNER_HOME}/${target}" "$@"
}
