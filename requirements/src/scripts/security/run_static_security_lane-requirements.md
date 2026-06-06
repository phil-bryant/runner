# Static Security Lane Requirements

## Scope

Applies to `src/scripts/security/run_static_security_lane.sh`.

R001  Statement: Print an explicit startup banner before scanner orchestration.
Design: Define `print_tool_header` to render a bordered per-tool intro banner used before each scanner runs.
Tests:
- R001-T01: Verify the lane defines a `print_tool_header` banner helper.

R005  Statement: Resolve the repo root and execute under strict shell settings.
Design: Run with `set -euo pipefail` and call `security_init_repo_root` to operate from the resolved repository root.
Tests:
- R005-T01: Verify strict-mode shell settings and `security_init_repo_root` invocation.

R010  Statement: Bootstrap an isolated security toolchain venv before scans.
Design: `ensure_security_venv` creates a dedicated `python3 -m venv` security environment before SAST scanners run.
Tests:
- R010-T01: Verify the lane creates an isolated security venv before scanning.

R015  Statement: Default to SAST-on, DAST-off lane behavior.
Design: Default `RUN_SAST=true` and `RUN_DAST=false` so the static lane runs SAST by default.
Tests:
- R015-T01: Verify the `RUN_SAST`/`RUN_DAST` default toggles.

R020  Statement: Print completion markers and the report artifact location.
Design: Emit a final completion message that includes the resolved report directory.
Tests:
- R020-T01: Verify the lane prints a completion marker with the report path.

R025  Statement: Execute Ruff and persist `ruff.json` into report artifacts.
Design: `run_ruff_sast` runs `ruff check` and writes results to the Ruff report artifact.
Tests:
- R025-T01: Verify the lane runs Ruff and persists its report.

R030  Statement: Include Ruff findings in the centralized blocking SAST gate.
Design: Feed all scanner reports, including Ruff, into the consolidated `sast_summary_gate.py` blocking gate.
Tests:
- R030-T01: Verify the lane invokes the consolidated SAST summary gate.

R035  Statement: Exclude generated cache/report paths from secret scanning.
Design: Exclude generated artifacts such as `__pycache__`, `.ruff_cache`, and `artifacts/cache` from detect-secrets scan input.
Tests:
- R035-T01: Verify generated cache paths are excluded from secret-scan input.

R040  Statement: Run gitleaks against a tracked-source snapshot input.
Design: `run_gitleaks_sast` copies git-tracked files into a snapshot directory and runs `gitleaks detect --source` against it.
Tests:
- R040-T01: Verify gitleaks runs against a tracked-source snapshot directory.

R045  Statement: Emit detailed Semgrep status in unsuppressed runs.
Design: After Semgrep runs, print a detailed status line with exit code, findings, and report path.
Tests:
- R045-T01: Verify the lane prints a detailed Semgrep status line.

R047  Statement: Invoke Semgrep without a `--quiet` suppression flag.
Design: Run `semgrep scan` with explicit argument control and no quiet-mode flag so findings are not suppressed.
Tests:
- R047-T01: Verify the Semgrep invocation omits a `--quiet` suppression flag.

R050  Statement: Emit detailed Bandit status in unsuppressed runs.
Design: After Bandit runs, print a detailed status line with exit code, findings, and report path.
Tests:
- R050-T01: Verify the lane prints a detailed Bandit status line.

R055  Statement: Emit detailed pip-audit status in unsuppressed runs.
Design: After pip-audit runs, print a detailed status line with exit code, vulnerabilities, and report path.
Tests:
- R055-T01: Verify the lane prints a detailed pip-audit status line.

R060  Statement: Emit detailed detect-secrets status in unsuppressed runs.
Design: After detect-secrets runs, print a detailed status line with exit code, findings, and report path.
Tests:
- R060-T01: Verify the lane prints a detailed detect-secrets status line.

R065  Statement: Emit detailed Ruff status in unsuppressed runs.
Design: After Ruff runs, print a detailed status line with exit code, findings, and report path.
Tests:
- R065-T01: Verify the lane prints a detailed Ruff status line.

R070  Statement: Emit detailed ShellCheck status in unsuppressed runs.
Design: After ShellCheck runs, print a detailed status line with exit code, findings, and report path.
Tests:
- R070-T01: Verify the lane prints a detailed ShellCheck status line.

R080  Statement: Keep `__pycache__` under `artifacts/cache` via the shared cache env.
Design: Rely on the shared cache-env contract and exclude `artifacts/cache`/`__pycache__` from scan inputs.
Tests:
- R080-T01: Verify cache paths under `artifacts/cache` and `__pycache__` are treated as generated.

R090  Statement: Enforce a medium-or-higher blocker policy across scanners.
Design: Default the financial-app policy to block medium-or-higher findings and pass the `medium` threshold into the consolidated gate.
Tests:
- R090-T01: Verify the lane enforces a medium-or-higher blocking threshold.

R100  Statement: Redact persisted Schemathesis token-bearing artifacts.
Design: Use `redact_secret_in_file`/`redact_secret_in_place` to persist only token-redacted artifacts.
Tests:
- R100-T01: Verify token-bearing artifacts are redacted before persistence.

R105  Statement: Enforce hash-pinned security requirements for toolchain bootstrap.
Design: Install the security toolchain with `pip install --require-hashes -r <security requirements>`.
Tests:
- R105-T01: Verify toolchain install uses `--require-hashes`.

R110  Statement: Emit SBOM + signing scaffold artifacts for supply-chain visibility.
Design: `generate_supply_chain_artifacts` produces SBOM and signing scaffold artifacts, presence-gated on hash-pinned lockfiles.
Tests:
- R110-T01: Verify the lane invokes supply-chain artifact generation.

R115  Statement: Default supply-chain signing mode to required in CI.
Design: When the signing-mode knob is unset, default it to `required` under CI and `scaffold` otherwise.
Tests:
- R115-T01: Verify the CI default sets the signing mode to `required`.

R120  Statement: Enforce a secure pip baseline before dependency vulnerability scanning.
Design: `enforce_pip_audit_secure_baseline` requires the pip-audit target interpreter to meet `PIP_AUDIT_MIN_SECURE_PIP_VERSION` before pip-audit runs.
Tests:
- R120-T01: Verify the lane enforces a secure pip baseline before pip-audit.
