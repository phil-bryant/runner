#!/usr/bin/env bash
umask 007
set -uo pipefail

# Side-by-side parity harness for Phase 1. Runs the legacy NN_/tNN_ script and the new
# rNN_/rtNN_ thin pointer for the same lane, captures stdout+stderr and exit code, then
# diffs the normalized output. Use during verification before Phase 2 deprecation.
#
# Usage:
#   verify_rnn_parity.sh <repo> <name>          # runbook pair: <repo>/<name>.sh vs <repo>/r<name>.sh
#   verify_rnn_parity.sh <repo> tests/<name>    # test pair:   <repo>/tests/<name>.sh vs .../rt<name>.sh
#
# Only invoke on lanes that are safe to run in the current environment (read-only / idempotent).

EGGNEST_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

usage() { echo "usage: verify_rnn_parity.sh <repo> <name|tests/name>"; exit 2; }
[[ $# -eq 2 ]] || usage
REPO="$1"
RAW_NAME="$2"
shift 2 || true

if [[ "$RAW_NAME" == tests/* ]]; then
  base="${RAW_NAME#tests/}"
  legacy="${EGGNEST_ROOT}/${REPO}/tests/${base}.sh"
  pointer="${EGGNEST_ROOT}/${REPO}/tests/rt${base#t}.sh"
  lane_label="${REPO}/tests/${base}"
else
  legacy="${EGGNEST_ROOT}/${REPO}/${RAW_NAME}.sh"
  pointer="${EGGNEST_ROOT}/${REPO}/r${RAW_NAME}.sh"
  lane_label="${REPO}/${RAW_NAME}"
fi

if [[ ! -f "$legacy" ]]; then echo "❌ legacy script not found: $legacy"; exit 1; fi
if [[ ! -f "$pointer" ]]; then echo "❌ pointer script not found: $pointer"; exit 1; fi

tmp_dir="$(mktemp -d)"
legacy_out="${tmp_dir}/legacy.out"
pointer_out="${tmp_dir}/pointer.out"

run_capture() {
  local script="$1" out="$2" dir
  dir="$(cd "$(dirname "$script")" && pwd)"
  ( cd "$dir" && "$script" ) >"$out" 2>&1
  echo $?
}

#R001: Normalize volatile content (timestamps, tmp paths, durations) before diffing.
normalize() {
  sed -E \
    -e 's#/[A-Za-z0-9_./-]+\.XXXXXX[A-Za-z0-9]*#<TMP>#g' \
    -e 's/[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9:.]+Z?/<TS>/g' \
    -e 's/[0-9]+(\.[0-9]+)?s\b/<DUR>/g' \
    "$1"
}

echo "▶ Parity: ${lane_label}"
echo "  legacy : ${legacy}"
echo "  pointer: ${pointer}"
legacy_exit="$(run_capture "$legacy" "$legacy_out")"
pointer_exit="$(run_capture "$pointer" "$pointer_out")"

echo "  exit codes: legacy=${legacy_exit} pointer=${pointer_exit}"
status=0
if [[ "$legacy_exit" != "$pointer_exit" ]]; then
  echo "  ❌ exit code mismatch"
  status=1
fi

if diff -u <(normalize "$legacy_out") <(normalize "$pointer_out") >"${tmp_dir}/diff.txt"; then
  echo "  ✅ normalized output matches"
else
  echo "  ⚠️  normalized output differs:"
  sed 's/^/    /' "${tmp_dir}/diff.txt"
  status=1
fi

trash_dir="${HOME}/.Trash/verify_rnn_parity_$(date +%Y-%m-%d-%H.%M.%S)_$$"
mkdir -p "$trash_dir"
mv "$tmp_dir" "$trash_dir/" 2>/dev/null || true

if [[ "$status" -eq 0 ]]; then
  echo "✅ PARITY OK: ${lane_label}"
else
  echo "❌ PARITY DIFF: ${lane_label}"
fi
exit "$status"
