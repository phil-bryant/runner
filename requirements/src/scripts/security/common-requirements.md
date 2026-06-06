# Security Common Helpers Requirements

## Scope

Applies to `src/scripts/security/common.sh`.

R001  Statement: Helpers provide explicit security-lane startup messaging contracts.
Design: `print_tool_header` renders deterministic bordered tool intro output for lane operators.
Tests:
- R001-T01: Source helper file and verify `print_tool_header` function is defined.

R005  Statement: Helpers resolve and initialize repository execution context.
Design: `security_init_repo_root` derives repo root from script path, changes into root, and exports `SECURITY_REPO_ROOT`.
Tests:
- R005-T01: Verify `security_init_repo_root` function is defined and references `SECURITY_REPO_ROOT`.

R010  Statement: Helpers enforce command/file/toolchain preconditions.
Design: `python_interpreter_usable`, `require_command`, and `require_file` provide reusable prerequisite checks.
Tests:
- R010-T01: Verify prerequisite helper functions are defined in source.

R015  Statement: Helpers support default lane toggle handling in callers.
Design: Common helper surface includes reusable lane setup primitives expected by lane scripts.
Tests:
- R015-T01: Verify lane setup helper signatures are present in source.

R020  Statement: Helpers provide common status formatting primitives.
Design: Shared helper output functions emit deterministic status/log formatting for lane tools.
Tests:
- R020-T01: Verify status-format helper functions are present in source.

R025  Statement: Helpers support scanner orchestration utility flow.
Design: Shared shell helpers expose reusable scanner command assembly and invocation helpers.
Tests:
- R025-T01: Verify scanner orchestration helper functions are present in source.

R030  Statement: Helpers provide reusable gate plumbing for blocker policy checks.
Design: Shared helper functions include gate-oriented wrappers used by static/dynamic security lanes.
Tests:
- R030-T01: Verify gate/helper plumbing functions are present in source.

R035  Statement: Helpers support exclusion-aware command invocation.
Design: Helper library includes command wrappers that support exclusion-aware scanning.
Tests:
- R035-T01: Verify exclusion-aware helper signatures are present in source.

R040  Statement: Helpers support tracked-source scan command construction.
Design: Shared helper surface includes tracked-source enumeration utilities for scanner inputs.
Tests:
- R040-T01: Verify tracked-source helper signatures are present in source.

R045  Statement: Helpers support Semgrep status formatting.
Design: Common helper functions include Semgrep-specific status/report formatting routines.
Tests:
- R045-T01: Verify Semgrep status helper signatures are present in source.

R047  Statement: Helpers support Semgrep invocation wiring.
Design: Semgrep helper wiring runs with explicit argument control and no quiet-mode suppression.
Tests:
- R047-T01: Verify Semgrep invocation helper signatures are present in source.

R050  Statement: Helpers support Bandit status/report output.
Design: Common helper functions include Bandit-specific report handling paths.
Tests:
- R050-T01: Verify Bandit helper signatures are present in source.

R055  Statement: Helpers support pip-audit status/report output.
Design: Common helper functions include pip-audit-specific report handling paths.
Tests:
- R055-T01: Verify pip-audit helper signatures are present in source.

R060  Statement: Helpers support detect-secrets status/report output.
Design: Common helper functions include detect-secrets-specific report handling paths.
Tests:
- R060-T01: Verify detect-secrets helper signatures are present in source.

R065  Statement: Helpers support Ruff status/report output.
Design: Common helper functions include Ruff-specific report handling paths.
Tests:
- R065-T01: Verify Ruff helper signatures are present in source.

R070  Statement: Helpers support ShellCheck status/report output.
Design: Common helper functions include ShellCheck-specific report handling paths.
Tests:
- R070-T01: Verify ShellCheck helper signatures are present in source.

R080  Statement: Helpers export deterministic Python bytecode cache path.
Design: Security helper setup sources cache-env script and exports cache path under `artifacts/cache`.
Tests:
- R080-T01: Verify helper source references cache-env export integration.

R090  Statement: Helpers support medium-or-higher gate plumbing.
Design: Common helper surface includes reusable severity-threshold gate logic.
Tests:
- R090-T01: Verify medium-or-higher gate helper signatures are present in source.

R100  Statement: Helpers provide secret redaction for persisted artifacts.
Design: `redact_secret_in_file` and `redact_secret_in_place` sanitize persisted content before archival.
Tests:
- R100-T01: Verify redaction helper functions are present in source.

R105  Statement: Helpers enforce hash-pinned toolchain requirements.
Design: `require_command` guidance references hash-pinned install command using security requirements file.
Tests:
- R105-T01: Verify helper source references hash-pinned requirements install guidance.

R110  Statement: Helpers support supply-chain artifact generation wiring.
Design: Common helper surface includes reusable functions consumed by SBOM/signing orchestration scripts.
Tests:
- R110-T01: Verify supply-chain helper signatures are present in source.

R115  Statement: Helpers preserve CI-default required-signing behavior.
Design: Common helper setup exposes primitives consumed by static lane CI-required signing policy.
Tests:
- R115-T01: Verify CI signing policy helper signatures are present in source.

## Changelog

- 2026-06-02: Added reverse-engineered traceability requirements for shared security helper library.
- 2026-06-06: Recovered into runner requirements tree from classy provenance.
