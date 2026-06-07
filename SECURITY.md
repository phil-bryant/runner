# Runner Security Policy

## Scope

This repository provides the shared runbook engine used by sibling repositories to run prerequisite checks, security lanes, test lanes, and restore/deploy automation.

Security expectations focus on:

- Safe execution of shell/python automation on developer machines and CI workers.
- Secret handling through 1Password CLI (`1psa`) and explicit environment fallbacks.
- Supply-chain integrity for Python lockfiles and generated SBOM artifacts.

## Supported Branches

Security fixes are applied to the active development branch used for release readiness.

## Reporting Security Issues

For any suspected vulnerability in runner scripts, lane orchestration, or secret handling:

1. Do not open a public issue containing exploit details.
2. Contact the maintainer directly through the existing private maintainer channel.
3. Include:
   - script path(s),
   - minimal reproduction steps,
   - impact assessment,
   - any temporary mitigation.

## Security Gates

The baseline security gate is the static security lane:

- `tests/t03_run_static_security_tests.sh`

This lane enforces:

- Semgrep, Bandit, pip-audit, detect-secrets, gitleaks, Ruff, and ShellCheck.
- Centralized severity gating via `tests/py/security/sast_summary_gate.py`.
- Hash-pinned dependency requirements for security tooling.

## Known Temporary Exceptions

Temporary vulnerability ignores must be documented with owner and review-by date in:

- `docs/security/dependency-vuln-exceptions.md`
