# DAST Baseline Snapshot Requirements

## Scope

Applies to `src/scripts/dast_baseline.py`.

R001  Statement: Capture a baseline snapshot of mutable DAST-affected database tables.
Design: Record baseline maxima and full mutable-row snapshots for `nys_snw_category`, `transaction_email_match`, and `transaction_nys_snw_category` with profile metadata.
Tests:
- R001-T01: Verify baseline payload structure includes profile details, maxima, and table snapshot arrays.

R005  Statement: Degrade safely when database dependencies are unavailable.
Design: On import/setup failure, write a `status=skipped` payload with reason metadata instead of failing hard.
Tests:
- R005-T01: Simulate database import failure and verify skipped payload generation with explanatory reason text.

R010  Statement: Emit operator-readable baseline summary output.
Design: Print concise JSON summary with captured counts and output path after successful snapshot write.
Tests:
- R010-T01: Verify successful run emits summary JSON including status, profile, and table count fields.

R030  Statement: Serialize baseline rows and datetimes into JSON-safe payload values.
Design: Convert DB row values through stable serialization helpers (`_iso`, `_serialize_row`) before writing artifacts.
Tests:
- R030-T01: Verify datetime/row serialization helpers produce stable JSON-safe baseline row payloads.

R035  Statement: Capture baseline artifacts with skip degradation and summary emission.
Design: Orchestrate baseline capture end-to-end, degrading to skipped on unavailable dependencies and emitting status summary output.
Tests:
- R035-T01: Verify `main` writes captured/skip artifacts and emits expected summary status fields.
- R035-T02: Verify invalid CLI invocation returns usage exit code.
- R035-T03: Verify captured baseline path records maxima and row snapshots for all mutable tables.
