from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterable


REQ_ID_PATTERN = re.compile(r"^R\d{3}(?:-\d{3})*")
REQ_LINE_PATTERN = re.compile(r"^(R\d{3}(?:-\d{3})*)\s+Statement:")
SOURCE_TAG_PATTERN = re.compile(r"#(R\d{3}(?:-\d{3})*)")
SCOPED_SOURCE_TAG_PATTERN = re.compile(r"#(R\d{3}(?:-\d{3})*):\s*[A-Za-z0-9_]")
NUMBERED_TEST_TAG_PATTERN = re.compile(r"#(R\d{3}(?:-\d{3})*-T\d{2})")
NUMBERED_BULLET_PATTERN = re.compile(r"^-\s+(R\d{3}(?:-\d{3})*)-T(\d{2})\s*:")
BACKTICK_TOKEN_PATTERN = re.compile(r"`([^`]+)`")

UI_HINT_PATTERN = re.compile(r"ui[\s-]*test|xcuitest|xctest[\s-]*ui|ui[\s-]*mode", flags=re.IGNORECASE)

ALLOWED_SCOPE_FILE_EXTS = {
    "sh",
    "py",
    "swift",
    "sql",
    "c",
    "cc",
    "cpp",
    "cxx",
    "m",
    "mm",
    "h",
    "hpp",
}
ALLOWED_SCOPE_FILENAMES = {"Makefile", ".gitignore"}

_BATS_START_RE = re.compile(
    r"^\s*(?:@test\b.*\{\s*$|bats_test_function\b.*\{\s*$|[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{\s*$)"
)
_PYTHON_START_RE = re.compile(r"^\s*def\s+test[_A-Za-z0-9]*\s*\(")
_SWIFT_START_RE = re.compile(r"^\s*func\s+test[_A-Za-z0-9]*\s*\(")


#R001: Extract requirement IDs from requirements docs (lines beginning `Rxxx`).
def extract_requirement_ids(text: str) -> list[str]:
    ids = set()
    for line in text.splitlines():
        match = REQ_ID_PATTERN.match(line)
        if match:
            ids.add(match.group(0))
    return sorted(ids)


#R005: Extract source #R tag IDs (scoped or bare) from a source file's text.
def extract_source_ids(text: str) -> list[str]:
    ids = {match.group(1) for match in SOURCE_TAG_PATTERN.finditer(text)}
    return sorted(ids)


#R010: Extract only scoped source IDs (the `#Rxxx: <text>` form, ignoring bare tags).
def extract_scoped_source_ids(text: str) -> list[str]:
    ids = {match.group(1) for match in SCOPED_SOURCE_TAG_PATTERN.finditer(text)}
    return sorted(ids)


#R100: shard-3 function tag
def detect_header_bundle_tags(text: str, max_lines: int = 40) -> str | None:
    for idx, raw_line in enumerate(text.splitlines()[:max_lines], start=1):
        total = len(SOURCE_TAG_PATTERN.findall(raw_line))
        scoped = len(re.findall(r"#R\d{3}(?:-\d{3})*:", raw_line))
        if total >= 3 and scoped == 0:
            return f"{idx}:{raw_line}"
    return None


#R105: shard-3 function tag
def extract_source_files_from_requirements(text: str) -> list[str]:
    files: set[str] = set()
    in_scope = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if stripped == "## Scope":
            in_scope = True
            continue
        if stripped.startswith("## ") and in_scope:
            in_scope = False
        if REQ_ID_PATTERN.match(stripped) and in_scope:
            in_scope = False
        if not in_scope:
            continue
        for match in BACKTICK_TOKEN_PATTERN.finditer(line):
            token = match.group(1)
            if token.startswith("./"):
                token = token[2:]
            path = Path(token)
            ext = path.suffix.lower().lstrip(".")
            if ext in ALLOWED_SCOPE_FILE_EXTS or token in ALLOWED_SCOPE_FILENAMES:
                files.add(token)
    return sorted(files)


#R110: shard-3 function tag
def extract_ui_required_ids(text: str) -> list[str]:
    ids = set()
    for line in text.splitlines():
        lowered = line.lower()
        if not re.match(r"^r\d{3}(?:-\d{3})*\s+statement:", lowered):
            continue
        rid = line.split(None, 1)[0].upper()
        if UI_HINT_PATTERN.search(lowered):
            ids.add(rid)
    return sorted(ids)


#R015: Parse numbered `- Rxxx-Tnn:` test bullets under `Tests:`, scoped to the
# requirement they belong to.
def extract_numbered_requirement_test_ids(text: str) -> list[str]:
    current_requirement_id: str | None = None
    in_tests = False
    ids: set[str] = set()
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        req_match = REQ_LINE_PATTERN.match(stripped)
        if req_match:
            current_requirement_id = req_match.group(1)
            in_tests = False
            continue
        if stripped == "Tests:":
            in_tests = True
            continue
        if in_tests and stripped.startswith("- "):
            match = NUMBERED_BULLET_PATTERN.match(stripped)
            if match and current_requirement_id and match.group(1) == current_requirement_id:
                ids.add(f"{match.group(1)}-T{match.group(2)}")
            continue
        if in_tests and stripped and not stripped.startswith("- "):
            in_tests = False
    return sorted(ids)


#R020: Validate numbered test bullets are well-formed and matched to their owning
# requirement (flag unnumbered/mismatched bullets under `Tests:`).
def verify_requirements_numbered_test_bullets(text: str, requirements_file: str) -> list[str]:
    current_requirement_id: str | None = None
    in_tests = False
    seen_numbers: dict[str, list[int]] = {}
    issues: list[str] = []
    for idx, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        req_match = REQ_LINE_PATTERN.match(stripped)
        if req_match:
            current_requirement_id = req_match.group(1)
            in_tests = False
            seen_numbers.setdefault(current_requirement_id, [])
            continue
        if stripped == "Tests:":
            in_tests = True
            continue
        if in_tests and stripped.startswith("- "):
            match = NUMBERED_BULLET_PATTERN.match(stripped)
            if not match:
                expected = ""
                if current_requirement_id:
                    next_number = len(seen_numbers.get(current_requirement_id, [])) + 1
                    expected = f" (expected prefix: {current_requirement_id}-T{next_number:02d})"
                issues.append(
                    f"{requirements_file}:{idx}: unnumbered/invalid test bullet under Tests:{expected}"
                )
                continue
            bullet_requirement_id = match.group(1)
            bullet_test_number = int(match.group(2))
            if current_requirement_id and bullet_requirement_id != current_requirement_id:
                issues.append(
                    f"{requirements_file}:{idx}: test bullet {bullet_requirement_id}-T{bullet_test_number:02d} does not match requirement {current_requirement_id}"
                )
                continue
            if current_requirement_id:
                seen_numbers[current_requirement_id].append(bullet_test_number)
            continue
        if in_tests and stripped and not stripped.startswith("- "):
            in_tests = False
    return issues


_TS_GET_PARSER = None  # None = not yet attempted, False = unavailable, else callable
_TS_PARSER_CACHE: dict[str, object] = {}


#R045: shard-3 function tag
def _treesitter_parser(language_name: str):
    """Return a cached tree-sitter parser for ``language_name``.

    Tree-sitter is mandatory for non-Python parser-backed checks. Missing or
    unusable parsers are hard errors so CI cannot silently ship weaker
    heuristics.
    """
    global _TS_GET_PARSER
    if _TS_GET_PARSER is None:
        try:
            from tree_sitter_language_pack import get_parser

            _TS_GET_PARSER = get_parser
        except Exception:
            _TS_GET_PARSER = False
    if _TS_GET_PARSER is False:
        raise RuntimeError(
            "tree_sitter_language_pack could not be imported; strict traceability parsing requires it."
        )
    if language_name not in _TS_PARSER_CACHE:
        try:
            _TS_PARSER_CACHE[language_name] = _TS_GET_PARSER(language_name)
        except Exception as exc:
            raise RuntimeError(
                f"tree_sitter_language_pack could not provide parser for '{language_name}'."
            ) from exc
    return _TS_PARSER_CACHE[language_name]


# The tree-sitter binding shipped by tree-sitter-language-pack exposes node
# accessors as methods (`kind()`, `start_position()`, `child(i)`), whereas the
# upstream python-tree-sitter exposes them as properties (`type`, `start_point`,
# `children`). These adapters normalize both so the detector is binding-agnostic.
_MISSING = object()


#R115: shard-3 function tag
def _ts_value(value):
    return value() if callable(value) else value


#R115: shard-3 function tag
def _ts_attr(obj, *names):
    for name in names:
        attr = getattr(obj, name, _MISSING)
        if attr is not _MISSING:
            return _ts_value(attr)
    return None


#R115: shard-3 function tag
def _point_row(point) -> int:
    if point is None:
        return 0
    row = getattr(point, "row", None)
    if row is not None:
        return row
    try:
        return point[0]
    except Exception:
        return 0


#R115: shard-3 function tag
def _ts_kind(node) -> str | None:
    return _ts_attr(node, "type", "kind")


#R115: shard-3 function tag
def _ts_children(node) -> list:
    children = getattr(node, "children", _MISSING)
    if children is not _MISSING and not callable(children):
        return list(children)
    count = _ts_attr(node, "child_count")
    if count is None:
        return list(children()) if callable(children) else []
    return [node.child(i) for i in range(count)]


#R115: shard-3 function tag
def _ts_node_name(node, source_bytes: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    text = getattr(name_node, "text", _MISSING)
    if text is not _MISSING:
        text = _ts_value(text)
        if isinstance(text, (bytes, bytearray)):
            return bytes(text).decode("utf-8", "replace")
        if text is not None:
            return str(text)
    start = _ts_attr(name_node, "start_byte")
    end = _ts_attr(name_node, "end_byte")
    if start is not None and end is not None:
        return source_bytes[start:end].decode("utf-8", "replace")
    return None


#R045: shard-3 function tag
def _ts_parse(parser, source_text: str):
    try:
        return parser.parse(source_text.encode("utf-8"))
    except TypeError:
        return parser.parse(source_text)


#R045: shard-3 function tag
def _treesitter_block_ranges(
    language_name: str, source_text: str, node_kinds: set[str], name_prefix: str | None = None
) -> list[tuple[int, int]] | None:
    spans = _treesitter_block_spans(language_name, source_text, node_kinds, name_prefix)
    return [(start, end) for _name, start, end in spans]


#R155: Include tree-sitter node names with parser-backed function spans.
def _treesitter_block_spans(
    language_name: str, source_text: str, node_kinds: set[str], name_prefix: str | None = None
) -> list[tuple[str | None, int, int]]:
    parser = _treesitter_parser(language_name)
    try:
        tree = _ts_parse(parser, source_text)
    except Exception as exc:
        raise RuntimeError(
            f"tree-sitter parse failed for language '{language_name}'."
        ) from exc
    source_bytes = source_text.encode("utf-8")
    spans: list[tuple[str | None, int, int]] = []
    stack = [_ts_attr(tree, "root_node")]
    while stack:
        node = stack.pop()
        if node is None:
            continue
        if _ts_kind(node) in node_kinds:
            name = _ts_node_name(node, source_bytes)
            if name_prefix is None or (name is not None and name.startswith(name_prefix)):
                spans.append(
                    (
                        name,
                        _point_row(_ts_attr(node, "start_point", "start_position")) + 1,
                        _point_row(_ts_attr(node, "end_point", "end_position")) + 1,
                    )
                )
        stack.extend(_ts_children(node))
    return spans


#R120: shard-3 function tag
def _brace_ranges(lines: list[str], start_re: re.Pattern[str]) -> list[tuple[int, int]]:
    """Fallback block detector: brace-balanced ranges started by ``start_re``.

    Reproduces the legacy heuristic for use when tree-sitter is unavailable.
    """
    ranges: list[tuple[int, int]] = []
    in_block = False
    depth = 0
    start = 0
    for idx, line in enumerate(lines, start=1):
        if not in_block and start_re.search(line):
            in_block = True
            depth = 0
            start = idx
        if in_block:
            depth += line.count("{")
            depth -= line.count("}")
            if depth <= 0:
                ranges.append((start, idx))
                in_block = False
                depth = 0
    if in_block:
        ranges.append((start, len(lines)))
    return ranges


#R120: shard-3 function tag
def _python_indentation_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """Fallback block detector for unparseable Python (SyntaxError)."""
    ranges: list[tuple[int, int]] = []
    in_block = False
    block_indent = 0
    start = 0
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" \t"))
        if not in_block:
            if _PYTHON_START_RE.search(line):
                in_block = True
                block_indent = indent
                start = idx
            continue
        if stripped and indent <= block_indent and not _PYTHON_START_RE.search(line):
            ranges.append((start, idx - 1))
            in_block = False
            if _PYTHON_START_RE.search(line):
                in_block = True
                block_indent = indent
                start = idx
    if in_block:
        ranges.append((start, len(lines)))
    return ranges


#R125: shard-3 function tag
def _python_test_block_ranges(text: str, lines: list[str]) -> list[tuple[int, int]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _python_indentation_ranges(lines)
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            end = getattr(node, "end_lineno", None) or node.lineno
            ranges.append((node.lineno, end))
    return ranges


_BATS_TEST_DECL_RE = re.compile(r"^(\s*)(?:@test\b.*|bats_test_function\b.*)\{\s*$")


#R130: shard-3 function tag
def _bats_to_bash(text: str) -> str:
    """Rewrite bats ``@test "..." {`` headers into valid bash function decls.

    The rewrite is line-preserving (same number of lines, replacement stays on
    the original line) so tree-sitter node rows map 1:1 back to source lines.
    """
    out_lines: list[str] = []
    for line in text.splitlines():
        match = _BATS_TEST_DECL_RE.match(line)
        if match:
            out_lines.append(f"{match.group(1)}function _bats_test_shim() {{")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


#R130: shard-3 function tag
def _bats_test_block_ranges(text: str, lines: list[str]) -> list[tuple[int, int]]:
    ranges = _treesitter_block_ranges("bash", _bats_to_bash(text), {"function_definition"})
    if ranges is None:
        raise RuntimeError("tree-sitter did not return bats test block ranges.")
    return ranges


#R135: shard-3 function tag
def _swift_test_block_ranges(text: str, lines: list[str]) -> list[tuple[int, int]]:
    ranges = _treesitter_block_ranges("swift", text, {"function_declaration"}, name_prefix="test")
    if ranges is None:
        raise RuntimeError("tree-sitter did not return swift test block ranges.")
    return ranges


#R140: shard-3 function tag
def _test_block_line_ranges(suffix: str, text: str, lines: list[str]) -> list[tuple[int, int]] | None:
    """Inclusive (start_line, end_line) ranges of test bodies for ``suffix``.

    Returns ``None`` for languages with no defined test-block convention, which
    signals "collect tags anywhere, enforce no placement" to the caller.
    """
    if suffix == ".py":
        return _python_test_block_ranges(text, lines)
    if suffix == ".bats":
        return _bats_test_block_ranges(text, lines)
    if suffix == ".swift":
        return _swift_test_block_ranges(text, lines)
    return None


#R145: shard-3 function tag
def _numbered_tags_by_line(lines: list[str]) -> list[tuple[int, str]]:
    tags: list[tuple[int, str]] = []
    for idx, line in enumerate(lines, start=1):
        for match in NUMBERED_TEST_TAG_PATTERN.finditer(line):
            tags.append((idx, match.group(1)))
    return tags


#R145: shard-3 function tag
def _line_in_ranges(ranges: list[tuple[int, int]], line_number: int) -> bool:
    return any(start <= line_number <= end for start, end in ranges)


#R025: Extract numbered `#Rxxx-Tnn` tags from a test file and enforce that they
# live inside executable test blocks (reporting misplaced tags). Test-block
# boundaries come from a parser (Python `ast`; bats/swift via tree-sitter) so
# braces/dedents inside strings, comments, and heredocs no longer mislead the
# detector; languages with no block convention collect tags without placement.
def extract_numbered_test_ids(test_file: Path) -> tuple[list[str], list[str]]:
    if not test_file.exists():
        return [], []

    text = test_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    tags = _numbered_tags_by_line(lines)
    ranges = _test_block_line_ranges(test_file.suffix.lower(), text, lines)

    ids: set[str] = set()
    misplaced: list[str] = []
    if ranges is None:
        for _line_number, tag in tags:
            ids.add(tag)
        return sorted(ids), misplaced

    for line_number, tag in tags:
        if _line_in_ranges(ranges, line_number):
            ids.add(tag)
        else:
            misplaced.append(f"{test_file}:{line_number}: #{tag}")
    return sorted(ids), misplaced


#R050: Detect numbered #Rxxx-Tnn tags that are not anchored to a real,
# parser-recognized executable test definition. Reuses the same test-block
# enumeration as placement detection (`_test_block_line_ranges`: Python via the
# stdlib `ast`; bats/swift via tree-sitter). Fails closed for test files whose
# language has no parseable test-block convention: any numbered tag in such a
# file is reported as unanchored rather than silently accepted from anywhere. A
# file with no numbered tags yields no findings.
def find_unanchored_numbered_test_tags(
    test_file: Path, text: str | None = None
) -> list[tuple[int, str, str]]:
    if text is None:
        if not test_file.is_file():
            return []
        text = test_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    tags = _numbered_tags_by_line(lines)
    if not tags:
        return []
    ranges = _test_block_line_ranges(test_file.suffix.lower(), text, lines)
    if ranges is None:
        reason = f"no parseable test definitions in '{test_file.suffix}' test file"
        return [(line_number, tag, reason) for line_number, tag in tags]
    issues: list[tuple[int, str, str]] = []
    for line_number, tag in tags:
        if not _line_in_ranges(ranges, line_number):
            issues.append((line_number, tag, "not inside a parser-recognized test definition"))
    return issues


_ANY_SOURCE_TAG_PATTERN = re.compile(r"#(R\d{3}(?:-\d{3})*)(-T\d{2})?")
_SCOPED_SUFFIX_PATTERN = re.compile(r":\s*\S")


#R030: Locate bare source #R tags that omit scoped requirement text (strictness).
def find_unscoped_source_tags(text: str) -> list[str]:
    """Locate source #Rxxx tags that carry no scoped requirement text.

    A compliant source tag is the scoped form ``#Rxxx: <text>``; a bare ``#Rxxx``
    with nothing meaningful after it is reported as ``<line>:<tag>``. Numbered
    test tags (``#Rxxx-Tnn``) are intentionally ignored here; see
    :func:`find_unscoped_numbered_test_tags`.
    """
    issues: list[str] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for match in _ANY_SOURCE_TAG_PATTERN.finditer(line):
            if match.group(2):
                continue
            if not _SCOPED_SUFFIX_PATTERN.match(line[match.end():]):
                issues.append(f"{idx}:{match.group(0)}")
    return issues


#R035: Locate numbered #Rxxx-Tnn test tags that omit scoped text (strictness).
def find_unscoped_numbered_test_tags(text: str) -> list[str]:
    """Locate numbered ``#Rxxx-Tnn`` test tags that carry no scoped text.

    A compliant numbered tag is ``#Rxxx-Tnn: <text>``; a bare ``#Rxxx-Tnn`` is
    reported as ``<line>:#<tag>``.
    """
    issues: list[str] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for match in NUMBERED_TEST_TAG_PATTERN.finditer(line):
            if not _SCOPED_SUFFIX_PATTERN.match(line[match.end():]):
                issues.append(f"{idx}:#{match.group(1)}")
    return issues


FUNCTION_TAG_PATTERN = re.compile(r"#R\d{3}(?:-\d{3})*(?:-T\d{2})?:\s*\S")

# Map source suffix -> (tree-sitter language, function node kinds). Python is
# handled separately via the stdlib ast. Languages with no enumerable function
# concept here (e.g. .sql) are intentionally absent and yield "unsupported".
_FUNCTION_TS_LANGS: dict[str, tuple[str, set[str]]] = {
    ".sh": ("bash", {"function_definition"}),
    ".bats": ("bash", {"function_definition"}),
    ".swift": ("swift", {"function_declaration"}),
    ".c": ("c", {"function_definition"}),
    ".h": ("c", {"function_definition"}),
    ".cc": ("cpp", {"function_definition"}),
    ".cpp": ("cpp", {"function_definition"}),
    ".cxx": ("cpp", {"function_definition"}),
    ".hpp": ("cpp", {"function_definition"}),
    ".m": ("objc", {"function_definition", "method_definition"}),
    ".mm": ("cpp", {"function_definition"}),
}

_FUNCTION_NAME_RE = re.compile(r"(?:func|function)?\s*([A-Za-z_][A-Za-z0-9_]*)\s*[\(\{]")
_OBJC_METHOD_NAME_RE = re.compile(r"^\s*[-+]\s*\([^)]*\)\s*([A-Za-z_][A-Za-z0-9_]*)")


#R150: shard-3 function tag
def _python_function_spans(text: str) -> list[tuple[str, int, int]] | None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    spans: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", None) or node.lineno
            spans.append((node.name, node.lineno, end))
    return spans


#R155: shard-3 function tag
def iter_function_spans(suffix: str, text: str) -> list[tuple[str, int, int]] | None:
    """Return ``(name, start_line, end_line)`` for every function in ``text``.

    Python uses the stdlib ``ast`` (all ``def``/``async def`` incl. nested,
    dunder and private); bash/bats/swift/c/cpp/objc use tree-sitter. Returns
    ``None`` for unsupported languages or when the source cannot be parsed.
    """
    suffix = suffix.lower()
    if suffix == ".py":
        return _python_function_spans(text)
    if suffix == ".mm":
        return _objective_cxx_function_spans(text)
    lang = _FUNCTION_TS_LANGS.get(suffix)
    if lang is None:
        return None
    language_name, node_kinds = lang
    parse_text = _bats_to_bash(text) if suffix == ".bats" else text
    ts_spans = _treesitter_block_spans(language_name, parse_text, node_kinds)
    lines = text.splitlines()
    spans: list[tuple[str, int, int]] = []
    for ts_name, start, end in ts_spans:
        spans.append((_resolved_function_name(ts_name, lines, start), start, end))
    return spans


#R155: Resolve function names from parser nodes and source-line fallbacks.
def _resolved_function_name(ts_name: str | None, lines: list[str], start: int) -> str:
    if ts_name:
        return ts_name
    if not (1 <= start <= len(lines)):
        return "<anonymous>"
    line = lines[start - 1]
    objc_match = _OBJC_METHOD_NAME_RE.search(line)
    if objc_match:
        return objc_match.group(1)
    match = _FUNCTION_NAME_RE.search(line)
    if match:
        return match.group(1)
    return "<anonymous>"


#R170: Enumerate Objective-C++ spans by unioning C++ and Objective-C parsers.
def _objective_cxx_function_spans(text: str) -> list[tuple[str, int, int]]:
    lines = text.splitlines()
    merged_by_start: dict[int, tuple[str, int, int]] = {}
    cpp_spans = _treesitter_block_spans("cpp", text, {"function_definition"})
    objc_spans = _treesitter_block_spans("objc", text, {"method_definition"})
    for ts_name, start, end in cpp_spans + objc_spans:
        resolved = _resolved_function_name(ts_name, lines, start)
        prior = merged_by_start.get(start)
        if prior is None or prior[0] == "<anonymous>" and resolved != "<anonymous>":
            merged_by_start[start] = (resolved, start, end)
    return [merged_by_start[start] for start in sorted(merged_by_start)]


#R160: shard-3 function tag
def _leading_comment_start(lines: list[str], start_line: int) -> int:
    """First line of the contiguous comment/decorator/blank block above a def.

    Matches the codebase convention of putting a ``#Rxxx:`` tag on the comment
    line(s) immediately above the function rather than inside its body.
    """
    first = start_line
    cursor = start_line - 1
    while cursor >= 1:
        stripped = lines[cursor - 1].strip()
        if stripped == "" or stripped.startswith(("#", "@", "//", "/*", "*")):
            first = cursor
            cursor -= 1
        else:
            break
    return first


#R160: shard-3 function tag
def function_is_tagged(lines: list[str], start_line: int, end_line: int) -> bool:
    lead = _leading_comment_start(lines, start_line)
    upper = min(end_line, len(lines))
    for line_number in range(lead, upper + 1):
        if FUNCTION_TAG_PATTERN.search(lines[line_number - 1]):
            return True
    return False


#R040: Detect functions that carry no scoped requirement tag (in their leading
# comment block or body), enumerating every function via ast/tree-sitter so the
# per-function tag-coverage gate can flag untagged functions; unsupported or
# unparseable files yield no findings.
def find_untagged_functions(path: Path, text: str | None = None) -> list[tuple[str, int]]:
    if text is None:
        if not path.is_file():
            return []
        text = path.read_text(encoding="utf-8")
    spans = iter_function_spans(path.suffix, text)
    if not spans:
        return []
    lines = text.splitlines()
    return [(name, start) for (name, start, end) in spans if not function_is_tagged(lines, start, end)]


#R165: shard-3 function tag
def format_bulleted(items: Iterable[str], prefix: str = "  - ") -> str:
    return "\n".join(f"{prefix}{item}" for item in items)
