# ZAP Summary Parser Requirements

## Scope

Applies to `tests/py/security/zap_summary_parser.py`.

R001  Statement: Risk counts are extracted from ZAP summary content with safe defaults.
Design: `extract_count` parses risk-class count cells from summary content and returns zero when absent.
Tests:
- R001-T01: Verify count extraction returns parsed values and defaults to zero for missing entries.

R005  Statement: CLI parsing emits summary JSON and writes report output.
Design: `main` reads the input report, computes risk totals, writes summary JSON, and returns a success exit code.
Tests:
- R005-T01: Verify CLI summary parsing writes expected counts and total output.
