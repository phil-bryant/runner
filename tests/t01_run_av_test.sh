#!/usr/bin/env bash
umask 007
#R001: Run in strict shell mode and execute from repository root.
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../src/scripts/runbook_common.sh"
REPO_ROOT="$RUNBOOK_REPO_ROOT"
cd "$REPO_ROOT"

#R005: Support configurable report destination and AV gating behavior.
REPORT_DIR="${SECURITY_REPORT_DIR:-./artifacts/security/reports}"
RUN_CLAMAV="${RUN_CLAMAV:-true}"
FAIL_ON_INFECTED="${AV_FAIL_ON_INFECTED:-true}"

mkdir -p "$REPORT_DIR"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "❌ Missing required command: $1"
    echo "Install prerequisites with: ./01_install_prerequisites.sh"
    exit 1
  fi
}

print_tool_header() {
  #R030: Delimit AV tool execution with boxed descriptor headers.
  local tool_name="$1"
  local explainer_line_1="$2"
  local explainer_line_2="$3"
  local tool_url="$4"
  local border="+==============================================================================+"
  printf '%s\n' "$border"
  printf '| %-76s |\n' "Security Tool: ${tool_name}"
  printf '| %-76s |\n' "${explainer_line_1}"
  printf '| %-76s |\n' "${explainer_line_2}"
  printf '| %-76s |\n' "URL: ${tool_url}"
  printf '%s\n' "$border"
}

resolve_target_abs_path() {
  local target_path="$1"
  if [[ -d "$target_path" ]]; then
    (
      cd "$target_path"
      pwd
    )
    return
  fi
  (
    cd "$(dirname "$target_path")"
    printf '%s/%s\n' "$(pwd)" "$(basename "$target_path")"
  )
}

detect_clamav_db_dir() {
  local brew_prefix=""
  if [[ -n "${CLAMAV_DB_DIR:-}" ]]; then
    printf '%s\n' "${CLAMAV_DB_DIR}"
    return
  fi
  brew_prefix="$(brew --prefix 2>/dev/null || true)"
  if [[ -n "$brew_prefix" ]] && [[ -d "${brew_prefix}/var/lib/clamav" ]]; then
    printf '%s\n' "${brew_prefix}/var/lib/clamav"
    return
  fi
  if [[ -d "/var/lib/clamav" ]]; then
    printf '%s\n' "/var/lib/clamav"
    return
  fi
  printf '%s\n' ""
}

print_clamav_signature_status() {
  #R015: Print signature freshness metadata before scan execution.
  local db_dir="$1"
  local max_age_hours="$2"
  local status_path="$3"
  printf '%s\n' "unknown" > "$status_path"
  if [[ -z "$db_dir" ]]; then
    echo "ℹ️  ClamAV signature freshness: unknown (database directory not found)."
    return
  fi
  echo "▶ ClamAV signature DB directory: ${db_dir}"
  python3 - <<'PY' "$db_dir" "$max_age_hours" "$status_path"
import datetime as dt
import json
import pathlib
import sys

db_dir = pathlib.Path(sys.argv[1])
max_age_hours = int(sys.argv[2])
status_path = pathlib.Path(sys.argv[3])
patterns = ("*.cvd", "*.cld", "*.inc")
files = []
for pattern in patterns:
    files.extend(db_dir.glob(pattern))

if not files:
    print("⚠️  ClamAV signature freshness: no database files found.")
    status_path.write_text("missing\n", encoding="utf-8")
    sys.exit(0)

latest = max(files, key=lambda p: p.stat().st_mtime)
latest_dt = dt.datetime.fromtimestamp(latest.stat().st_mtime, tz=dt.timezone.utc)
now = dt.datetime.now(tz=dt.timezone.utc)
age_hours = (now - latest_dt).total_seconds() / 3600.0
status = "fresh" if age_hours <= max_age_hours else "stale"
status_path.write_text(f"{status}\n", encoding="utf-8")

payload = {
    "latest_file": latest.name,
    "updated_utc": latest_dt.isoformat().replace("+00:00", "Z"),
    "age_hours": round(age_hours, 2),
    "max_age_hours": max_age_hours,
    "status": status,
}
print("▶ ClamAV signature freshness:")
print(json.dumps(payload, indent=2))
if status == "stale":
    print("⚠️  ClamAV signatures look stale; consider running 'freshclam --stdout'.")
PY
}

run_freshclam_refresh() {
  local clamav_report="$1"
  if ! command -v freshclam >/dev/null 2>&1; then
    echo "❌ ClamAV database refresh required but 'freshclam' is unavailable."
    return 1
  fi

  set +e
  freshclam --stdout 2>&1 | tee "${clamav_report}.freshclam.log"
  local freshclam_exit=${PIPESTATUS[0]}
  set -e
  local freshclam_log_text=""
  if [[ -f "${clamav_report}.freshclam.log" ]]; then
    freshclam_log_text="$(<"${clamav_report}.freshclam.log")"
  fi
  if [[ "$freshclam_exit" -ne 0 ]] && [[ "$freshclam_log_text" == *"Can't open/parse the config file"* ]]; then
    echo "⚠️  freshclam config missing or invalid; attempting one-time config bootstrap."
    if ensure_freshclam_config; then
      set +e
      freshclam --stdout 2>&1 | tee "${clamav_report}.freshclam.log"
      freshclam_exit=${PIPESTATUS[0]}
      set -e
    fi
  fi
  if [[ "$freshclam_exit" -ne 0 ]]; then
    echo "❌ freshclam failed to download ClamAV signatures."
    echo "Run 'freshclam --stdout' manually, then rerun AV checks."
    return 1
  fi
  return 0
}

run_clamscan_once() {
  #R020: Emit heartbeat progress lines while ClamAV scan is running.
  local report_path="$1"
  local scan_target="$2"
  local scan_target_abs="$3"
  local heartbeat_seconds="${CLAMAV_HEARTBEAT_SECONDS:-15}"
  local poll_seconds="${CLAMAV_POLL_SECONDS:-1}"
  if ! [[ "$heartbeat_seconds" =~ ^[0-9]+$ ]] || (( heartbeat_seconds < 1 )); then
    heartbeat_seconds=15
  fi
  if ! [[ "$poll_seconds" =~ ^[0-9]+$ ]] || (( poll_seconds < 1 )); then
    poll_seconds=1
  fi
  local start_ts
  start_ts="$(date +%s)"
  local next_heartbeat_ts=$(( start_ts + heartbeat_seconds ))
  clamscan \
    --recursive \
    --infected \
    --exclude-dir='\.git(/|$)' \
    --exclude-dir='artifacts/security/reports(/|$)' \
    --exclude-dir='artifacts/security(/|$)' \
    --exclude-dir='artifacts/parallel(/|$)' \
    --exclude-dir='artifacts/mutation(/|$)' \
    --exclude-dir='artifacts/fuzz(/|$)' \
    --exclude-dir='artifacts/macos-ui-regression(/|$)' \
    --exclude-dir='\.derivedData-ui-tests(/|$)' \
    --exclude-dir='artifacts/cache/hypothesis(/|$)' \
    --exclude-dir='artifacts/cache/ruff(/|$)' \
    --exclude-dir='artifacts/security-dast(/|$)' \
    --exclude-dir='__pycache__' \
    --exclude-dir='\.ruff_cache(/|$)' \
    --exclude-dir='\.pytest_cache(/|$)' \
    --exclude-dir='\.cursor(/|$)' \
    --exclude-dir='\.semgrep-home(/|$)' \
    --exclude-dir='/backups(/|$)' \
    --exclude-dir='/archive(/|$)' \
    "$scan_target" > "$report_path" 2>&1 &
  local clamav_pid=$!
  echo "▶ ClamAV scan in progress (started) target=${scan_target_abs}"
  while kill -0 "$clamav_pid" >/dev/null 2>&1; do
    sleep "$poll_seconds"
    if kill -0 "$clamav_pid" >/dev/null 2>&1; then
      local now_ts
      now_ts="$(date +%s)"
      if (( now_ts >= next_heartbeat_ts )); then
        next_heartbeat_ts=$(( now_ts + heartbeat_seconds ))
        local elapsed
        elapsed=$(( now_ts - start_ts ))
        echo "▶ ClamAV scan in progress (${elapsed}s elapsed) target=${scan_target_abs}"
      fi
    fi
  done
  wait "$clamav_pid"
  local scan_exit=$?
  if [[ -f "$report_path" ]]; then
    cat "$report_path"
  fi
  return "$scan_exit"
}

print_clamav_error_excerpt() {
  local report_path="$1"
  local max_lines="${2:-5}"
  if ! [[ "$max_lines" =~ ^[0-9]+$ ]] || (( max_lines < 1 )); then
    max_lines=5
  fi
  if [[ ! -f "$report_path" ]]; then
    return
  fi
  python3 - <<'PY' "$report_path" "$max_lines"
from pathlib import Path
import sys

report_path = Path(sys.argv[1])
max_lines = int(sys.argv[2])
text = report_path.read_text(encoding="utf-8", errors="replace")

error_lines = []
for line in text.splitlines():
    if "ERROR:" in line:
        error_lines.append(line.strip())
    if len(error_lines) >= max_lines:
        break

if error_lines:
    print(f"⚠️  ClamAV reported file-level scan errors (showing up to {max_lines}):")
    for line in error_lines:
        print(f"    {line}")
PY
}

ensure_freshclam_config() {
  local conf_path=""
  local sample_path=""
  local brew_prefix=""

  brew_prefix="$(brew --prefix 2>/dev/null || true)"
  if [[ -n "$brew_prefix" ]]; then
    conf_path="${brew_prefix}/etc/clamav/freshclam.conf"
    sample_path="${brew_prefix}/etc/clamav/freshclam.conf.sample"
  fi

  if [[ -z "$conf_path" ]]; then
    return 1
  fi

  if [[ ! -f "$conf_path" ]]; then
    if [[ -f "$sample_path" ]]; then
      cp "$sample_path" "$conf_path"
      echo "▶ Created ClamAV freshclam config from sample at ${sample_path}"
    else
      return 1
    fi
  fi

  if [[ -f "$conf_path" ]] && grep -Eq '^[[:space:]]*Example([[:space:]]|$)' "$conf_path"; then
    python3 - <<'PY' "$conf_path"
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = re.sub(r'(?m)^[ \t]*Example(?:[ \t].*)?$', '# Example', text)
path.write_text(text, encoding="utf-8")
PY
    echo "▶ Updated ${conf_path} to disable 'Example' mode"
  fi
}

run_clamav_scan() {
  #R010: Run repository malware scanning with ClamAV and persist machine-readable summary.
  local clamav_report="$1"
  local clamav_summary="$2"
  local clamav_scan_target="${CLAMAV_SCAN_TARGET:-.}"
  local clamav_signature_max_age_hours="${CLAMAV_SIGNATURE_MAX_AGE_HOURS:-24}"
  local clamav_max_scan_errors="${CLAMAV_MAX_SCAN_ERRORS:-5}"
  local freshclam_ran=false
  if ! [[ "$clamav_max_scan_errors" =~ ^[0-9]+$ ]]; then
    echo "⚠️  Invalid CLAMAV_MAX_SCAN_ERRORS='${clamav_max_scan_errors}'; defaulting to 5."
    clamav_max_scan_errors=5
  fi

  if [[ "$RUN_CLAMAV" != "true" ]]; then
    echo "ℹ️  ClamAV repository scan skipped (set RUN_CLAMAV=true to enable)."
    printf '%s\n' '{"scanned_files":0,"infected_files":0,"total_errors":0,"exit_code":0,"skipped":true}' > "$clamav_summary"
    : > "$clamav_report"
    return 0
  fi

  require_command clamscan
  print_tool_header \
    "ClamAV" \
    "Signature-based malware scan across repository files." \
    "Detects known malicious payloads before release or deployment." \
    "https://www.clamav.net/"

  if [[ ! -e "$clamav_scan_target" ]]; then
    echo "❌ ClamAV scan target not found: ${clamav_scan_target}"
    exit 1
  fi

  local clamav_scan_target_abs=""
  clamav_scan_target_abs="$(resolve_target_abs_path "$clamav_scan_target")"
  echo "▶ Running ClamAV repository scan"
  echo "▶ ClamAV scan target: ${clamav_scan_target_abs}"
  local clamav_db_dir=""
  clamav_db_dir="$(detect_clamav_db_dir)"
  local clamav_signature_status_file="${clamav_report}.signature-status"
  print_clamav_signature_status "$clamav_db_dir" "$clamav_signature_max_age_hours" "$clamav_signature_status_file"
  local clamav_signature_status="unknown"
  if [[ -f "$clamav_signature_status_file" ]]; then
    clamav_signature_status="$(tr -d '[:space:]' < "$clamav_signature_status_file")"
  fi
  if [[ "$clamav_signature_status" == "stale" ]]; then
    echo "⚠️  ClamAV signatures are stale (> ${clamav_signature_max_age_hours}h); enforcing refresh with freshclam."
    if ! run_freshclam_refresh "$clamav_report"; then
      exit 1
    fi
    freshclam_ran=true
    echo "▶ Continuing ClamAV repository scan after enforced signature refresh"
  fi

  set +e
  run_clamscan_once "$clamav_report" "$clamav_scan_target" "$clamav_scan_target_abs"
  local clamav_exit=$?
  set -e

  local clamav_report_text=""
  if [[ -f "$clamav_report" ]]; then
    clamav_report_text="$(<"$clamav_report")"
  fi
  #R025: Retry one time after freshclam when signature databases are missing.
  if [[ "$clamav_exit" -gt 1 ]] && [[ "$clamav_report_text" == *"No supported database files found"* ]]; then
    if [[ "$freshclam_ran" == "true" ]]; then
      echo "⚠️  ClamAV signatures are still missing after proactive refresh; retrying scan once without another refresh."
    else
      echo "⚠️  ClamAV signatures are missing; attempting one-time database refresh with freshclam."
      if ! run_freshclam_refresh "$clamav_report"; then
        exit 1
      fi
      freshclam_ran=true
    fi
    echo "▶ Retrying ClamAV repository scan after signature refresh"
    set +e
    run_clamscan_once "$clamav_report" "$clamav_scan_target" "$clamav_scan_target_abs"
    clamav_exit=$?
    set -e
    if [[ -f "$clamav_report" ]]; then
      clamav_report_text="$(<"$clamav_report")"
    fi
  fi

  python3 - <<'PY' "$clamav_report" "$clamav_summary" "$clamav_exit" "$clamav_max_scan_errors"
import json
import re
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
exit_code = int(sys.argv[3])
scan_error_threshold = int(sys.argv[4])
text = ""
if report_path.exists():
    text = report_path.read_text(encoding="utf-8", errors="replace")

scanned_match = re.search(r"Scanned files:\s*(\d+)", text)
infected_match = re.search(r"Infected files:\s*(\d+)", text)
errors_match = re.search(r"Total errors:\s*(\d+)", text)

total_errors = int(errors_match.group(1)) if errors_match else 0

summary = {
    "scanned_files": int(scanned_match.group(1)) if scanned_match else 0,
    "infected_files": int(infected_match.group(1)) if infected_match else (1 if exit_code == 1 else 0),
    "total_errors": total_errors,
    "max_scan_errors": scan_error_threshold,
    "exit_code": exit_code,
    "skipped": False,
}

with summary_path.open("w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
    fh.write("\n")

print("ClamAV summary")
print(json.dumps(summary, indent=2))
PY

  local clamav_infected_files=0
  local clamav_total_errors=0
  read -r clamav_infected_files clamav_total_errors < <(
    python3 - <<'PY' "$clamav_summary"
import json
import sys
from pathlib import Path

payload = {}
path = Path(sys.argv[1])
if path.exists():
    with path.open("r", encoding="utf-8") as fh:
        loaded = json.load(fh)
        if isinstance(loaded, dict):
            payload = loaded

print(
    int(payload.get("infected_files", 0)),
    int(payload.get("total_errors", 0)),
)
PY
  )

  if [[ "$clamav_exit" -eq 2 ]] && (( clamav_infected_files == 0 )); then
    echo "⚠️  ClamAV completed with scan errors: ${clamav_total_errors} (threshold=${clamav_max_scan_errors})."
    print_clamav_error_excerpt "$clamav_report" 5
    if (( clamav_total_errors <= clamav_max_scan_errors )); then
      echo "✅ ClamAV soft-pass: no infections detected and scan errors are within threshold."
      return 0
    fi
    echo "❌ ClamAV scan errors exceeded threshold (${clamav_total_errors} > ${clamav_max_scan_errors})."
    exit 1
  fi

  if [[ "$clamav_exit" -eq 1 ]]; then
    echo "⚠️  ClamAV detected infected files."
    return 0
  fi

  if [[ "$clamav_exit" -eq 0 ]]; then
    if (( clamav_total_errors > 0 )); then
      echo "⚠️  ClamAV reported scan errors despite exit 0: ${clamav_total_errors}."
      print_clamav_error_excerpt "$clamav_report" 5
    fi
    return 0
  fi

  echo "❌ ClamAV scan encountered a runtime error (exit code ${clamav_exit})."
  print_clamav_error_excerpt "$clamav_report" 5
  exit 1
}

#R035: Enforce optional AV gate on infected findings and print explicit completion output.
run_clamav_scan "${REPORT_DIR}/clamav.log" "${REPORT_DIR}/clamav-summary.json"
clamav_infected_files="$(python3 - <<'PY' "${REPORT_DIR}/clamav-summary.json"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print(0)
    raise SystemExit(0)

with path.open("r", encoding="utf-8") as fh:
    payload = json.load(fh)

if isinstance(payload, dict):
    print(int(payload.get("infected_files", 0)))
else:
    print(0)
PY
)"

if [[ "$FAIL_ON_INFECTED" == "true" ]] && (( clamav_infected_files > 0 )); then
  echo "❌ Antivirus (AV) gate failed: infected files detected."
  exit 1
fi

echo "✅ Antivirus (AV) checks completed. Reports: ${REPORT_DIR}"
