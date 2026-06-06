# Traceability Engine Discovery Requirements

## Scope

Applies to `tests/py/traceability/discovery.py`, which locates requirements docs,
their declared source files, companion test files, and the repository software
universe used for coverage.

R001  Statement: Requirements roots are resolved with an override.
Design: `list_requirements_roots` defaults to `repo_root/requirements` and honors `TRACEABILITY_REQUIREMENTS_ROOTS` parsed as a colon/comma/newline separated list of absolute or repo-relative paths.
Tests:
- R001-T01: Verify the default root and a `TRACEABILITY_REQUIREMENTS_ROOTS` override are resolved.

R005  Statement: Requirements docs are discovered by glob.
Design: `list_requirements_files` recursively globs `*-requirements.md` under every requirements root and returns a sorted, de-duplicated list.
Tests:
- R005-T01: Verify a `*-requirements.md` file under a root is discovered.

R010  Statement: A doc's declared source files are read from its Scope section.
Design: `extract_source_files_from_requirements_path` parses backtick-quoted paths with allowed source extensions from the `## Scope` block.
Tests:
- R010-T01: Verify a backtick-quoted source path in Scope is extracted.

R015  Statement: Companion test files are discovered by convention.
Design: `discover_test_files_for_requirements` maps a doc/source set to `tests/sh/<stem>.bats`, `tests/py/test_<stem>.py`, and swift lanes by stem.
Tests:
- R015-T01: Verify a shell source maps to its `tests/sh/<stem>.bats` companion.

R020  Statement: The repository software universe applies exclusions.
Design: `list_repository_software_files` walks the repo for allowed source extensions while pruning vendored/generated/test trees and excluded paths.
Tests:
- R020-T01: Verify an excluded tree is omitted while a normal source file is included.

R025  Statement: The traceability engine self-includes its own sources for coverage.
Design: `list_traceability_engine_files` force-includes `tests/py/traceability/*.py` (excluding `__init__.py`) and the lane wrapper, and `list_repository_software_files` merges them so an undocumented engine module is flagged like any other untraced source.
Tests:
- R025-T01: Verify the engine modules and wrapper are present in the software universe.

R030  Statement: Per-function tag-coverage candidate files are enumerable.
Design: `list_function_tag_candidate_files` walks the repo for analyzable source and test extensions, pruning vendored/build/venv dirs and any nested git repository so an umbrella workspace does not sweep its subrepos.
Tests:
- R030-T01: Verify analyzable files are listed while an excluded dir and a nested git repo are pruned.

## Changelog

- 2026-06-06: Added R030 (candidate-file enumeration) for the opt-in per-function tag-coverage gate.
- 2026-06-06: Created with the self-coverage rule (R025) so the engine no longer silently excludes itself from coverage.
