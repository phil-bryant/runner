# Check Teller API Version Freshness Requirements

## Scope

Applies to `src/scripts/check_teller_api_version_freshness.py`.

R001  Statement: Discover latest Teller API version from configured HTTPS metadata sources.
Design: Query configured docs/OpenAPI endpoints over HTTPS, parse version metadata, and record source-specific warnings when extraction fails.
Tests:
- R001-T01: Verify `discover_version` falls back across configured sources and preserves warning context for invalid responses.
- R001-T02: Verify source iteration across docs/OpenAPI endpoints accumulates parse/fetch warnings when no latest version is discoverable.

R005  Statement: Support authenticated dashboard-derived version state when 1psa credentials are configured.
Design: Optionally authenticate to the Teller dashboard using 1psa credentials/OTP, parse current/latest dashboard versions, and report explicit dashboard-check status.
Tests:
- R005-T01: Verify dashboard login/MFA parsing and OTP credential error handling update dashboard status fields correctly.
- R005-T02: Verify OTP parsing helpers handle digit extraction and invalid otpauth payloads.
- R005-T03: Verify dashboard latest-version helpers and standardized error payload generation.
- R005-T04: Verify dashboard discovery handles missing 1psa configuration/binary and missing credentials.
- R005-T05: Verify dashboard login and MFA submit helpers return deterministic success/error payloads.
- R005-T06: Verify authenticated dashboard flow handles login-page fetch, csrf extraction, and MFA-required branches.
- R005-T07: Verify MFA completion and parsed-version applier branches cover csrf/mfa-failure and parse-miss outcomes.
- R005-T08: Verify 1psa field reader supports password fast-path, fallback field read, and command failure behavior.

R010  Statement: Normalize semver/date-style version values and compare drift status.
Design: Parse version strings into comparable triplets and compute deterministic equality/ordering outcomes for gate logic.
Tests:
- R010-T01: Verify `parse_semver` and `compare_versions` produce consistent equal/newer/older outcomes for dated-version inputs.
- R010-T02: Verify helper compare/source-resolution branches cover fallback source configuration and invalid version inputs.
- R010-T03: Verify drift/newer-available computation handles unknown/latest/missing-baseline branches.

R030  Statement: Retrieve JSON/text metadata from HTTPS sources, including cookie-opener fetch flows.
Design: Enforce HTTPS-only retrieval for version sources and support opener-based authenticated text fetches with parseable error messages.
Tests:
- R030-T01: Verify HTTPS metadata fetch paths (`fetch_json`, `fetch_text`, opener-backed fetch) return payloads/errors for valid and invalid source responses.
- R030-T02: Verify fetch helpers cover requests-missing and network-error branches for JSON/text metadata retrieval.
- R030-T03: Verify JSON/text fetch helpers reject invalid JSON payloads and non-HTTPS source schemes.

R035  Statement: Assemble and render version freshness drift/gate reports.
Design: Build a normalized report payload with dashboard/source status and warnings, then render a stable text summary for artifacts/stdout.
Tests:
- R035-T01: Verify `build_report` and `format_report` include expected status, source, warning, and drift fields.

R040  Statement: Enforce CLI artifact writing and fail-on-new gate exit behavior.
Design: Parse CLI options, write JSON/text artifacts, and exit non-zero only when fail-on-new is enabled and drift is detected.
Tests:
- R040-T01: Verify CLI `main` writes both artifacts and returns non-zero only for fail-on-new gate failures.
