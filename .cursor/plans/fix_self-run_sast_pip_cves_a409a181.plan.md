---
name: Fix self-run SAST pip CVEs
overview: Make the runner self-test security lane pass by remediating the vulnerable pip baseline in the project venv, then harden self-run defaults so the issue cannot recur. Keep the existing medium-or-higher SAST gate unchanged.
todos:
  - id: harden-static-lane-pip-baseline
    content: Update run_static_security_lane.sh to enforce secure pip baseline on pip-audit target interpreter before scanning.
    status: completed
  - id: align-runner-profile-bootstrap
    content: Fix runner.env bootstrap knobs so self-run profile consistently uses pinned secure pip bootstrap.
    status: completed
  - id: document-self-run-recovery
    content: Update README self-run instructions with secure pip baseline and stale-venv remediation guidance.
    status: completed
  - id: add-regression-test
    content: Add shell unit coverage to prevent regression of vulnerable-pip auditing behavior.
    status: completed
  - id: verify-self-run-green
    content: Re-run t03 and full 11 self-test suite to confirm strict gate passes without suppressions.
    status: completed
isProject: false
---

# Fix self-run SAST pip CVE failure (real remediation)

## What is failing now
- `t03` fails because the SAST summary is entirely driven by `pip-audit` vulnerabilities (`pip_audit_vulnerabilities: 3`, `medium_or_higher_total: 3`) in [`artifacts/security/reports/sast-summary.json`](artifacts/security/reports/sast-summary.json).
- The vulnerable package is `pip==25.3` in the active project venv (see [`artifacts/security/reports/pip-audit.json`](artifacts/security/reports/pip-audit.json)); CVEs require upgrade to `>=26.1`.
- The gate itself is correct and should stay strict ([`tests/py/security/sast_summary_gate.py`](tests/py/security/sast_summary_gate.py)).

## Key code facts to preserve
- The static lane currently runs `pip-audit` against the project interpreter and immediately gates results ([`src/scripts/security/run_static_security_lane.sh`](src/scripts/security/run_static_security_lane.sh)).
- Runner self-run profile currently contains contradictory bootstrap knobs (`LOAD_REQUIREMENTS_BOOTSTRAP_PIP="false"` while pinning `BOOTSTRAP_PIP_VERSION="26.1.2"`) in [`config/runbook/runner.env`](config/runbook/runner.env).
- README self-run flow explicitly expects dependency loading before `11_run_all_self_tests_parallel.sh` ([`README.md`](README.md)).

## Implementation plan
1. **Add secure pip bootstrap in static lane (non-suppressive fix)**
   - Update [`src/scripts/security/run_static_security_lane.sh`](src/scripts/security/run_static_security_lane.sh) to enforce a minimum secure pip version on the `pip-audit` target interpreter before scanning.
   - Use existing bootstrap knobs (`BOOTSTRAP_PIP_VERSION`, `BOOTSTRAP_PIP_SHA256`) and hash-verified install path where possible, so this is an auditable remediation step rather than an unpinned silent upgrade.
   - Keep policy behavior untouched: scanner findings still fail gate; we only remove known vulnerable `pip` from the scanned environment.

2. **Make runner self-run profile deterministic**
   - Update [`config/runbook/runner.env`](config/runbook/runner.env) so the self-run profile consistently enables pinned pip bootstrap (`LOAD_REQUIREMENTS_BOOTSTRAP_PIP="true"`) and avoids contradictory fallback behavior.
   - Ensure profile comments match actual behavior to prevent future drift.

3. **Document the secure baseline workflow**
   - Update [`README.md`](README.md) self-run section to explicitly state the expected secure pip bootstrap step and stale-venv recovery path (re-run load requirements before self-test when needed).
   - Keep guidance aligned with existing no-cheating policy (no gate downgrades, no suppressions).

4. **Add regression coverage**
   - Add/extend shell unit tests under [`tests/sh`](tests/sh) (executed by [`src/scripts/run_unit_test_lanes.sh`](src/scripts/run_unit_test_lanes.sh)) to verify the static lane enforces secure pip baseline before `pip-audit` execution.
   - Include a test that fails if the lane regresses to auditing a vulnerable pip without remediation.

## Validation after changes
- Run `./tests/t03_run_static_security_tests.sh` and verify `gate_failed: false` in `artifacts/security/reports/sast-summary.json` with no medium+ findings from pip baseline.
- Run `./11_run_all_self_tests_parallel.sh` and verify all 5 self lanes pass.
- Confirm no gate policy variables were weakened and no scanner suppressions were introduced.
