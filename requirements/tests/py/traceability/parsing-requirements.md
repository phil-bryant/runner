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
Design: `extract_numbered_test_ids` extracts `#Rxxx-Tnn` tags from a test file and reports any tag found outside a test body. Block boundaries come from parsers (Python via stdlib `ast`; bats/swift via mandatory tree-sitter), so braces or dedents inside strings, comments, and heredocs no longer mislead placement.
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
Design: `find_untagged_functions` enumerates every function (Python via `ast`; bash/bats/swift/c/cpp via tree-sitter through `iter_function_spans`) and reports those with no scoped `#Rxxx`/`#Rxxx-Tnn` tag in their leading comment block or body (`function_is_tagged`); unsupported files yield no findings.
Tests:
- R040-T01: Verify an untagged function is reported while ones tagged above or inside the body are not.
- R040-T02: Verify private, nested, and dunder functions are enumerated (not exempt).
- R040-T03: Verify a syntax-error Python file and an unsupported suffix yield no findings.
- R040-T04: Verify tree-sitter languages (bash/swift) enumerate functions and flag untagged ones.

R045  Statement: Tree-sitter-backed traceability parsing is strict and non-disablable.
Design: `_treesitter_parser` and parser-backed helpers hard-fail when tree-sitter is unavailable or cannot parse a required language; there is intentionally no `STRICT_TRACEABILITY_TREESITTER` runtime knob and no downgrade fallback for tree-sitter-backed checks.
Tests:
- R045-T01: Verify parser-backed bats extraction raises when tree-sitter is unavailable.

R050  Statement: Numbered #Rxxx-Tnn tags must be anchored to a real, parser-recognized test definition.
Design: `find_unanchored_numbered_test_tags` enumerates parser-recognized executable test blocks via the same `_test_block_line_ranges` helper used for placement detection (Python `def test_*` via the stdlib `ast`; bats `@test`/swift `func test*` via tree-sitter) and reports any `#Rxxx-Tnn` tag not inside one. Test files whose language has no parseable test-block convention fail closed: every numbered tag in such a file is reported as unanchored rather than silently accepted from anywhere. A file with no numbered tags yields no findings.
Tests:
- R050-T01: Verify a numbered tag inside a real Python `def test_*` block is anchored while a module-level tag is reported.
- R050-T02: Verify a numbered tag inside a bats `@test` block is anchored while one outside any block is reported.
- R050-T03: Verify an unparseable test-language file with a numbered tag fails closed while a file with no numbered tags yields no findings.

R100  Statement: Header-bundled #R tags are detectable in early file headers.
Design: `detect_header_bundle_tags` scans leading lines and flags lines that bundle multiple bare tags.
Tests:
- R100-T01: Verify a header line with three bare tags is detected and a scoped tag line is ignored.

R105  Statement: Scope-listed source files are extracted from backtick paths.
Design: `extract_source_files_from_requirements` parses `## Scope` backtick tokens and filters to source extensions.
Tests:
- R105-T01: Verify scope extraction returns only allowed source paths from the Scope section.

R110  Statement: Frontend-hinted requirements are detectable from requirement statement text.
Design: `extract_ui_required_ids` identifies requirement statements carrying frontend hint phrases.
Tests:
- R110-T01: Verify UI-hinted statements are detected and non-UI statements are ignored.

R115  Statement: Tree-sitter adapter helpers normalize method/property node access.
Design: `_ts_value`, `_ts_attr`, `_point_row`, `_ts_kind`, `_ts_children`, and `_ts_node_name` normalize binding differences.
Tests:
- R115-T01: Verify adapter helpers normalize callable/property node forms.

R120  Statement: Fallback block-range detectors recover test ranges without tree-sitter.
Design: `_brace_ranges` and `_python_indentation_ranges` recover ranges using brace and indentation heuristics.
Tests:
- R120-T01: Verify brace and indentation fallback detectors return expected ranges.

R125  Statement: Python test-block range extraction uses ast with syntax-error fallback.
Design: `_python_test_block_ranges` uses stdlib `ast` and falls back to indentation scanning on `SyntaxError`.
Tests:
- R125-T01: Verify AST ranges are used for valid Python and indentation fallback handles syntax errors.

R130  Statement: Bats test headers are rewritten line-preservingly for parser-backed range extraction.
Design: `_bats_to_bash` rewrites bats declarations and `_bats_test_block_ranges` extracts parser-backed ranges.
Tests:
- R130-T01: Verify bats rewrite preserves line count and parser-backed ranges cover rewritten tests.

R135  Statement: Swift test block ranges are discovered by `test*` function prefix.
Design: `_swift_test_block_ranges` extracts `func test*` ranges via tree-sitter swift function declarations.
Tests:
- R135-T01: Verify swift test-prefixed functions are included and helper functions are excluded.

R140  Statement: Test-block range extraction dispatches by suffix and returns None when unsupported.
Design: `_test_block_line_ranges` dispatches Python/bats/swift detectors and returns `None` for unsupported suffixes.
Tests:
- R140-T01: Verify suffix dispatch returns ranges for supported types and `None` for unsupported ones.

R145  Statement: Numbered test tags are enumerable by line and line membership checks ranges.
Design: `_numbered_tags_by_line` collects numbered tags with line numbers and `_line_in_ranges` checks membership.
Tests:
- R145-T01: Verify numbered tags include source line numbers and range membership checks behave correctly.

R150  Statement: Python function spans enumerate all defs and return None on parse failure.
Design: `_python_function_spans` enumerates all function defs via ast and returns `None` on syntax errors.
Tests:
- R150-T01: Verify function-span enumeration includes nested/private/dunder defs and returns None on parse failure.

R155  Statement: Function-span enumeration dispatches per language and returns None when unsupported.
Design: `iter_function_spans` dispatches Python and parser-backed languages and returns `None` for unsupported suffixes.
Tests:
- R155-T01: Verify span dispatch returns results for Python and None for unsupported suffixes.

R160  Statement: Function tag-search windows include leading comment blocks and function bodies.
Design: `_leading_comment_start` and `function_is_tagged` compute the search window and detect scoped tags.
Tests:
- R160-T01: Verify a scoped tag in a leading comment block is detected and untagged functions are not.

R165  Statement: Bulleted rendering formats iterable items with configurable prefixes.
Design: `format_bulleted` renders each item with the provided bullet prefix.
Tests:
- R165-T01: Verify bulleted formatting for default and custom prefixes.

## Changelog

- 2026-06-06: Added R100-R165 parsing helper requirements for shard-3 function-level traceability coverage.
- 2026-06-06: Added R050 (`find_unanchored_numbered_test_tags`) backing the numbered-test-tag anchoring gate; tags must sit inside parser-recognized test definitions and unparseable test-language files fail closed.
- 2026-06-06: Added R045 and removed the `STRICT_TRACEABILITY_TREESITTER` opt-out; tree-sitter-backed parsing is now mandatory/non-disablable.
- 2026-06-06: Added R040 (per-function tag detection primitive) backing the function-tag-coverage gate.
- 2026-06-06: Created; added the strict tag-text detectors (R030/R035) backing the unconditional mandatory-text enforcement.
