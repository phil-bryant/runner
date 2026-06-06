# Generic Local API TLS Installer Requirements

## Scope

Applies to `src/scripts/install_api_tls_generic.sh`.

R001  Statement: Establish the runner/repo contract with TLS material stored outside the repo.
Design: Source `runbook_common.sh` for the `RUNNER_HOME`/`RUNBOOK_REPO_ROOT` contract and default TLS material under a per-repo dotfile directory in `$HOME`.
Tests:
- R001-T01: Verify the script sources `runbook_common.sh` and defaults the TLS directory under `$HOME/.<repo>`.

R005  Statement: Drive install location and labelling from profile knobs.
Design: Resolve `API_TLS_LABEL`, `API_TLS_DIR`, `API_TLS_CERT_FILE`, and `API_TLS_KEY_FILE` from knobs, create the directory with `700` permissions, and echo the resolved cert/key paths.
Tests:
- R005-T01: Verify knob-driven label/cert/key resolution and that the TLS directory is created with `700` permissions.

R010  Statement: Respect a force-regenerate toggle and keep good existing material by default.
Design: Parse `API_TLS_FORCE_REGENERATE` truthy values; when valid cert/key already exist, regenerate on force, replace legacy self-signed material, otherwise exit unchanged.
Tests:
- R010-T01: Verify force-regenerate truthy parsing and the unchanged/replace/regenerate decision branches.

R015  Statement: Require mkcert and generate locally-trusted loopback certificates.
Design: Fail with guidance when `mkcert` is absent; otherwise generate a cert/key for `localhost 127.0.0.1 ::1` and lock both files to `600` permissions.
Tests:
- R015-T01: Verify the mkcert prerequisite guard, the loopback cert generation command, and the `600` key/cert permissions.
