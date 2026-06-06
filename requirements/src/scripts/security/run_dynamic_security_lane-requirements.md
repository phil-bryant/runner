# Dynamic Security Lane Requirements

## Scope

Applies to `src/scripts/security/run_dynamic_security_lane.sh`.

R001  Statement: Print an explicit startup banner before DAST orchestration.
Design: Define `print_tool_header` to render a bordered per-tool intro banner used before DAST scanners run.
Tests:
- R001-T01: Verify the lane defines a `print_tool_header` banner helper.

R005  Statement: Resolve the repo root and execute under strict shell settings.
Design: Run with `set -euo pipefail` and call `security_init_repo_root` to operate from the resolved repository root.
Tests:
- R005-T01: Verify strict-mode shell settings and `security_init_repo_root` invocation.

R010  Statement: Bootstrap an isolated security toolchain venv for DAST dependencies.
Design: Create a dedicated `python3 -m venv` security environment before DAST scanners run.
Tests:
- R010-T01: Verify the lane creates an isolated security venv.

R015  Statement: Default to DAST-on, SAST-off lane behavior.
Design: Default `RUN_DAST=true` and `RUN_SAST=false` so the dynamic lane runs DAST by default.
Tests:
- R015-T01: Verify the `RUN_DAST`/`RUN_SAST` default toggles.

R020  Statement: Print completion markers and the report artifact location.
Design: Emit DAST and overall completion messages that include the resolved report directory.
Tests:
- R020-T01: Verify the lane prints completion markers with the report path.

R025  Statement: Capture a baseline and execute cleanup to avoid DB state leakage.
Design: Capture a pre-run database baseline via `dast_baseline.py`, register an EXIT trap, and restore/clean it via `dast_cleanup.py` after the run.
Tests:
- R025-T01: Verify the lane captures a baseline and registers a cleanup EXIT trap.

R030  Statement: Parse the ZAP summary and enforce a configurable severity threshold gate.
Design: Parse the ZAP classification summary and fail the lane when findings meet/exceed `SECURITY_ZAP_FAIL_THRESHOLD`.
Tests:
- R030-T01: Verify the lane parses the ZAP summary and enforces the configurable threshold gate.

R035  Statement: Treat Schemathesis findings as blocking by default.
Design: Schemathesis findings are blocking unless explicitly downgraded via the fail-on-findings toggle.
Tests:
- R035-T01: Verify Schemathesis findings are blocking by default.

R040  Statement: Prevent the Mailcart stub from colliding with the DAST API host:port.
Design: When the stub host/port matches the API host/port, auto-select a non-colliding available port.
Tests:
- R040-T01: Verify the lane resolves a non-colliding Mailcart stub port when it matches the API.

R045  Statement: Run Schemathesis from the report directory to keep `.schemathesis` out of the repo root.
Design: Execute the Schemathesis subprocess with its working directory set to the report directory.
Tests:
- R045-T01: Verify the Schemathesis subprocess runs with the report directory as its working directory.

R050  Statement: Redact persisted Schemathesis token-bearing artifacts.
Design: Use `redact_secret_in_file`/`redact_secret_in_place` to persist only token-redacted Schemathesis logs and JUnit output.
Tests:
- R050-T01: Verify token-bearing Schemathesis artifacts are redacted before persistence.

R055  Statement: Enforce hash-pinned security requirements for toolchain reinstall.
Design: Reinstall the security toolchain with `pip install --require-hashes --force-reinstall -r <security requirements>`.
Tests:
- R055-T01: Verify the toolchain reinstall uses `--require-hashes`.
