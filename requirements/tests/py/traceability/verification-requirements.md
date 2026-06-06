# Traceability Engine Verification Requirements

## Scope

Applies to `tests/py/traceability/verification.py`, the orchestration and check
logic of the runner traceability engine (strict tag matching, scoped-comment and
anti-cheat enforcement, test traceability, coverage, requirements-only handling,
and the unconditional mandatory tag-text rules).

R001  Statement: Requirement IDs and source #R tags must match 1:1.
Design: `verify_strict_pair` fails when a requirement has no source tag or a source tag has no requirement.
Tests:
- R001-T01: Verify a missing or extra #R tag fails the strict pair check.

R005  Statement: Every requirement needs a scoped #R comment in source.
Design: `verify_scoped_traceability_comments` requires a `#Rxxx:` scoped comment per requirement ID.
Tests:
- R005-T01: Verify a requirement lacking a scoped comment fails.

R010  Statement: Header-level bundled #R tags are rejected (anti-cheat).
Design: `verify_single_pair` uses `detect_header_bundle_tags` to fail sources that list many #R tags in a single header line instead of scoped per-block tags.
Tests:
- R010-T01: Verify a bundled header tag line is rejected.

R015  Statement: Every requirement must have at least one tagged test.
Design: `verify_requirements_test_traceability` fails when a requirement ID has no `#Rxxx` tag in any discovered test file.
Tests:
- R015-T01: Verify a requirement with no tagged test is reported.

R020  Statement: Numbered #Rxxx-Tnn tags must be 1:1 and well-placed.
Design: `verify_numbered_test_traceability` unconditionally enforces a 1:1 mapping between requirement bullets and test tags and that tags sit inside executable test blocks; there is intentionally no runtime env knob to weaken it.
Tests:
- R020-T01: Verify a missing numbered test tag fails the 1:1 check.

R025  Statement: Requirements-only docs skip source/test traceability.
Design: `is_requirements_only_mode` recognizes `Requirements-only mode: true` in Scope so inventory docs are not held to source/test mapping.
Tests:
- R025-T01: Verify a requirements-only doc is detected.

R030  Statement: Repository software files must be covered by requirements docs.
Design: `verify_repository_source_requirements_coverage` unconditionally fails when a software file has no requirements doc; there is intentionally no runtime env knob to skip this coverage gate.
Tests:
- R030-T01: Verify an uncovered software file is reported.

R035  Statement: The engine aggregates per-doc and global checks into a verdict.
Design: `verify_all_requirements` runs every doc plus the global coverage/alignment checks and prints a `pass/fail` summary, returning overall status.
Tests:
- R035-T01: Verify the aggregate verdict reflects a failing doc.

R040  Statement: Source #R tags must include scoped requirement text — always on.
Design: `verify_source_tag_text_strictness` fails any source file containing a bare `#Rxxx` tag that lacks `: <text>`. This enforcement is unconditional and non-disablable: there is intentionally no environment knob to turn it off, so the standard cannot be quietly lowered by a future change.
Tests:
- R040-T01: Verify a bare source tag fails with no way to opt out.

R045  Statement: Numbered #Rxxx-Tnn test tags must include scoped text — always on.
Design: `verify_numbered_test_tag_text` fails any discovered test file whose numbered `#Rxxx-Tnn` tags lack `: <text>`. Like R040 this is unconditional and non-disablable (no env knob), running independently of the numbered-tag coverage knobs.
Tests:
- R045-T01: Verify a bare numbered test tag fails with no way to opt out.

R050  Statement: Requirements-only mode must not bypass enforcement for in-repo goldens.
Design: `_handle_requirements_only` (via `_is_legitimate_requirements_only`/`_has_mappable_in_repo_source`) treats `Requirements-only mode: true` as legitimate only when the doc has no mappable first-party in-repo source. If a real source file exists in the repo, the doc fails closed and must be fully traced; cross-repo delegation is documented with thin pointer docs instead. This closes the loophole where real code hid behind requirements-only.
Tests:
- R050-T01: Verify a requirements-only doc with an existing in-repo source fails.
- R050-T02: Verify a requirements-only doc with no mappable in-repo source is a legitimate skip.

R055  Statement: Engine self-coverage is unconditional — no exclude-source escape hatch.
Design: `verify_repository_source_requirements_coverage` builds the coverage universe with `list_repository_software_files(repo_root)` and grants no self-exemption: there is no exclude-source env knob and no `__file__` self-exclusion of `verification.py`. The engine's own sources (wrapper + every `tests/py/traceability/*.py`) are force-included via `list_traceability_engine_files`, so the engine is held to its own coverage standard like any other source.
Tests:
- R055-T01: Verify the wrapper and engine modules (including verification.py) are in the coverage universe with no exclusion argument.

R060  Statement: The per-function requirement-tag gate is unconditional (no opt-out, no baseline suppression).
Design: `verify_function_tag_coverage` reports every analyzable function lacking a scoped requirement tag as `file:line: name`. This enforcement is always on: `STRICT_TRACEABILITY_FUNCTION_TAGS` and `TRACEABILITY_FUNCTION_TAG_BASELINE` are intentionally unsupported so the standard cannot be quietly weakened.
Tests:
- R060-T01: Verify the gate fails on an untagged function.
- R060-T02: Verify legacy opt-out/baseline env knobs do not weaken the gate.

R070  Statement: Every #Rxxx-Tnn test tag must be anchored to a parser-recognized executable test definition.
Design: `verify_numbered_test_tag_anchoring` walks each discovered test file and, via `find_unanchored_numbered_test_tags`, fails when any `#Rxxx-Tnn` tag is not inside a parser-enumerated executable test block (Python `def test_*` via the stdlib `ast`; bats `@test`/swift `func test*` via tree-sitter) — the same ast/tree-sitter methodology the per-function tag-coverage gate (R060) uses to recognize a genuine function definition. This closes the prior hole where test files in languages with no parseable test-block convention accepted numbered tags from anywhere: such files now fail closed when they carry numbered tags. The gate is unconditional with no env opt-out.
Tests:
- R070-T01: Verify a numbered tag anchored inside a real test block passes the gate.
- R070-T02: Verify a numbered tag placed outside any test block (module top-level) fails the gate.
- R070-T03: Verify a test file in a language with no parseable test-block convention fails closed when it carries a numbered tag.

R100  Statement: Single-pair verification runs strict/source/test checks for one requirements-source pair.
Design: `verify_single_pair_with_tests` executes strict pair checks plus discovered-test traceability and numbered-tag checks.
Tests:
- R100-T01: Verify single-pair verification reports pass/fail by combining strict and discovered-test checks.

R105  Statement: Per-doc verification resolves source files and enforces all mapped checks.
Design: `verify_requirements_file_sources` resolves scope/analogous sources, verifies each, and runs doc-level test checks.
Tests:
- R105-T01: Verify per-doc source resolution and enforcement fail when mapped sources are missing.

R110  Statement: Numbered script docs and deprecated-path filtering are enforced.
Design: `verify_numbered_script_requirements_coverage` checks numbered scripts have numbered docs and `_is_deprecated_path` filters deprecated paths.
Tests:
- R110-T01: Verify numbered script coverage fails for missing docs and skips deprecated paths.

R115  Statement: Numbered requirements must scope-match numbered sources.
Design: `verify_numbered_requirement_scope_alignment` enforces NN requirement docs map to NN source prefixes.
Tests:
- R115-T01: Verify numbered requirement scope alignment fails on mismatched numbering.

R120  Statement: Numbered scripts require companion bats coverage.
Design: `verify_numbered_script_test_coverage` enforces `tests/sh/<stem>.bats` coverage for numbered scripts.
Tests:
- R120-T01: Verify numbered script test coverage fails when companion bats files are missing.

R125  Statement: Shared-runner source coverage credit requires byte-identical sources.
Design: `_collect_shared_runner_covered_sources`, `_discover_runner_root`, and `_files_identical` grant coverage only for identical sources.
Tests:
- R125-T01: Verify shared-runner coverage includes only byte-identical source files.

R130  Statement: Test-ID collection gathers #R ids and numbered ids from discovered tests.
Design: `collect_ids_from_test_list` and `collect_numbered_test_ids_from_list` aggregate ids and misplaced numbered tags.
Tests:
- R130-T01: Verify test-id collectors return aggregated ids and misplaced numbered-tag diagnostics.

R135  Statement: Locked-source detection and exception-policy validation are enforced.
Design: `is_locked_source_file` detects lock markers and `verify_locked_exception` enforces locked-policy requirements.
Tests:
- R135-T01: Verify lock markers are detected and locked-policy requirements are validated.

R140  Statement: CLI dispatch and usage handling map invocation shapes to verification outcomes.
Design: `run` and `print_usage` dispatch `argv` modes (help/all/single-pair) and return process-compatible exit codes.
Tests:
- R140-T01: Verify CLI dispatch and return-code mapping across help, all, and single-pair invocations.

R145  Statement: Path/inline helpers normalize repository-relative path handling and test list rendering.
Design: `_to_repo_path`, `_rel`, and `tests_inline_from_list` normalize path handling and discovered-test display strings.
Tests:
- R145-T01: Verify path normalization and inline test-list rendering behavior.

## Changelog
- 2026-06-06: Relocated R065 env-knob-surface contract from verification to discovery requirements; verification now carries CLI dispatch under R140.
- 2026-06-06: Added R070 (numbered-test-tag anchoring gate; every `#Rxxx-Tnn` tag must sit inside a parser-recognized executable test definition via `verify_numbered_test_tag_anchoring`, fail-closed for unparseable test-language files — closes the collect-tags-from-anywhere hole).
- 2026-06-06: Abolished weakening knobs (`STRICT_TRACEABILITY_FULL_COVERAGE`, `STRICT_TRACEABILITY_NUMBERED_TAGS`, `STRICT_TRACEABILITY_NUMBERED_BULLETS`, `STRICT_TRACEABILITY_FUNCTION_TAGS`, `TRACEABILITY_FUNCTION_TAG_BASELINE`); strict verification gates are now unconditional and R065 locks env surface to scope knobs only.
- 2026-06-06: Added R065 (weakening-knob surface contract lock; anti-footgun requires deliberate requirements+test updates for any knob-surface change).
- 2026-06-06: Added R060 (opt-in per-function tag-coverage gate with baseline ratchet).
- 2026-06-06: Removed the exclude-source env knob and the `verification.py` self-exclusion (R055); engine self-coverage is now unconditional (anti-cheat: no self-exemption).

- 2026-06-06: Created. R040/R045 add unconditional, non-disablable mandatory tag-text enforcement (anti-cheat: no env opt-out).
