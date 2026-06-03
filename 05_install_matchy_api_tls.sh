#!/usr/bin/env bash
umask 007
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#R001: Operate on the target repo (rNN_ pointer sets RUNBOOK_REPO_ROOT); default to self.
SCRIPT_DIR="${RUNBOOK_REPO_ROOT:-$SCRIPT_DIR}"
cd "$SCRIPT_DIR"

#R001: Install local TLS cert/key material for the Matchy-compatible Mailcart API.
TLS_DIR="${MAILCART_MATCHY_TLS_DIR:-$HOME/.mailcart}"
TLS_CERT_FILE="${MAILCART_MATCHY_TLS_CERT_FILE:-$TLS_DIR/matchy-localhost-cert.pem}"
TLS_KEY_FILE="${MAILCART_MATCHY_TLS_KEY_FILE:-$TLS_DIR/matchy-localhost-key.pem}"

echo "▶ Checking local Matchy API TLS materials"
echo "  cert: ${TLS_CERT_FILE}"
echo "  key : ${TLS_KEY_FILE}"

mkdir -p "$TLS_DIR"
chmod 700 "$TLS_DIR"

cert_is_self_signed() {
  local meta unique_count
  meta="$(openssl x509 -in "$TLS_CERT_FILE" -noout -subject -issuer 2>/dev/null || true)"
  unique_count="$(printf '%s\n' "$meta" | sort -u | wc -l | tr -d ' ')"
  [[ "$unique_count" == "1" ]]
}

#R005: Respect force-regenerate toggle for replacing existing TLS materials.
force_regenerate="${MAILCART_MATCHY_TLS_FORCE_REGENERATE:-false}"
case "$force_regenerate" in
  1|true|TRUE|yes|YES|on|ON) force_regenerate=true ;;
  *) force_regenerate=false ;;
esac

if [[ -s "$TLS_CERT_FILE" && -s "$TLS_KEY_FILE" ]]; then
  if [[ "$force_regenerate" == "true" ]]; then
    echo "ℹ️  Regenerating TLS cert/key (MAILCART_MATCHY_TLS_FORCE_REGENERATE=true)."
    rm -f "$TLS_CERT_FILE" "$TLS_KEY_FILE"
  elif cert_is_self_signed; then
    echo "ℹ️  Replacing legacy self-signed TLS cert/key with mkcert-trusted material."
    rm -f "$TLS_CERT_FILE" "$TLS_KEY_FILE"
  else
    echo "✅ TLS cert/key already installed; no changes made."
    exit 0
  fi
fi

echo "▶ Generating local Matchy API TLS materials"

#R010: Require mkcert to generate trusted localhost TLS cert/key files.
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
