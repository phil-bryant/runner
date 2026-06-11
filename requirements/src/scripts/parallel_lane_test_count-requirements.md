# Parallel Lane Test Count Requirements

## Scope

Applies to `src/scripts/parallel_lane_test_count.py`.

R001  Statement: Resolve the traceability lane count from the engine summary line.
Design: Parse the `Summary: total=N pass=.. fail=..` line of the traceability lane log and return `N`.
Tests:
- R001-T01: Verify the traceability lane returns the `total` from a summary log line.
- R001-T02: Verify traceability summary parser ignores unrelated lines and selects the latest valid summary total.
- R001-T03: Verify traceability parser returns no count when summary formatting is absent or invalid.

R005  Statement: Resolve the shell-unit lane count from bats TAP output.
Design: Sum all bats `1..N` plan lines, falling back to counting `ok` result lines when no plan is present.
Tests:
- R005-T01: Verify the shell-unit lane sums multiple bats TAP plan counts.

R010  Statement: Resolve the python-unit lane count from the pytest summary.
Design: Return `0` for "no tests ran", otherwise sum the outcome counts from the pytest summary line, with a `collected N items` fallback. Generic pytest-based e2e lanes (`*_run_e2e_tests`, excluding the more specific landing-e2e suffix) resolve through the same parser.
Tests:
- R010-T01: Verify the python-unit lane parses the pytest passed-summary count.
- R010-T02: Verify the python-unit lane falls back to `collected N items` when no summary outcome tuple is present.
- R010-T03: Verify a pytest-based e2e lane resolves its total through the pytest parser, including xfailed/xpassed outcomes.

R022  Statement: Resolve SQL-unit lane counts from pg_prove/TAP output.
Design: Prefer pg_prove `Tests=N` summary totals, then TAP plan counts, and finally counted `ok` records when summary/plan lines are absent.
Tests:
- R022-T01: Verify SQL-unit lane total selection prefers `Tests=N` summaries over TAP fallbacks.
- R022-T02: Verify SQL-unit lane falls back to summed TAP plan totals when pg_prove summary lines are absent.
- R022-T03: Verify SQL-unit lane falls back to counted `ok` rows when both summary and TAP plan lines are absent.

R012  Statement: Resolve the swift-unit lane count from XCTest summary output.
Design: Parse XCTest summary lines (`Executed N tests` / `Test run with N tests`) and use the most recent matched total when multiple summaries are present.
Tests:
- R012-T01: Verify the swift-unit lane parses the most recent XCTest summary total.
- R012-T02: Verify trailing `Test run with 0 tests` metadata does not override real executed totals.

R015  Statement: Resolve artifact-summary lane counts from a summary JSON field.
Design: Read an integer count field from a lane summary JSON (fuzz `property_test_count`, mutation `total`) and return it when present.
Tests:
- R015-T01: Verify the fuzz lane reads `property_test_count` from its summary artifact.
- R015-T02: Verify the mutation lane reads `total` from its summary artifact.

R018  Statement: Resolve macOS UI regression lane count from scenario output artifacts.
Design: Prefer the lane timing summary `... over N scenarios`, then fallback to parsing the XCUITest selector line or `artifacts/macos-ui-regression/xcuitest-steps.env`.
Tests:
- R018-T01: Verify the macOS UI regression lane reads the scenario count from the timing summary line.
- R018-T02: Verify selector syntax (`1-3,5,7-8`) expands to a unique selected-step count.
- R018-T03: Verify the steps artifact selector is used when the lane log has no parsable scenario summary/selector line.
- R018-T04: Verify macOS UI regression output with XCTest summaries uses the executed test total.

R020  Statement: Resolve the code-quality lane count from non-skipped sub-check reports.
Design: Count quality sub-check report files that exist and whose content is not exactly `skipped`.
Tests:
- R020-T01: Verify the quality lane counts only non-skipped sub-check reports.

R025  Statement: Resolve security lane counts from log-declared report directories.
Design: Extract the report directory from the lane log `Reports:` line (falling back to a default) and count discovered tool artifact files within it.
Tests:
- R025-T01: Verify the static security lane counts discovered tool artifacts from the report path declared in the log.
- R025-T02: Verify security-lane count falls back to default artifacts path when the log omits a `Reports:` declaration.

R035  Statement: Resolve landing-unit lane counts from the vitest summary.
Design: Parse the most recent vitest `Tests ... (N)` summary line and return the parenthesized grand total.
Tests:
- R035-T01: Verify the landing-unit lane parses the vitest Tests summary total, including mixed failed/passed summaries.

R040  Statement: Resolve landing-e2e lane counts from playwright outcome lines.
Design: Sum the final playwright `N passed`/`N failed`/`N flaky`/`N skipped` outcome lines.
Tests:
- R040-T01: Verify the landing-e2e lane sums playwright outcome line counts.

R045  Statement: Resolve landing-typecheck lane counts from the astro-check result.
Design: Parse the astro-check `Result (N files)` line and return the checked-file count.
Tests:
- R045-T01: Verify the landing-typecheck lane parses the astro-check Result files count.

R030  Statement: Emit a safe single-test fallback for unknown or uncountable lanes.
Design: Print `1` when the lane is unknown or yields a `None`/negative count, otherwise print the resolved count.
Tests:
- R030-T01: Verify an unknown lane falls back to printing `1`.
- R030-T02: Verify an uncountable swift lane log falls back to printing `1`.
- R030-T03: Verify an unparseable macOS UI regression lane log falls back to printing `1`.
- R030-T04: Verify non-positive resolved lane counts are clamped to fallback `1`.
