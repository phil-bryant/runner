# Runner Threat Model

## System Role

Runner is a local-first orchestration engine that delegates repeatable shell and python gates into component repos. It runs prerequisite installation, dependency setup, SAST/DAST lanes, and DB lifecycle scripts.

## Trust Boundaries

1. **Repo Inputs**: shell/python sources from the active repository checkout.
2. **Secrets Boundary**: credentials resolved from `1psa`, with optional explicit `.env` fallback.
3. **Execution Boundary**: subprocess calls to local binaries (`psql`, `gitleaks`, `semgrep`, `pip-audit`, `cosign`, etc.).
4. **Network Boundary**: optional calls to package indexes, CVE feeds, and DAST targets.

## Key Threats And Mitigations

### Command Injection In Shell Automation

- Mitigations:
  - strict shell mode (`set -euo pipefail`) in executable lanes.
  - quoted argument passing and constrained helper wrappers.
  - ShellCheck in static security lane, including `src/scripts/**/*.sh`.

### Unsafe Python Subprocess Usage

- Mitigations:
  - avoid `shell=True`.
  - argument-list subprocess invocation.
  - Bandit + Semgrep in static lane.

### Secret Exposure

- Mitigations:
  - prefer `1psa` secret retrieval over hardcoded values.
  - detect-secrets baseline and gitleaks scan in static lane.
  - encrypted backup artifacts via GPG flow in DB backup/restore scripts.

### Supply-Chain Drift

- Mitigations:
  - hash-pinned lockfiles.
  - CycloneDX SBOM generation and signature scaffolding.
  - dependency freshness and vulnerability lanes.

### Destructive DB Operations

- Mitigations:
  - explicit confirmation prompts for destroy paths.
  - profile-aware target resolution and validation.
  - identifier validation before SQL drop/alter paths.

## Residual Risks

- Local execution model means host compromise remains out of scope.
- Some security lanes depend on platform tooling availability.
- Temporary pip-audit CVE ignores are tracked separately and must be removed by review date.
