# Dependency Vulnerability Exceptions

This file tracks time-bounded vulnerability ignores that are temporarily required to keep the security lane operational.

## Active Exceptions

### PyJWT Constraint Compatibility (Semgrep rulepack constraint)

- **Affected gate variable**: `PIP_AUDIT_IGNORE_VULNS` in `src/scripts/security/run_static_security_lane.sh`
- **Ignored IDs**:
  - `CVE-2026-48522`
  - `CVE-2026-48524`
  - `CVE-2026-48525`
  - `CVE-2026-48526`
- **Reason**: Current Semgrep security bundle compatibility keeps PyJWT on a constrained major in this lane.
- **Owner**: runner maintainer
- **Review-by date**: 2026-09-30
- **Removal condition**: upgrade path validated and ignores removed from `PIP_AUDIT_IGNORE_VULNS`.
