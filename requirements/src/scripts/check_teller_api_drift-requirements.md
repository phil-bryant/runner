# Check Teller API Drift Requirements

## Scope

Applies to `src/scripts/check_teller_api_drift.py`.

R001  Statement: Resolve Teller credentials with predictable local-token fallback behavior.
Design: Prefer explicit environment credentials, otherwise discover `~/.teller/auth_token*.json` candidates, support suffix filtering, and surface ambiguity warnings.
Tests:
- R001-T01: Verify default discovery, institution filtering, and run-all-token candidate expansion behavior.

R005  Statement: Execute live canary checks when credentials are available and degrade safely when they are not.
Design: Run `/institutions` plus authenticated `/accounts` and `/identity` checks with mTLS/auth when available; return fallback mode with actionable warnings when dependencies or credentials are missing.
Tests:
- R005-T01: Verify live and fallback decision logic emits expected check lists and warning states.

R010  Statement: Persist API drift smoke artifacts and fail only on hard check failures.
Design: Write JSON/text reports with mode/status/checks metadata and return non-zero only when status is `fail`.
Tests:
- R010-T01: Verify report persistence and process exit behavior for passing, warning, and failing scenarios.

R015  Statement: Support strict live-canary execution mode for scheduled compatibility gates.
Design: `--require-live` fails when live canary cannot run and fallback mode is used; `--fail-on-warn` promotes warning status to a non-zero exit to force remediation in strict live lanes.
Tests:
- R015-T01: Verify `--require-live` returns non-zero when run falls back.
- R015-T02: Verify `--fail-on-warn` returns non-zero when report status is warn.

R030  Statement: Read credential inputs and resolve Teller auth material.
Design: Read text/token files, discover candidate local tokens, resolve cert/key defaults, filter/select candidates, and return normalized credential payloads.
Tests:
- R030-T01: Verify credential resolution selects the expected local token candidate and metadata when multiple token sources exist (`tests/py/test_check_teller_api_drift.py`).

R035  Statement: Execute authenticated live Teller canary drift checks.
Design: Execute live endpoint checks (including authenticated checks) and collect source/live check statuses that determine pass/warn/fail outcomes.
Tests:
- R035-T01: Verify live canary checks mark drift failures when endpoint checks return non-200 responses (`tests/py/test_check_teller_api_drift.py`).

R040  Statement: Run fallback drift checks when live mode is unavailable.
Design: Emit fallback-mode result payloads and validate required local docs/source endpoint markers when live checks cannot run.
Tests:
- R040-T01: Verify fallback mode returns expected warning/failure status when live execution prerequisites are unavailable (`tests/py/test_check_teller_api_drift.py`).

R045  Statement: Render reports and enforce CLI gate exits for drift checks.
Design: Parse CLI options, render deterministic text output, persist artifacts, and enforce gate flags for fail/warn/live-required conditions.
Tests:
- R045-T01: Verify CLI report generation and gate exits return expected status for warning/failure scenarios (`tests/py/test_check_teller_api_drift.py`).
