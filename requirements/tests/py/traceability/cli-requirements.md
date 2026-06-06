# Traceability Engine CLI Requirements

## Scope

Applies to `tests/py/traceability/cli.py`, the command-line entry point of the
runner traceability engine invoked by the lane wrapper as
`python3 -m traceability.cli`.

R001  Statement: CLI resolves its arguments, defaulting to the process argv.
Design: `main(argv)` uses the provided list, or `sys.argv[1:]` when `argv` is `None`, and forwards them to the verifier's `run`.
Tests:
- R001-T01: Verify `main(["--help"])` forwards the flag and returns success.

R005  Statement: CLI treats the current working directory as the repo under test.
Design: `main` constructs `TraceabilityVerifier(repo_root=Path.cwd())` so the lane checks whatever repository it is run from.
Tests:
- R005-T01: Verify `main([])` run from an empty directory fails (no requirements docs found there).

R010  Statement: CLI propagates the verifier's status as the process exit code.
Design: The module entry point raises `SystemExit(main())`, and `main` returns the verifier's boolean result mapped to `0`/`1`.
Tests:
- R010-T01: Verify `main` returns `0` on success and `1` on failure.

## Changelog

- 2026-06-06: Created so the traceability engine self-traces its own CLI entry point.
