# Check PostgreSQL Freshness Requirements

## Scope

Applies to `src/scripts/check_postgres_freshness.py`.

R020  Statement: Collect PostgreSQL client/server freshness data with policy-aware gating.
Design: Discover client version via `psql --version`, optionally query server version, and evaluate minimum-version policies with a stale-component summary.
Tests:
- R020-T01: Verify client/server version parsing and stale-component gating for compliant and non-compliant versions.

R025  Statement: Evaluate CVE exposure using snapshot and policy inputs.
Design: Load snapshot/policy payloads, evaluate affected version ranges for client/server scopes, and mark gate failures when configured policy is violated.
Tests:
- R025-T01: Verify CVE matching, severity thresholds, stale snapshot handling, and fail-on-CVE behavior.

R030  Statement: Parse and normalize PostgreSQL version/severity data for gating.
Design: Parse client/server versions, normalize severity labels/scores, parse timestamps, and derive scoped version metadata for policy evaluation.
Tests:
- R030-T01: Verify version parsing/normalization produces expected comparable values for semantic and server-version inputs (`tests/py/test_check_postgres_freshness.py`).

R035  Statement: Evaluate affected-version range expressions against installed versions.
Design: Parse constraint/range expressions and detect whether client/server versions fall within any affected vulnerability ranges.
Tests:
- R035-T01: Verify version-range evaluation correctly matches and rejects boundary version cases (`tests/py/test_check_postgres_freshness.py`).

R040  Statement: Discover client/server version state through command probes.
Design: Build server-version probe commands, run command probes with timeout handling, and populate client/server freshness status payloads.
Tests:
- R040-T01: Verify server version query flow populates parsed server version and freshness status fields (`tests/py/test_check_postgres_freshness.py`).

R045  Statement: Load, refresh, and freshness-evaluate CVE snapshot data.
Design: Load snapshot/policy JSON, fetch/parse PostgreSQL security data when refreshing, and apply snapshot freshness policy semantics.
Tests:
- R045-T01: Verify snapshot refresh/load decision logic recognizes changed payloads and freshness metadata behavior (`tests/py/test_check_postgres_freshness.py`).

R050  Statement: Match CVE entries to installed versions and summarize findings.
Design: Validate CVE entries, evaluate component/range matches for client/server versions, and merge vulnerability findings into overall summary state.
Tests:
- R050-T01: Verify CVE gate fails when installed versions match affected ranges above threshold (`tests/py/test_check_postgres_freshness.py`).

R055  Statement: Apply CVE policy thresholds and gate-failure semantics.
Design: Load CVE policy configuration, normalize policy payload fields, and mark policy-failed status when stale-snapshot or threshold rules require failure.
Tests:
- R055-T01: Verify CVE policy loading and gate-failed flags honor configured stale-snapshot and threshold policy values (`tests/py/test_check_postgres_freshness.py`).

R060  Statement: Build and render PostgreSQL freshness report output.
Design: Assemble report lines from client/server/CVE payloads and render deterministic text output including stale/warning summaries.
Tests:
- R060-T01: Verify formatted report output contains expected summary fields and warning sections (`tests/py/test_check_postgres_freshness.py`).

R065  Statement: Enforce CLI artifact writing and final gate exit behavior.
Design: Parse CLI options, write JSON/text artifacts, and return non-zero only when summary gate failure status is true.
Tests:
- R065-T01: Verify CLI run writes artifacts and exits with gate-driven status code (`tests/py/test_check_postgres_freshness.py`).
