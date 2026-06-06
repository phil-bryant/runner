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
Design: `verify_numbered_test_traceability` enforces a 1:1 mapping between requirement bullets and test tags and that tags sit inside executable test blocks (gated by `STRICT_TRACEABILITY_NUMBERED_TAGS`).
Tests:
- R020-T01: Verify a missing numbered test tag fails the 1:1 check.

R025  Statement: Requirements-only docs skip source/test traceability.
Design: `is_requirements_only_mode` recognizes `Requirements-only mode: true` in Scope so inventory docs are not held to source/test mapping.
Tests:
- R025-T01: Verify a requirements-only doc is detected.

R030  Statement: Repository software files must be covered by requirements docs.
Design: `verify_repository_source_requirements_coverage` fails when a software file has no requirements doc (gated by `STRICT_TRACEABILITY_FULL_COVERAGE`).
Tests:
- R030-T01: Verify an uncovered software file is reported when coverage is enabled.

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

R060  Statement: The per-function requirement-tag gate is enforced by default.
Design: `verify_function_tag_coverage` reports every analyzable function lacking a scoped requirement tag as `file:line: name`. It is enforced by default (`STRICT_TRACEABILITY_FUNCTION_TAGS` defaults to on; set it to `false` to opt out) and honors an optional baseline allowlist (`_load_function_tag_baseline`) so a repo can fail only on newly-introduced untagged functions.
Tests:
- R060-T01: Verify the gate enforces by default (unset env) and is disabled only by an explicit `false`.
- R060-T02: Verify an enabled gate fails listing an untagged function, and a baseline entry suppresses its listing.

## Changelog
- 2026-06-06: Added R060 (opt-in per-function tag-coverage gate with baseline ratchet).
- 2026-06-06: Removed the exclude-source env knob and the `verification.py` self-exclusion (R055); engine self-coverage is now unconditional (anti-cheat: no self-exemption).

- 2026-06-06: Created. R040/R045 add unconditional, non-disablable mandatory tag-text enforcement (anti-cheat: no env opt-out).
