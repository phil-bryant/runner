#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../src/scripts/runbook_common.sh"
REPO_ROOT="$RUNBOOK_REPO_ROOT"
#R001: Run from repository root regardless of caller cwd.
cd "$REPO_ROOT"

#R005: Execute only the shell unit-test lane.
#R005: Run ShellCheck before Bats so this lane matches the documented "shellcheck + Bats" contract.
RUN_SHELLCHECK_GATE="${RUN_SHELLCHECK_GATE:-true}"
if [[ "$RUN_SHELLCHECK_GATE" == "true" ]]; then
  echo "▶ Running ShellCheck gate for shell unit-test lane..."
  shellcheck_targets=()
  shopt -s nullglob
  for target in ./[0-9][0-9]_*.sh ./t[0-9][0-9]_*.sh; do
    shellcheck_targets+=("$target")
  done
  shopt -u nullglob
  if [[ -d "./src/scripts" ]]; then
    while IFS= read -r target; do
      shellcheck_targets+=("$target")
    done < <(find ./src/scripts -type f -name "*.sh" | sort)
  fi
  if [[ "${#shellcheck_targets[@]}" -gt 0 ]]; then
    shellcheck "${shellcheck_targets[@]}"
  else
    echo "ℹ️  ShellCheck skipped (no shell targets discovered)."
  fi
else
  echo "ℹ️  RUN_SHELLCHECK_GATE=false; skipping ShellCheck preflight for this shell-unit run."
fi

if RUN_SHELL_TESTS=true \
  RUN_PYTHON_TESTS=false \
  RUN_SQL_TESTS=false \
  RUN_SWIFT_TESTS=false \
  RUN_MACOS_UI_REGRESSION_TESTS=false \
  BATS_JOBS=1 \
  "${RUNNER_HOME}/src/scripts/run_unit_test_lanes.sh"; then
  #R006: Emit an unambiguous success marker at completion.
  echo "✅ Shell unit tests succeeded."
else
  #R006: Emit an unambiguous failure marker at completion.
  echo "❌ Shell unit tests failed."
  exit 1
fi
