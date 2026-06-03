#!/usr/bin/env bash
umask 007
set -euo pipefail

#R001: Establish RUNNER_HOME (code) and RUNBOOK_REPO_ROOT (target repo) contract.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/src/scripts/runbook_common.sh"
runbook_cd_repo

#R005: Delegate requirements-traceability verification to the shared Python CLI, operating
#R005: on the target repo. Prefer the repo's own traceability package; fall back to runner's.
TRACEABILITY_PYTHONPATH="${RUNBOOK_REPO_ROOT}/tests/py"
if [[ ! -d "${TRACEABILITY_PYTHONPATH}/traceability" ]]; then
  TRACEABILITY_PYTHONPATH="${RUNNER_HOME}/tests/py"
fi

#R010: Preserve strict entrypoint contract while delegating all policy to the Python CLI.
exec env \
  PYTHONPATH="${TRACEABILITY_PYTHONPATH}${PYTHONPATH:+:${PYTHONPATH}}" \
  TRACEABILITY_EXCLUDE_SOURCE="$(basename "$0")" \
  python3 -m traceability.cli "$@"
