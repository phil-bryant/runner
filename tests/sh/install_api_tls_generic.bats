#!/usr/bin/env bats
# Self-contained shell unit tests for src/scripts/install_api_tls_generic.sh (generic local-TLS installer golden).

#R001: shard-3 function tag
setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/install_api_tls_generic.sh"
}

@test "sources runbook_common and defaults TLS dir under HOME/.<repo>" {
  #R001-T01: Verify the script sources runbook_common.sh and defaults the TLS directory under $HOME/.<repo>.
  run bash -n "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'source "${SCRIPT_DIR}/runbook_common.sh"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'TLS_DIR="${API_TLS_DIR:-$HOME/.${RUNBOOK_REPO_NAME}}"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "resolves knob-driven label/cert/key and locks the dir to 700" {
  #R005-T01: Verify knob-driven label/cert/key resolution and that the TLS directory is created with 700 permissions.
  run grep -q 'API_TLS_LABEL="${API_TLS_LABEL:-local API}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'TLS_CERT_FILE="${API_TLS_CERT_FILE:-' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'TLS_KEY_FILE="${API_TLS_KEY_FILE:-' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'chmod 700 "$TLS_DIR"' "$SRC"
  [ "$status" -eq 0 ]
}

@test "parses force-regenerate toggle and branches on existing material" {
  #R010-T01: Verify force-regenerate truthy parsing and the unchanged/replace/regenerate decision branches.
  run grep -q 'force_regenerate="${API_TLS_FORCE_REGENERATE:-false}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -Eq '1\|true\|TRUE\|yes\|YES\|on\|ON\) force_regenerate=true' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'TLS cert/key already installed; no changes made' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'Replacing legacy self-signed TLS cert/key' "$SRC"
  [ "$status" -eq 0 ]
}

@test "requires mkcert and generates locked loopback certificates" {
  #R015-T01: Verify the mkcert prerequisite guard, the loopback cert generation command, and the 600 key/cert permissions.
  run grep -q 'command -v mkcert' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'mkcert is required but not available on PATH' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'mkcert -cert-file "$TLS_CERT_FILE" -key-file "$TLS_KEY_FILE" localhost 127.0.0.1 ::1' "$SRC"
  [ "$status" -eq 0 ]
  run grep -q 'chmod 600 "$TLS_CERT_FILE" "$TLS_KEY_FILE"' "$SRC"
  [ "$status" -eq 0 ]
}
