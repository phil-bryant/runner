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
Design: `extract_numbered_test_ids` extracts `#Rxxx-Tnn` tags from a test file and reports any tag found outside a test body. Block boundaries come from a parser (Python via the stdlib `ast`; bats/swift via tree-sitter with a graceful brace-counting fallback), so braces or dedents inside strings, comments, and heredocs no longer mislead placement.
Tests:
- R025-T01: Verify a tag inside a bats `@test` block is collected and an outside tag is flagged.
- R025-T02: Verify ast collects a tag in a class test method and flags a module-level tag.
- R025-T03: Verify a dedented brace inside a Python multi-line string does not end the block.
- R025-T04: Verify an unparseable Python file falls back to the indentation scan without raising.
- R025-T05: Verify a stray brace inside a bats string does not close the block early.
- R025-T06: Verify swift closure/string braces do not end a test function early.

R030  Statement: Bare source #R tags without scoped text are detectable.
Design: `find_unscoped_source_tags` returns line diagnostics for `#Rxxx` source tags missing the `: <text>` scope, ignoring numbered test tags.
Tests:
- R030-T01: Verify a bare `#Rxxx` is reported while `#Rxxx: text` is not.

R035  Statement: Bare numbered test tags without scoped text are detectable.
Design: `find_unscoped_numbered_test_tags` returns line diagnostics for `#Rxxx-Tnn` tags missing the `: <text>` scope.
Tests:
- R035-T01: Verify a bare `#Rxxx-Tnn` is reported while `#Rxxx-Tnn: text` is not.

R040  Statement: Functions lacking a scoped requirement tag are detectable.
Design: `find_untagged_functions` enumerates every function (Python via `ast`; bash/bats/swift/c/cpp via tree-sitter through `iter_function_spans`) and reports those with no scoped `#Rxxx`/`#Rxxx-Tnn` tag in their leading comment block or body (`function_is_tagged`); unsupported or unparseable files yield no findings.
Tests:
- R040-T01: Verify an untagged function is reported while ones tagged above or inside the body are not.
- R040-T02: Verify private, nested, and dunder functions are enumerated (not exempt).
- R040-T03: Verify a syntax-error Python file and an unsupported suffix yield no findings.
- R040-T04: Verify tree-sitter languages (bash/swift) enumerate functions and flag untagged ones.

## Changelog

- 2026-06-06: Added R040 (per-function tag detection primitive) backing the opt-in function-tag-coverage gate.
- 2026-06-06: Created; added the strict tag-text detectors (R030/R035) backing the unconditional mandatory-text enforcement.
