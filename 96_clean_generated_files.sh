#!/usr/bin/env bash
#R001: Enforce strict shell mode and secure default permissions.
umask 007
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#R005: Resolve target repo root through the shared runbook contract.
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/src/scripts/runbook_common.sh"
runbook_cd_repo
REPO_ROOT="$RUNBOOK_REPO_ROOT"

MOVED_COUNT=0
SKIPPED_COUNT=0
TRASH_RUN_DIR=""

#R001: shard-3 function tag
ensure_trash_run_dir() {
  if [[ -n "$TRASH_RUN_DIR" ]]; then
    return
  fi
  mkdir -p "${HOME}/.Trash"
  TRASH_RUN_DIR="$(mktemp -d "${HOME}/.Trash/runner_generated_cleanup_XXXXXX")"
}

#R001: shard-3 function tag
move_target_to_trash() {
  local relative_target="$1"
  local source_path=""
  local destination_path=""

  source_path="${REPO_ROOT}/${relative_target#./}"
  if [[ ! -e "$source_path" && ! -L "$source_path" ]]; then
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    return
  fi

  ensure_trash_run_dir
  destination_path="${TRASH_RUN_DIR}/${relative_target#./}"
  mkdir -p "$(dirname "$destination_path")"
  mv "$source_path" "$destination_path"
  MOVED_COUNT=$((MOVED_COUNT + 1))
  echo "🗑️  moved: ${relative_target}"
}

#R010: Security and fuzzing reports.
move_target_to_trash "./artifacts/security"
move_target_to_trash "./artifacts/security-dast"
move_target_to_trash "./artifacts/fuzz"

#R015: Coverage reports and test-run logs.
move_target_to_trash "./artifacts/coverage"
move_target_to_trash "./artifacts/parallel"

#R020: Traceability and quality logs/reports.
move_target_to_trash "./artifacts/traceability"
move_target_to_trash "./artifacts/traceability.latest.log"
move_target_to_trash "./artifacts/quality"
move_target_to_trash "./artifacts/quality.latest.log"

#R025: Print a deterministic completion summary and keep absent targets non-fatal.
if [[ "$MOVED_COUNT" -eq 0 ]]; then
  echo "ℹ️  No generated artifacts found to clean."
  echo "Checked targets: security/fuzz, coverage, test logs, traceability/quality."
  exit 0
fi

echo "✅ Cleanup complete: moved ${MOVED_COUNT} target(s) to ${TRASH_RUN_DIR}."
if [[ "$SKIPPED_COUNT" -gt 0 ]]; then
  echo "ℹ️  Skipped ${SKIPPED_COUNT} absent target(s)."
fi
