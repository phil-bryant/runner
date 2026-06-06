# Category Integrity Check Requirements

## Scope

Applies to `tests/py/security/category_integrity_check.py`.

R001  Statement: Parse canonical seed SQL into deterministic seed bounds.
Design: Parse canonical seed SQL `VALUES` blocks and derive expected seed row count bounds for integrity checks.
Tests:
- R001-T01: Verify canonical seed parser fails clearly when the expected SQL block is missing or empty.

R005  Statement: Emit deterministic category integrity report artifacts.
Design: Build a base report payload, persist report JSON artifacts, and include strict-mode/runtime diagnostics for operational triage.
Tests:
- R005-T01: Verify base-report and write-report paths emit deterministic artifact structure and status fields.

R010  Statement: Evaluate integrity invariants and enforce strict/non-strict gate behavior.
Design: Append invariant results, serialize invariant sample rows, and set gate exit status based on strict-mode policy.
Tests:
- R010-T01: Verify invariant failures drive strict vs non-strict gate behavior and final status fields.
