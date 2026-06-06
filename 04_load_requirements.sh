#!/usr/bin/env bash
#R001: Run with a secure umask and strict shell mode so the self-run shim fails fast.
umask 007
set -euo pipefail

# Thin compatibility shim: delegate to the canonical generic loader.
# This avoids drift from src/scripts/load_requirements_generic.sh.
#R005: Resolve the script's own directory and default RUNBOOK_REPO_ROOT to it so
# self-runs target the runner repo unless the caller overrides it.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export RUNBOOK_REPO_ROOT="${RUNBOOK_REPO_ROOT:-$SCRIPT_DIR}"

#R010: When targeting runner itself and no external profile has already been loaded,
# source runner's profile so direct ./04_load_requirements.sh self-runs keep the
# secure bootstrap defaults (pinned pip) used by self-test workflows.
if [ "$RUNBOOK_REPO_ROOT" = "$SCRIPT_DIR" ] && [ -z "${RUNBOOK_PROFILE_LOADED:-}" ] && [ -f "${SCRIPT_DIR}/config/runbook/runner.env" ]; then
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/config/runbook/runner.env"
    export RUNBOOK_PROFILE_LOADED="runner"
fi

#R015: Delegate the real load to the canonical generic loader, passing arguments
# through unchanged to avoid drift.
exec "${SCRIPT_DIR}/src/scripts/load_requirements_generic.sh" "$@"
