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
#   - Set RUNBOOK_PROFILE="<repo>" before sourcing. Explicit selection is
#     preferred over guessing from a (possibly symlinked) basename.
#   - Source this file via a path resolved relative to the pointer, e.g.
#       source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../runner/src/scripts" \
#         && pwd -P)/pointer_shim.sh"
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

#R015: Load the repo-specific runbook profile the pointer selected via RUNBOOK_PROFILE.
if [[ -z "${RUNBOOK_PROFILE:-}" ]]; then
  echo "❌ pointer_shim: RUNBOOK_PROFILE must be set by the pointer before sourcing." >&2
  exit 1
elif [[ ! -f "${RUNNER_HOME}/config/runbook/${RUNBOOK_PROFILE}.env" ]]; then
  echo "❌ pointer_shim: runbook profile not found: ${RUNNER_HOME}/config/runbook/${RUNBOOK_PROFILE}.env" >&2
  exit 1
else
  # shellcheck source=/dev/null
  source "${RUNNER_HOME}/config/runbook/${RUNBOOK_PROFILE}.env"
fi

#R020: Delegate to the mapped runner golden under RUNNER_HOME with argument passthrough.
delegate_golden() {
  local target="$1"
  shift
  exec "${RUNNER_HOME}/${target}" "$@"
}
