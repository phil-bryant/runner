#!/usr/bin/env bash
#R001: Secure umask and strict shell mode for the traceability lane entrypoint.
umask 007
set -euo pipefail

#R005: Resolve RUNNER_HOME/RUNBOOK_REPO_ROOT through the shared runbook contract
# and operate from the target repo root regardless of caller cwd.
SCRIPT_PATH="${BASH_SOURCE[0]-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../src/scripts/runbook_common.sh"
REPO_ROOT="$RUNBOOK_REPO_ROOT"

cd "$REPO_ROOT"

#R010: Select the traceability engine on PYTHONPATH, defaulting to the runner
# engine (runner-first) so shared requirements/bats roots evaluate consistently;
# allow a repo-first override that falls back to runner when absent.
TRACEABILITY_PYTHONPATH="${RUNNER_HOME}/tests/py"
if [[ "${TRACEABILITY_ENGINE_MODE:-runner-first}" == "repo-first" ]]; then
  TRACEABILITY_PYTHONPATH="${REPO_ROOT}/tests/py"
  if [[ ! -d "${TRACEABILITY_PYTHONPATH}/traceability" ]]; then
    TRACEABILITY_PYTHONPATH="${RUNNER_HOME}/tests/py"
  fi
fi

#R020: Delegate the entire check to the Python traceability CLI, passing
# arguments through unchanged and propagating its exit status. The wrapper takes
# no coverage self-exemption; its own requirements doc traces it like any source.
exec env \
  PYTHONPATH="${TRACEABILITY_PYTHONPATH}${PYTHONPATH:+:${PYTHONPATH}}" \
  python3 -m traceability.cli "$@"
