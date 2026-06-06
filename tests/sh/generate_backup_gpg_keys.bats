#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  SRC="${REPO_ROOT}/src/scripts/security/generate_backup_gpg_keys.sh"
}

@test "script defines strict mode and rejects unknown args" {
  #R001-T01: Verify the script declares strict shell mode and exits non-zero for unknown arguments (`tests/sh/generate_backup_gpg_keys.bats`).
  run grep 'set -euo pipefail' "$SRC"
  [ "$status" -eq 0 ]

  run bash "$SRC" --not-a-real-flag
  [ "$status" -eq 2 ]
}

@test "script exposes expected customization flags and env defaults" {
  #R005-T01: Verify the script includes all supported customization flags and corresponding default env vars (`tests/sh/generate_backup_gpg_keys.bats`).
  run grep 'OUTPUT_DIR="\${OUTPUT_DIR:-\./artifacts/security/backup-gpg}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep 'KEY_NAME="\${BACKUP_GPG_KEY_NAME:-Teller Postgres Backup Encryption}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep 'KEY_EMAIL="\${BACKUP_GPG_KEY_EMAIL:-backup-encryption@local.invalid}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep 'KEY_EXPIRY="\${BACKUP_GPG_KEY_EXPIRY:-1y}"' "$SRC"
  [ "$status" -eq 0 ]
  run grep -- '--output-dir' "$SRC"
  [ "$status" -eq 0 ]
  run grep -- '--name' "$SRC"
  [ "$status" -eq 0 ]
  run grep -- '--email' "$SRC"
  [ "$status" -eq 0 ]
  run grep -- '--expiry' "$SRC"
  [ "$status" -eq 0 ]
}

@test "script enforces non-empty passphrase handling" {
  #R010-T01: Verify the script contains explicit non-empty passphrase enforcement and mismatch failure handling (`tests/sh/generate_backup_gpg_keys.bats`).
  run grep 'Passphrase confirmation did not match' "$SRC"
  [ "$status" -eq 0 ]
  run grep 'Passphrase must be non-empty' "$SRC"
  [ "$status" -eq 0 ]
}

@test "script contains key generation, export, metadata and guidance output" {
  #R015-T01: Verify the script includes key generation, armored export, metadata output, and 1psa/.env guidance emission (`tests/sh/generate_backup_gpg_keys.bats`).
  run grep -- '--quick-gen-key' "$SRC"
  [ "$status" -eq 0 ]
  run grep -- '--export-secret-keys' "$SRC"
  [ "$status" -eq 0 ]
  run grep 'fingerprint=\${KEY_FINGERPRINT}' "$SRC"
  [ "$status" -eq 0 ]
  run grep '1psa item: POSTGRES_BACKUP_ENCRYPTION' "$SRC"
  [ "$status" -eq 0 ]
  run grep '.env fallback variables:' "$SRC"
  [ "$status" -eq 0 ]
}
