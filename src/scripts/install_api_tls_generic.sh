#!/usr/bin/env bash
umask 007
set -euo pipefail

# Generic, knob-driven local-TLS installer golden. Per-repo NN_ pointers set the
# API_TLS_* knobs from their profile and exec this wrapper. Replaces the previously
# duplicated 05_install_classifier_api_tls.sh / 05_install_matchy_api_tls.sh goldens.

#R001: Establish RUNNER_HOME / RUNBOOK_REPO_ROOT contract (TLS material lives outside the repo).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/runbook_common.sh"

#R005: Profile knobs select where TLS material is installed and how it is labelled.
API_TLS_LABEL="${API_TLS_LABEL:-local API}"
TLS_DIR="${API_TLS_DIR:-$HOME/.${RUNBOOK_REPO_NAME}}"
TLS_CERT_FILE="${API_TLS_CERT_FILE:-$TLS_DIR/${RUNBOOK_REPO_NAME}-localhost-cert.pem}"
TLS_KEY_FILE="${API_TLS_KEY_FILE:-$TLS_DIR/${RUNBOOK_REPO_NAME}-localhost-key.pem}"

echo "▶ Checking local ${API_TLS_LABEL} TLS materials"
echo "  cert: ${TLS_CERT_FILE}"
echo "  key : ${TLS_KEY_FILE}"

mkdir -p "$TLS_DIR"
chmod 700 "$TLS_DIR"

#R001: function tag for cert_is_self_signed
cert_is_self_signed() {
  local meta unique_count
  meta="$(openssl x509 -in "$TLS_CERT_FILE" -noout -subject -issuer 2>/dev/null || true)"
  unique_count="$(printf '%s\n' "$meta" | sort -u | wc -l | tr -d ' ')"
  [[ "$unique_count" == "1" ]]
}

#R010: Respect a force-regenerate toggle for replacing existing TLS materials.
force_regenerate="${API_TLS_FORCE_REGENERATE:-false}"
case "$force_regenerate" in
  1|true|TRUE|yes|YES|on|ON) force_regenerate=true ;;
  *) force_regenerate=false ;;
esac

#R010: Keep existing mkcert-generated cert decisions by default.
if [[ -s "$TLS_CERT_FILE" && -s "$TLS_KEY_FILE" ]]; then
  if [[ "$force_regenerate" == "true" ]]; then
    echo "ℹ️  Regenerating TLS cert/key (API_TLS_FORCE_REGENERATE=true)."
    rm -f "$TLS_CERT_FILE" "$TLS_KEY_FILE"
  elif cert_is_self_signed; then
    echo "ℹ️  Replacing legacy self-signed TLS cert/key with mkcert-trusted material."
    rm -f "$TLS_CERT_FILE" "$TLS_KEY_FILE"
  else
    echo "✅ TLS cert/key already installed; no changes made."
    exit 0
  fi
fi

echo "▶ Generating local ${API_TLS_LABEL} TLS materials"

#R015: Require mkcert for locally-trusted certificate generation.
if ! command -v mkcert >/dev/null 2>&1; then
  echo "❌ mkcert is required but not available on PATH."
  echo "Run ./01_install_prerequisites.sh first, then rerun this script."
  exit 1
fi

#R015: Generate cert/key for localhost loopback names and lock file permissions.
mkcert -install >/dev/null 2>&1 || true
mkcert -cert-file "$TLS_CERT_FILE" -key-file "$TLS_KEY_FILE" localhost 127.0.0.1 ::1
chmod 600 "$TLS_CERT_FILE" "$TLS_KEY_FILE"
echo "✅ Generated locally-trusted TLS cert/key via mkcert."
