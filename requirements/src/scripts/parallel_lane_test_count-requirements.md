# Parallel Lane Test Count Requirements

## Scope

Applies to `src/scripts/parallel_lane_test_count.py`.

R001  Statement: Resolve the traceability lane count from the engine summary line.
Design: Parse the `Summary: total=N pass=.. fail=..` line of the traceability lane log and return `N`.
Tests:
- R001-T01: Verify the traceability lane returns the `total` from a summary log line.

R005  Statement: Resolve the shell-unit lane count from bats TAP output.
Design: Sum all bats `1..N` plan lines, falling back to counting `ok` result lines when no plan is present.
Tests:
- R005-T01: Verify the shell-unit lane sums multiple bats TAP plan counts.

R010  Statement: Resolve the python-unit lane count from the pytest summary.
Design: Return `0` for "no tests ran", otherwise sum the outcome counts from the pytest summary line, with a `collected N items` fallback.
Tests:
- R010-T01: Verify the python-unit lane parses the pytest passed-summary count.

R015  Statement: Resolve artifact-summary lane counts from a summary JSON field.
Design: Read an integer count field from a lane summary JSON (fuzz `property_test_count`, mutation `total`) and return it when present.
Tests:
- R015-T01: Verify the fuzz lane reads `property_test_count` from its summary artifact.

R020  Statement: Resolve the code-quality lane count from non-skipped sub-check reports.
Design: Count quality sub-check report files that exist and whose content is not exactly `skipped`.
Tests:
- R020-T01: Verify the quality lane counts only non-skipped sub-check reports.

R025  Statement: Resolve security lane counts from log-declared report directories.
Design: Extract the report directory from the lane log `Reports:` line (falling back to a default) and count discovered tool artifact files within it.
Tests:
- R025-T01: Verify the static security lane counts discovered tool artifacts from the report path declared in the log.

R030  Statement: Emit a safe single-test fallback for unknown or uncountable lanes.
Design: Print `1` when the lane is unknown or yields a `None`/negative count, otherwise print the resolved count.
Tests:
- R030-T01: Verify an unknown lane falls back to printing `1`.
