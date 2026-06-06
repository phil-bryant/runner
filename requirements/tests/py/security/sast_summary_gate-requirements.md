# SAST Summary Gate Requirements

## Scope

Applies to `tests/py/security/sast_summary_gate.py`.

R001  Statement: Load scanner artifact JSON payloads from report directory inputs.
Design: Read required scanner JSON artifacts from the supplied report directory and expose normalized payloads for aggregation.
Tests:
- R001-T01: Verify scanner artifact loader handles required report files and returns parsed JSON payloads.

R005  Statement: Normalize pip-audit payload variants into vulnerability counts.
Design: Accept list-style, dependency-style, and direct-vuln pip-audit payload variants and count vulnerabilities consistently.
Tests:
- R005-T01: Verify pip-audit counter normalizes multiple payload shapes into expected totals.

R010  Statement: Aggregate severities, write summary JSON, and enforce policy gate exits.
Design: Compute medium/high aggregates across scanners, persist `sast-summary.json`, and return policy-gated exit codes by mode.
Tests:
- R010-T01: Verify summary aggregation and policy-mode gate exit behavior for clean and failing finding sets.
