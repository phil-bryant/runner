# DAST Cleanup Restore Requirements

## Scope

Applies to `src/scripts/dast_cleanup.py`.

R001  Statement: Restore baseline-captured database state in one transactional cleanup sequence.
Design: Restore baseline mutable rows, delete post-baseline inserts, reconcile classifications/categories, and persist operation counts in a summary artifact. Classification reconciliation must use bound SQL parameters (for example `transaction_id = ANY(:baseline_tx_ids)`) instead of dynamic SQL interpolation.
Tests:
- R001-T01: Verify cleanup applies expected delete/restore sequence and writes count metadata on success.

R005  Statement: Refuse unsafe cleanup when baseline profile mismatches active profile.
Design: Compare baseline and active profile names, return `refused` unless `DAST_CLEANUP_FORCE=true`, and emit refusal diagnostics in summary output.
Tests:
- R005-T01: Verify profile mismatch returns non-zero refusal without mutating data unless force override is enabled.

R010  Statement: Handle missing/non-captured baselines as non-fatal skips with diagnostics.
Design: When baseline is missing or not `captured`, write `status=skipped` summary output with explicit reason and exit zero.
Tests:
- R010-T01: Verify missing and skipped-status baselines produce non-fatal summaries with actionable error messages.

R030  Statement: Execute restore/delete reconciliation in one cleanup transaction.
Design: Run `_run_cleanup_transaction` to restore baseline rows and delete post-baseline inserts for matches, audits, categories, and classifications atomically.
Tests:
- R030-T01: Verify a single transaction executes restore/delete sequence and records expected count fields.

R035  Statement: Enforce profile-mismatch refusal safety.
Design: Build mismatch refusal diagnostics and terminate with refused status when baseline profile does not match active profile without override.
Tests:
- R035-T01: Verify profile mismatch path returns refused status with non-zero exit and no cleanup mutation.

R040  Statement: Apply baseline load/skip semantics for unavailable restore input.
Design: Load baseline artifacts and downgrade to skipped status on absent baseline or import/setup errors.
Tests:
- R040-T01: Verify missing/non-captured baseline paths emit skipped status and zero exit.

R045  Statement: Emit and persist cleanup summary artifacts.
Design: Write JSON cleanup summary and stdout status payload with consistent status/count/error fields.
Tests:
- R045-T01: Verify summary artifact and emitted payload are written for applied and failure flows.

## Changelog

- 2026-05-25: Clarified R001 to require bound-parameter SQL for classification reconciliation deletes.
