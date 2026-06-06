# Traceability Engine Parsing Requirements

## Scope

Applies to `tests/py/traceability/parsing.py`, the tag/ID parsing primitives used
across the traceability engine (requirement IDs, source tags, scoped tags,
numbered test bullets/tags, and the strict tag-text detectors).

R001  Statement: Requirement IDs are parsed from requirements docs.
Design: `extract_requirement_ids` collects IDs from lines beginning with `Rxxx` (including dashed sub-IDs).
Tests:
- R001-T01: Verify requirement IDs are extracted from `Rxxx Statement:` lines.

R005  Statement: Source #R tag IDs are parsed from source text.
Design: `extract_source_ids` returns the set of `#Rxxx` IDs (scoped or bare) found anywhere in a source file.
Tests:
- R005-T01: Verify scoped and bare source tags both yield their IDs.

R010  Statement: Scoped source IDs are parsed distinctly from bare tags.
Design: `extract_scoped_source_ids` returns only IDs written in the scoped `#Rxxx: <text>` form.
Tests:
- R010-T01: Verify a scoped tag is returned while a bare tag is not.

R015  Statement: Numbered requirement test bullets are parsed per requirement.
Design: `extract_numbered_requirement_test_ids` reads `- Rxxx-Tnn:` bullets under `Tests:`, scoping them to the active requirement block.
Tests:
- R015-T01: Verify a `- Rxxx-Tnn:` bullet is bound to its requirement.

R020  Statement: Malformed numbered test bullets are reported.
Design: `verify_requirements_numbered_test_bullets` flags unnumbered or mismatched bullets under `Tests:` with line diagnostics.
Tests:
- R020-T01: Verify an unnumbered bullet under `Tests:` is reported.

R025  Statement: Numbered test tags must live inside executable test blocks.
Design: `extract_numbered_test_ids` extracts `#Rxxx-Tnn` tags from a test file and reports any tag found outside a `@test`/`def test*`/`func test*` body.
Tests:
- R025-T01: Verify a tag inside a bats `@test` block is collected and an outside tag is flagged.

R030  Statement: Bare source #R tags without scoped text are detectable.
Design: `find_unscoped_source_tags` returns line diagnostics for `#Rxxx` source tags missing the `: <text>` scope, ignoring numbered test tags.
Tests:
- R030-T01: Verify a bare `#Rxxx` is reported while `#Rxxx: text` is not.

R035  Statement: Bare numbered test tags without scoped text are detectable.
Design: `find_unscoped_numbered_test_tags` returns line diagnostics for `#Rxxx-Tnn` tags missing the `: <text>` scope.
Tests:
- R035-T01: Verify a bare `#Rxxx-Tnn` is reported while `#Rxxx-Tnn: text` is not.

## Changelog

- 2026-06-06: Created; added the strict tag-text detectors (R030/R035) backing the unconditional mandatory-text enforcement.
