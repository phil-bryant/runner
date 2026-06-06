# Check Teller API Version Freshness Requirements

## Scope

Applies to `src/scripts/check_teller_api_version_freshness.py`.

R001  Statement: Discover latest Teller API version from configured HTTPS metadata sources.
Design: Query configured docs/OpenAPI endpoints over HTTPS, parse version metadata, and record source-specific warnings when extraction fails.
Tests:
- R001-T01: Verify `discover_version` falls back across configured sources and preserves warning context for invalid responses.

R005  Statement: Support authenticated dashboard-derived version state when 1psa credentials are configured.
Design: Optionally authenticate to the Teller dashboard using 1psa credentials/OTP, parse current/latest dashboard versions, and report explicit dashboard-check status.
Tests:
- R005-T01: Verify dashboard login/MFA parsing and OTP credential error handling update dashboard status fields correctly.

R010  Statement: Normalize semver/date-style version values and compare drift status.
Design: Parse version strings into comparable triplets and compute deterministic equality/ordering outcomes for gate logic.
Tests:
- R010-T01: Verify `parse_semver` and `compare_versions` produce consistent equal/newer/older outcomes for dated-version inputs.

R030  Statement: Retrieve JSON/text metadata from HTTPS sources, including cookie-opener fetch flows.
Design: Enforce HTTPS-only retrieval for version sources and support opener-based authenticated text fetches with parseable error messages.
Tests:
- R030-T01: Verify HTTPS metadata fetch paths (`fetch_json`, `fetch_text`, opener-backed fetch) return payloads/errors for valid and invalid source responses.

R035  Statement: Assemble and render version freshness drift/gate reports.
Design: Build a normalized report payload with dashboard/source status and warnings, then render a stable text summary for artifacts/stdout.
Tests:
- R035-T01: Verify `build_report` and `format_report` include expected status, source, warning, and drift fields.

R040  Statement: Enforce CLI artifact writing and fail-on-new gate exit behavior.
Design: Parse CLI options, write JSON/text artifacts, and exit non-zero only when fail-on-new is enabled and drift is detected.
Tests:
- R040-T01: Verify CLI `main` writes both artifacts and returns non-zero only for fail-on-new gate failures.
